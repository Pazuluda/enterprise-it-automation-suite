#!/usr/bin/env bash

set -Eeuo pipefail
umask 0027

if [ "$EUID" -ne 0 ]; then
    echo "ERREUR : exécution root requise."
    exit 1
fi

ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd
)"

PACKAGE="$ROOT/packaging/identity-update"

SOURCE_HELPER="$PACKAGE/libexec/eitas-identity-update-source-check"
SOURCE_SERVICE="$PACKAGE/systemd/eitas-identity-update-source-check.service"
SOURCE_PATH="$PACKAGE/systemd/eitas-identity-update-source-check.path"

TARGET_HELPER="/usr/local/libexec/eitas-identity-update-source-check"
TARGET_SERVICE="/etc/systemd/system/eitas-identity-update-source-check.service"
TARGET_PATH="/etc/systemd/system/eitas-identity-update-source-check.path"

START_PATH=0

case "${1:-}" in
    "")
        ;;
    --start-path)
        START_PATH=1
        ;;
    -h|--help)
        echo "Usage : $0 [--start-path]"
        exit 0
        ;;
    *)
        echo "Usage : $0 [--start-path]" >&2
        exit 2
        ;;
esac

test -s "$SOURCE_HELPER"
test -s "$SOURCE_SERVICE"
test -s "$SOURCE_PATH"

(
    PYCACHE_DIR="$(mktemp -d)"

    cleanup_pycache() {
        rm -rf "$PYCACHE_DIR"
    }

    trap cleanup_pycache EXIT

    PYTHONPYCACHEPREFIX="$PYCACHE_DIR"       python3 -m py_compile "$SOURCE_HELPER"
)

systemd-analyze verify \
  "$SOURCE_SERVICE" \
  "$SOURCE_PATH"

install -d -o root -g root -m 0755 \
  /usr/local/libexec

install -o root -g root -m 0755 \
  "$SOURCE_HELPER" \
  "$TARGET_HELPER"

install -o root -g root -m 0644 \
  "$SOURCE_SERVICE" \
  "$TARGET_SERVICE"

install -o root -g root -m 0644 \
  "$SOURCE_PATH" \
  "$TARGET_PATH"

install -d -o root -g eitas -m 0750 \
  /var/lib/eitas/identity-update

install -d -o eitas -g eitas -m 0750 \
  /var/lib/eitas/identity-update/requests

install -d -o root -g root -m 0700 \
  /var/lib/eitas/identity-update/processing \
  /var/lib/eitas/identity-update/reports

systemctl daemon-reload

systemctl disable \
  eitas-identity-update-source-check.path \
  >/dev/null 2>&1 || true

if [ "$START_PATH" -eq 1 ]; then
    systemctl reset-failed \
      eitas-identity-update-source-check.service \
      2>/dev/null || true

    systemctl start \
      eitas-identity-update-source-check.path
fi

echo "Runner installé."
echo "Démarrage automatique : désactivé."

if [ "$START_PATH" -eq 1 ]; then
    echo "Watcher courant : actif."
else
    echo "Watcher courant : non démarré."
fi
