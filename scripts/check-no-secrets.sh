#!/usr/bin/env bash
set -euo pipefail

echo "=== Check fichiers sensibles ==="

BAD_FILES=$(find . \
  -type f \
  \( -name "config.json" -o -name ".env" -o -name "secrets.json" \) \
  -not -path "./api/.venv/*" \
  -not -path "./.git/*" || true)

if [ -n "$BAD_FILES" ]; then
  echo "DANGER: fichiers sensibles trouvés :"
  echo "$BAD_FILES"
  exit 1
fi

echo "OK: aucun fichier config.json/.env/secrets.json dans le projet"

echo ""
echo "=== Check clés API probables ==="

if grep -RInE 'EITAS_API_KEY=[a-f0-9]{32,}|\"ApiKey\"[[:space:]]*:[[:space:]]*\"[a-f0-9]{32,}\"' . \
  --exclude-dir=.git \
  --exclude-dir=.venv \
  --exclude-dir=api/.venv \
  --exclude="*.backup*" \
  --exclude="*.broken*" ; then
  echo "DANGER: clé API probable détectée"
  exit 1
fi

echo "OK: aucune clé API réelle détectée"
