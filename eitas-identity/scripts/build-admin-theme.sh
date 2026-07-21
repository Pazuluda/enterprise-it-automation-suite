#!/usr/bin/env bash

set -Eeuo pipefail

ROOT="$(
    cd "$(
        dirname "${BASH_SOURCE[0]}"
    )/.." &&
    pwd
)"

VERSION="26.7.0-eitas.10"
THEME_NAME="eitas-admin"

OFFICIAL_JAR="$ROOT/runtime/keycloak-26.7.0-eitas-preprod/lib/lib/main/org.keycloak.keycloak-admin-ui-26.7.0.jar"
OVERLAY="$ROOT/overlay/themes/eitas-admin"
OUTPUT="$ROOT/build/eitas-identity-admin-theme-${VERSION}.jar"

TMP_DIR="$(
    mktemp -d \
      /tmp/eitas-build-admin-theme.XXXXXX
)"

cleanup() {
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT

SOURCE_DIR="$TMP_DIR/source"
PACKAGE_DIR="$TMP_DIR/package"

install -d -m 0700 \
  "$SOURCE_DIR" \
  "$PACKAGE_DIR"

install -d -m 0755 \
  "$ROOT/build"

test -s "$OFFICIAL_JAR"
test -s "$OVERLAY/theme.properties"
test -s "$OVERLAY/resources/css/eitas-admin-v3.css"
test -s "$OVERLAY/resources/js/eitas-admin-v5.js"
test -s "$OVERLAY/resources/img/eitas-identity.svg"
test -s "$OVERLAY/resources/img/eitas-favicon.svg"

unzip -q \
  "$OFFICIAL_JAR" \
  'theme/keycloak.v2/admin/*' \
  -d "$SOURCE_DIR"

test -d \
  "$SOURCE_DIR/theme/keycloak.v2/admin"

install -d -m 0755 \
  "$PACKAGE_DIR/theme/$THEME_NAME"

cp -a \
  "$SOURCE_DIR/theme/keycloak.v2/admin" \
  "$PACKAGE_DIR/theme/$THEME_NAME/admin"

install -m 0644 \
  "$OVERLAY/theme.properties" \
  "$PACKAGE_DIR/theme/$THEME_NAME/admin/theme.properties"

install -d -m 0755 \
  "$PACKAGE_DIR/theme/$THEME_NAME/admin/resources/css" \
  "$PACKAGE_DIR/theme/$THEME_NAME/admin/resources/js" \
  "$PACKAGE_DIR/theme/$THEME_NAME/admin/resources/img" \
  "$PACKAGE_DIR/META-INF"

install -m 0644 \
  "$OVERLAY/resources/css/eitas-admin-v3.css" \
  "$PACKAGE_DIR/theme/$THEME_NAME/admin/resources/css/eitas-admin-v3.css"

install -m 0644 \
    "$OVERLAY/resources/js/eitas-admin-v5.js" \
    "$PACKAGE_DIR/theme/$THEME_NAME/admin/resources/js/eitas-admin-v5.js"

install -m 0644 \
  "$OVERLAY/resources/img/eitas-identity.svg" \
  "$PACKAGE_DIR/theme/$THEME_NAME/admin/resources/img/eitas-identity.svg"

install -m 0644 \
  "$OVERLAY/resources/img/eitas-favicon.svg" \
  "$PACKAGE_DIR/theme/$THEME_NAME/admin/resources/img/eitas-favicon.svg"

cat > "$PACKAGE_DIR/META-INF/MANIFEST.MF" <<MANIFEST
Manifest-Version: 1.0
Implementation-Title: EITAS Identity Admin Theme
Implementation-Version: $VERSION
Implementation-Vendor: EITAS
MANIFEST

cat > "$PACKAGE_DIR/META-INF/keycloak-themes.json" <<JSON
{
  "themes": [
    {
      "name": "$THEME_NAME",
      "types": [
        "admin"
      ]
    }
  ]
}
JSON

rm -f "$OUTPUT"

python3 - \
  "$PACKAGE_DIR" \
  "$OUTPUT" <<'PYTHON'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import stat
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])

files = sorted(
    item
    for item in source.rglob("*")
    if item.is_file()
)

manifest = source / "META-INF/MANIFEST.MF"

if manifest not in files:
    raise SystemExit("Manifest absent")

files.remove(manifest)
files.insert(0, manifest)

with ZipFile(
    output,
    "w",
    compression=ZIP_DEFLATED,
    compresslevel=9,
) as archive:
    for path in files:
        relative = path.relative_to(source).as_posix()

        info = ZipInfo(
            relative,
            date_time=(1980, 1, 1, 0, 0, 0),
        )

        info.compress_type = ZIP_DEFLATED
        info.create_system = 3
        info.external_attr = (
            stat.S_IFREG | 0o644
        ) << 16

        archive.writestr(
            info,
            path.read_bytes(),
        )

output.chmod(0o644)
PYTHON

test -s "$OUTPUT"

echo "JAR    : $OUTPUT"
echo "Taille : $(du -h "$OUTPUT" | awk '{print $1}')"
echo "SHA256 : $(sha256sum "$OUTPUT" | awk '{print $1}')"
