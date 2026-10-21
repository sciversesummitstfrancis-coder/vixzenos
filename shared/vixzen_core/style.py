"""Vixzen shared styling: one CSS provider helper for every GTK app."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "preview", "src"))
from design import LIQUID_CARD, css_for


def provider_for(theme="dark", perf="balanced", wallpaper="Indigo Dusk",
                 accent="Vixzen Indigo", extra=""):
    """Build a Gtk.CssProvider with Vixzen tokens. Imports Gtk lazily so
    this module stays importable headless (tests)."""
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk
    css = Gtk.CssProvider()
    refresh(css, theme, perf, wallpaper, accent, extra)
    return css


def refresh(provider, theme="dark", perf="balanced",
            wallpaper="Indigo Dusk", accent="Vixzen Indigo", extra=""):
    """Reload a live-attached provider in place (theme switching)."""
    provider.load_from_data((css_for(theme, perf, wallpaper, accent)
                             + LIQUID_CARD + extra).encode())


def apply_display(provider):
    """Attach a provider to the default display. Returns False headless."""
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk, Gdk
        disp = Gdk.Display.get_default()
        if disp is None:
            return False
        Gtk.StyleContext.add_provider_for_display(
            disp, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        return True
    except Exception:
        return False


def inform(parent, heading, body):
    """Consistent Vixzen dialog (replaces per-app toast/message copies)."""
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw
    dlg = Adw.MessageDialog.new(parent, heading)
    dlg.set_body(body)
    dlg.add_response("ok", "OK")
    dlg.present()
    return dlg
