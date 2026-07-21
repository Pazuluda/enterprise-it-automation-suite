#!/bin/bash
set -euo pipefail

ROOT="/opt/eitas-identity"
ACCOUNT_ROOT="$ROOT/ui/account-console"

RUNTIME="$ROOT/runtime/keycloak-26.7.0-eitas"
PROVIDERS="$RUNTIME/providers"
LOCK_FILE="$RUNTIME/EITAS-RUNTIME.lock"

SERVICE="eitas-identity-test.service"
ENV_FILE="/etc/eitas-identity/eitas-identity-test.env"

REALM="eitas-validation"
THEME_NAME="eitas-account"
THEME_VERSION="26.7.0-eitas.31"

JAR_NAME="eitas-identity-account-theme-${THEME_VERSION}.jar"
SOURCE_JAR="$ROOT/build/$JAR_NAME"
INSTALLED_JAR="$PROVIDERS/$JAR_NAME"

KCADM="$RUNTIME/bin/kcadm.sh"

BACKUP_DIR="/var/backups/eitas-identity/b3.16.7-account-theme-$(date +%Y%m%d-%H%M%S)"
KCADM_CONFIG="$(mktemp /tmp/eitas-b3.16.7-kcadm-XXXXXX)"
SERVER_INFO="$(mktemp /tmp/eitas-b3.16.7-serverinfo-XXXXXX.json)"
REALM_INFO="$(mktemp /tmp/eitas-b3.16.7-realm-XXXXXX.json)"

cleanup() {
    rm -f \
      "$KCADM_CONFIG" \
      "$SERVER_INFO" \
      "$REALM_INFO"
}

trap cleanup EXIT

run_keycloak_build() {
    local KC_FEATURES_VALUE
    local KC_FEATURES_DISABLED_VALUE
    local -a BUILD_ENV

    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a

    KC_FEATURES_VALUE="${KC_FEATURES:-}"
    KC_FEATURES_DISABLED_VALUE="${KC_FEATURES_DISABLED:-}"

    if [ -z "$KC_FEATURES_VALUE" ]; then
        echo "ERREUR : KC_FEATURES absent de $ENV_FILE."
        return 1
    fi

    case ",$KC_FEATURES_VALUE," in
        *,oid4vc-vci,*|*,oid4vc-vci:v1,*)
            echo "Feature de build : $KC_FEATURES_VALUE"
            ;;
        *)
            echo "ERREUR : oid4vc-vci absent de KC_FEATURES."
            return 1
            ;;
    esac

    BUILD_ENV=(
        env
    )

    if [ -n "$KC_FEATURES_DISABLED_VALUE" ]; then
        BUILD_ENV+=(
            "KC_FEATURES_DISABLED=$KC_FEATURES_DISABLED_VALUE"
        )
    else
        BUILD_ENV+=(
            -u KC_FEATURES_DISABLED
        )
    fi

    BUILD_ENV+=(
        "HOME=/var/lib/eitas-identity"
        "KC_FEATURES=$KC_FEATURES_VALUE"
    )

    runuser \
      -u eitas-identity \
      -- \
      "${BUILD_ENV[@]}" \
      "$RUNTIME/bin/kc.sh" \
      build \
      --db=postgres \
      --health-enabled=true \
      --metrics-enabled=true \
      --http-relative-path=/identity-test \
      --http-management-health-enabled=true \
      --http-management-relative-path=/
}

restore_runtime() {
    echo
    echo "=== RESTAURATION DU RUNTIME ==="

    rm -f "$INSTALLED_JAR"

    if [ -d "$BACKUP_DIR/providers" ]; then
        find "$BACKUP_DIR/providers" \
          -maxdepth 1 \
          -type f \
          -name 'eitas-identity-account-theme-*.jar' \
          -exec mv -t "$PROVIDERS" {} +
    fi

    run_keycloak_build || true
    systemctl start "$SERVICE" || true
}

echo "============================================================"
echo " B3.16.7 — DÉPLOIEMENT ACCOUNT EITAS"
echo "============================================================"

echo
echo "=== 1. CONTRÔLES PRÉALABLES ==="

test -x "$ROOT/scripts/build-account-theme.sh"
test -x "$KCADM"
test -r "$ENV_FILE"
test -d "$PROVIDERS"

systemctl is-active --quiet nginx.service
systemctl is-active --quiet keycloak.service
systemctl is-active --quiet "$SERVICE"

PRODUCTION_BEFORE="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      https://10.10.10.11:62443/auth/realms/eitas/.well-known/openid-configuration
)"

