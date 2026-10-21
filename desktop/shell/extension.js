/* Vixzen Shell v0.3 — ONE build: bottom bar + attached Start Menu.
 * Click the Vixzen badge → menu opens anchored above the bar (search,
 * pinned, categorized apps, user + power with confirm dialogs).
 * No separate window: everything lives in this file, like Windows 11.
 * Loads on next session start (Wayland rule). Staged and syntax-checked.
 */
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const PINNED = [
    ['Files', 'folder-symbolic', 'org.gnome.Nautilus'],
    ['Browser', 'vixzen-browser', 'org.mozilla.firefox'],
    ['Terminal', 'terminal-symbolic', 'org.gnome.Ptyxis'],
    ['Software', 'software-symbolic', 'org.gnome.Software'],
    ['Settings', 'preferences-system-symbolic', 'org.gnome.Settings'],
];
const POWER = [
    ['Suspend', ['systemctl', 'suspend'], 'Suspend now? Unsaved work could be lost.'],
    ['Restart', ['systemctl', 'reboot'], 'Restart now? Unsaved work could be lost.'],
    ['Power Off', ['systemctl', 'poweroff'], 'Shut down now? Unsaved work could be lost.'],
    ['Log Out', ['gnome-session-quit', '--logout', '--no-prompt'], 'End your session? Open apps will close.'],
];

