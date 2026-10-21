#!/bin/bash
# VixzenOS perf snapshot — read-only. Logs startup + idle RSS of preview.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== VixzenOS perf ==="
echo "-- startup (smoke, timed) --"
/usr/bin/time -f "smoke time: %es, mem: %M KB" python3 "$HERE/preview/src/vixzen_preview.py" --smoke
echo "-- files/settings smoke --"
python3 "$HERE/apps/file-manager/vixzen_files.py" --smoke
python3 "$HERE/apps/system-settings/vixzen_settings.py" --smoke
echo "-- budgets: smoke ≤1.5s, preview idle ≤120MB (check manually with: ps -o rss -C python3) --"
