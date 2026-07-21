#!/bin/bash
set -euo pipefail

ROOT="/opt/eitas-identity"
RUNTIME="$ROOT/runtime/keycloak-26.7.0-eitas"
ENV_FILE="/etc/eitas-identity/eitas-identity-test.env"
KCADM="$RUNTIME/bin/kcadm.sh"

LOCAL_SERVER="http://127.0.0.1:8280/identity-test"
PUBLIC_ROOT="https://10.10.10.11:62443/identity-test"

REALM="eitas-validation"
CLIENT_ID="eitas-theme-preview"
REDIRECT_URI="$PUBLIC_ROOT/theme-preview/callback"

TEMP_DIR="$(
    mktemp -d /tmp/eitas-b3.13-XXXXXX
)"

KCADM_CONFIG="$TEMP_DIR/kcadm.config"
SERVERINFO_FILE="$TEMP_DIR/serverinfo.json"
REALM_FILE="$TEMP_DIR/realm.json"
REALM_RESULT="$TEMP_DIR/realm-result.json"
CLIENT_FILE="$TEMP_DIR/client.json"
CLIENT_RESULT="$TEMP_DIR/client-result.json"
LOGIN_HEADERS="$TEMP_DIR/login-headers.txt"
LOGIN_BODY="$TEMP_DIR/login.html"
CSS_BODY="$TEMP_DIR/eitas.css"
SVG_BODY="$TEMP_DIR/eitas-identity.svg"

cleanup() {
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

echo "============================================================"
echo " B3.13 — REALM DE VALIDATION ET THÈME EITAS"
echo "============================================================"

echo
echo "=== 1. CONTRÔLES PRÉALABLES ==="

test -x "$KCADM"
test -r "$ENV_FILE"

systemctl is-active --quiet nginx.service
systemctl is-active --quiet keycloak.service
systemctl is-active --quiet eitas-identity-test.service

HEALTH_STATUS="$(
    curl -fsS \
      http://127.0.0.1:9100/health/ready |
    python3 -c \
      'import json,sys; print(json.load(sys.stdin).get("status",""))'
)"

echo "Santé EITAS Identity : $HEALTH_STATUS"
test "$HEALTH_STATUS" = "UP"

PRODUCTION_CODE="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      https://10.10.10.11:62443/auth/realms/eitas/.well-known/openid-configuration
)"

echo "OIDC production /auth : $PRODUCTION_CODE"
test "$PRODUCTION_CODE" = "200"

echo
echo "=== 2. LECTURE DES IDENTIFIANTS ADMINISTRATEUR ==="

ADMIN_USERNAME="$(
    sed -n \
      's/^KC_BOOTSTRAP_ADMIN_USERNAME=//p' \
      "$ENV_FILE"
)"

ADMIN_PASSWORD="$(
    sed -n \
      's/^KC_BOOTSTRAP_ADMIN_PASSWORD=//p' \
      "$ENV_FILE"
)"

if [ -z "$ADMIN_USERNAME" ]; then
    echo "ERREUR : administrateur bootstrap introuvable."
    exit 1
fi

if [ -z "$ADMIN_PASSWORD" ]; then
    echo "ERREUR : mot de passe bootstrap introuvable."
    exit 1
fi

echo "Administrateur détecté : $ADMIN_USERNAME"
echo "Mot de passe affiché    : non"

touch "$KCADM_CONFIG"
chmod 0600 "$KCADM_CONFIG"

echo
echo "=== 3. AUTHENTIFICATION KCADM LOCALE ==="

"$KCADM" \
  config credentials \
  --config "$KCADM_CONFIG" \
  --server "$LOCAL_SERVER" \
  --realm master \
  --user "$ADMIN_USERNAME" \
  --password "$ADMIN_PASSWORD"

echo "Authentification administrateur : OK"

echo
echo "=== 4. VÉRIFICATION DU THÈME INSTALLÉ ==="

"$KCADM" \
  get serverinfo \
  --config "$KCADM_CONFIG" \
  > "$SERVERINFO_FILE"

python3 - "$SERVERINFO_FILE" <<'PYTHON_THEME'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)

found = False


def inspect(value):
    global found

    if isinstance(value, dict):
        if value.get("name") == "eitas":
            found = True

        for child in value.values():
            inspect(child)

    elif isinstance(value, list):
        for child in value:
            inspect(child)


inspect(payload)

if not found:
    print("ERREUR : le thème eitas n’est pas déclaré par le serveur.")
    raise SystemExit(1)

print("Thème eitas déclaré par Keycloak : OK")
PYTHON_THEME

echo
echo "=== 5. DÉFINITION DU REALM DE VALIDATION ==="

