#!/bin/bash
set -euo pipefail

ROOT="/opt/eitas-identity"
CONFIG_DIR="/etc/eitas-identity"
ENV_FILE="$CONFIG_DIR/eitas-identity-test.env"

DB_NAME="eitas_identity_test"
DB_USER="eitas_identity_test"

BOOTSTRAP_ADMIN="eitas-identity-admin"

PUBLIC_URL="https://10.10.10.11:62443/identity-test"
HTTP_PORT="8280"
MANAGEMENT_PORT="9100"

echo
echo "=== 1. VÉRIFICATION DES OUTILS ==="

command -v python3
command -v psql
command -v createdb
command -v runuser

systemctl is-active --quiet postgresql@17-main.service

echo "PostgreSQL 17 : actif"

echo
echo "=== 2. ÉTAT INITIAL POSTGRESQL ==="

ROLE_EXISTS="$(
    runuser -u postgres -- \
      psql \
        -d postgres \
        -Atqc \
        "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER';"
)"

DATABASE_EXISTS="$(
    runuser -u postgres -- \
      psql \
        -d postgres \
        -Atqc \
        "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';"
)"

echo "Rôle existant : ${ROLE_EXISTS:-non}"
echo "Base existante : ${DATABASE_EXISTS:-non}"

echo
echo "=== 3. CONFIGURATION SÉCURISÉE ==="

install -d \
  -o root \
  -g eitas-identity \
  -m 0750 \
  "$CONFIG_DIR"

if [ ! -f "$ENV_FILE" ]; then
    if [ -n "$ROLE_EXISTS" ] || [ -n "$DATABASE_EXISTS" ]; then
        echo "ERREUR : la base ou le rôle existe déjà mais le fichier"
        echo "de configuration sécurisé est absent."
        echo
        echo "Aucune modification PostgreSQL n’a été effectuée."
        exit 1
    fi

    DB_PASSWORD="$(
        python3 -c \
          'import secrets; print(secrets.token_hex(32))'
    )"

    ADMIN_PASSWORD="$(
        python3 -c \
          'import secrets; print(secrets.token_hex(24))'
    )"

    umask 027

    cat > "$ENV_FILE" <<EOF
KC_DB=postgres
KC_DB_URL=jdbc:postgresql://127.0.0.1:5432/$DB_NAME
KC_DB_USERNAME=$DB_USER
KC_DB_PASSWORD=$DB_PASSWORD

KC_HTTP_ENABLED=true
KC_HTTP_HOST=127.0.0.1
KC_HTTP_PORT=$HTTP_PORT
KC_HTTP_MANAGEMENT_PORT=$MANAGEMENT_PORT

KC_HOSTNAME=$PUBLIC_URL
KC_PROXY_HEADERS=xforwarded

KC_CACHE=local
KC_LOG=console
KC_LOG_LEVEL=INFO

KC_BOOTSTRAP_ADMIN_USERNAME=$BOOTSTRAP_ADMIN
KC_BOOTSTRAP_ADMIN_PASSWORD=$ADMIN_PASSWORD
EOF

    chown \
      root:eitas-identity \
      "$ENV_FILE"

    chmod 0640 "$ENV_FILE"

    echo "Configuration créée : $ENV_FILE"
else
    echo "Configuration existante conservée : $ENV_FILE"
fi

DB_PASSWORD="$(
    sed -n \
      's/^KC_DB_PASSWORD=//p' \
      "$ENV_FILE"
)"

ADMIN_PASSWORD="$(
    sed -n \
      's/^KC_BOOTSTRAP_ADMIN_PASSWORD=//p' \
      "$ENV_FILE"
)"

if [ -z "$DB_PASSWORD" ]; then
    echo "ERREUR : KC_DB_PASSWORD absent."
    exit 1
fi

if [ -z "$ADMIN_PASSWORD" ]; then
    echo "ERREUR : mot de passe bootstrap absent."
    exit 1
fi

echo
echo "=== 4. CRÉATION DU RÔLE POSTGRESQL ==="

runuser -u postgres -- \
  psql \
    -d postgres \
    -v ON_ERROR_STOP=1 <<SQL
