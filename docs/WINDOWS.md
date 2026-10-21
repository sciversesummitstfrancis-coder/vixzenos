# Run Vixzen Blink on Windows

Short version: the WebKit app (`vixzen-web`) **cannot** run on Windows —
WebKitGTK has no Windows port. **Vixzen Blink can**: Qt6 ships official
Windows wheels, and the app uses zero Linux-only APIs.

## Steps (on the Windows machine)

1. Install Python 3.14 64-bit from python.org (tick "Add python.exe to PATH").
2. In PowerShell:
   ```powershell
   pip install PyQt6 PyQt6-WebEngine
   ```
3. Copy the whole `vixzenos/apps/web-browser-blink/` folder plus
   `vixzenos/apps/web-browser/vixzen_search.py` and `blocklist.py` next
   to it (same layout as the repo: `web-browser-blink/` beside
   `web-browser/`), then:
   ```powershell
   python vixzen_blink.py
   ```

## Notes

- First run creates `%USERPROFILE%\.config\vixzen-web\` for bookmarks,
  history, settings, blocklist — copy that folder from Linux to keep
  everything in sync.
- SmartScreen may flag the unsigned script on first launch — "More info →
  Run anyway". A signed installer is future work, not planned solo.
- Performance: QtWebEngine downloads its own Chromium — no extra install.
- Not tested by us on Windows yet (we build on Fedora): if a button
  misbehaves, tell us the exact click + any console text.