cat > "$REALM_FILE" <<'REALM_JSON'
{
  "realm": "eitas-validation",
  "enabled": true,
  "displayName": "EITAS Identity — Validation",
  "loginTheme": "eitas",
  "internationalizationEnabled": true,
  "supportedLocales": [
    "fr",
    "en"
  ],
  "defaultLocale": "fr",
  "registrationAllowed": false,
  "registrationEmailAsUsername": false,
  "rememberMe": true,
  "verifyEmail": false,
  "resetPasswordAllowed": true,
  "editUsernameAllowed": false,
  "bruteForceProtected": true,
  "permanentLockout": false,
  "failureFactor": 5,
  "waitIncrementSeconds": 60,
  "minimumQuickLoginWaitSeconds": 60,
  "maxFailureWaitSeconds": 900,
  "maxDeltaTimeSeconds": 43200,
  "quickLoginCheckMilliSeconds": 1000
}
REALM_JSON

if "$KCADM" \
  get "realms/$REALM" \
  --config "$KCADM_CONFIG" \
  >/dev/null 2>&1
then
    "$KCADM" \
      update "realms/$REALM" \
      --config "$KCADM_CONFIG" \
      -f "$REALM_FILE"

    echo "Realm actualisé : $REALM"
else
    "$KCADM" \
      create realms \
      --config "$KCADM_CONFIG" \
      -f "$REALM_FILE"

    echo "Realm créé : $REALM"
fi

echo
echo "=== 6. VALIDATION DU REALM ==="

"$KCADM" \
  get "realms/$REALM" \
  --config "$KCADM_CONFIG" \
  > "$REALM_RESULT"

python3 - "$REALM_RESULT" <<'PYTHON_REALM'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    realm = json.load(stream)

expected = {
    "realm": "eitas-validation",
    "enabled": True,
    "loginTheme": "eitas",
    "internationalizationEnabled": True,
    "defaultLocale": "fr",
    "bruteForceProtected": True,
}

failed = False

for key, expected_value in expected.items():
    actual_value = realm.get(key)

    if actual_value == expected_value:
        print(f"{key}: {actual_value} — OK")
    else:
        print(
            f"{key}: attendu={expected_value!r}, "
            f"obtenu={actual_value!r} — ERREUR"
        )
        failed = True

locales = set(realm.get("supportedLocales") or [])

if locales == {"fr", "en"}:
    print("supportedLocales: fr,en — OK")
else:
    print(f"supportedLocales: {sorted(locales)} — ERREUR")
    failed = True

if failed:
    raise SystemExit(1)
PYTHON_REALM

echo
echo "=== 7. CLIENT DE PRÉVISUALISATION ==="

cat > "$CLIENT_FILE" <<CLIENT_JSON
{
  "clientId": "$CLIENT_ID",
  "name": "EITAS Identity Theme Preview",
  "description": "Client interne utilisé pour valider le thème de connexion EITAS.",
  "enabled": true,
  "protocol": "openid-connect",
  "publicClient": true,
  "standardFlowEnabled": true,
  "implicitFlowEnabled": false,
  "directAccessGrantsEnabled": false,
  "serviceAccountsEnabled": false,
  "frontchannelLogout": true,
  "rootUrl": "$PUBLIC_ROOT",
  "baseUrl": "$PUBLIC_ROOT/",
  "redirectUris": [
    "$PUBLIC_ROOT/theme-preview/*"
  ],
  "webOrigins": [
    "https://10.10.10.11:62443"
  ]
}
CLIENT_JSON

"$KCADM" \
  get clients \
  --config "$KCADM_CONFIG" \
  -r "$REALM" \
  -q "clientId=$CLIENT_ID" \
  > "$CLIENT_RESULT"

CLIENT_UUID="$(
    python3 - "$CLIENT_RESULT" <<'PYTHON_CLIENT_ID'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    clients = json.load(stream)

if clients:
    print(clients[0].get("id", ""))
PYTHON_CLIENT_ID
)"

if [ -n "$CLIENT_UUID" ]; then
    "$KCADM" \
      update "clients/$CLIENT_UUID" \
      --config "$KCADM_CONFIG" \
      -r "$REALM" \
      -f "$CLIENT_FILE"

    echo "Client actualisé : $CLIENT_ID"
else
    CLIENT_UUID="$(
        "$KCADM" \
          create clients \
          --config "$KCADM_CONFIG" \
          -r "$REALM" \
          -f "$CLIENT_FILE" \
          -i
    )"

    echo "Client créé : $CLIENT_ID"
fi

test -n "$CLIENT_UUID"

echo "Identifiant interne du client : présent"

echo
echo "=== 8. ENDPOINT OIDC DU REALM ==="

OIDC_FILE="$TEMP_DIR/realm-oidc.json"

OIDC_CODE="$(
    curl -k -sS \
      -o "$OIDC_FILE" \
      -w '%{http_code}' \
      "$PUBLIC_ROOT/realms/$REALM/.well-known/openid-configuration"
)"

echo "OIDC $REALM : HTTP $OIDC_CODE"
test "$OIDC_CODE" = "200"

python3 - "$OIDC_FILE" <<'PYTHON_OIDC'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)

issuer = payload.get("issuer")

expected = (
    "https://10.10.10.11:62443/"
    "identity-test/realms/eitas-validation"
)

