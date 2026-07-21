#!/usr/bin/env bash

set -Eeuo pipefail
umask 0077

ROOT="$(
  cd "$(
    dirname "${BASH_SOURCE[0]}"
  )/.." &&
  pwd
)"

SQL_FILE="$ROOT/scripts/sql/eitas-identity-fr-profile.sql"
STATE_SQL_FILE="$ROOT/scripts/sql/eitas-identity-fr-profile-state.sql"

DATABASE=""
SERVICE=""
CONFIRM_PRODUCTION_DB=""
CONFIRM_PRODUCTION_CHANGE=""

usage() {
  cat <<'EOF'
Usage :
  apply-eitas-identity-fr-profile.sh \
    --database NOM_BASE \
    [--service NOM_SERVICE]

Production uniquement :
  --confirm-production-db keycloak
  --confirm-production-change APPLY-EITAS-IDENTITY-PRODUCTION

Le service associé doit être arrêté avant l’application.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --database)
      DATABASE="${2:-}"
      shift 2
      ;;

    --service)
      SERVICE="${2:-}"
      shift 2
      ;;

    --confirm-production-db)
      CONFIRM_PRODUCTION_DB="${2:-}"
      shift 2
      ;;

    --confirm-production-change)
      CONFIRM_PRODUCTION_CHANGE="${2:-}"
      shift 2
      ;;

    --help|-h)
      usage
      exit 0
      ;;

    *)
      echo "ERREUR : argument inconnu : $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "ERREUR : ce script doit être exécuté par root." >&2
  exit 1
fi

if [ -z "$DATABASE" ]; then
  echo "ERREUR : --database est obligatoire." >&2
  exit 2
fi

if [[ ! "$DATABASE" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "ERREUR : nom de base invalide." >&2
  exit 2
fi

if [ -n "$SERVICE" ] &&
   [[ ! "$SERVICE" =~ ^[A-Za-z0-9_.@-]+$ ]]
then
  echo "ERREUR : nom de service invalide." >&2
  exit 2
fi

test -s "$SQL_FILE"
test -s "$STATE_SQL_FILE"

DATABASE_EXISTS="$(
  runuser -u postgres -- \
    psql -X -At -d postgres \
    -c "
      SELECT count(*)
      FROM pg_database
      WHERE datname='$DATABASE';
    "
)"

if [ "$DATABASE_EXISTS" != "1" ]; then
  echo "ERREUR : base absente : $DATABASE" >&2
  exit 1
fi

if [ "$DATABASE" = "keycloak" ]; then
  if [ "$SERVICE" != "keycloak.service" ]; then
    echo \
      "ERREUR : la production exige --service keycloak.service." \
      >&2
    exit 1
  fi

  if [ "$CONFIRM_PRODUCTION_DB" != "keycloak" ]; then
    echo \
      "ERREUR : confirmation de la base de production absente." \
      >&2
    exit 1
  fi

  if [
    "$CONFIRM_PRODUCTION_CHANGE" !=
    "APPLY-EITAS-IDENTITY-PRODUCTION"
  ]; then
    echo \
      "ERREUR : confirmation finale de production absente." \
      >&2
    exit 1
  fi
fi

if [ -n "$SERVICE" ] &&
   systemctl is-active --quiet "$SERVICE"
then
  echo "ERREUR : le service $SERVICE est encore actif." >&2
  exit 1
fi

ACTIVE_CONNECTIONS="$(
  runuser -u postgres -- \
    psql -X -At -d postgres \
    -c "
      SELECT count(*)
      FROM pg_stat_activity
      WHERE datname='$DATABASE';
    "
)"

if [ "$ACTIVE_CONNECTIONS" != "0" ]; then
  echo \
    "ERREUR : $ACTIVE_CONNECTIONS connexion(s) active(s) " \
    "sur $DATABASE." \
    >&2
  exit 1
fi

REALMS="$(
  runuser -u postgres -- \
    psql -X -At -d "$DATABASE" \
    -c "
      SELECT count(*)
      FROM realm
      WHERE name IN ('master','eitas');
    "
)"

if [ "$REALMS" != "2" ]; then
  echo \
    "ERREUR : les realms master et eitas sont requis." \
    >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$(
  printf \
    '/var/backups/eitas-identity/profile-apply-%s-%s' \
    "$DATABASE" \
    "$STAMP"
)"
DUMP="$BACKUP_DIR/before-profile.dump"

install -d \
  -o root \
  -g root \
  -m 0700 \
  "$BACKUP_DIR"

