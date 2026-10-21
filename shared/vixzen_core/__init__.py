"""Vixzen shared core: config + styling for every Vixzen GTK app."""
from .config import load, path, save
from .style import apply_display, inform, provider_for, refresh

__all__ = ["load", "save", "path", "provider_for", "refresh",
           "apply_display", "inform"]
