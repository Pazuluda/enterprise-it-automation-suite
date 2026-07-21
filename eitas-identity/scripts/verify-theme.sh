#!/bin/bash
set -euo pipefail

ROOT="/opt/eitas-identity"
THEME="$ROOT/overlay/themes/eitas"
LOGIN="$THEME/login"

REQUIRED_FILES=(
    "$LOGIN/theme.properties"
    "$LOGIN/resources/css/eitas.css"
    "$LOGIN/resources/img/eitas-identity.svg"
    "$LOGIN/messages/messages_fr.properties"
    "$LOGIN/messages/messages_en.properties"
    "$THEME/README.md"
)

FAILED=0

for FILE in "${REQUIRED_FILES[@]}"; do
    if [ -s "$FILE" ]; then
        echo "Présent : $FILE"
    else
        echo "ERREUR : fichier absent ou vide : $FILE"
        FAILED=1
    fi
done

if grep -qx 'parent=keycloak.v2' "$LOGIN/theme.properties"; then
    echo "Parent keycloak.v2 : OK"
else
    echo "Parent keycloak.v2 : ERREUR"
    FAILED=1
fi

if grep -qx 'styles=css/styles.css css/eitas.css' "$LOGIN/theme.properties"; then
    echo "Feuille CSS déclarée : OK"
else
    echo "Feuille CSS déclarée : ERREUR"
    FAILED=1
fi

if grep -qx 'locales=fr,en' "$LOGIN/theme.properties"; then
    echo "Langues fr/en : OK"
else
    echo "Langues fr/en : ERREUR"
    FAILED=1
fi

if git -C "$ROOT/source/keycloak" diff --quiet &&
   git -C "$ROOT/source/keycloak" diff --cached --quiet &&
   [ -z "$(
       git -C "$ROOT/source/keycloak" status --porcelain
   )" ]; then
    echo "Source Keycloak non modifié : OK"
else
    echo "Source Keycloak non modifié : ERREUR"
    git -C "$ROOT/source/keycloak" status --short
    FAILED=1
fi

if [ "$FAILED" -ne 0 ]; then
    echo
    echo "VALIDATION DU THÈME : ÉCHEC"
    exit 1
fi

echo
echo "VALIDATION DU THÈME : OK"
