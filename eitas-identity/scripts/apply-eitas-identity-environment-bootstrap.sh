#!/usr/bin/env bash

set -Eeuo pipefail
umask 0077

ROOT="$(
  cd "$(
    dirname "${BASH_SOURCE[0]}"
  )/.." &&
  pwd
)"

SQL_FILE="$ROOT/scripts/sql/eitas-identity-environment-bootstrap.sql"

DATABASE=""
SERVICE=""
REALM_NAME="eitas"
ADMIN_USERNAME=""
ORGANIZATION_NAME=""
ORGANIZATION_ALIAS=""
ORGANIZATION_DESCRIPTION=""

CONFIRM_PRODUCTION_DB=""
CONFIRM_PRODUCTION_CHANGE=""

usage() {
  cat <<'EOF'
Usage :
  apply-eitas-identity-environment-bootstrap.sh \
    --database NOM_BASE \
    --admin-user NOM_UTILISATEUR \
    --organization-name NOM \
    --organization-alias ALIAS \
    [--organization-description DESCRIPTION] \
    [--realm eitas] \
    [--service NOM_SERVICE]

Production uniquement :
  --confirm-production-db keycloak
  --confirm-production-change BOOTSTRAP-EITAS-IDENTITY-PRODUCTION

Le service associé doit être arrêté avant toute application.
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

    --realm)
      REALM_NAME="${2:-}"
      shift 2
      ;;

    --admin-user)
      ADMIN_USERNAME="${2:-}"
      shift 2
      ;;

    --organization-name)
      ORGANIZATION_NAME="${2:-}"
      shift 2
      ;;

    --organization-alias)
      ORGANIZATION_ALIAS="${2:-}"
      shift 2
      ;;

    --organization-description)
      ORGANIZATION_DESCRIPTION="${2:-}"
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

if [ -z "$DATABASE" ] ||
   [ -z "$ADMIN_USERNAME" ] ||
   [ -z "$ORGANIZATION_NAME" ] ||
   [ -z "$ORGANIZATION_ALIAS" ]
then
  echo "ERREUR : des paramètres obligatoires sont absents." >&2
  usage >&2
  exit 2
fi

if [[ ! "$DATABASE" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "ERREUR : nom de base invalide." >&2
  exit 2
fi

if [[ ! "$REALM_NAME" =~ ^[A-Za-z0-9._@-]+$ ]]; then
  echo "ERREUR : nom de realm invalide." >&2
  exit 2
fi

if [[ ! "$ADMIN_USERNAME" =~ ^[A-Za-z0-9._@-]+$ ]]; then
  echo "ERREUR : nom d’utilisateur invalide." >&2
  exit 2
fi

if [[ ! "$ORGANIZATION_ALIAS" =~ ^[a-z0-9][a-z0-9-]{0,62}$ ]]; then
  echo "ERREUR : alias d’organisation invalide." >&2
  exit 2
fi

if [ -n "$SERVICE" ] &&
   [[ ! "$SERVICE" =~ ^[A-Za-z0-9_.@-]+$ ]]
then
  echo "ERREUR : nom de service invalide." >&2
  exit 2
fi

if [[ "$ORGANIZATION_NAME" == *$'\n'* ]] ||
   [[ "$ORGANIZATION_DESCRIPTION" == *$'\n'* ]]
then
  echo "ERREUR : les retours à la ligne sont interdits." >&2
  exit 2
fi

test -s "$SQL_FILE"

DATABASE_EXISTS="$(
  runuser -u postgres -- psql \
    -X \
    -qAt \
    -d postgres \
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

  if [ "$CONFIRM_PRODUCTION_CHANGE" != "BOOTSTRAP-EITAS-IDENTITY-PRODUCTION" ]; then
    echo \
      "ERREUR : confirmation finale de production absente." \
      >&2
    exit 1
  fi
fi

if [ -n "$SERVICE" ]; then
  LOAD_STATE="$(
    systemctl show "$SERVICE" \
      -p LoadState \
      --value
  )"

  if [ "$LOAD_STATE" != "loaded" ]; then
    echo "ERREUR : service introuvable : $SERVICE" >&2
    exit 1
  fi

  if systemctl is-active --quiet "$SERVICE"; then
    echo "ERREUR : le service $SERVICE est encore actif." >&2
    exit 1
  fi
fi

ACTIVE_CONNECTIONS="$(
  runuser -u postgres -- psql \
    -X \
    -qAt \
    -d postgres \
    -c "
      SELECT count(*)
      FROM pg_stat_activity
      WHERE datname='$DATABASE';
    "
)"

