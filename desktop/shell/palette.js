/* Vixzen Palette v1.0 — keyboard-first command surface for VixzenOS.
 *
 * One overlay, searched fuzzily (fuzzy.js), four providers:
 *   Windows      — every open window, any workspace. Enter focuses.
 *                  Ctrl+Enter sends that window to the next workspace.
 *   Applications — launchable desktop apps.
 *   Actions      — user-level state toggles only (Dark Mode, Do Not Disturb).
 *   Workspaces   — jump to another workspace.
 *
 * Engineering notes (see docs/PALETTE.md):
 *   - Zero cost while closed: the UI is built on open, destroyed on close,
 *     and no provider polls anything in the background.
 *   - Perf modes: 'saver' renders with no animation, matching Vixzen rules.
 *   - Failure states: a provider that throws simply contributes no rows;
 *     zero results shows a status line instead of a dead panel.
 *   - Permission boundary: no privileged commands run from here. Toggles use
 *     per-user GSettings; nothing touches polkit or root.
 */
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {fuzzyScore, highlightedLabel} from './fuzzy.js';

const MAX_ROWS = 12;

const STYLE = {
    surface: 'background-color: rgba(24,26,38,0.97); border: 1px solid rgba(255,255,255,0.14); border-top: 2px solid #4F46E5; border-radius: 20px; padding: 16px; spacing: 8px;',
    entry: 'border-radius: 12px; padding: 10px 14px; font-size: 16px;',
    row: 'border-radius: 10px; padding: 8px 12px; spacing: 10px;',
    rowSelected: 'background-color: rgba(79,70,229,0.35); border-radius: 10px; padding: 8px 12px; spacing: 10px;',
    title: 'color: #E8EAF2; font-size: 14px;',
    subtitle: 'color: #9CA3AF; font-size: 11px;',
    status: 'color: #9CA3AF; font-size: 13px; padding: 12px;',
};

function _gicon(names, fallback) {
    try {
        return Gio.ThemedIcon.new_from_names([...names, fallback]);
    } catch (e) {
        return null;
    }
}

export class VixzenPalette {
    /* ext: the VixzenShell Extension instance (owns perf mode) */
    constructor(ext) {
        this._ext = ext;
        this._box = null;
        this._rows = [];
        this._sel = 0;
    }

    get perf() {
        return this._ext._vixPerf || 'balanced';
    }

    toggle() {
        if (this._box) this.close();
        else this.open();
    }

    open() {
        if (this._box)
            return;
        const mon = Main.layoutManager.primaryMonitor;
        const W = 640;

        this._box = new St.BoxLayout({ name: 'vixzen-palette', vertical: true, style: STYLE.surface });
        this._box.set_width(W);
        this._box.set_position(mon.x + Math.floor((mon.width - W) / 2), mon.y + Math.floor(mon.height * 0.14));

        this._entry = new St.Entry({ hint_text: 'Search windows, apps, actions…', style: STYLE.entry, x_expand: true });
        this._box.add_child(this._entry);
        this._entry.get_clutter_text().connect('key-press-event', (a, event) => this._onKey(a, event));
        this._entry.get_clutter_text().connect('text-changed', () => this._refill());

        this._scroll = new St.ScrollView({ y_expand: true });
        this._list = new St.BoxLayout({ vertical: true, style: 'spacing: 4px;' });
        this._scroll.set_child(this._list);
        this._box.add_child(this._scroll);

        this._providers = this._gatherProviders();
        Main.uiGroup.add_child(this._box);

        if (this.perf !== 'saver') {
            try {
                this._box.set_pivot_point(0.5, 0.0);
                this._box.set_opacity(0);
                this._box.ease({ opacity: 255, duration: this.perf === 'insane' ? 130 : 100,
                                 mode: Clutter.AnimationMode.EASE_OUT_QUAD });
            } catch (e) {}
        }
        this._refill();
        try { global.stage.set_key_focus(this._entry); } catch (e) {}
    }

    close() {
        if (!this._box)
            return;
        const b = this._box;
        this._box = null;
        this._rows = [];
        try { b.destroy(); } catch (e) {}
    }