print(f"Issuer obtenu  : {issuer}")
print(f"Issuer attendu : {expected}")

if issuer != expected:
    raise SystemExit(1)
PYTHON_OIDC

echo
echo "=== 9. CHARGEMENT DE LA PAGE DE CONNEXION ==="

LOGIN_CODE="$(
    curl -k -sS \
      -G \
      -H 'Accept-Language: fr' \
      -D "$LOGIN_HEADERS" \
      -o "$LOGIN_BODY" \
      -w '%{http_code}' \
      --data-urlencode "client_id=$CLIENT_ID" \
      --data-urlencode "redirect_uri=$REDIRECT_URI" \
      --data-urlencode "response_type=code" \
      --data-urlencode "scope=openid" \
      "$PUBLIC_ROOT/realms/$REALM/protocol/openid-connect/auth"
)"

echo "Page de connexion : HTTP $LOGIN_CODE"
test "$LOGIN_CODE" = "200"

grep -q 'eitas.css' "$LOGIN_BODY"
echo "Feuille eitas.css référencée : OK"

grep -q 'EITAS Identity' "$LOGIN_BODY"
echo "Identité EITAS présente dans la page : OK"

echo
echo "=== 10. VALIDATION DU CSS ET DU LOGO ==="

CSS_URL="$(
    python3 - "$LOGIN_BODY" \
      "$PUBLIC_ROOT/realms/$REALM/protocol/openid-connect/auth" \
      <<'PYTHON_CSS_URL'
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import sys


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attributes):
        if tag.lower() != "link":
            return

        values = dict(attributes)
        href = values.get("href", "")

        if "eitas.css" in href:
            self.hrefs.append(href)


body = Path(sys.argv[1]).read_text(
    encoding="utf-8",
    errors="replace",
)

parser = LinkParser()
parser.feed(body)

if not parser.hrefs:
    raise SystemExit("URL eitas.css introuvable.")

print(urljoin(sys.argv[2], parser.hrefs[0]))
PYTHON_CSS_URL
)"

echo "CSS : $CSS_URL"

CSS_CODE="$(
    curl -k -sS \
      -o "$CSS_BODY" \
      -w '%{http_code}' \
      "$CSS_URL"
)"

echo "Chargement CSS : HTTP $CSS_CODE"
test "$CSS_CODE" = "200"

grep -q 'eitas-identity.svg' "$CSS_BODY"
echo "Logo déclaré dans le CSS : OK"

SVG_URL="$(
    python3 - "$CSS_URL" <<'PYTHON_SVG_URL'
from urllib.parse import urljoin
import sys

print(
    urljoin(
        sys.argv[1],
        "../img/eitas-identity.svg",
    )
)
PYTHON_SVG_URL
)"

echo "Logo : $SVG_URL"

SVG_CODE="$(
    curl -k -sS \
      -o "$SVG_BODY" \
      -w '%{http_code}' \
      "$SVG_URL"
)"

echo "Chargement SVG : HTTP $SVG_CODE"
test "$SVG_CODE" = "200"

grep -q '<svg' "$SVG_BODY"
grep -q 'EITAS Identity' "$SVG_BODY"

echo "Logo SVG EITAS valide : OK"

echo
echo "=== 11. DOCUMENTATION NON SENSIBLE ==="

cat > "$ROOT/docs/validation-realm.md" <<'DOCUMENTATION'
# Realm de validation EITAS Identity

## Realm

- Nom : `eitas-validation`
- État : activé
- Thème de connexion : `eitas`
- Internationalisation : activée
- Langue par défaut : français
- Langues disponibles : français et anglais
- Protection brute force : activée

## Client de prévisualisation

- Client ID : `eitas-theme-preview`
- Type : public
- Authorization Code : activé
- Implicit Flow : désactivé
- Direct Access Grants : désactivé
- Service Account : désactivé

Ce client est destiné uniquement à la validation de l’interface de
connexion de l’instance parallèle.
DOCUMENTATION

chmod 0644 "$ROOT/docs/validation-realm.md"

echo
echo "=== 12. NON-RÉGRESSION FINALE ==="

FINAL_PRODUCTION_CODE="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      https://10.10.10.11:62443/auth/realms/eitas/.well-known/openid-configuration
)"

echo "OIDC production /auth : $FINAL_PRODUCTION_CODE"

test "$FINAL_PRODUCTION_CODE" = "200"
systemctl is-active --quiet keycloak.service

echo
echo "=== 13. ÉTAT GIT ET DISQUE ==="

git status --short
df -h /

echo
echo "============================================================"
echo " B3.13 VALIDÉE"
echo " Realm : $REALM"
echo " Thème de connexion : eitas"
echo
echo " Prévisualisation :"
echo " $PUBLIC_ROOT/realms/$REALM/account/"
echo
echo " Console administrateur :"
echo " $PUBLIC_ROOT/admin/master/console/#/$REALM"
echo
echo " Production /auth inchangée"
echo " AVANCEMENT ESTIMÉ DU PACK B3 : 77 %"
echo "============================================================"