IDENTITY_BEFORE="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      https://10.10.10.11:62443/identity-test/realms/eitas-validation/.well-known/openid-configuration
)"

echo "Production /auth : HTTP $PRODUCTION_BEFORE"
echo "EITAS Identity   : HTTP $IDENTITY_BEFORE"

test "$PRODUCTION_BEFORE" = "200"
test "$IDENTITY_BEFORE" = "200"

echo
echo "=== 2. CONSTRUCTION DU JAR ==="

"$ROOT/scripts/build-account-theme.sh"

test -s "$SOURCE_JAR"

SOURCE_HASH="$(
    sha256sum "$SOURCE_JAR" |
    awk '{print $1}'
)"

echo "SHA256 source : $SOURCE_HASH"

echo
echo "=== 3. SAUVEGARDE DU RUNTIME ==="

install -d \
  -o root \
  -g root \
  -m 0700 \
  "$BACKUP_DIR/providers"

while IFS= read -r OLD_JAR; do
    cp -a \
      "$OLD_JAR" \
      "$BACKUP_DIR/providers/"
done < <(
    find "$PROVIDERS" \
      -maxdepth 1 \
      -type f \
      -name 'eitas-identity-account-theme-*.jar' \
      -print
)

cp -a \
  "$LOCK_FILE" \
  "$BACKUP_DIR/EITAS-RUNTIME.lock"

echo "Sauvegarde : $BACKUP_DIR"

echo
echo "=== 4. INSTALLATION DU PROVIDER ==="

systemctl stop "$SERVICE"

find "$PROVIDERS" \
  -maxdepth 1 \
  -type f \
  -name 'eitas-identity-account-theme-*.jar' \
  -delete

install \
  -o eitas-identity \
  -g eitas-identity \
  -m 0644 \
  "$SOURCE_JAR" \
  "$INSTALLED_JAR"

INSTALLED_HASH="$(
    sha256sum "$INSTALLED_JAR" |
    awk '{print $1}'
)"

echo "SHA256 installé : $INSTALLED_HASH"
test "$INSTALLED_HASH" = "$SOURCE_HASH"

echo
echo "=== 5. RECONSTRUCTION DU RUNTIME ==="

if ! run_keycloak_build; then
    echo "ERREUR : la reconstruction Keycloak a échoué."
    restore_runtime
    exit 1
fi

echo "Runtime reconstruit : OK"

echo
echo "=== 6. REDÉMARRAGE DE L’INSTANCE ==="

systemctl start "$SERVICE"

READY=0

for ATTEMPT in $(seq 1 90); do
    if curl -fsS \
      http://127.0.0.1:9100/health/ready \
      > /tmp/eitas-b3.16.7-health.json \
      2>/dev/null
    then
        READY=1
        echo "Instance prête après ${ATTEMPT} tentative(s)."
        break
    fi

    if systemctl is-failed --quiet "$SERVICE"; then
        break
    fi

    sleep 2
done

if [ "$READY" != "1" ]; then
    echo "ERREUR : l’instance ne revient pas en état UP."
    restore_runtime
    exit 1
fi

echo
echo "=== 7. AUTHENTIFICATION ADMINISTRATEUR ==="

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

: "${KC_BOOTSTRAP_ADMIN_USERNAME:?Administrateur absent}"
: "${KC_BOOTSTRAP_ADMIN_PASSWORD:?Mot de passe absent}"

install -m 0600 /dev/null "$KCADM_CONFIG"

"$KCADM" \
  config credentials \
  --config "$KCADM_CONFIG" \
  --server http://127.0.0.1:8280/identity-test \
  --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
  --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"

echo "Authentification administrateur : OK"

echo
echo "=== 8. DÉTECTION DU THÈME INSTALLÉ ==="

"$KCADM" \
  get serverinfo \
  --config "$KCADM_CONFIG" \
  > "$SERVER_INFO"

python3 - \
  "$SERVER_INFO" \
  "$THEME_NAME" <<'PYTHON_SERVER_INFO'
import json
import sys

path = sys.argv[1]
theme_name = sys.argv[2]

with open(path, encoding="utf-8") as stream:
    data = json.load(stream)

def contains_theme(value):
    if isinstance(value, dict):
        if (
            value.get("name") == theme_name
            and (
                value.get("type") in (None, "account")
                or "account" in value.get("types", [])
            )
        ):
            return True

        return any(
            contains_theme(child)
            for child in value.values()
        )

    if isinstance(value, list):
        return any(
            contains_theme(child)
            for child in value
        )

    return value == theme_name

