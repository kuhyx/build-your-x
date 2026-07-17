#!/bin/bash
# ============================================================================
# Install byox_ladder for the current user and enable the sync timer.
#
#   - Installs the package (and its crdt_sync dependency) into the SYSTEM
#     interpreter's user site, so both the `byox` command and the systemd
#     timer's `/usr/bin/python -m byox_ladder` resolve it.
#   - Installs and enables the 15-minute sync user timer.
#   - Reminds you to create the sync token if it is missing.
# ============================================================================

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly REPO_DIR
# Use the SAME interpreter the systemd service uses, so the editable install
# lands where the timer will look for it (crdt-sync migration skill, step 6).
readonly SERVICE_PY="/usr/bin/python"
readonly UNIT_DIR="$HOME/.config/systemd/user"
readonly TOKEN_FILE="$HOME/.config/byox_ladder/sync_token"

main() {
    echo "Installing byox_ladder from $REPO_DIR ..."
    "$SERVICE_PY" -m pip install --user --break-system-packages -e "$REPO_DIR"

    # Confirm the service interpreter can actually import the sync dependency.
    if ! "$SERVICE_PY" -c "import crdt_sync" 2>/dev/null; then
        echo "ERROR: $SERVICE_PY cannot import crdt_sync after install." >&2
        exit 1
    fi

    echo "Installing sync timer ..."
    mkdir -p "$UNIT_DIR"
    cp "$REPO_DIR/byox-sync.service" "$REPO_DIR/byox-sync.timer" "$UNIT_DIR/"
    systemctl --user daemon-reload
    systemctl --user enable --now byox-sync.timer

    if [[ ! -s "$TOKEN_FILE" ]]; then
        echo
        echo "NOTE: cross-device sync needs a token at:"
        echo "  $TOKEN_FILE   (mode 600)"
        echo "  a fine-grained GitHub PAT with contents read/write on kuhyx/syncs."
        echo "  Without it, byox works fully offline (sync no-ops)."
    fi

    echo
    echo "Done. Check the timer with: systemctl --user status byox-sync.timer"
}

main "$@"
