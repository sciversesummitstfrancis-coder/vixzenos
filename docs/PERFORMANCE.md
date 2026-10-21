# VixzenOS Performance Budgets (HD 520 / 8 GB target)

Measure with `./scripts/diag.sh` and `tests/test_preview.py --perf`.
No perf claim without a number.
| Metric | Budget | How to check |
|---|---|---|
| Preview idle RAM | ≤ 120 MB | `ps -o rss` after 30 s idle |
| Preview startup | ≤ 1.5 s | `time python3 preview/src/vixzen_preview.py --smoke` |
| Taskbar click → window | ≤ 100 ms | manual + `--perf` log |
| Animations | ≤ 200 ms, interruptible, off in Saver mode | CSS `transition-duration` audit |
| Insane mode (opt-in) | 600 ms + glows + intro splash, exempt from budget | `design.css_for("dark","insane")` contains `600ms` |
| Boot splash | 66 generated frames, same sizes/count as stock | `assets/boot/frames/` + Plymouth `vixzen` theme |
| ISO size | report only (no promise yet) | `du -h build/*.iso` |
| Build RAM | close other apps; 8 GB is tight for livemedia | `free -h` before build |

## Rules
- No polling loops < 1 s; clock ticks once per second only.
- No blur (`backdrop-filter`) in Saver/Balanced; flat surfaces.
- File previews lazy + capped (text ≤ 4 KB in preview mock).
- One `in_progress` animation at a time; `prefers-reduced-motion` respected via Saver mode.
- Icons: SVG first, no duplicate PNG densities.

## Measured (host, 2026-10-01 — first numbers on record)
| Metric | Budget | Measured | Verdict |
|---|---|---|---|
| Preview smoke startup | ≤ 1.5 s | 0.29 s (`time ... --smoke`) | ✅ pass |
| Host boot to graphical | report only | 24.9 s (`systemd-analyze`; 1.0 kernel + 4.2 initrd + 19.7 userspace) | recorded |
| Failed services (host) | 0 | 0 (`systemctl --failed`) | ✅ pass |
| Preview idle RAM | ≤ 120 MB | not yet measured (needs GUI run: launch, wait 30 s, `ps -o rss`) | ⬜ open |
| Taskbar click → window | ≤ 100 ms | not yet measured (needs `--perf` log + manual) | ⬜ open |
| ISO boot time (QEMU) | report only | not yet measured (serial log timestamps) | ⬜ open |
| Vixzen Web v0.7 window frame | ≤ 0.2 s (perceived startup) | 0.03 s chrome present, tab fills in via idle (HD 520 host) | ✅ pass |
| Vixzen Web new tab | ≤ 0.2 s | 0.057 s | ✅ pass |
| Vixzen Web UI RSS, 2 tabs | report only | 168 MB UI process (WebKit web content runs in sandboxed processes; page-cache + GPU compositing on) | recorded |