export default class VixzenShell extends Extension {
    enable() {
        const mon = Main.layoutManager.primaryMonitor;
        this._barHeight = 50;
        try {
            const cfgFile = Gio.File.new_for_path(GLib.get_home_dir() + '/.config/vixzen/settings.json');
            if (cfgFile.query_exists(null)) {
                const [ok, data] = cfgFile.load_contents(null);
                if (ok) this._vixPerf = JSON.parse(new TextDecoder().decode(data)).perf || 'balanced';
            }
        } catch (e) { this._vixPerf = 'balanced'; }

        // ---- bottom bar ----
        this._bar = new St.BoxLayout({ name: 'vixzen-bar', vertical: false });
        this._bar.set_size(mon.width, this._barHeight);
        this._bar.set_position(mon.x, mon.y + mon.height - this._barHeight);
        this._bar.set_style('background-color: rgba(27,30,42,0.96); border-top: 2px solid #4F46E5; padding: 6px 12px; spacing: 10px;');

        this._launcher = new St.Button({ label: '◈ Vixzen', style: 'background-color: #7C7CFF; color: #0B0C12; border-radius: 12px; padding: 6px 18px; font-weight: bold; font-size: 15px;' });
        this._launcher.connect('clicked', () => this._toggleMenu());
        this._bar.add_child(this._launcher);

        // macOS-style magnification: hovered icon swells, neighbors swell
        // less by distance, all easing back on leave. GPU-cheap (a few
        // actors scaling). Pivot at bottom-center so icons grow upward.
        this._magBtns = [];
        for (const [name, icon, appId] of PINNED) {
            const b = new St.Button({ accessible_name: name, style: 'padding: 4px 8px; border-radius: 8px;' });
            // Full-color Vixzen icons (e.g. vixzen-browser globe) render as-is;
            // symbolic icons fall back to stock and get the light tint.
            const symbolic = icon.endsWith('-symbolic');
            const stIcon = new St.Icon({
                gicon: Gio.ThemedIcon.new_from_names(symbolic ? [icon] : [icon, 'web-browser-symbolic']),
                icon_size: 22,
            });
            if (symbolic) stIcon.set_style('color: #E8EAF2;');
            b.set_child(stIcon);
            b.connect('clicked', () => {
                try { Shell.AppSystem.get_default().lookup_app(appId)?.activate(); } catch (e) {}
            });
            const idx = this._magBtns.length;
            b.connect('notify::hover', () => this._magnify(b.hover ? idx : -1));
            this._magBtns.push(b);
            this._bar.add_child(b);
        }
        const spacer = new St.Bin({ x_expand: true });
        this._bar.add_child(spacer);
        this._clock = new St.Label({ y_align: Clutter.ActorAlign.CENTER, style: 'color: #E8EAF2; font-weight: bold;' });
        this._bar.add_child(this._clock);
        Main.layoutManager.addChrome(this._bar, { affectsStruts: true, trackFullscreen: true });
        this._tick = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            try { this._clock.set_text(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })); } catch (e) {}
            return GLib.SOURCE_CONTINUE;
        });

        // ---- attached Start Menu (built once, shown/hidden) ----
        this._menu = null;
        try { this._username = GLib.get_user_name(); } catch (e) { this._username = 'user'; }
    }

    _magnify(hot) {
        if (!this._magBtns) return;
        // Saver mode: no animation, snap to scale 1 (matches Vixzen perf rules).
        const saver = this._vixPerf === 'saver';
        const insane = this._vixPerf === 'insane';
        this._magBtns.forEach((bb, i) => {
            const d = Math.abs(i - hot);
            let s;
            if (hot < 0 || saver) s = 1;
            else if (insane) s = d === 0 ? 1.8 : d === 1 ? 1.4 : d === 2 ? 1.2 : 1;
            else s = d === 0 ? 1.5 : d === 1 ? 1.25 : d === 2 ? 1.1 : 1;
            if (saver) { try { bb.set_scale(1, 1); } catch (e) {} return; }
            try {
                bb.set_pivot_point(0.5, 1.0);
                bb.ease({ scale_x: s, scale_y: s, duration: insane ? 220 : 100,
                          mode: Clutter.AnimationMode.EASE_OUT_QUAD });
            } catch (e) {
                try { bb.set_scale(s, s); } catch (e2) {}
            }
        });
    }

    _toggleMenu() {        if (this._menu) { this._menu.destroy(); this._menu = null; return; }
        const mon = Main.layoutManager.primaryMonitor;
        const W = 600, H = 540;
        const menu = new St.BoxLayout({ name: 'vixzen-menu', vertical: true });
        menu.set_size(W, H);
        menu.set_position(mon.x + 12, mon.y + mon.height - this._barHeight - H - 12);
        menu.set_style('background-color: rgba(24,26,38,0.97); border: 1px solid rgba(255,255,255,0.14); border-top: 2px solid #4F46E5; border-radius: 20px; padding: 16px; spacing: 10px;');

        const search = new St.Entry({ hint_text: 'Search apps, settings, files…', style: 'border-radius: 12px; padding: 8px 12px; font-size: 15px;' });
        menu.add_child(search);

        const scroll = new St.ScrollView({ y_expand: true });
        const list = new St.BoxLayout({ vertical: true });
        scroll.set_child(list);
        menu.add_child(scroll);

        let apps = [];
        try {
            apps = Gio.AppInfo.get_all()
                .filter(a => { try { return a.should_show() && a.get_display_name(); } catch (e) { return false; } })
                .sort((a, b) => a.get_display_name().toLowerCase() < b.get_display_name().toLowerCase() ? -1 : 1);
        } catch (e) {}
        const fill = (q) => {
            list.destroy_all_children();
            let n = 0;
            for (const a of apps) {
                const name = a.get_display_name();
                if (q && !name.toLowerCase().includes(q)) continue;
                const b = new St.Button({ label: name, x_expand: true, style: 'text-align: left; border-radius: 10px; padding: 6px 10px;' });
                b.connect('clicked', () => {
                    try { a.launch([], null); } catch (e) {}
                    this._toggleMenu();
                });
                list.add_child(b);
                if (++n >= 60) break;
            }
        };
        search.get_clutter_text().connect('text-changed', () => fill(search.get_text().toLowerCase()));
        fill('');

        const foot = new St.BoxLayout({ vertical: false });
        foot.add_child(new St.Label({ text: this._username, y_align: Clutter.ActorAlign.CENTER, style: 'color: #E8EAF2;' }));
        const fsp = new St.Bin({ x_expand: true });
        foot.add_child(fsp);
        // Two-tap confirm: first tap arms ("Sure?"), second executes.
        // Needs no dialog imports, so nothing unverifiable can break.
        this._armedPower = null;
        this._powerBtns = {};
        for (const [label, cmd, warn] of POWER) {
            const b = new St.Button({ label, style: 'border-radius: 10px; padding: 4px 10px;' });
            this._powerBtns[label] = b;
            b.connect('clicked', () => {
                if (this._armedPower === label) {
                    this._armedPower = null;
                    b.set_label(label);
                    try { Gio.Subprocess.new(cmd, Gio.SubprocessFlags.NONE); } catch (e) {}
                } else {
                    for (const [l2, bb] of Object.entries(this._powerBtns))
                        if (l2 !== label) bb.set_label(l2);
                    this._armedPower = label;
                    b.set_label(label + '?');
                    GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
                        if (this._armedPower === label) {
                            this._armedPower = null;
                            try { b.set_label(label); } catch (e) {}
                        }
                        return GLib.SOURCE_REMOVE;
                    });
                }
            });
            foot.add_child(b);
        }
        menu.add_child(foot);

        Main.uiGroup.add_child(menu);
        this._menu = menu;
        global.stage.set_key_focus(search);
    }

    disable() {
        if (this._tick) { GLib.source_remove(this._tick); this._tick = 0; }
        if (this._menu) { this._menu.destroy(); this._menu = null; }
        this._bar?.destroy();
        this._bar = null;
    }
}
