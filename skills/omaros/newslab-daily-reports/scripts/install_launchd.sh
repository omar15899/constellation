#!/usr/bin/env bash
# Install the newslab-daily-reports launchd agents:
#   com.omaros.newslab-importer        — KeepAlive drip importer (decoupled GDELT fetch)
#   com.omaros.newslab-daily-reports   — run-once 07:00 daily report builder + LLM + commit
# Clones the claude-conversations-sync installer; renders __REPO_ROOT__ into each plist.
set -euo pipefail

REPO_ROOT="/Users/omarkhalil/OmarOS"
LAUNCHD_DIR="/Users/omarkhalil/GitHub/Constellation/skills/omaros/newslab-daily-reports/launchd"
DST_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$DST_DIR"

for LABEL in com.omaros.newslab-importer com.omaros.newslab-daily-reports; do
    SRC="$LAUNCHD_DIR/$LABEL.plist"
    DST="$DST_DIR/$LABEL.plist"
    sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$SRC" > "$DST"
    launchctl unload "$DST" 2>/dev/null || true
    launchctl load "$DST"
    echo "Loaded $LABEL  ->  $DST"
done

echo
echo "Verify both registered cleanly (status column must be 0, not 2):"
echo "  launchctl list | grep newslab"
echo
echo "Importer logs:  $REPO_ROOT/docs/newslab_importer_daemon.log"
echo "Report logs:    $REPO_ROOT/docs/newslab_daily_reports_daemon.log"
echo "Headless-claude JSON: $REPO_ROOT/.claude/logs/newslab_daily.out.json"
echo
echo "Trigger one report run now (without waiting for 07:00):"
echo "  launchctl kickstart -k gui/\$(id -u)/com.omaros.newslab-daily-reports"
echo
echo "Uninstall both:"
echo "  for L in com.omaros.newslab-importer com.omaros.newslab-daily-reports; do \\"
echo "    launchctl unload \"$DST_DIR/\$L.plist\" && rm \"$DST_DIR/\$L.plist\"; done"