if [ "$ACTIVE_CONNECTIONS" != "0" ]; then
  echo \
    "ERREUR : $ACTIVE_CONNECTIONS connexion(s) active(s) sur $DATABASE." \
    >&2
  exit 1
fi

REALM_COUNT="$(
  runuser -u postgres -- psql \
    -X \
    -qAt \
    -d "$DATABASE" \
    -v realm_name="$REALM_NAME" \
    -f - <<'SQL'
      SELECT count(*)
      FROM realm
      WHERE name=:'realm_name';
SQL
)"

USER_COUNT="$(
  runuser -u postgres -- psql \
    -X \
    -qAt \
    -d "$DATABASE" \
    -v realm_name="$REALM_NAME" \
    -v admin_username="$ADMIN_USERNAME" \
    -f - <<'SQL'
      SELECT count(*)
      FROM user_entity AS user_account
      JOIN realm AS r
        ON r.id=user_account.realm_id
      WHERE r.name=:'realm_name'
        AND user_account.username=:'admin_username';
SQL
)"

ROLE_COUNT="$(
  runuser -u postgres -- psql \
    -X \
    -qAt \
    -d "$DATABASE" \
    -v realm_name="$REALM_NAME" \
    -f - <<'SQL'
      SELECT count(*)
      FROM keycloak_role AS role
      JOIN realm AS r
        ON r.id=role.realm_id
      WHERE r.name=:'realm_name'
        AND role.name='UltraAdmin'
        AND role.client_role=false;
SQL
)"

if [ "$REALM_COUNT" != "1" ]; then
  echo "ERREUR : realm unique introuvable : $REALM_NAME" >&2
  exit 1
fi

if [ "$USER_COUNT" != "1" ]; then
  echo "ERREUR : administrateur unique introuvable." >&2
  exit 1
fi

if [ "$ROLE_COUNT" != "1" ]; then
  echo "ERREUR : rôle realm UltraAdmin unique introuvable." >&2
  exit 1
fi

read -r \
  ROOT_GROUP_ID \
  ROLE_GROUP_ID \
  ORGANIZATION_ID \
  ORGANIZATION_GROUP_ID \
  < <(
    python3 - <<'PY'
import uuid

print(
    str(uuid.uuid4()),
    str(uuid.uuid4()),
    str(uuid.uuid4()),
    str(uuid.uuid4()),
)
PY
  )

NOW_MS="$(date +%s%3N)"
STAMP="$(date +%Y%m%d-%H%M%S)"

BACKUP_DIR="$(
  printf \
    '/var/backups/eitas-identity/environment-bootstrap-%s-%s' \
    "$DATABASE" \
    "$STAMP"
)"

DUMP="$BACKUP_DIR/before-bootstrap.dump"

install -d \
  -o root \
  -g root \
  -m 0700 \
  "$BACKUP_DIR"

echo "============================================================"
echo " EITAS IDENTITY — BOOTSTRAP DE L’ENVIRONNEMENT"
echo "============================================================"
echo
echo "Base         : $DATABASE"
echo "Service      : ${SERVICE:-aucun}"
echo "Realm        : $REALM_NAME"
echo "Administrateur : $ADMIN_USERNAME"
echo "Organisation : $ORGANIZATION_NAME"
echo "Alias        : $ORGANIZATION_ALIAS"
echo "Sauvegarde   : $BACKUP_DIR"

echo
echo "=== 1. SAUVEGARDE AVANT MODIFICATION ==="

runuser -u postgres -- pg_dump \
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

runuser -u postgres -- psql \
  -X \
  -v ON_ERROR_STOP=1 \
  -d "$DATABASE" \
  -v realm_name="$REALM_NAME" \
  -v admin_username="$ADMIN_USERNAME" \
  -v organization_name="$ORGANIZATION_NAME" \
  -v organization_alias="$ORGANIZATION_ALIAS" \
  -v organization_description="$ORGANIZATION_DESCRIPTION" \
  -v root_group_id="$ROOT_GROUP_ID" \
  -v role_group_id="$ROLE_GROUP_ID" \
  -v organization_id="$ORGANIZATION_ID" \
  -v organization_group_id="$ORGANIZATION_GROUP_ID" \
  -v now_ms="$NOW_MS" \
  -f "$SQL_FILE"