if not contains_theme(data):
    raise SystemExit(
        f"Le thème {theme_name!r} "
        "n’apparaît pas dans serverinfo."
    )

print(f"Thème détecté par Keycloak : {theme_name}")
PYTHON_SERVER_INFO

echo
echo "=== 9. APPLICATION AU REALM DE VALIDATION ==="

"$KCADM" \
  update "realms/$REALM" \
  --config "$KCADM_CONFIG" \
  -s "accountTheme=$THEME_NAME"

"$KCADM" \
  get "realms/$REALM" \
  --config "$KCADM_CONFIG" \
  > "$REALM_INFO"

ACCOUNT_THEME="$(
    python3 - "$REALM_INFO" <<'PYTHON_REALM'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    realm = json.load(stream)

print(realm.get("accountTheme", ""))
PYTHON_REALM
)"

echo "Account Theme du realm : $ACCOUNT_THEME"
test "$ACCOUNT_THEME" = "$THEME_NAME"

echo
echo "=== 10. MISE À JOUR DU VERROU RUNTIME ==="

python3 - \
  "$LOCK_FILE" \
  "$SOURCE_HASH" <<'PYTHON_LOCK'
from pathlib import Path
import sys

path = Path(sys.argv[1])
theme_hash = sys.argv[2]
key = "EITAS_ACCOUNT_THEME_SHA256"

lines = (
    path.read_text(encoding="utf-8").splitlines()
    if path.exists()
    else []
)

result = []
updated = False

for line in lines:
    if line.startswith(f"{key}="):
        result.append(f"{key}={theme_hash}")
        updated = True
    else:
        result.append(line)

if not updated:
    result.append(f"{key}={theme_hash}")

path.write_text(
    "\n".join(result) + "\n",
    encoding="utf-8",
)
PYTHON_LOCK

chown \
  eitas-identity:eitas-identity \
  "$LOCK_FILE"

chmod 0640 "$LOCK_FILE"

grep '^EITAS_ACCOUNT_THEME_SHA256=' \
  "$LOCK_FILE"

echo
echo "=== 11. TESTS PUBLICS ==="

PRODUCTION_AFTER="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      https://10.10.10.11:62443/auth/realms/eitas/.well-known/openid-configuration
)"

IDENTITY_AFTER="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      https://10.10.10.11:62443/identity-test/realms/eitas-validation/.well-known/openid-configuration
)"

ACCOUNT_REDIRECT="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      https://10.10.10.11:62443/identity-test/realms/eitas-validation/account/
)"

ACCOUNT_FINAL="$(
    curl -k -sS \
      -L \
      -o /tmp/eitas-b3.16.7-account-page.html \
      -w '%{http_code}' \
      https://10.10.10.11:62443/identity-test/realms/eitas-validation/account/
)"

echo "Production /auth        : HTTP $PRODUCTION_AFTER"
echo "EITAS Identity          : HTTP $IDENTITY_AFTER"
echo "Account première réponse: HTTP $ACCOUNT_REDIRECT"
echo "Account après redirection: HTTP $ACCOUNT_FINAL"

test "$PRODUCTION_AFTER" = "200"
test "$IDENTITY_AFTER" = "200"
test "$ACCOUNT_FINAL" = "200"

case "$ACCOUNT_REDIRECT" in
    200|302|303)
        ;;
    *)
        echo "Réponse inattendue de l’espace compte."
        exit 1
        ;;
esac

echo
echo "=== 12. ÉTAT DU SERVICE ==="

systemctl is-active "$SERVICE"

curl -fsS \
  http://127.0.0.1:9100/health/ready

echo
echo
echo "=== 13. ÉTAT GIT ET DISQUE ==="

cd "$ROOT"

git status --short
df -h /

echo
echo "============================================================"
echo " B3.16.7 — DÉPLOIEMENT TECHNIQUE VALIDÉ"
echo " Thème installé       : $THEME_NAME"
echo " Realm                : $REALM"
echo " JAR                  : $JAR_NAME"
echo " SHA256               : $SOURCE_HASH"
echo " Production /auth     : HTTP $PRODUCTION_AFTER"
echo " EITAS Identity       : HTTP $IDENTITY_AFTER"
echo " Account Console      : HTTP $ACCOUNT_FINAL"
echo " AVANCEMENT PACK B3   : 100 % — validé"
echo "============================================================"
