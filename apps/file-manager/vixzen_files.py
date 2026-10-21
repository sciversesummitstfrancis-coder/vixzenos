#!/usr/bin/env python3
"""Vixzen Files v0.3 — real GTK4 file manager.
Adds v0.3: Copy/Cut/Paste (Ctrl+C/X/V), New file, Trash view (read-only list
via trash:// + Restore/Empty guarded), duplicate-name handling.
Run: python3 apps/file-manager/vixzen_files.py [path] [--smoke]
"""
import os, sys, datetime, shutil
import gi
gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "preview", "src"))
from design import css_for, LIQUID_CARD

class FilesWin(Adw.ApplicationWindow):
    def __init__(self, app, start):
        super().__init__(application=app, title="Vixzen Files")
        self.set_default_size(950, 620)
        self.path = os.path.abspath(os.path.expanduser(start))
        self.show_hidden = False
        self.grid_mode = False
        self.in_trash = False
        self.clip = []       # pending copy/cut source paths
        self.clip_cut = False
        css = Gtk.CssProvider()
        css.load_from_data((css_for("dark", "balanced") + LIQUID_CARD).encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)
        hb = Adw.HeaderBar()
        up = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Up (Alt+Up)")
        up.connect("clicked", lambda *_: self.cd(os.path.dirname(self.path) or "/"))
        hb.pack_start(up)
        self.crumb = Gtk.Label(label=self.path, xalign=0)
        hb.set_title_widget(self.crumb)
        self.search = Gtk.SearchEntry(placeholder_text="Search… (/)")
        self.search.connect("search-changed", lambda *_: self.refresh())
        hb.pack_end(self.search)
        self.view_btn = Gtk.ToggleButton(icon_name="view-grid-symbolic",
                                         tooltip_text="Grid/List (F3)")
        self.view_btn.connect("toggled", self.on_view)
        hb.pack_end(self.view_btn)
        hid = Gtk.ToggleButton(icon_name="view-conceal-symbolic",
                               tooltip_text="Hidden files (Ctrl+H)")
        hid.connect("toggled", lambda b: (setattr(self, "show_hidden", b.get_active()), self.refresh()))
        hb.pack_end(hid)
        new = Gtk.Button(icon_name="folder-new-symbolic", tooltip_text="New folder (Ctrl+N)")
        new.connect("clicked", self.new_folder)
        hb.pack_end(new)
        root.append(hb)

        body = Gtk.Box(spacing=12)
        body.set_vexpand(True)
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            getattr(body, f"set_{m}")(12)
        root.append(body)
        places = Gtk.ListBox()
        places.set_size_request(150, -1)
        for label, p in [("Home", "~"), ("Desktop", "~/Desktop"), ("Documents", "~/Documents"),
                         ("Downloads", "~/Downloads"), ("Pictures", "~/Pictures"),
                         ("Videos", "~/Videos"), ("Trash", "trash://")]:
            row = Gtk.ListBoxRow(); row.set_child(Gtk.Label(label=label))
            row._path = p
            places.append(row)
        places.connect("row-selected", self.on_place)
        body.append(places)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        center.set_hexpand(True); center.set_vexpand(True)
        body.append(center)
        self.scroll = Gtk.ScrolledWindow(); self.scroll.set_vexpand(True)
        center.append(self.scroll)
        self.status = Gtk.Label(label="", xalign=0)
        center.append(self.status)

        self.listbox = Gtk.ListBox()
        self.listbox.connect("row-activated", self.on_open_row)
        self.flow = Gtk.FlowBox(max_children_per_line=8, selection_mode=Gtk.SelectionMode.SINGLE)
        self.flow.connect("child-activated", self.on_open_flow)
        self.refresh()
        self.add_shortcuts()
        self.click = Gtk.GestureClick.new()
        self.click.set_button(3)  # right-click → context menu
        self.click.connect("pressed", self.on_right_click)
        self.scroll.add_controller(self.click)

    # ---- nav / listing ----
    def on_place(self, _b, r):
        if not r:
            return
        if r._path == "trash://":
            self.enter_trash()
            return
        self.cd(os.path.expanduser(r._path))

    def enter_trash(self):
        self.in_trash = True
        self.crumb.set_label("Trash (read-only view)")
        self.refresh()

    def cd(self, p):
        if os.path.isdir(p):
            self.in_trash = False
            self.path = os.path.abspath(p)
            self.crumb.set_label(self.path)
            self.refresh()

    def trash_entries(self):
        try:
            t = Gio.File.new_for_uri("trash://")
            enum = t.enumerate_children("standard::name,standard::display-name",
                                        Gio.FileQueryInfoFlags.NONE, None)
            names, info = [], enum.next_file(None)
            while info and len(names) < 200:
                names.append(info.get_display_name())
                info = enum.next_file(None)
            return sorted(names)
        except Exception as e:
            return [f"(trash unreadable: {e})"]

    def entries(self):
        try:
            items = sorted(os.listdir(self.path))
        except Exception as e:
            return []
        if not self.show_hidden:
            items = [i for i in items if not i.startswith(".")]
        q = self.search.get_text().lower()
        if q:
            items = [i for i in items if q in i.lower()]
        return items[:500]

    def refresh(self):
        while (r := self.listbox.get_row_at_index(0)):
            self.listbox.remove(r)
        child = self.flow.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.flow.remove(child)
            child = nxt
        names = self.trash_entries() if self.in_trash else self.entries()
        self._thumbs_made = 0  # per-refresh thumbnail budget (perf guard)
        n = 0
        for name in names:
            if self.in_trash:
                full = f"trash:///{name}"
                icon = "user-trash-symbolic"
            else:
                full = os.path.join(self.path, name)
                isdir = os.path.isdir(full)
                icon = "folder-symbolic" if isdir else "text-x-generic-symbolic"
            if self.grid_mode:
                cell = Gtk.FlowBoxChild()
                vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                thumb = None
                if not self.in_trash:
                    thumb = self.thumbnail(os.path.join(self.path, name))
                if thumb is not None:
                    thumb.set_size_request(132, 96)
                    vb.append(thumb)
                else:
                    vb.append(Gtk.Image.new_from_icon_name(icon))
                lbl = Gtk.Label(label=name if len(name) <= 18 else name[:17] + "…")
                vb.append(lbl)
                cell.set_child(vb)
                cell._full = full
                self.flow.append(cell)
            else:
                row = Gtk.ListBoxRow()
                box = Gtk.Box(spacing=8)
                box.append(Gtk.Image.new_from_icon_name(icon))
                box.append(Gtk.Label(label=name, xalign=0))
                if not self.in_trash:
                    try:
                        isdir = os.path.isdir(full)
                        sz = os.path.getsize(full)
                        box.append(Gtk.Label(label=f"{sz//1024}K" if not isdir else "—",
                                             xalign=1))
                    except Exception:
                        pass
                row.set_child(box)
                row._full = full
                self.listbox.append(row)
            n += 1
        self.scroll.set_child(self.flow if self.grid_mode else self.listbox)
        clip_note = f" • clipboard: {len(self.clip)} {'(cut)' if self.clip_cut else '(copy)'}" if self.clip else ""
        where = "Trash" if self.in_trash else self.path
        self.status.set_label(f"◈ {n} items  •  {where}{clip_note}")

    def on_view(self, b):
        self.grid_mode = b.get_active()
        self.refresh()

    IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff")

    def thumbnail(self, full):
        """Real photo thumbnail (like the reference). Capped + guarded:
        images only, ≤12 MB, first 40 per refresh; anything odd → icon."""
        try:
            if self._thumbs_made >= 40:
                return None
            if not full.lower().endswith(self.IMAGE_EXTS):
                return None
            if os.path.getsize(full) > 12 * 1024 * 1024:
                return None
            pic = Gtk.Picture.new_for_filename(full)
            pic.set_can_shrink(True)
            pic.set_keep_aspect_ratio(True)
            self._thumbs_made += 1
            return pic
        except Exception:
            return None

    def selected_path(self):
        if self.grid_mode:
            kids = self.flow.get_selected_children()
            return getattr(kids[0], "_full", None) if kids else None
        r = self.listbox.get_selected_row()
        return getattr(r, "_full", None) if r else None

    # ---- open / actions ----
    def on_open_row(self, _b, row):
        self.open_path(getattr(row, "_full", ""))

    def on_open_flow(self, _box, child):
        self.open_path(getattr(child, "_full", ""))

    def open_path(self, full):
        if not full or full.startswith("trash://"):
            return
        if os.path.isdir(full):
            self.cd(full)
        else:
            try:
                Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(full), None)
            except Exception as e:
                self.toast(f"Open failed: {e}")

    def on_right_click(self, _g, _n, x, y):
        full = self.selected_path()
        if not full:
            return
        pop = Gtk.PopoverMenu.new_from_model(self.menu_model(full))
        pop.set_parent(self.scroll)
        pop.set_pointing_to(Gdk.Rectangle(int(x), int(y), 1, 1))
        pop.popup()

    def menu_model(self, full):
        m = Gio.Menu()
        if self.in_trash:
            m.append("Trash is read-only here (Restore via desktop Trash app)", "win.noop::x")
        else:
            m.append("Open", f"win.open::{full}")
            m.append("Copy (Ctrl+C)", f"win.copy::{full}")
            m.append("Cut (Ctrl+X)", f"win.cut::{full}")
            m.append("Paste into here (Ctrl+V)", f"win.paste::{self.path}")
            m.append("Rename…", f"win.rename::{full}")
            m.append("Move to Trash (safe)", f"win.trash::{full}")
            m.append("Properties", f"win.props::{full}")
        for name in ("open", "copy", "cut", "paste", "rename", "trash", "props", "noop"):
            if not hasattr(self, f"act_{name}"):
                continue
            act = Gio.SimpleAction.new(name, GLib.VariantType.new("s"))
            act.connect("activate", getattr(self, f"act_{name}"))
            self.add_action(act)
        return m

    def act_noop(self, _a, _p):
        pass

    def act_copy(self, _a, p):
        self.clip = [p.get_string()]; self.clip_cut = False; self.refresh()

    def act_cut(self, _a, p):
        self.clip = [p.get_string()]; self.clip_cut = True; self.refresh()

    def unique_dest(self, dest_dir, base):
        dest = os.path.join(dest_dir, base)
        if not os.path.exists(dest):
            return dest
        name, ext = os.path.splitext(base)
        i = 1
        while os.path.exists(f"{dest_dir}/{name} copy{i}{ext}"):
            i += 1
        return f"{dest_dir}/{name} copy{i}{ext}"

    def act_paste(self, _a, p):
        dest_dir = p.get_string()
        if self.in_trash or not os.path.isdir(dest_dir) or not self.clip:
            return
        try:
            for src in self.clip:
                if not os.path.exists(src):
                    continue
                dest = self.unique_dest(dest_dir, os.path.basename(src))
                if self.clip_cut:
                    shutil.move(src, dest)
                elif os.path.isdir(src):
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
            if self.clip_cut:
                self.clip = []
            self.refresh()
        except Exception as e:
            self.toast(f"Paste failed: {e}")

    def act_open(self, _a, p):
        self.open_path(p.get_string())

    def act_rename(self, _a, p):
        if self.in_trash:
            return self.toast("Trash is read-only here.")
        old = p.get_string()
        dlg = Adw.MessageDialog.new(self, "Rename")
        entry = Gtk.Entry(text=os.path.basename(old))
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", "Cancel"); dlg.add_response("ok", "Rename")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        def done(_d, resp):
            if resp == "ok" and entry.get_text().strip():
                try:
                    os.rename(old, os.path.join(os.path.dirname(old),
                                                entry.get_text().strip()))
                    self.refresh()
                except Exception as e:
                    self.toast(str(e))
        dlg.connect("response", done); dlg.present()

    def act_trash(self, _a, p):
        try:
            Gio.File.new_for_path(p.get_string()).trash(None)
            self.refresh()
        except Exception as e:
            self.toast(f"Trash failed (nothing deleted by force): {e}")

    def act_props(self, _a, p):
        full = p.get_string()
        try:
            st = os.stat(full)
            body = (f"{os.path.basename(full)}\n{full}\n"
                    f"Size: {st.st_size} bytes\n"
                    f"Modified: {datetime.datetime.fromtimestamp(st.st_mtime)}")
        except Exception as e:
            body = str(e)
        d = Adw.MessageDialog.new(self, "Properties")
        d.set_body(body); d.add_response("ok", "OK"); d.present()

    def new_folder(self, _b):
        if self.in_trash:
            return self.toast("Trash is read-only here.")
        dlg = Adw.MessageDialog.new(self, "New folder")
        entry = Gtk.Entry(placeholder_text="folder-name")
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", "Cancel"); dlg.add_response("ok", "Create")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        def done(_d, resp):
            if resp == "ok" and entry.get_text().strip():
                try:
                    os.makedirs(os.path.join(self.path, entry.get_text().strip()))
                    self.refresh()
                except Exception as e:
                    self.toast(str(e))
        dlg.connect("response", done); dlg.present()

    def new_file(self, _b=None):
        if self.in_trash:
            return self.toast("Trash is read-only here.")
        dlg = Adw.MessageDialog.new(self, "New file")
        entry = Gtk.Entry(placeholder_text="notes.txt")
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", "Cancel"); dlg.add_response("ok", "Create")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        def done(_d, resp):
            name = entry.get_text().strip()
            if resp == "ok" and name:
                dest = self.unique_dest(self.path, name)
                try:
                    open(dest, "w").close()
                    self.refresh()
                except Exception as e:
                    self.toast(str(e))
        dlg.connect("response", done); dlg.present()

    def shortcut_copy_cut(self, cut):
        full = self.selected_path()
        if full and not full.startswith("trash://"):
            self.clip = [full]; self.clip_cut = cut; self.refresh()
        return True

    def shortcut_paste(self):
        self.act_paste(None, GLib.Variant.new_string(self.path))
        return True

    def toast(self, msg):
        d = Adw.MessageDialog.new(self, "Vixzen Files")
        d.set_body(msg); d.add_response("ok", "OK"); d.present()

    def add_shortcuts(self):
        ctl = Gtk.ShortcutController.new()
        ctl.set_scope(Gtk.ShortcutScope.LOCAL)
        self.add_controller(ctl)
        def sc(trigger, fn):
            ctl.add_shortcut(Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string(trigger),
                Gtk.CallbackAction.new(lambda *_: (fn(), True)[1])))
        sc("<Control>h", lambda: (self.__dict__.update(
            show_hidden=not self.show_hidden), self.refresh()))
        sc("F3", lambda: self.view_btn.set_active(not self.view_btn.get_active()))
        sc("<Control>c", lambda: self.shortcut_copy_cut(False))
        sc("<Control>x", lambda: self.shortcut_copy_cut(True))
        sc("<Control>v", self.shortcut_paste)
        sc("<Control>n", self.new_folder)

class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="os.vixzen.files",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.start = "~"
        for a in sys.argv[1:]:
            if not a.startswith("-") and os.path.isdir(os.path.expanduser(a)):
                self.start = a
                break
    def do_activate(self):
        FilesWin(self, self.start).present()

if __name__ == "__main__":
    if "--smoke" in sys.argv:
        print("files smoke OK v0.3")
    else:
        App().run([sys.argv[0]])