    /* ---------- providers (gathered once per open, never polled) ---------- */

    _gatherProviders() {
        const out = { windows: [], apps: [], actions: [], workspaces: [] };
        try {
            const wins = global.display.get_tab_list(Meta.TabList.NORMAL_ALL, null) || [];
            for (const w of wins) {
                try {
                    const app = Shell.WindowTracker.get_default().get_window_app(w);
                    const appName = app ? app.get_name() : (w.get_wm_class() || 'Window');
                    const title = w.get_title() || appName;
                    out.windows.push({ kind: 'window', win: w, title, subtitle: `${appName} · Workspace ${(w.get_workspace().index() + 1)}` });
                } catch (e) {}
            }
        } catch (e) {}
        try {
            const apps = Gio.AppInfo.get_all()
                .filter(a => { try { return a.should_show() && a.get_display_name(); } catch (e) { return false; } })
                .sort((a, b) => a.get_display_name().toLowerCase() < b.get_display_name().toLowerCase() ? -1 : 1)
                .slice(0, 200);
            for (const a of apps)
                out.apps.push({ kind: 'app', app: a, title: a.get_display_name(), subtitle: 'Application' });
        } catch (e) {}
        try { out.actions.push(...this._quickActions()); } catch (e) {}
        try {
            const wm = global.workspace_manager;
            const n = wm.get_n_workspaces();
            const cur = wm.get_active_workspace().index();
            for (let i = 0; i < n && i < 8; i++) {
                if (i === cur)
                    continue;
                out.workspaces.push({ kind: 'workspace', index: i, title: `Workspace ${i + 1}`, subtitle: 'Switch workspace' });
            }
        } catch (e) {}
        return out;
    }

    _quickActions() {
        const actions = [];
        try {
            const iface = new Gio.Settings({ schema: 'org.gnome.desktop.interface' });
            const dark = iface.get_string('color-scheme') === 'prefer-dark';
            actions.push({
                kind: 'action',
                title: `Dark Mode: ${dark ? 'On' : 'Off'}`,
                subtitle: 'Toggle appearance',
                icon: _gicon(['dark-mode-symbolic', 'weather-clear-night-symbolic'], 'preferences-system-symbolic'),
                run: () => iface.set_string('color-scheme', dark ? 'prefer-light' : 'prefer-dark'),
            });
        } catch (e) {}
        try {
            const notif = new Gio.Settings({ schema: 'org.gnome.desktop.notifications' });
            const dnd = !notif.get_boolean('show-banners');
            actions.push({
                kind: 'action',
                title: `Do Not Disturb: ${dnd ? 'On' : 'Off'}`,
                subtitle: 'Toggle notifications',
                icon: _gicon(['notifications-disabled-symbolic'], 'preferences-system-notifications-symbolic'),
                run: () => notif.set_boolean('show-banners', dnd),
            });
        } catch (e) {}
        return actions;
    }

    /* ---------- rendering ---------- */

