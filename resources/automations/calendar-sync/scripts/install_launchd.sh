#!/usr/bin/env bash
# Install (or reinstall) the calendar-sync LaunchAgent in daemon mode.
# Idempotent: safe to re-run.

set -euo pipefail

LABEL="com.omaros.calendar-sync"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_PLIST="$SKILL_DIR/launchd/$LABEL.plist"
DEST_PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ ! -f "$SRC_PLIST" ]]; then
    echo "source plist missing: $SRC_PLIST" >&2
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"

if [[ -f "$DEST_PLIST" ]]; then
    launchctl unload "$DEST_PLIST" 2>/dev/null || true
fi

# Verify Calendar access before loading. EventKit can only obtain access
# from a foreground process the first time, so we refuse to install the
# daemon until that happened — otherwise launchd would re-spawn a denied
# daemon every ThrottleInterval and spam the logs.
echo "Verifying Calendar access for the OmarOS Python binary…"
if ! /opt/homebrew/bin/uv run "$SKILL_DIR/scripts/fetch_calendar.py" /tmp/_cal_probe.json --lookback 1 --lookahead 1 >/dev/null 2>&1; then
    echo
    echo "  Calendar access NOT granted yet."
    echo "  Run this once interactively from Terminal to trigger the prompt:"
    echo
    echo "    cd /Users/omarkhalil/OmarOS"
    echo "    uv run /Users/omarkhalil/GitHub/Constellation/resources/automations/calendar-sync/scripts/setup_access.py"
    echo
    echo "  Then re-run this installer."
    rm -f /tmp/_cal_probe.json
    exit 2
fi
rm -f /tmp/_cal_probe.json
echo "  → access OK."

cp "$SRC_PLIST" "$DEST_PLIST"
launchctl load "$DEST_PLIST"

echo "installed: $DEST_PLIST"
echo "interval:  $(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:INTERVAL_SECONDS' "$DEST_PLIST") s"
echo
echo "logs:"
echo "  /Users/omarkhalil/OmarOS/docs/calendar_sync_daemon.log"
echo "  /Users/omarkhalil/OmarOS/docs/calendar_sync_daemon.err"
echo
echo "to unload: launchctl unload $DEST_PLIST"
