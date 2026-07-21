#!/bin/bash

set -Eeuo pipefail
umask 0077

ROOT="/opt/eitas-identity"
SOURCE="$ROOT/source/keycloak"

UPSTREAM_LOCK="$ROOT/docs/UPSTREAM.lock"
PATCH_LOCK="$ROOT/docs/EITAS_CORE_PATCH.lock"
PATCH_MANIFEST="$ROOT/docs/EITAS_CORE_PATCHES.sha256"

FAILED=0
TEMP_DIR=""

cleanup() {
    if [ -n "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

fail() {
    echo "$1 : ERREUR"
    FAILED=1
}

check_equal() {
    local label="$1"
    local expected="$2"
    local actual="$3"

    if [ "$expected" = "$actual" ]; then
        echo "$label : OK"
    else
        echo "$label : ERREUR"
        echo "  attendu : $expected"
        echo "  obtenu  : $actual"
        FAILED=1
    fi
}

check_secure_root_file() {
    local path="$1"
    local label="$2"

    if [ ! -f "$path" ]; then
        fail "$label absent"
        return
    fi

    if [ "$(stat -c '%u' "$path")" != "0" ]; then
        fail "$label propriétaire root"
        return
    fi

    if find "$path" \
      -maxdepth 0 \
      -perm /022 \
      -print \
      -quit |
      grep -q .
    then
        fail "$label permissions"
        return
    fi

    echo "$label sécurisé : OK"
}

if [ ! -d "$SOURCE/.git" ]; then
    echo "ERREUR : dépôt source absent."
    exit 1
fi

check_secure_root_file \
  "$UPSTREAM_LOCK" \
  "UPSTREAM.lock"

check_secure_root_file \
  "$PATCH_LOCK" \
  "Verrou du patch"

check_secure_root_file \
  "$PATCH_MANIFEST" \
  "Manifeste du patch"

if [ "$FAILED" -ne 0 ]; then
    exit 1
fi

# Ces fichiers sont root-owned, non modifiables par le runner.
# shellcheck disable=SC1090
source "$UPSTREAM_LOCK"

# shellcheck disable=SC1090
source "$PATCH_LOCK"

check_equal \
  "Répertoire source" \
  "$SOURCE" \
  "$EITAS_IDENTITY_SOURCE_DIRECTORY"

ACTUAL_REMOTE="$(
    git -C "$SOURCE" \
      remote \
      get-url \
      origin
)"

ACTUAL_TAG="$(
    git -C "$SOURCE" \
      describe \
      --tags \
      --exact-match \
      HEAD
)"

ACTUAL_COMMIT="$(
    git -C "$SOURCE" \
      rev-parse \
      HEAD
)"

check_equal \
  "Remote amont" \
  "$EITAS_IDENTITY_UPSTREAM_URL" \
  "$ACTUAL_REMOTE"

check_equal \
  "Tag amont" \
  "$EITAS_IDENTITY_UPSTREAM_TAG" \
  "$ACTUAL_TAG"

check_equal \
  "Commit amont" \
  "$EITAS_IDENTITY_UPSTREAM_COMMIT" \
  "$ACTUAL_COMMIT"

check_equal \
  "Commit de base du patch" \
  "$EITAS_IDENTITY_CORE_PATCH_BASE_COMMIT" \
  "$ACTUAL_COMMIT"

ACTUAL_MANIFEST_SHA="$(
    sha256sum "$PATCH_MANIFEST" |
    awk '{print $1}'
)"

check_equal \
  "Intégrité du manifeste" \
  "$EITAS_IDENTITY_CORE_PATCH_MANIFEST_SHA256" \
  "$ACTUAL_MANIFEST_SHA"

ACTUAL_FILE_COUNT="$(
    wc -l < "$PATCH_MANIFEST"
)"

check_equal \
  "Nombre de fichiers approuvés" \
  "$EITAS_IDENTITY_CORE_PATCH_FILE_COUNT" \
  "$ACTUAL_FILE_COUNT"

TEMP_DIR="$(mktemp -d)"
EXPECTED_STATUS="$TEMP_DIR/expected-status.txt"
ACTUAL_STATUS="$TEMP_DIR/actual-status.txt"

while read -r digest relative_path; do
    if ! [[ "$digest" =~ ^[0-9a-f]{64}$ ]]; then
        echo "Hash invalide dans le manifeste : $digest"
        FAILED=1
        continue
    fi

    if [ -z "$relative_path" ]; then
        echo "Chemin vide dans le manifeste."
        FAILED=1
        continue
    fi

    printf ' M %s\n' "$relative_path"
done < "$PATCH_MANIFEST" |
LC_ALL=C sort > "$EXPECTED_STATUS"

git -C "$SOURCE" \
  status \
  --short \
  --untracked-files=all |
LC_ALL=C sort > "$ACTUAL_STATUS"

if cmp -s "$EXPECTED_STATUS" "$ACTUAL_STATUS"; then
    echo "Liste exacte des patches approuvés : OK"
else
    echo "Liste exacte des patches approuvés : ERREUR"

    diff -u \
      "$EXPECTED_STATUS" \
      "$ACTUAL_STATUS" \
      || true

    FAILED=1
fi

if (
    cd "$SOURCE"

    sha256sum \
      --check \
      --strict \
      "$PATCH_MANIFEST"
); then
    echo "Contenu des patches approuvés : OK"
else
    echo "Contenu des patches approuvés : ERREUR"
    FAILED=1
fi

ACTUAL_PATCH_SHA="$(
    git -C "$SOURCE" \
      diff \
      --binary \
      --full-index \
      HEAD |
    sha256sum |
    awk '{print $1}'
)"

check_equal \
  "Patch cœur complet" \
  "$EITAS_IDENTITY_CORE_PATCH_SHA256" \
  "$ACTUAL_PATCH_SHA"

DIFF_SUMMARY="$(
    git -C "$SOURCE" \
      diff \
      --summary \
      HEAD
)"

if [ -z "$DIFF_SUMMARY" ]; then
    echo "Modes, renommages et suppressions : OK"
else
    echo "Modes, renommages et suppressions : ERREUR"
    printf '%s\n' "$DIFF_SUMMARY"
    FAILED=1
fi

if git -C "$SOURCE" diff --check; then
    echo "Cohérence du diff : OK"
else
    echo "Cohérence du diff : ERREUR"
    FAILED=1
fi

if [ -f "$SOURCE/LICENSE.txt" ]; then
    echo "Licence amont : OK"
else
    echo "Licence amont : ERREUR"
    FAILED=1
fi

if [ "$FAILED" -ne 0 ]; then
    echo
    echo "VÉRIFICATION AMONT : ÉCHEC"
    exit 1
fi

echo
echo "Arbre source contrôlé : OK"
echo "Patch cœur EITAS approuvé : 15 fichiers"
echo "VÉRIFICATION AMONT : OK"
