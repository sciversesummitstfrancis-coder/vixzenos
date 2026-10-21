/* Vixzen host-bar injector — runs in the LIVE shell via org.gnome.Shell.Eval.
 * No logout, no install. Idempotent: removes any previous Vixzen bar first.
 * Remove anytime: run host_remove.js the same way, or just log out.
 */
const Main = imports.ui.main;
const St = imports.gi.St;
const Clutter = imports.gi.Clutter;
const GLib = imports.gi.GLib;
const Shell = imports.gi.Shell;

if (globalThis._vixzenBar) { try { globalThis._vixzenBar.destroy(); } catch (e) {} globalThis._vixzenBar = null; }
if (globalThis._vixzenTick) { try { GLib.source_remove(globalThis._vixzenTick); } catch (e) {} globalThis._vixzenTick = 0; }

const mon = Main.layoutManager.primaryMonitor;
const bar = new St.BoxLayout({ name: 'vixzen-bar', vertical: false, reactive: true });
bar.set_size(mon.width, 46);
bar.set_position(mon.x, mon.y + mon.height - 46);
bar.set_style('background-color: rgba(27,30,42,0.96); border-top: 1px solid #2E3448; padding: 5px 10px; spacing: 8px;');

const launcher = new St.Button({ label: 'Vixzen', style: 'background-color: #7C7CFF; color: #0B0C12; border-radius: 10px; padding: 4px 16px; font-weight: bold;' });
launcher.connect('clicked', () => { Main.overview.toggle(); });
bar.add_child(launcher);

const pinned = [
    ['Files', 'folder-symbolic', 'org.gnome.Nautilus'],
    ['Terminal', 'terminal-symbolic', 'org.gnome.Terminal'],
    ['Browser', 'web-browser-symbolic', 'org.gnome.Epiphany'],
    ['Software', 'software-symbolic', 'org.gnome.Software'],
    ['Settings', 'preferences-system-symbolic', 'org.gnome.Settings'],
];
for (const item of pinned) {
    const b = new St.Button({ accessible_name: item[0], style: 'padding: 4px 8px; border-radius: 8px;' });
    b.set_child(new St.Icon({ icon_name: item[1], icon_size: 20, style: 'color: #E8EAF2;' }));
    b.connect('clicked', () => {
        try {
            const app = Shell.AppSystem.get_default().lookup_app(item[2]);
            if (app) app.activate();
        } catch (e) {}
    });
    bar.add_child(b);
}

const spacer = new St.Bin({ x_expand: true });
bar.add_child(spacer);

const clock = new St.Label({ y_align: Clutter.ActorAlign.CENTER, style: 'color: #E8EAF2; font-weight: bold;' });
bar.add_child(clock);
function vixTick() {
    try { clock.set_text(new Date().toLocaleString()); } catch (e) {}
    return GLib.SOURCE_CONTINUE;
}
vixTick();
globalThis._vixzenTick = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, vixTick);

Main.layoutManager.addChrome(bar, { affectsStruts: true, trackFullscreen: true });
globalThis._vixzenBar = bar;
'vixzen bar injected';
