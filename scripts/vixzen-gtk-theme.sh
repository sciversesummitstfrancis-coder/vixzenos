#!/bin/bash
# Vixzen GTK rework — restyles native GTK4/Libadwaita apps (Files, Settings,
# Software) with the Vixzen palette. User-scoped, instant for newly opened
# apps (reopen Files to see). Fully reversible (restores prior symlinks).
# Usage: ./scripts/vixzen-gtk-theme.sh --apply [--accent indigo|neon] | --revert
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BK="$HOME/.config/vixzen/gtk-theme.backup"
ACCENT="indigo"
[ "${2:-}" = "--accent" ] && ACCENT="${3:-indigo}"
[ "$1" = "--accent" ] && ACCENT="${2:-indigo}"
case "${1:---apply}" in
  --apply)
    mkdir -p "$HOME/.config/vixzen"
    [ -f "$BK" ] || {
      echo "gtk.css -> $(readlink "$HOME/.config/gtk-4.0/gtk.css" 2>/dev/null)" > "$BK"
      echo "gtk-dark.css -> $(readlink "$HOME/.config/gtk-4.0/gtk-dark.css" 2>/dev/null)" >> "$BK"
      echo "assets -> $(readlink "$HOME/.config/gtk-4.0/assets" 2>/dev/null)" >> "$BK"
    }
    mkdir -p "$HOME/.config/gtk-4.0"
    rm -f "$HOME/.config/gtk-4.0/gtk.css" "$HOME/.config/gtk-4.0/gtk-dark.css"
    # NOTE: on GNOME 50 + Libadwaita only gtk.css is actually loaded, even in
    # dark mode (measured: dark Adw apps resolve gtk.css values). Fluent-Dark
    # does the same. So the dark sheet goes in BOTH files; the light sheet
    # stays in the repo for light-mode sessions (swap manually).
    cp "$HERE/assets/gtk-theme/vixzen-gtk-dark.css" "$HOME/.config/gtk-4.0/gtk.css"
    if [ "$ACCENT" = "neon" ]; then
      cat "$HERE/assets/gtk-theme/vixzen-gtk-neon.css" >> "$HOME/.config/gtk-4.0/gtk.css"
    fi
    cp "$HERE/assets/gtk-theme/vixzen-gtk-dark.css" "$HOME/.config/gtk-4.0/gtk-dark.css"
    if [ "$ACCENT" = "neon" ]; then
      cat "$HERE/assets/gtk-theme/vixzen-gtk-neon.css" >> "$HOME/.config/gtk-4.0/gtk-dark.css"
    fi
    echo "Vixzen GTK theme applied (dark, accent=$ACCENT). Reopen Files/Settings to see it."
    ;;
  --revert)
    if [ -f "$BK" ]; then
      rm -f "$HOME/.config/gtk-4.0/gtk.css" "$HOME/.config/gtk-4.0/gtk-dark.css"
      while IFS= read -r line; do
        name="${line%% -> *}"; target="${line##*-> }"
        if [ -n "$target" ] && [ "$target" != "$name" ]; then
          ln -sf "$target" "$HOME/.config/gtk-4.0/$name" 2>/dev/null || true
        fi
      done < "$BK"
      echo "GTK theme reverted (see $BK). Reopen apps to see it."
    else
      echo "No backup found, nothing to revert."
    fi
    ;;
esac
