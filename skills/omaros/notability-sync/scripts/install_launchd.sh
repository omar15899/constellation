#!/usr/bin/env bash
# Install the notability-sync LaunchAgent.
#
# Discovers OneDrive Notability_Backup folders at install time and injects
# them into the plist's WatchPaths before loading. Idempotent.

set -euo pipefail

LABEL="com.omaros.notability-sync"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_PLIST="$SKILL_DIR/launchd/$LABEL.plist"
DEST_PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ ! -f "$SRC_PLIST" ]]; then
    echo "source plist missing: $SRC_PLIST" >&2
    exit 1
fi

extra_watches=()
shopt -s nullglob
for d in \
    "$HOME/Library/CloudStorage"/OneDrive-*/Notability_Backup \
    "$HOME/Library/CloudStorage"/OneDrive-*/Documents/Notability_Backup; do
    [[ -d "$d" ]] && extra_watches+=("$d")
done
shopt -u nullglob

tmp="$(mktemp -t notability-sync.plist)"
cp "$SRC_PLIST" "$tmp"

if (( ${#extra_watches[@]} > 0 )); then
    inject=""
    for w in "${extra_watches[@]}"; do
        inject+="        <string>$w</string>"$'\n'
    done
    awk -v inject="$inject" '
        /<key>WatchPaths<\/key>/ { print; in_wp=1; next }
        in_wp && /<array>/ { print; printf "%s", inject; next }
        in_wp && /<\/array>/ { in_wp=0 }
        { print }
    ' "$tmp" > "$tmp.new" && mv "$tmp.new" "$tmp"
fi

mkdir -p "$HOME/Library/LaunchAgents"

if launchctl list | grep -q "$LABEL"; then
    launchctl unload "$DEST_PLIST" 2>/dev/null || true
fi

cp "$tmp" "$DEST_PLIST"
rm -f "$tmp"

launchctl load "$DEST_PLIST"

echo "installed: $DEST_PLIST"
echo "watching:"
/usr/libexec/PlistBuddy -c "Print :WatchPaths" "$DEST_PLIST" | sed 's/^/  /'
echo
echo "logs:"
echo "  /tmp/notability-sync.log"
echo "  /tmp/notability-sync.out.log"
echo "  /tmp/notability-sync.err.log"
echo
echo "to unload: launchctl unload $DEST_PLIST"