echo
echo "=== 3. VALIDATION FINALE ==="

VALIDATION="$(
  runuser -u postgres -- psql \
    -X \
    -qAt \
    -F '|' \
    -d "$DATABASE" \
    -v realm_name="$REALM_NAME" \
    -v admin_username="$ADMIN_USERNAME" \
    -v organization_name="$ORGANIZATION_NAME" \
    -v organization_alias="$ORGANIZATION_ALIAS" \
    -v organization_description="$ORGANIZATION_DESCRIPTION" \
    -f - <<'SQL'
WITH
target_realm AS (
  SELECT id
  FROM realm
  WHERE name=:'realm_name'
),
root_group AS (
  SELECT group_row.id
  FROM keycloak_group AS group_row
  JOIN target_realm AS r
    ON r.id=group_row.realm_id
  WHERE group_row.parent_group=' '
    AND group_row.name='EITAS Roles'
    AND group_row.type=0
),
role_group AS (
  SELECT group_row.id
  FROM keycloak_group AS group_row
  JOIN target_realm AS r
    ON r.id=group_row.realm_id
  JOIN root_group AS root
    ON root.id=group_row.parent_group
  WHERE group_row.name='UltraAdmin'
    AND group_row.type=0
),
target_user AS (
  SELECT user_account.id
  FROM user_entity AS user_account
  JOIN target_realm AS r
    ON r.id=user_account.realm_id
  WHERE user_account.username=:'admin_username'
),
target_role AS (
  SELECT role.id
  FROM keycloak_role AS role
  JOIN target_realm AS r
    ON r.id=role.realm_id
  WHERE role.name='UltraAdmin'
    AND role.client_role=false
),
target_org AS (
  SELECT organization.*
  FROM org AS organization
  JOIN target_realm AS r
    ON r.id=organization.realm_id
  WHERE organization.alias=:'organization_alias'
)
SELECT
  (SELECT count(*) FROM root_group),
  (SELECT count(*) FROM role_group),
  (
    SELECT count(*)
    FROM group_role_mapping AS mapping
    JOIN role_group AS role_group_row
      ON role_group_row.id=mapping.group_id
    JOIN target_role AS role
      ON role.id=mapping.role_id
  ),
  (
    SELECT count(*)
    FROM user_group_membership AS membership
    JOIN role_group AS role_group_row
      ON role_group_row.id=membership.group_id
    JOIN target_user AS user_account
      ON user_account.id=membership.user_id
    WHERE membership.membership_type='UNMANAGED'
  ),
  (
    SELECT count(*)
    FROM target_org AS organization
    JOIN keycloak_group AS organization_group
      ON organization_group.id=organization.group_id
    WHERE organization.enabled=true
      AND organization.name=:'organization_name'
      AND coalesce(organization.description,'')=
          :'organization_description'
      AND organization_group.type=1
      AND organization_group.parent_group=' '
      AND organization_group.name=organization.id
      AND organization_group.org_id=organization.id
  ),
  (
    SELECT count(*)
    FROM target_org AS organization
    JOIN user_group_membership AS membership
      ON membership.group_id=organization.group_id
    JOIN target_user AS user_account
      ON user_account.id=membership.user_id
    WHERE membership.membership_type='UNMANAGED'
  );
SQL
)"

echo "racine|groupe-rôle|mapping|adhésion-rôle|organisation|adhésion-organisation"
echo "$VALIDATION"

if [ "$VALIDATION" != "1|1|1|1|1|1" ]; then
  echo "ERREUR : validation finale incorrecte." >&2
  echo "Sauvegarde disponible : $BACKUP_DIR" >&2
  exit 1
fi

printf '%s\n' \
  "database=$DATABASE" \
  "realm=$REALM_NAME" \
  "admin_username=$ADMIN_USERNAME" \
  "organization_name=$ORGANIZATION_NAME" \
  "organization_alias=$ORGANIZATION_ALIAS" \
  "validation=$VALIDATION" \
  > "$BACKUP_DIR/validation.txt"

chmod 0600 "$BACKUP_DIR/validation.txt"

sha256sum "$BACKUP_DIR/validation.txt" |
tee "$BACKUP_DIR/validation.txt.sha256"

echo
echo "BOOTSTRAP EITAS IDENTITY : VALIDÉ"
echo "Sauvegarde : $BACKUP_DIR"