    _refill() {
        const q = (this._entry.get_text() || '').trim();
        this._list.destroy_all_children();
        this._rows = [];
        this._sel = 0;

        const all = [
            ...this._providers.windows.map(r => ({ ...r, icon: this._iconFor(r) })),
            ...this._providers.apps.map(r => ({ ...r, icon: this._iconFor(r) })),
            ...this._providers.actions.map(r => ({ ...r })),
            ...this._providers.workspaces.map(r => ({ ...r, icon: _gicon(['workspace-switcher-symbolic', 'view-grid-symbolic'], 'preferences-desktop-symbolic') })),
        ];

        let scored;
        if (q.length === 0) {
            scored = all;
        } else {
            scored = all
                .map(r => ({ r, s: fuzzyScore(q, r.title) }))
                .filter(x => x.s !== null)
                .sort((a, b) => b.s - a.s)
                .map(x => x.r);
        }

        if (scored.length === 0) {
            const none = new St.Label({ text: q ? `No matches for “${q}”` : 'Nothing to search yet', style: STYLE.status });
            this._list.add_child(none);
            return;
        }

        for (const r of scored.slice(0, MAX_ROWS)) {
            this._rows.push(r);
            const row = new St.Button({ x_expand: true, style: STYLE.row, accessible_name: `${r.title}. ${r.subtitle}` });
            const hbox = new St.BoxLayout({ vertical: false, style: 'spacing: 10px;' });
            const ic = new St.Icon({ gicon: r.icon || _gicon(['system-search-symbolic'], 'edit-find-symbolic'), icon_size: 22 });
            ic.set_style('color: #E8EAF2; padding-top: 2px;');
            hbox.add_child(ic);
            const v = new St.BoxLayout({ vertical: true, style: 'spacing: 1px;' });
            const title = new St.Label({ style: STYLE.title });
            try { title.clutter_text.set_text(highlightedLabel(q, r.title)); title.clutter_text.set_use_markup(true); }
            catch (e) { title.set_text(r.title); }
            v.add_child(title);
            v.add_child(new St.Label({ text: r.subtitle, style: STYLE.subtitle }));
            hbox.add_child(v);
            row.set_child(hbox);
            const idx = this._rows.length - 1;
            row.connect('clicked', () => this._execute(idx));
            this._list.add_child(row);
        }
        this._paintSelection();
    }

    _iconFor(r) {
        try {
            if (r.kind === 'window') {
                const app = Shell.WindowTracker.get_default().get_window_app(r.win);
                return app ? app.get_icon() : _gicon(['application-x-executable'], 'preferences-system-symbolic');
            }
            if (r.kind === 'app')
                return r.app.get_icon() || _gicon(['application-x-executable'], 'preferences-system-symbolic');
        } catch (e) {}
        return null;
    }

    _paintSelection() {
        const kids = this._list.get_children();
        this._rows.forEach((r, i) => {
            try {
                const btn = kids[i];
                if (!btn) return;
                btn.set_style(i === this._sel ? STYLE.rowSelected : STYLE.row);
            } catch (e) {}
        });
    }

    /* ---------- keyboard ---------- */

    _onKey(actor, event) {
        const sym = event.get_key_symbol();
        const ctrl = (event.get_state() & Clutter.ModifierType.CONTROL_MASK) !== 0;
        if (sym === Clutter.KEY_Escape) { this.close(); return true; }
        if (this._rows.length === 0)
            return false;
        if (sym === Clutter.KEY_Down) { this._sel = (this._sel + 1) % this._rows.length; this._paintSelection(); return true; }
        if (sym === Clutter.KEY_Up) { this._sel = (this._sel - 1 + this._rows.length) % this._rows.length; this._paintSelection(); return true; }
        if (sym === Clutter.KEY_Return || sym === Clutter.KEY_KP_Enter) {
            if (ctrl) { this._sendToNextWorkspace(this._rows[this._sel]); return true; }
            this._execute(this._sel);
            return true;
        }
        return false;
    }

    _execute(idx) {
        const r = this._rows[idx];
        if (!r) { this.close(); return; }
        const t = global.get_current_time();
        this.close();
        try {
            if (r.kind === 'window') { Main.activateWindow(r.win, t); return; }
            if (r.kind === 'app') { r.app.launch([], null); return; }
            if (r.kind === 'workspace') { global.workspace_manager.get_workspace_by_index(r.index).activate(t); return; }
            if (r.kind === 'action') { r.run(); return; }
        } catch (e) {
            try { Main.notify('Vixzen Palette', 'That action failed — nothing was changed.'); } catch (e2) {}
        }
    }

    /* Ctrl+Enter: Flow-lite — send the selected window to the next workspace */
    _sendToNextWorkspace(r) {
        if (!r || r.kind !== 'window') { this.close(); return; }
        try {
            const wm = global.workspace_manager;
            const cur = r.win.get_workspace().index();
            const next = wm.get_workspace_by_index(Math.min(cur + 1, Math.max(wm.get_n_workspaces() - 1, 1)));
            r.win.change_workspace(next);
            next.activate(global.get_current_time());
        } catch (e) {} finally { this.close(); }
    }
}
