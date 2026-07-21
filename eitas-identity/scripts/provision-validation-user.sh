#!/bin/bash
set -euo pipefail

ROOT="/opt/eitas-identity"
RUNTIME="$ROOT/runtime/keycloak-26.7.0-eitas"
ENV_FILE="/etc/eitas-identity/eitas-identity-test.env"
KCADM="$RUNTIME/bin/kcadm.sh"

REALM="eitas-validation"
USERNAME="eitas-validation-user"
EMAIL="validation.user@eitas.local"
FIRST_NAME="Validation"
LAST_NAME="EITAS"

PUBLIC_ROOT="https://10.10.10.11:62443/identity-test"
ACCOUNT_URL="$PUBLIC_ROOT/realms/$REALM/account/"

SECRET_FILE="/etc/eitas-identity/eitas-validation-user.secret"

TEMP_DIR="$(
    mktemp -d /tmp/eitas-b3.15-XXXXXX
)"

KCADM_CONFIG="$TEMP_DIR/kcadm.config"
USER_RESULT="$TEMP_DIR/user-result.json"
ACCOUNT_HTML="$TEMP_DIR/account-login.html"

cleanup() {
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

echo "============================================================"
echo " B3.15 — UTILISATEUR DE VALIDATION FONCTIONNELLE"
echo "============================================================"

echo
echo "=== 1. CONTRÔLES PRÉALABLES ==="

test -x "$KCADM"
test -r "$ENV_FILE"

systemctl is-active --quiet nginx.service
systemctl is-active --quiet keycloak.service
systemctl is-active --quiet eitas-identity-test.service
systemctl is-active --quiet postgresql@17-main.service

HEALTH_STATUS="$(
    curl -fsS \
      http://127.0.0.1:9100/health/ready |
    python3 -c \
      'import json,sys; print(json.load(sys.stdin).get("status",""))'
)"

PRODUCTION_CODE="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      https://10.10.10.11:62443/auth/realms/eitas/.well-known/openid-configuration
)"

VALIDATION_CODE="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      "$PUBLIC_ROOT/realms/$REALM/.well-known/openid-configuration"
)"

echo "Santé EITAS Identity : $HEALTH_STATUS"
echo "Production /auth     : HTTP $PRODUCTION_CODE"
echo "Realm de validation  : HTTP $VALIDATION_CODE"

test "$HEALTH_STATUS" = "UP"
test "$PRODUCTION_CODE" = "200"
test "$VALIDATION_CODE" = "200"

echo
echo "=== 2. IDENTIFIANTS ADMINISTRATEUR ==="

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

test -n "$ADMIN_USERNAME"
test -n "$ADMIN_PASSWORD"

echo "Administrateur : $ADMIN_USERNAME"
echo "Mot de passe   : non affiché"

install -m 0600 /dev/null "$KCADM_CONFIG"

echo
echo "=== 3. AUTHENTIFICATION KCADM ==="

"$KCADM" \
  config credentials \
  --config "$KCADM_CONFIG" \
  --server http://127.0.0.1:8280/identity-test \
  --realm master \
  --user "$ADMIN_USERNAME" \
  --password "$ADMIN_PASSWORD"

echo "Authentification administrateur : OK"

echo
echo "=== 4. CONTRÔLE DU REALM ==="

REALM_THEME="$(
    "$KCADM" \
      get "realms/$REALM" \
      --config "$KCADM_CONFIG" \
      --fields loginTheme \
      --format csv \
      --noquotes |
    tail -n 1
)"

echo "Thème du realm : $REALM_THEME"
test "$REALM_THEME" = "eitas"

echo
echo "=== 5. CRÉATION OU ACTUALISATION DE L’UTILISATEUR ==="

"$KCADM" \
  get users \
  --config "$KCADM_CONFIG" \
  -r "$REALM" \
  -q "username=$USERNAME" \
  > "$USER_RESULT"

USER_ID="$(
    python3 - "$USER_RESULT" <<'PYTHON_USER_ID'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    users = json.load(stream)

for user in users:
    if user.get("username") == "eitas-validation-user":
        print(user.get("id", ""))
        break
PYTHON_USER_ID
)"

if [ -z "$USER_ID" ]; then
    USER_ID="$(
        "$KCADM" \
          create users \
          --config "$KCADM_CONFIG" \
          -r "$REALM" \
          -s "username=$USERNAME" \
          -s "email=$EMAIL" \
          -s "firstName=$FIRST_NAME" \
          -s "lastName=$LAST_NAME" \
          -s enabled=true \
          -s emailVerified=true \
          -i
    )"

    echo "Utilisateur créé : $USERNAME"
else
    "$KCADM" \
      update "users/$USER_ID" \
      --config "$KCADM_CONFIG" \
      -r "$REALM" \
      -s "email=$EMAIL" \
      -s "firstName=$FIRST_NAME" \
      -s "lastName=$LAST_NAME" \
      -s enabled=true \
      -s emailVerified=true

    echo "Utilisateur existant actualisé : $USERNAME"
fi

test -n "$USER_ID"

echo "Identifiant interne utilisateur : présent"

echo
echo "=== 6. MOT DE PASSE TEMPORAIRE ALÉATOIRE ==="

TEMPORARY_PASSWORD="$(
    python3 - <<'PYTHON_PASSWORD'
import secrets
import string

alphabet = (
    string.ascii_letters
    + string.digits
    + "-_.!"
)

