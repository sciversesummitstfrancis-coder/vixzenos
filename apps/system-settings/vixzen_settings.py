#!/usr/bin/env python3
"""Vixzen Settings v0.3 — Appearance / Performance / About.
New v0.3: 'Apply to GNOME' buttons (reversible, user-scoped gsettings only):
theme → org.gnome.desktop.interface color-scheme, wallpaper → background
picture-uri using our SVG. Never touches system files.
Run: python3 apps/system-settings/vixzen_settings.py [--smoke]
"""
import os, sys, subprocess
import gi
gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "preview", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from design import THEMES, WALLPAPERS, ACCENTS
from vixzen_core import apply_display, load, provider_for, refresh
from vixzen_core import save as save_cfg

DEFAULTS = {"theme": "dark", "perf": "balanced", "wallpaper": "Indigo Dusk",
            "accent": "Vixzen Indigo"}

class Win(Adw.PreferencesWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Vixzen Settings")
        self.set_default_size(640, 500)
        cfg = load("settings", DEFAULTS)
        self.cfg = cfg
        css = provider_for(cfg.get("theme", "dark"),
                           cfg.get("perf", "balanced"),
                           cfg.get("wallpaper", "Indigo Dusk"),
                           cfg.get("accent", "Vixzen Indigo"))
        apply_display(css)
        self.css = css

        # Appearance
        pg = Adw.PreferencesPage.new()
        pg.set_title("Appearance"); pg.set_icon_name("preferences-desktop-theme-symbolic")
        grp = Adw.PreferencesGroup.new(); grp.set_title("Theme and wallpaper")
        pg.add(grp)
        theme = Adw.ComboRow.new()
        theme.set_title("Theme")
        theme.set_model(Gtk.StringList.new(["Dark", "Light"]))
        theme.set_selected(0 if cfg.get("theme", "dark") == "dark" else 1)
        theme.connect("notify::selected", self.on_theme)
        grp.add(theme)
        wp = Adw.ComboRow.new()
        wp.set_title("Wallpaper")
        wp.set_model(Gtk.StringList.new(list(WALLPAPERS)))
        try:
            wp.set_selected(list(WALLPAPERS).index(cfg.get("wallpaper", "Indigo Dusk")))
        except ValueError:
            wp.set_selected(0)
        wp.connect("notify::selected", self.on_wp)
        grp.add(wp)
        ac = Adw.ComboRow.new()
        ac.set_title("Brand accent")
        ac.set_model(Gtk.StringList.new(list(ACCENTS)))
        try:
            ac.set_selected(list(ACCENTS).index(cfg.get("accent", "Vixzen Indigo")))
        except ValueError:
            ac.set_selected(0)
        ac.connect("notify::selected", self.on_accent)
        grp.add(ac)
        apply_row = Adw.ActionRow.new()
        apply_row.set_title("Apply Vixzen look to GNOME")
        apply_row.set_subtitle("Sets your GNOME theme + wallpaper (you can revert in GNOME Settings)")
        apply_btn = Gtk.Button(label="Apply")
        apply_btn.connect("clicked", self.apply_to_gnome)
        apply_row.add_suffix(apply_btn)
        grp.add(apply_row)
        self.gnome_note = Adw.ActionRow.new()
        self.gnome_note.set_title("GNOME status")
        self.gnome_note.set_subtitle("Not applied yet this session.")
        grp.add(self.gnome_note)
        dnd_row = Adw.SwitchRow.new()
        dnd_row.set_title("Do Not Disturb")
        dnd_row.set_subtitle("Silence banners (kept in notification history).")
        dnd_row.set_active(not self.banners_enabled())
        dnd_row.connect("notify::active", self.on_dnd)
        grp.add(dnd_row)
        self.add(pg)

        # Performance
        pg2 = Adw.PreferencesPage.new()
        pg2.set_title("Performance"); pg2.set_icon_name("battery-good-symbolic")
        g2 = Adw.PreferencesGroup.new()
        g2.set_title("Vixzen Performance Mode")
        g2.set_description("Saver: no animations. Balanced: short (150ms). Enhanced: shadows + 220ms. Insane: cinematic 600ms + intro (needs decent GPU).")
        pg2.add(g2)
        perf = Adw.ComboRow.new()
        perf.set_title("Mode")
        perf.set_model(Gtk.StringList.new(["Saver", "Balanced", "Enhanced", "Insane"]))
        perf.set_selected(("saver", "balanced", "enhanced", "insane").index(cfg.get("perf", "balanced")))
        perf.connect("notify::selected", self.on_perf)
        g2.add(perf)
        # GNOME system animations (user-scoped, reversible):
        # Saver -> animations OFF, Balanced/Enhanced -> ON.
        self.anim_row = Adw.SwitchRow.new()
        self.anim_row.set_title("GNOME animations")
        self.anim_row.set_subtitle("Off in Saver, on otherwise. Toggle anytime.")
        self.anim_row.set_active(self.gnome_anims_enabled())
        self.anim_row.connect("notify::active", self.on_anim_toggle)
        g2.add(self.anim_row)
        anim_apply = Adw.ActionRow.new()
        anim_apply.set_title("Apply performance to GNOME")
        anim_apply.set_subtitle("Sets enable-animations from the mode above")
        anim_btn = Gtk.Button(label="Apply")
        anim_btn.connect("clicked", lambda _b: self.apply_perf_to_gnome())
        anim_apply.add_suffix(anim_btn)
        g2.add(anim_apply)
        self.perf_note = Adw.ActionRow.new()
        self.perf_note.set_title("GNOME status")
        self.perf_note.set_subtitle("Not applied yet this session.")
        g2.add(self.perf_note)
        self.add(pg2)

        # School Admin
        pg4 = Adw.PreferencesPage.new()
        pg4.set_title("School Admin"); pg4.set_icon_name("system-users-symbolic")
        g4 = Adw.PreferencesGroup.new()
        g4.set_title("Classroom lockdown")
        g4.set_description("Each change asks for the admin password. "
                           "Students (non-admin accounts) cannot reverse them.")
        pg4.add(g4)
        self.net_row = Adw.SwitchRow.new()
        self.net_row.set_title("Internet access")
        self.net_row.set_subtitle("Off disconnects everyone until an admin re-enables.")
        self.net_row.connect("notify::active", self.on_edu_net)
        g4.add(self.net_row)
        self.store_row = Adw.SwitchRow.new()
        self.store_row.set_title("Software store installs")
        self.store_row.set_subtitle("Off = store needs admin authentication to install.")
        self.store_row.connect("notify::active", self.on_edu_store)
        g4.add(self.store_row)
        self.edu_note = Adw.ActionRow.new()
        self.edu_note.set_title("Admin status")
        self.edu_note.set_subtitle("Helper missing: lockdown unavailable on this system.")
        g4.add(self.edu_note)
        self.add(pg4)
        self.refresh_edu(block=True)

        # About
        pg3 = Adw.PreferencesPage.new()
        pg3.set_title("About"); pg3.set_icon_name("help-about-symbolic")
        g3 = Adw.PreferencesGroup.new(); g3.set_title("This system (read-only)")
        pg3.add(g3)
        g3.add(Adw.ActionRow.new())
        info = self.sysinfo()
        row = Adw.ActionRow.new()
        row.set_title("System")
        row.set_subtitle(info[:300])
        g3.add(row)
        self.add(pg3)

    def restyle(self):
        refresh(self.css, self.cfg["theme"], self.cfg["perf"],
                self.cfg["wallpaper"],
                self.cfg.get("accent", "Vixzen Indigo"))
        save_cfg("settings", self.cfg)

    def on_accent(self, r, _p):
        self.cfg["accent"] = list(ACCENTS)[r.get_selected()]
        self.restyle()

    def on_theme(self, r, _p):
        self.cfg["theme"] = "dark" if r.get_selected() == 0 else "light"
        self.restyle()

    def on_wp(self, r, _p):
        self.cfg["wallpaper"] = list(WALLPAPERS)[r.get_selected()]
        self.restyle()

    def on_perf(self, r, _p):
        self.cfg["perf"] = ("saver", "balanced", "enhanced", "insane")[r.get_selected()]
        self.restyle()
        self.apply_perf_to_gnome()

    def gnome_anims_enabled(self):
        try:
            r = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface",
                                "enable-animations"], capture_output=True, text=True, timeout=5)
            return "true" in r.stdout.lower()
        except Exception:
            return True

    def apply_perf_to_gnome(self, enabled=None):
        """Reversible, user-scoped: enable-animations from perf mode."""
        if enabled is None:
            enabled = self.cfg.get("perf", "balanced") != "saver"
        try:
            subprocess.run(["gsettings", "set", "org.gnome.desktop.interface",
                            "enable-animations", "true" if enabled else "false"],
                           check=True, timeout=5)
            msg = f"animations={'on' if enabled else 'off'} (perf={self.cfg.get('perf')})"
        except Exception as e:
            msg = f"animations failed: {e}"
        if hasattr(self, "perf_note"):
            self.perf_note.set_subtitle(msg[:300])
        if hasattr(self, "anim_row"):
            try:
                self.anim_row.set_active(bool(enabled))
            except Exception:
                pass
        return msg

    def on_anim_toggle(self, r, _p):
        self.apply_perf_to_gnome(enabled=r.get_active())

    def banners_enabled(self):
        try:
            r = subprocess.run(["gsettings", "get",
                                "org.gnome.desktop.notifications",
                                "show-banners"], capture_output=True,
                               text=True, timeout=5)
            return "true" in r.stdout.lower()
        except Exception:
            return True

    def on_dnd(self, r, _p):
        try:
            subprocess.run(["gsettings", "set",
                            "org.gnome.desktop.notifications", "show-banners",
                            "false" if r.get_active() else "true"],
                           check=True, timeout=5)
        except Exception:
            try:
                r.set_active(not r.get_active())
            except Exception:
                pass

    # ---- School Admin (Edu lockdown; privileged ops via pkexec) ----
    def edu_helper(self):
        cands = ("/usr/libexec/vixzen-edu-admin",
                 os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                              "..", "scripts",
                                              "vixzen-edu-admin.sh")))
        for p in cands:
            if os.path.isfile(p):
                return p
        return None

    def edu_state(self):
        """(net_on, store_unlocked) without authentication (read-only)."""
        h = self.edu_helper()
        if h is None:
            return None
        try:
            net = subprocess.run([h, "net-status"], capture_output=True,
                                 text=True, timeout=10).stdout.strip()
            store = subprocess.run([h, "store-status"], capture_output=True,
                                   text=True, timeout=10).stdout.strip()
            return (net == "on", store == "unlocked")
        except Exception:
            return None

    def refresh_edu(self, block=False):
        st = self.edu_state()
        if st is None:
            if hasattr(self, "edu_note"):
                self.edu_note.set_subtitle("Helper missing: lockdown unavailable.")
            return
        net_on, unlocked = st
        for row, val in ((self.net_row, net_on), (self.store_row, unlocked)):
            try:
                if block:
                    row.handler_block_by_func(self.on_edu_net)
                    row.handler_block_by_func(self.on_edu_store)
                row.set_active(val)
            except Exception:
                try:
                    row.set_active(val)
                except Exception:
                    pass
            finally:
                try:
                    row.handler_unblock_by_func(self.on_edu_net)
                    row.handler_unblock_by_func(self.on_edu_store)
                except Exception:
                    pass
        if hasattr(self, "edu_note"):
            self.edu_note.set_subtitle(
                f"Internet {'on' if net_on else 'OFF'} • "
                f"store {'open' if unlocked else 'LOCKED'}")

    def edu_apply(self, action):
        h = self.edu_helper()
        if h is None:
            return "helper missing"
        try:
            r = subprocess.run(["pkexec", h, action], capture_output=True,
                               text=True, timeout=120)
            ok = r.returncode == 0
            return (r.stdout.strip() or r.stderr.strip() or
                    ("done" if ok else "cancelled/failed"))
        except Exception as e:
            return f"failed: {e}"

    def on_edu_net(self, r, _p):
        msg = self.edu_apply("net-on" if r.get_active() else "net-off")
        self.edu_note.set_subtitle(f"Internet: {msg}"[:300])
        self.refresh_edu(block=True)

    def on_edu_store(self, r, _p):
        msg = self.edu_apply("store-unlock" if r.get_active() else "store-lock")
        self.edu_note.set_subtitle(f"Store: {msg}"[:300])
        self.refresh_edu(block=True)

    def apply_to_gnome(self, _b):
        """User-scoped, reversible: color-scheme + wallpaper + animations only."""
        msgs = []
        scheme = "prefer-dark" if self.cfg.get("theme", "dark") == "dark" else "prefer-light"
        try:
            subprocess.run(["gsettings", "set", "org.gnome.desktop.interface",
                            "color-scheme", scheme], check=True, timeout=5)
            msgs.append(f"theme={scheme}")
        except Exception as e:
            msgs.append(f"theme failed: {e}")
        wp_map = {"Starry Night": "vixzen-starry-1920x1080.png",
                  "Vixzen Signature": "vixzen-signature-1920x1080.png",
                  "Neon Burst": "vixzen-burst-1920x1080.png",
                  "Indigo Dusk": "indigo-dusk.svg",
                  "Slate Calm": "indigo-dusk.svg",
                  "Deep Night": "indigo-dusk.svg"}
        wp_file = os.path.join(os.path.dirname(__file__), "..", "..",
                               "assets", "wallpapers",
                               wp_map.get(self.cfg.get("wallpaper", "Vixzen Signature"),
                                          "vixzen-signature-1920x1080.png"))
        wp_file = os.path.abspath(wp_file)
        try:
            uri = f"file://{wp_file}"
            for key in ("picture-uri", "picture-uri-dark"):
                subprocess.run(["gsettings", "set", "org.gnome.desktop.background",
                                key, uri], check=False, timeout=5)
            msgs.append("wallpaper set (revert anytime in GNOME Settings)")
        except Exception as e:
            msgs.append(f"wallpaper failed: {e}")
        msgs.append(self.apply_perf_to_gnome())
        self.gnome_note.set_subtitle("; ".join(msgs)[:300])

    def sysinfo(self):
        out = []
        for f, cmd in (("os", ["cat", "/etc/fedora-release"]),
                       ("cpu", ["lscpu"]),
                       ("mem", ["free", "-h"])):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                out.append(r.stdout.splitlines()[0] if f == "cpu" else r.stdout.strip()[:200])
            except Exception as e:
                out.append(f"{f}: {e}")
        return " | ".join(out)

class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="os.vixzen.settings",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
    def do_activate(self):
        Win(self).present()

if __name__ == "__main__":
    if "--smoke" in sys.argv:
        assert set(THEMES) == {"light", "dark"} and len(WALLPAPERS) >= 2
        print("settings smoke OK v0.3")
    else:
        App().run(sys.argv)
