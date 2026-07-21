#!/bin/bash
set -euo pipefail

ROOT="/opt/eitas-identity"
THEME_SOURCE="$ROOT/overlay/themes/eitas"
BUILD_DIR="$ROOT/build"

VERSION="$(
    awk -F= \
      '$1 == "EITAS_IDENTITY_VERSION" { print $2 }' \
      "$ROOT/VERSION"
)"

if [ -z "$VERSION" ]; then
    echo "ERREUR : version EITAS Identity introuvable."
    exit 1
fi

ARCHIVE="$BUILD_DIR/eitas-identity-theme-${VERSION}.jar"
CHECKSUM="$ARCHIVE.sha256"

REQUIRED_FILES=(
    "$THEME_SOURCE/login/theme.properties"
    "$THEME_SOURCE/login/template.ftl"
    "$THEME_SOURCE/login/resources/css/eitas-login-v3.css"
    "$THEME_SOURCE/login/resources/img/eitas-identity.svg"
    "$THEME_SOURCE/login/messages/messages_fr.properties"
    "$THEME_SOURCE/login/messages/messages_en.properties"
)

for FILE in "${REQUIRED_FILES[@]}"; do
    if [ ! -s "$FILE" ]; then
        echo "ERREUR : fichier absent ou vide : $FILE"
        exit 1
    fi
done

install -d \
  -o root \
  -g root \
  -m 0755 \
  "$BUILD_DIR"

rm -f \
  "$ARCHIVE" \
  "$CHECKSUM"

python3 - \
  "$THEME_SOURCE" \
  "$ARCHIVE" \
  "$VERSION" <<'PYTHON_BUILD'
from __future__ import annotations

import json
import stat
import sys
import zipfile
from pathlib import Path

theme_source = Path(sys.argv[1]).resolve()
archive_path = Path(sys.argv[2]).resolve()
version = sys.argv[3]

if not theme_source.is_dir():
    raise SystemExit(f"Thème absent : {theme_source}")

fixed_datetime = (2026, 1, 1, 0, 0, 0)

manifest = (
    "Manifest-Version: 1.0\r\n"
    "Created-By: EITAS Identity\r\n"
    "Implementation-Title: EITAS Identity Theme\r\n"
    f"Implementation-Version: {version}\r\n"
    "\r\n"
).encode("utf-8")

descriptor = (
    json.dumps(
        {
            "themes": [
                {
                    "name": "eitas",
                    "types": ["login"],
                }
            ]
        },
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")
    + b"\n"
)


def write_entry(
    archive: zipfile.ZipFile,
    name: str,
    content: bytes,
) -> None:
    info = zipfile.ZipInfo(
        filename=name,
        date_time=fixed_datetime,
    )

    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (
        stat.S_IFREG | 0o644
    ) << 16

    archive.writestr(info, content)


with zipfile.ZipFile(
    archive_path,
    mode="w",
    compression=zipfile.ZIP_DEFLATED,
    compresslevel=9,
) as archive:
    write_entry(
        archive,
        "META-INF/MANIFEST.MF",
        manifest,
    )

    write_entry(
        archive,
        "META-INF/keycloak-themes.json",
        descriptor,
    )

    theme_files = sorted(
        path
        for path in theme_source.rglob("*")
        if path.is_file()
    )

    for source_file in theme_files:
        relative_path = source_file.relative_to(
            theme_source
        )

        archive_name = (
            Path("theme")
            / "eitas"
            / relative_path
        ).as_posix()

        write_entry(
            archive,
            archive_name,
            source_file.read_bytes(),
        )

print(f"Archive générée : {archive_path}")
PYTHON_BUILD

chmod 0644 "$ARCHIVE"

sha256sum "$ARCHIVE" > "$CHECKSUM"

chmod 0644 "$CHECKSUM"

echo "Archive : $ARCHIVE"
echo "SHA256  : $(awk '{print $1}' "$CHECKSUM")"
