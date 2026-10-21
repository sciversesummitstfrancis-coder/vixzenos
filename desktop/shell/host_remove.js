/* Vixzen host-bar remover — run via org.gnome.Shell.Eval like the injector. */
const GLib = imports.gi.GLib;
if (globalThis._vixzenTick) { try { GLib.source_remove(globalThis._vixzenTick); } catch (e) {} globalThis._vixzenTick = 0; }
if (globalThis._vixzenBar) { try { globalThis._vixzenBar.destroy(); } catch (e) {} globalThis._vixzenBar = null; }
'vixzen bar removed';
