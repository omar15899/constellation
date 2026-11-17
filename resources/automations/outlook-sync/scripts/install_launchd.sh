#!/usr/bin/env bash
set -euo pipefail

# Installs the OmarOS outlook-sync launchd agent (com.omaros.outlook-sync).
# Schedule: daily at 07:00. Entrypoint: scripts/daemon.py via the omaros venv.
# Refuses to install unless a silent Microsoft Graph token is already cached
# (i.e. auth.py has been run successfully at least once).

LABEL="com.omaros.outlook-sync"
PROD_SKILL="/Users/omarkhalil/GitHub/Constellation/resources/automations/outlook-sync"
PLIST_SRC="${PROD_SKILL}/launchd/${LABEL}.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
VENV_PYTHON="/Users/omarkhalil/.venvs/omaros/bin/python"
SCRIPTS_DIR="${PROD_SKILL}/scripts"
STDOUT_LOG="/Users/omarkhalil/OmarOS/docs/outlook_sync_daemon.log"
STDERR_LOG="/Users/omarkhalil/OmarOS/docs/outlook_sync_daemon.err"

if [[ ! -f "${PLIST_SRC}" ]]; then
	echo "ERROR: plist not found at ${PLIST_SRC}" >&2
	echo "Restore the automation at its source path before installing." >&2
	exit 1
fi

if [[ ! -x "${VENV_PYTHON}" ]]; then
	echo "ERROR: omaros venv python not found at ${VENV_PYTHON}" >&2
	exit 1
fi

echo "Verifying a silent Microsoft Graph token is cached..."
if ! OMAROS_ROOT="/Users/omarkhalil/OmarOS" "${VENV_PYTHON}" - "${SCRIPTS_DIR}" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
from graph_client import GraphClient, GraphError

try:
    GraphClient.from_config()._token()
except GraphError as exc:
    print(f"  no silent token: {exc}", file=sys.stderr)
    sys.exit(1)
except Exception as exc:  # noqa: BLE001
    print(f"  token check failed: {exc}", file=sys.stderr)
    sys.exit(1)
print("  silent token OK")
PYEOF
then
	echo "" >&2
	echo "ERROR: no cached Microsoft token available." >&2
	echo "Run the interactive device-code login first:" >&2
	echo "    ${VENV_PYTHON} ${SCRIPTS_DIR}/auth.py" >&2
	echo "Then re-run this installer." >&2
	exit 2
fi

mkdir -p "${HOME}/Library/LaunchAgents"
mkdir -p "$(dirname "${STDOUT_LOG}")"

echo "Copying plist -> ${PLIST_DST}"
cp "${PLIST_SRC}" "${PLIST_DST}"

if launchctl list | grep -q "${LABEL}"; then
	echo "Unloading existing agent..."
	launchctl unload "${PLIST_DST}" 2>/dev/null || true
fi

echo "Loading agent..."
launchctl load "${PLIST_DST}"

echo ""
echo "Installed ${LABEL}."
echo "  Schedule : daily at 07:00 (StartCalendarInterval Hour=7 Minute=0)"
echo "  Python   : ${VENV_PYTHON}"
echo "  Entry    : ${SCRIPTS_DIR}/daemon.py"
echo "  Stdout   : ${STDOUT_LOG}"
echo "  Stderr   : ${STDERR_LOG}"
echo ""
echo "To run once now (applies in configured mode):"
echo "    launchctl start ${LABEL}"
echo "To run once in dry-run mode:"
echo "    OUTLOOK_SYNC_DRYRUN=1 ${VENV_PYTHON} ${SCRIPTS_DIR}/daemon.py"
echo "To uninstall:"
echo "    launchctl unload ${PLIST_DST} && rm ${PLIST_DST}"
