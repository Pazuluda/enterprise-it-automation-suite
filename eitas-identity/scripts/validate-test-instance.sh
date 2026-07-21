#!/bin/bash
set -euo pipefail

PUBLIC_ROOT="https://10.10.10.11:62443"
SERVICE="eitas-identity-test.service"

echo "=== Services ==="

systemctl is-active --quiet nginx.service
systemctl is-active --quiet keycloak.service
systemctl is-active --quiet "$SERVICE"

echo "Nginx              : actif"
echo "Keycloak production: actif"
echo "EITAS Identity     : actif"

echo
echo "=== Santé locale ==="

HEALTH_FILE="/tmp/eitas-identity-validation-health.json"

curl -fsS \
  http://127.0.0.1:9100/health/ready \
  > "$HEALTH_FILE"

python3 - "$HEALTH_FILE" <<'PYTHON_HEALTH'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)

status = payload.get("status")

print(f"Health ready : {status}")

if status != "UP":
    raise SystemExit(1)
PYTHON_HEALTH

echo
echo "=== OIDC interne et public ==="

LOCAL_CODE="$(
    curl -sS \
      -o /dev/null \
      -w '%{http_code}' \
      http://127.0.0.1:8280/identity-test/realms/master/.well-known/openid-configuration
)"

PUBLIC_FILE="/tmp/eitas-identity-validation-oidc.json"

PUBLIC_CODE="$(
    curl -k -sS \
      -o "$PUBLIC_FILE" \
      -w '%{http_code}' \
      "$PUBLIC_ROOT/identity-test/realms/master/.well-known/openid-configuration"
)"

PRODUCTION_CODE="$(
    curl -k -sS \
      -o /dev/null \
      -w '%{http_code}' \
      "$PUBLIC_ROOT/auth/realms/eitas/.well-known/openid-configuration"
)"

echo "OIDC interne    : HTTP $LOCAL_CODE"
echo "OIDC public     : HTTP $PUBLIC_CODE"
echo "OIDC production : HTTP $PRODUCTION_CODE"

test "$LOCAL_CODE" = "200"
test "$PUBLIC_CODE" = "200"
test "$PRODUCTION_CODE" = "200"

python3 - "$PUBLIC_FILE" <<'PYTHON_OIDC'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)

issuer = payload.get("issuer")

expected = (
    "https://10.10.10.11:62443/"
    "identity-test/realms/master"
)

print(f"Issuer : {issuer}")

if issuer != expected:
    raise SystemExit(1)
PYTHON_OIDC

echo
echo "=== Isolation réseau ==="

MAIN_LISTEN="$(
    ss -lnt |
    awk '$4 ~ /:8280$/ {print $4}'
)"

MANAGEMENT_LISTEN="$(
    ss -lnt |
    awk '$4 ~ /:9100$/ {print $4}'
)"

echo "Application : $MAIN_LISTEN"
echo "Management  : $MANAGEMENT_LISTEN"

printf '%s\n' "$MAIN_LISTEN" |
grep -q '127.0.0.1'

printf '%s\n' "$MANAGEMENT_LISTEN" |
grep -q '127.0.0.1'

if nginx -T 2>&1 |
  grep -q 'proxy_pass http://127.0.0.1:9100'
then
    echo "ERREUR : port management exposé par Nginx."
    exit 1
fi

echo "Management non exposé : OK"

echo
echo "=== Démarrage automatique ==="

ENABLED_STATE="$(
    systemctl is-enabled "$SERVICE" 2>/dev/null || true
)"

echo "État : $ENABLED_STATE"

test "$ENABLED_STATE" = "disabled"

echo
echo "VALIDATION INSTANCE DE TEST : OK"
