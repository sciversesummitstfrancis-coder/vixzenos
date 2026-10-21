# Building VixzenOS

## One command
```bash
./build-vixzenos.sh                # full pipeline (needs sudo for livemedia-creator)
./build-vixzenos.sh --check-only   # safe: only validates, builds nothing
./build-vixzenos.sh --clean        # remove build/ artifacts + caches
```

## What the script does
1. Checks deps: `livemedia-creator`, `lorax`, `python3`, `gtk4`, disk ≥ 20 GB free.
2. Validates structure (`preview/src`, `packaging/vixzenos.ks`, assets).
3. Runs preview smoke test (`tests/test_preview.py`).
4. If `--check-only`, stops here — no root, no downloads.
5. Else (requires sudo): calls `livemedia-creator --make-iso --ks packaging/vixzenos.ks --resultdir build/`.
6. Writes `build/build.log`, prints ISO path + size, runs `isoinfo` validation.

## Kickstart
`packaging/vixzenos.ks` starts from Fedora Workstation, adds:
`gtk4`, `libadwaita`, `python3-gobject`, Vixzen branding/assets, and the
preview app as `/usr/share/vixzen-preview/`. GNOME extension install lands in
Milestone 3.

Full ISO needs network + ~10–20 GB downloads; on 8 GB RAM run the build alone
(close other apps) or use `--check-only` for now.