DO \$eitas\$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = '$DB_USER'
    ) THEN
        CREATE ROLE "$DB_USER"
            WITH
            LOGIN
            PASSWORD '$DB_PASSWORD'
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOREPLICATION
            NOBYPASSRLS
            CONNECTION LIMIT 20;
    ELSE
        ALTER ROLE "$DB_USER"
            WITH
            LOGIN
            PASSWORD '$DB_PASSWORD'
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOREPLICATION
            NOBYPASSRLS
            CONNECTION LIMIT 20;
    END IF;
END
\$eitas\$;
SQL

echo "Rôle PostgreSQL : $DB_USER"

echo
echo "=== 5. CRÉATION DE LA BASE DÉDIÉE ==="

DATABASE_EXISTS="$(
    runuser -u postgres -- \
      psql \
        -d postgres \
        -Atqc \
        "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';"
)"

if [ -z "$DATABASE_EXISTS" ]; then
    runuser -u postgres -- \
      createdb \
        --owner="$DB_USER" \
        --encoding=UTF8 \
        --template=template0 \
        "$DB_NAME"

    echo "Base créée : $DB_NAME"
else
    echo "Base déjà existante : $DB_NAME"
fi

echo
echo "=== 6. DURCISSEMENT DES DROITS ==="

runuser -u postgres -- \
  psql \
    -d postgres \
    -v ON_ERROR_STOP=1 <<SQL
REVOKE ALL
ON DATABASE "$DB_NAME"
FROM PUBLIC;

GRANT CONNECT, TEMPORARY
ON DATABASE "$DB_NAME"
TO "$DB_USER";
SQL

echo "Accès public retiré : OK"

echo
echo "=== 7. TEST DE CONNEXION DÉDIÉE ==="

CONNECTION_RESULT="$(
    PGPASSWORD="$DB_PASSWORD" \
      psql \
        -h 127.0.0.1 \
        -p 5432 \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -Atqc \
        "SELECT current_database() || '|' || current_user;"
)"

echo "Connexion obtenue : $CONNECTION_RESULT"

test "$CONNECTION_RESULT" = "$DB_NAME|$DB_USER"

echo
echo "=== 8. CONTRÔLE DES PERMISSIONS DU SECRET ==="

PERMISSIONS="$(
    stat -c '%a' "$ENV_FILE"
)"

OWNER_GROUP="$(
    stat -c '%U:%G' "$ENV_FILE"
)"

echo "Permissions : $PERMISSIONS"
echo "Propriétaire : $OWNER_GROUP"

test "$PERMISSIONS" = "640"
test "$OWNER_GROUP" = "root:eitas-identity"

runuser \
  -u eitas-identity \
  -- \
  test -r "$ENV_FILE"

echo "Lecture par le service eitas-identity : OK"

echo
echo "=== 9. CONFIGURATION ASSAINIE ==="

sed -E \
  -e 's/^(KC_DB_PASSWORD)=.*/\1=<REDACTED>/' \
  -e 's/^(KC_BOOTSTRAP_ADMIN_PASSWORD)=.*/\1=<REDACTED>/' \
  "$ENV_FILE"

echo
echo "=== 10. DOCUMENTATION NON SENSIBLE ==="

cat > "$ROOT/docs/test-instance.md" <<EOF
# Instance parallèle EITAS Identity

## Runtime

- Répertoire : \`/opt/eitas-identity/runtime/keycloak-26.7.0-eitas\`
- Compte système : \`eitas-identity\`
- Configuration : \`/etc/eitas-identity/eitas-identity-test.env\`

## PostgreSQL

- Serveur : \`127.0.0.1:5432\`
- Base : \`$DB_NAME\`
- Rôle : \`$DB_USER\`
- Base de production \`keycloak\` : séparée et inchangée

## Réseau prévu

- HTTP interne : \`127.0.0.1:$HTTP_PORT\`
- Management : \`127.0.0.1:$MANAGEMENT_PORT\`
- URL publique prévue : \`$PUBLIC_URL\`
- Reverse proxy prévu : Nginx

## Cache

L'instance de test utilise un cache local afin de rester indépendante
de l'instance Keycloak de production.
EOF

chmod 0644 "$ROOT/docs/test-instance.md"

echo
echo "=== 11. RÉSULTAT ==="
echo "Base    : $DB_NAME"
echo "Rôle    : $DB_USER"
echo "Config  : $ENV_FILE"
echo "Admin   : $BOOTSTRAP_ADMIN"
echo
echo "PROVISIONNEMENT B3.9 : OK"
