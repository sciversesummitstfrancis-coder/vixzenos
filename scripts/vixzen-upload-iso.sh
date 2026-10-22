#!/bin/bash
# VixzenOS ISO uploader — publish a release ISO to GitHub.
# Designed to be run on a FAST connection (not the dev laptop): it is
# bandwidth-heavy by nature.
#
# Usage:
#   ./scripts/vixzen-upload-iso.sh <iso-path> [tag]
#
# Handles GitHub's 2 GiB release-asset limit automatically:
#   * ISO <= 2 GiB      -> uploaded as one file
#   * ISO >  2 GiB      -> split into .part1/.part2 (join with: cat part1 part2 > iso)
# Resumable (re-run continues), rate-limited by default so it never
# saturates the link.
#
# Env:
#   VIXZEN_GH_TOKEN    GitHub token (required)
#   VIXZEN_GH_REPO      owner/repo (default: sciversesummitstfrancis-coder/vixzenos)
#   VIXZEN_RATE         curl --limit-rate value (default 8M)
set -u
ISO="${1:-}"
TAG="${2:-v0.3-preview}"
REPO="${VIXZEN_GH_REPO:-sciversesummitstfrancis-coder/vixzenos}"
RATE="${VIXZEN_RATE:-8M}"
LIMIT=$((2 * 1024 * 1024 * 1024 - 64 * 1024 * 1024))   # 2 GiB, with headroom

[ -n "$ISO" ] || { echo "Usage: $0 <iso-path> [tag]"; exit 2; }
[ -f "$ISO" ] || { echo "No such file: $ISO"; exit 2; }
[ -n "${VIXZEN_GH_TOKEN:-}" ] || {
  echo "Set VIXZEN_GH_TOKEN first:" >&2
  echo "  export VIXZEN_GH_TOKEN=ghp_xxx" >&2
  exit 2; }
command -v curl >/dev/null || { echo "curl missing"; exit 2; }

size=$(stat -c%s "$ISO")
printf "ISO: %s (%.2f GB)\n" "$ISO" "$(echo "$size" | awk '{print $1/1073741824}')"

api() { curl -sS -H "Authorization: token $VIXZEN_GH_TOKEN" \
        -H "Accept: application/vnd.github+json" "$@"; }

# Find or create the release.
rel_json=$(api "https://api.github.com/repos/$REPO/releases/tags/$TAG")
rel_id=$(echo "$rel_json" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -z "$rel_id" ]; then
  echo "creating release $TAG ..."
  rel_id=$(api -X POST "https://api.github.com/repos/$REPO/releases" \
    -d "{\"tag_name\":\"$TAG\",\"name\":\"VixzenOS $TAG\",\"draft\":false,\"prerelease\":true}" \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))")
fi
[ -n "$rel_id" ] || { echo "could not resolve release id"; exit 1; }
echo "release id: $rel_id"

upload() { # name file
  local name="$1" file="$2"
  echo "--> uploading $name ($(du -h "$file" | cut -f1))"
  curl -sS -X POST -H "Authorization: token $VIXZEN_GH_TOKEN" \
    "https://uploads.github.com/repos/$REPO/releases/$rel_id/assets?name=$name" \
    -H "Content-Type: application/octet-stream" \
    --limit-rate "$RATE" --continue-at - --data-binary @"$file" \
    -o /dev/null -w "    HTTP:%{http_code}  %{speed_download} B/s\n"
}

if [ "$size" -le "$LIMIT" ]; then
  upload "$(basename "$ISO")" "$ISO"
else
  echo "ISO exceeds GitHub's 2 GiB asset limit — splitting."
  base=$(basename "$ISO")
  split -b "$LIMIT" -d --additional-suffix=.part "$ISO" "${base}.part"
  n=1
  for p in ${base}.part*; do
    upload "$(basename "$p")" "$p"
    n=$((n + 1))
  done
  cat > "${base}.JOIN.txt" <<EOF
This ISO was split because GitHub limits release assets to 2 GiB.
Rejoin it with:
    cat ${base}.part* > ${base}
then verify:
    sha256sum -c SHA256SUMS.txt
EOF
  upload "${base}.JOIN.txt" "${base}.JOIN.txt"
fi
echo "done: https://github.com/$REPO/releases/tag/$TAG"
