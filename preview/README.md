# VixzenOS Preview (safe mock — Milestone 2)

Interactive prototype of the Vixzen desktop. **Mock data only — modifies nothing.**

```bash
python3 src/vixzen_preview.py          # launch GUI (needs Wayland/X session)
python3 src/vixzen_preview.py --smoke # headless check (used by build script)
```

What you can try: bottom taskbar → ◈ Vixzen launcher, pinned apps,
sidebar → Desktop / Files (read-only `~` listing, capped 60) / Settings
(light-dark + Saver/Balanced/Enhanced) / About, header notifications mock.

Stack: Python + GTK4 + Libadwaita (`design.py` holds all colors/CSS).
