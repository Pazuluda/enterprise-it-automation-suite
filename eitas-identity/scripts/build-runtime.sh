#!/bin/bash
set -euo pipefail

ROOT="/opt/eitas-identity"
VERSION_FILE="$ROOT/VERSION"
UPSTREAM_LOCK="$ROOT/docs/UPSTREAM.lock"
THEME_BUILD_SCRIPT="$ROOT/scripts/build-theme.sh"

EITAS_VERSION="$(
    awk -F= \
      '$1 == "EITAS_IDENTITY_VERSION" { print $2 }' \
      "$VERSION_FILE"
)"

KEYCLOAK_VERSION="$(
    awk -F= \
      '$1 == "KEYCLOAK_UPSTREAM_VERSION" { print $2 }' \
      "$VERSION_FILE"
)"

SOURCE_DIST="/opt/keycloak-${KEYCLOAK_VERSION}"
RUNTIME_ROOT="$ROOT/runtime"
RUNTIME_DIST="$RUNTIME_ROOT/keycloak-${KEYCLOAK_VERSION}-eitas"

THEME_JAR="$ROOT/build/eitas-identity-theme-${EITAS_VERSION}.jar"
THEME_SHA="$THEME_JAR.sha256"

if [ -z "$EITAS_VERSION" ] || [ -z "$KEYCLOAK_VERSION" ]; then
    echo "ERREUR : versions introuvables dans $VERSION_FILE"
    exit 1
fi

if [ ! -x "$SOURCE_DIST/bin/kc.sh" ]; then
    echo "ERREUR : distribution Keycloak absente : $SOURCE_DIST"
    exit 1
fi

if [ ! -x "$THEME_BUILD_SCRIPT" ]; then
    echo "ERREUR : script de thème absent."
    exit 1
fi

if [ -e "$RUNTIME_DIST" ]; then
    echo "ERREUR : le runtime existe déjà :"
    echo "$RUNTIME_DIST"
    echo
    echo "Aucune suppression automatique n’est effectuée."
    exit 1
fi

echo
echo "=== Construction du thème ==="

"$THEME_BUILD_SCRIPT"

test -s "$THEME_JAR"
test -s "$THEME_SHA"

(
    cd "$(dirname "$THEME_JAR")"
    sha256sum -c "$(basename "$THEME_SHA")"
)

THEME_HASH="$(
    sha256sum "$THEME_JAR" |
    awk '{print $1}'
)"

UPSTREAM_COMMIT="$(
    awk -F= \
      '$1 == "EITAS_IDENTITY_UPSTREAM_COMMIT" { print $2 }' \
      "$UPSTREAM_LOCK"
)"

echo
echo "=== Copie de la distribution officielle ==="

install -d \
  -o eitas-identity \
  -g eitas-identity \
  -m 0750 \
  "$RUNTIME_ROOT"

cp -a \
  --reflink=auto \
  "$SOURCE_DIST" \
  "$RUNTIME_DIST"

echo
echo "=== Nettoyage des éléments d’exécution copiés ==="

if [ -d "$RUNTIME_DIST/data" ]; then
    find "$RUNTIME_DIST/data" \
      -mindepth 1 \
      -delete
fi

install -d \
  -m 0750 \
  "$RUNTIME_DIST/data"

echo
echo "=== Nettoyage des fournisseurs externes copiés ==="

install -d \
  -m 0755 \
  "$RUNTIME_DIST/providers"

find "$RUNTIME_DIST/providers" \
  -mindepth 1 \
  -delete

echo
echo "=== Installation du thème EITAS ==="

install \
  -o eitas-identity \
  -g eitas-identity \
  -m 0644 \
  "$THEME_JAR" \
  "$RUNTIME_DIST/providers/$(basename "$THEME_JAR")"

chown -R \
  eitas-identity:eitas-identity \
  "$RUNTIME_DIST"

echo
echo "=== Construction optimisée Keycloak ==="

runuser \
  -u eitas-identity \
  -- \
  env \
    HOME=/var/lib/eitas-identity \
    "$RUNTIME_DIST/bin/kc.sh" \
    build \
    --db=postgres

echo
echo "=== Manifeste du runtime ==="

{
    echo "EITAS_IDENTITY_VERSION=$EITAS_VERSION"
    echo "KEYCLOAK_UPSTREAM_VERSION=$KEYCLOAK_VERSION"
    echo "KEYCLOAK_UPSTREAM_COMMIT=$UPSTREAM_COMMIT"
    echo "EITAS_THEME_FILE=$(basename "$THEME_JAR")"
    echo "EITAS_THEME_SHA256=$THEME_HASH"
    echo "RUNTIME_DIRECTORY=$RUNTIME_DIST"
    echo "RUNTIME_BUILT_AT=$(date --iso-8601=seconds)"
    echo "DATABASE_VENDOR=postgres"
    echo "OPTIMIZED_BUILD=true"
} > "$RUNTIME_DIST/EITAS-RUNTIME.lock"

chown \
  eitas-identity:eitas-identity \
  "$RUNTIME_DIST/EITAS-RUNTIME.lock"

chmod 0640 \
  "$RUNTIME_DIST/EITAS-RUNTIME.lock"

echo
echo "=== Résultat ==="
echo "Runtime : $RUNTIME_DIST"
echo "Thème   : $(basename "$THEME_JAR")"
echo "SHA256  : $THEME_HASH"
echo
echo "CONSTRUCTION DU RUNTIME : OK"
