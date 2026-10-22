#!/bin/bash
# Lightweight build watcher: reports phase transitions from build/build.log
# without heavy polling (one read every 45s) so it never competes with the
# build for CPU or RAM.
LOG="/home/shonshyjo/Documents/Default Project/vixzenos/build/build.log"
LAST=""
for i in $(seq 1 200); do
  [ -f "$LOG" ] || { sleep 45; continue; }
  PHASE=$(grep -E "^(=== |\[[A-Z]+\]|2026-.*(Installation finished|Creating a squashfs|Rebuilding initrds|Building boot.iso|Disk Image install successful|ISO image produced))" "$LOG" 2>/dev/null | tail -n 1)
  if [ -n "$PHASE" ] && [ "$PHASE" != "$LAST" ]; then
    echo "[$(date +%H:%M:%S)] $PHASE"
    LAST="$PHASE"
  fi
  if grep -qE "\[OK\] ISO:|\[FAIL\]" "$LOG" 2>/dev/null; then
    echo "[$(date +%H:%M:%S)] BUILD FINISHED"
    grep -E "\[OK\] ISO:|\[FAIL\]" "$LOG" | tail -n 2
    exit 0
  fi
  sleep 45
done
echo "watcher: timed out after 2.5h"
