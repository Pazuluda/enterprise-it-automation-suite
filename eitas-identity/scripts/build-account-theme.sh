#!/bin/bash
set -euo pipefail

ROOT="/opt/eitas-identity"
ACCOUNT_ROOT="$ROOT/ui/account-console"

THEME_NAME="eitas-account"
THEME_VERSION="26.7.0-eitas.38"

STAGE="$ROOT/build/account-theme-stage"
OUTPUT="$ROOT/build/eitas-identity-account-theme-${THEME_VERSION}.jar"

echo "============================================================"
echo " CONSTRUCTION DU THÈME ACCOUNT EITAS"
echo "============================================================"

test -f "$ACCOUNT_ROOT/package.json"
test -f "$ACCOUNT_ROOT/pnpm-lock.yaml"
test -f "$ACCOUNT_ROOT/src/App.tsx"
test -f "$ACCOUNT_ROOT/maven-resources/META-INF/keycloak-themes.json"
test -d "$ACCOUNT_ROOT/maven-resources/theme/$THEME_NAME/account"

echo
echo "=== 1. BUILD REACT ==="

cd "$ACCOUNT_ROOT"

pnpm run build

test -d dist
test -f dist/.vite/manifest.json

echo
echo "=== 2. PRÉPARATION DU PAQUET ==="

rm -rf "$STAGE"

install -d \
  -o root \
  -g root \
  -m 0755 \
  "$STAGE"

cp -a \
  "$ACCOUNT_ROOT/maven-resources/." \
  "$STAGE/"

RESOURCE_TARGET="$STAGE/theme/$THEME_NAME/account/resources"

install -d \
  -o root \
  -g root \
  -m 0755 \
  "$RESOURCE_TARGET"

cp -a \
  "$ACCOUNT_ROOT/dist/." \
  "$RESOURCE_TARGET/"

test -f "$STAGE/META-INF/keycloak-themes.json"
test -f "$STAGE/theme/$THEME_NAME/account/index.ftl"
test -f "$STAGE/theme/$THEME_NAME/account/theme.properties"
test -f "$RESOURCE_TARGET/.vite/manifest.json"

echo "Arborescence du paquet : OK"

echo
echo "=== 3. CRÉATION REPRODUCTIBLE DU JAR ==="

install -d \
  -o root \
  -g root \
  -m 0755 \
  "$ROOT/build"

python3 - \
  "$STAGE" \
  "$OUTPUT" <<'PYTHON_JAR'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import stat
import sys

source_root = Path(sys.argv[1])
output_path = Path(sys.argv[2])

if output_path.exists():
    output_path.unlink()

files = sorted(
    path
    for path in source_root.rglob("*")
    if path.is_file()
)

if not files:
    raise SystemExit("Aucun fichier à intégrer au JAR.")

with ZipFile(
    output_path,
    mode="w",
    compression=ZIP_DEFLATED,
    compresslevel=9,
) as archive:
    for source_path in files:
        relative_path = source_path.relative_to(
            source_root
        ).as_posix()

        info = ZipInfo(
            filename=relative_path,
            date_time=(1980, 1, 1, 0, 0, 0),
        )

        info.create_system = 3
        info.compress_type = ZIP_DEFLATED
        info.external_attr = (
            stat.S_IFREG | 0o644
        ) << 16

        archive.writestr(
            info,
            source_path.read_bytes(),
            compress_type=ZIP_DEFLATED,
            compresslevel=9,
        )

print(f"{len(files)} fichiers intégrés.")
PYTHON_JAR

chmod 0644 "$OUTPUT"

test -s "$OUTPUT"

echo
echo "=== 4. VALIDATION DU CONTENU ==="

python3 - \
  "$OUTPUT" \
  "$THEME_NAME" <<'PYTHON_VALIDATE'
from zipfile import ZipFile
import json
import sys

archive_path = sys.argv[1]
theme_name = sys.argv[2]

required_files = {
    "META-INF/keycloak-themes.json",
    f"theme/{theme_name}/account/index.ftl",
    f"theme/{theme_name}/account/theme.properties",
    (
        f"theme/{theme_name}/account/resources/"
        ".vite/manifest.json"
    ),
    (
        f"theme/{theme_name}/account/resources/img/"
        "eitas-favicon.svg"
    ),
    (
        f"theme/{theme_name}/account/messages/"
        "messages_fr.properties"
    ),
    (
        f"theme/{theme_name}/account/messages/"
        "messages_en.properties"
    ),
}

with ZipFile(archive_path) as archive:
    names = set(archive.namelist())

    missing = required_files - names

    if missing:
        print("Fichiers manquants :")
        for name in sorted(missing):
            print(f"  {name}")
        raise SystemExit(1)

    metadata = json.loads(
        archive.read(
            "META-INF/keycloak-themes.json"
        ).decode("utf-8")
    )

themes = metadata.get("themes", [])

valid_theme = any(
    theme.get("name") == theme_name
    and "account" in theme.get("types", [])
    for theme in themes
)

if not valid_theme:
    raise SystemExit(
        "Le thème Account EITAS est absent "
        "de keycloak-themes.json."
    )

asset_files = [
    name
    for name in names
    if name.startswith(
        f"theme/{theme_name}/account/resources/assets/"
    )
]

if not asset_files:
    raise SystemExit(
        "Aucune ressource React compilée trouvée."
    )

print("Métadonnées Keycloak : OK")
print(f"Ressources compilées  : {len(asset_files)}")
PYTHON_VALIDATE

HASH="$(
    sha256sum "$OUTPUT" |
    awk '{print $1}'
)"

SIZE="$(
    du -h "$OUTPUT" |
    awk '{print $1}'
)"

echo
echo "JAR    : $OUTPUT"
echo "Taille : $SIZE"
echo "SHA256 : $HASH"

echo
echo "============================================================"
echo " THÈME ACCOUNT CONSTRUIT"
echo "============================================================"