echo "============================================================"
echo " EITAS IDENTITY — APPLICATION DU PROFIL FRANÇAIS"
echo "============================================================"
echo
echo "Base        : $DATABASE"
echo "Service     : ${SERVICE:-aucun}"
echo "Profil SQL  : $SQL_FILE"
echo "Sauvegarde  : $BACKUP_DIR"

echo
echo "=== 1. SAUVEGARDE AVANT MODIFICATION ==="

runuser -u postgres -- \
  pg_dump \
    --format=custom \
    --compress=6 \
    --no-owner \
    --no-acl \
    "$DATABASE" \
  > "$DUMP"

chmod 0600 "$DUMP"
test -s "$DUMP"

sha256sum "$DUMP" |
  tee "$DUMP.sha256"

echo
echo "=== 2. APPLICATION TRANSACTIONNELLE ==="

runuser -u postgres -- \
  psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -d "$DATABASE" \
    -f "$SQL_FILE"

echo
echo "=== 3. VALIDATION ==="

VALIDATION="$(
  runuser -u postgres -- \
    psql -X -At -F '|' -d "$DATABASE" \
    -c "
SELECT
  (
    SELECT count(*)
    FROM realm
    WHERE name='master'
      AND default_locale='fr'
      AND internationalization_enabled=true
      AND login_theme='eitas'
      AND account_theme='eitas-account'
      AND admin_theme='eitas-admin'
  ),
  (
    SELECT count(*)
    FROM realm
    WHERE name='eitas'
      AND default_locale='fr'
      AND internationalization_enabled=true
      AND login_theme='eitas'
      AND account_theme='eitas-account'
      AND admin_theme IS NULL
  ),
  (
    SELECT count(*)
    FROM realm_supported_locales AS rsl
    JOIN realm AS r
      ON r.id=rsl.realm_id
    WHERE r.name IN ('master','eitas')
      AND rsl.value IN ('en','fr')
  ),
  (
    SELECT count(*)
    FROM required_action_provider AS rap
    JOIN realm AS r
      ON r.id=rap.realm_id
    WHERE r.name IN ('master','eitas')
  ),
  (
    SELECT count(*)
    FROM client_scope AS cs
    JOIN realm AS r
      ON r.id=cs.realm_id
    WHERE r.name IN ('master','eitas')
  ),
  (
    SELECT count(*)
    FROM scope_mapping AS sm
    JOIN client AS c
      ON c.id=sm.client_id
    JOIN keycloak_role AS kr
      ON kr.id=sm.role_id
    JOIN realm AS r
      ON r.id=c.realm_id
    WHERE r.name='eitas'
      AND c.client_id='account-console'
      AND kr.name='UltraAdmin'
  );
    "
)"

echo \
  "master|eitas|locales|actions|périmètres|UltraAdmin"
echo "$VALIDATION"

if [ "$VALIDATION" != "1|1|4|28|30|1" ]; then
  echo "ERREUR : validation finale incorrecte." >&2
  exit 1
fi

echo
echo "=== 4. EMPREINTE EXACTE DU PROFIL ==="

PROFILE_STATE="$BACKUP_DIR/profile-state.txt"
EXPECTED_PROFILE_LINES="65"
EXPECTED_PROFILE_SHA256="ccacd20dbd6a5ab7b7c9c4934d840299a98e0f84429f5f8dc27b9e9f99f98597"

runuser -u postgres -- \
  psql \
    -X \
    -qAt \
    -d "$DATABASE" \
    -f "$STATE_SQL_FILE" \
  > "$PROFILE_STATE"

PROFILE_LINES="$(
  wc -l < "$PROFILE_STATE" |
  tr -d '[:space:]'
)"

PROFILE_SHA256="$(
  sha256sum "$PROFILE_STATE" |
  awk '{print $1}'
)"

echo "Lignes attendues : $EXPECTED_PROFILE_LINES"
echo "Lignes obtenues  : $PROFILE_LINES"
echo "SHA256 attendu   : $EXPECTED_PROFILE_SHA256"
echo "SHA256 obtenu    : $PROFILE_SHA256"

if [ "$PROFILE_LINES" != "$EXPECTED_PROFILE_LINES" ]; then
  echo "ERREUR : nombre de lignes du profil incorrect." >&2
  exit 1
fi

if [ "$PROFILE_SHA256" != "$EXPECTED_PROFILE_SHA256" ]; then
  echo "ERREUR : empreinte exacte du profil incorrecte." >&2
  exit 1
fi

echo
echo "PROFIL FRANÇAIS EITAS IDENTITY : VALIDÉ"
echo "Sauvegarde : $BACKUP_DIR"