while True:
    password = "".join(
        secrets.choice(alphabet)
        for _ in range(28)
    )

    if (
        any(character.islower() for character in password)
        and any(character.isupper() for character in password)
        and any(character.isdigit() for character in password)
        and any(character in "-_.!" for character in password)
    ):
        print(password)
        break
PYTHON_PASSWORD
)"

"$KCADM" \
  set-password \
  --config "$KCADM_CONFIG" \
  -r "$REALM" \
  --userid "$USER_ID" \
  --new-password "$TEMPORARY_PASSWORD" \
  --temporary

"$KCADM" \
  update "users/$USER_ID" \
  --config "$KCADM_CONFIG" \
  -r "$REALM" \
  -s 'requiredActions=["UPDATE_PASSWORD"]'

echo "Mot de passe temporaire défini : OK"
echo "Changement obligatoire         : UPDATE_PASSWORD"

echo
echo "=== 7. FICHIER SECRET HORS DU DÉPÔT ==="

install -d \
  -o root \
  -g root \
  -m 0750 \
  /etc/eitas-identity

umask 077

cat > "$SECRET_FILE" <<EOF
USERNAME=$USERNAME
TEMPORARY_PASSWORD=$TEMPORARY_PASSWORD
ACCOUNT_URL=$ACCOUNT_URL
EOF

chown root:root "$SECRET_FILE"
chmod 0600 "$SECRET_FILE"

test "$(stat -c '%a' "$SECRET_FILE")" = "600"
test "$(stat -c '%U:%G' "$SECRET_FILE")" = "root:root"

echo "Secret enregistré : $SECRET_FILE"
echo "Permissions       : 600 root:root"
echo "Secret versionné  : non"

echo
echo "=== 8. VALIDATION DE L’UTILISATEUR ==="

"$KCADM" \
  get "users/$USER_ID" \
  --config "$KCADM_CONFIG" \
  -r "$REALM" \
  > "$USER_RESULT"

python3 - "$USER_RESULT" <<'PYTHON_VALIDATE'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    user = json.load(stream)

checks = {
    "username": "eitas-validation-user",
    "email": "validation.user@eitas.local",
    "firstName": "Validation",
    "lastName": "EITAS",
    "enabled": True,
    "emailVerified": True,
}

failed = False

for key, expected in checks.items():
    actual = user.get(key)

    if actual == expected:
        print(f"{key}: {actual} — OK")
    else:
        print(
            f"{key}: attendu={expected!r}, "
            f"obtenu={actual!r} — ERREUR"
        )
        failed = True

required_actions = user.get("requiredActions") or []

if "UPDATE_PASSWORD" in required_actions:
    print("UPDATE_PASSWORD : présent — OK")
else:
    print("UPDATE_PASSWORD : absent — ERREUR")
    failed = True

if failed:
    raise SystemExit(1)
PYTHON_VALIDATE

echo
echo "=== 9. PAGE DE CONNEXION DU COMPTE ==="

ACCOUNT_CODE="$(
    curl -k -sS \
      -L \
      -H 'Accept-Language: fr' \
      -H 'Cache-Control: no-cache' \
      -o "$ACCOUNT_HTML" \
      -w '%{http_code}' \
      "$ACCOUNT_URL"
)"

echo "Page compte/connexion : HTTP $ACCOUNT_CODE"
test "$ACCOUNT_CODE" = "200"

grep -q 'eitas.css' "$ACCOUNT_HTML"
echo "Thème EITAS chargé : OK"

echo
echo "=== 10. DOCUMENTATION NON SENSIBLE ==="

cat > "$ROOT/docs/validation-user.md" <<EOF
# Utilisateur de validation fonctionnelle

- Realm : \`$REALM\`
- Utilisateur : \`$USERNAME\`
- Adresse e-mail : \`$EMAIL\`
- État : activé
- Adresse e-mail vérifiée : oui
- Changement initial du mot de passe : obligatoire
- Espace compte : \`$ACCOUNT_URL\`

Le mot de passe temporaire n'est pas conservé dans le dépôt Git.
Il est enregistré localement dans un fichier protégé sous
\`/etc/eitas-identity\`.
EOF

chmod 0644 "$ROOT/docs/validation-user.md"

echo
echo "=== 11. NON-RÉGRESSION FINALE ==="

FINAL_PRODUCTION_CODE="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      https://10.10.10.11:62443/auth/realms/eitas/.well-known/openid-configuration
)"

FINAL_VALIDATION_CODE="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      "$PUBLIC_ROOT/realms/$REALM/.well-known/openid-configuration"
)"

echo "Production /auth    : HTTP $FINAL_PRODUCTION_CODE"
echo "Realm de validation : HTTP $FINAL_VALIDATION_CODE"

test "$FINAL_PRODUCTION_CODE" = "200"
test "$FINAL_VALIDATION_CODE" = "200"

echo
echo "=== 12. ÉTAT GIT ET DISQUE ==="

git status --short
df -h /

echo
echo "============================================================"
echo " B3.15 — PRÉPARATION VALIDÉE"
echo " Utilisateur : $USERNAME"
echo " Mot de passe temporaire : non affiché"
echo " Secret : $SECRET_FILE"
echo " Compte : $ACCOUNT_URL"
echo " Production /auth inchangée"
echo " AVANCEMENT ESTIMÉ DU PACK B3 : 85 %"
echo "============================================================"
