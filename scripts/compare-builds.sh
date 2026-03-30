#!/bin/bash
# compare-builds.sh
# Compare two .wcp files to detect changes between builds.
#
# Usage:
#   ./compare-builds.sh <old.wcp> <new.wcp> [--json]
#
# Outputs:
#   - File count changes
#   - Size differences
#   - New/removed files
#   - Changed files (by size, since we can't diff binaries)
#   - profile.json differences
#
# Options:
#   --json    Output comparison result as JSON

set -euo pipefail

OLD_WCP="${1:-}"
NEW_WCP="${2:-}"
OUTPUT_FORMAT="${3:-text}"

if [[ -z "$OLD_WCP" || -z "$NEW_WCP" ]]; then
    echo "Usage: $0 <old.wcp> <new.wcp> [--json]"
    exit 1
fi

[[ -f "$OLD_WCP" ]] || { echo "Error: File not found: $OLD_WCP"; exit 1; }
[[ -f "$NEW_WCP" ]] || { echo "Error: File not found: $NEW_WCP"; exit 1; }

# --- Extract both .wcps to temp dirs ---
TMP_OLD="$(mktemp -d)"
TMP_NEW="$(mktemp -d)"
trap 'rm -rf "$TMP_OLD" "$TMP_NEW"' EXIT

extract_wcp() {
    local src="$1"
    local dst="$2"
    if command -v zstd &>/dev/null; then
        zstd -d "$src" -o "$dst/archive.tar" --quiet
        tar -xf "$dst/archive.tar" -C "$dst"
        rm "$dst/archive.tar"
    else
        python3 -c "
import zstandard, tarfile
with open('$src', 'rb') as f:
    dctx = zstandard.ZstdDecompressor()
    with dctx.stream_reader(f) as r:
        with tarfile.open(fileobj=r, mode='r|') as tf:
            tf.extractall('$dst')
"
    fi
}

echo "Extracting builds for comparison..."
extract_wcp "$OLD_WCP" "$TMP_OLD"
extract_wcp "$NEW_WCP" "$TMP_NEW"

# --- Collect file lists with sizes ---
list_files() {
    local base="$1"
    find "$base" -type f | sort | while read -r f; do
        rel="${f#$base/}"
        size="$(wc -c < "$f")"
        echo "$rel $size"
    done
}

OLD_LIST="$(list_files "$TMP_OLD")"
NEW_LIST="$(list_files "$TMP_NEW")"

OLD_COUNT="$(echo "$OLD_LIST" | wc -l)"
NEW_COUNT="$(echo "$NEW_LIST" | wc -l)"

OLD_SIZE_MB="$(du -sm "$TMP_OLD" | cut -f1)"
NEW_SIZE_MB="$(du -sm "$TMP_NEW" | cut -f1)"

# Files only in old (removed)
REMOVED="$(comm -23 \
    <(echo "$OLD_LIST" | awk '{print $1}' | sort) \
    <(echo "$NEW_LIST" | awk '{print $1}' | sort))"

# Files only in new (added)
ADDED="$(comm -13 \
    <(echo "$OLD_LIST" | awk '{print $1}' | sort) \
    <(echo "$NEW_LIST" | awk '{print $1}' | sort))"

# Files in both but with different sizes (changed)
CHANGED="$(comm -12 \
    <(echo "$OLD_LIST" | awk '{print $1}' | sort) \
    <(echo "$NEW_LIST" | awk '{print $1}' | sort) | while read -r fname; do
        OLD_SIZE="$(echo "$OLD_LIST" | awk -v f="$fname" '$1==f {print $2}')"
        NEW_SIZE="$(echo "$NEW_LIST" | awk -v f="$fname" '$1==f {print $2}')"
        if [[ "$OLD_SIZE" != "$NEW_SIZE" ]]; then
            echo "$fname ($OLD_SIZE -> $NEW_SIZE bytes)"
        fi
    done)"

REMOVED_COUNT="$(echo "$REMOVED" | grep -c . || echo 0)"
ADDED_COUNT="$(echo "$ADDED" | grep -c . || echo 0)"
CHANGED_COUNT="$(echo "$CHANGED" | grep -c . || echo 0)"

SIZE_DIFF=$(( NEW_SIZE_MB - OLD_SIZE_MB ))

# --- profile.json diff ---
PROFILE_DIFF=""
if [[ -f "$TMP_OLD/profile.json" && -f "$TMP_NEW/profile.json" ]]; then
    PROFILE_DIFF="$(diff "$TMP_OLD/profile.json" "$TMP_NEW/profile.json" || true)"
fi

# --- Output ---
if [[ "$OUTPUT_FORMAT" == "--json" ]]; then
    python3 -c "
import json, sys

data = {
    'old_file': '$OLD_WCP',
    'new_file': '$NEW_WCP',
    'old_file_count': $OLD_COUNT,
    'new_file_count': $NEW_COUNT,
    'old_size_mb': $OLD_SIZE_MB,
    'new_size_mb': $NEW_SIZE_MB,
    'size_diff_mb': $SIZE_DIFF,
    'removed_files': [x for x in '''$REMOVED'''.strip().split('\n') if x],
    'added_files': [x for x in '''$ADDED'''.strip().split('\n') if x],
    'changed_files': [x for x in '''$CHANGED'''.strip().split('\n') if x],
    'profile_diff': '''$PROFILE_DIFF''',
}
print(json.dumps(data, indent=2))
"
else
    echo ""
    echo "=== Build Comparison ==="
    printf "%-20s  %s  %s\n" "" "OLD" "NEW"
    printf "%-20s  %s  %s\n" "File" "$(basename "$OLD_WCP")" "$(basename "$NEW_WCP")"
    printf "%-20s  %dMB  %dMB  (diff: %+dMB)\n" "Size" "$OLD_SIZE_MB" "$NEW_SIZE_MB" "$SIZE_DIFF"
    printf "%-20s  %d  %d  (diff: %+d)\n" "File count" "$OLD_COUNT" "$NEW_COUNT" "$(( NEW_COUNT - OLD_COUNT ))"
    echo ""
    echo "--- Changes ---"
    echo "Added:   $ADDED_COUNT files"
    echo "Removed: $REMOVED_COUNT files"
    echo "Changed: $CHANGED_COUNT files"

    if [[ -n "$ADDED" ]]; then
        echo ""
        echo "=== Added files ($ADDED_COUNT) ==="
        echo "$ADDED" | head -50
        [[ $ADDED_COUNT -gt 50 ]] && echo "... and $(( ADDED_COUNT - 50 )) more"
    fi

    if [[ -n "$REMOVED" ]]; then
        echo ""
        echo "=== Removed files ($REMOVED_COUNT) ==="
        echo "$REMOVED" | head -50
        [[ $REMOVED_COUNT -gt 50 ]] && echo "... and $(( REMOVED_COUNT - 50 )) more"
    fi

    if [[ -n "$CHANGED" ]]; then
        echo ""
        echo "=== Changed files ($CHANGED_COUNT) ==="
        echo "$CHANGED" | head -50
        [[ $CHANGED_COUNT -gt 50 ]] && echo "... and $(( CHANGED_COUNT - 50 )) more"
    fi

    if [[ -n "$PROFILE_DIFF" ]]; then
        echo ""
        echo "=== profile.json diff ==="
        echo "$PROFILE_DIFF"
    fi
fi
