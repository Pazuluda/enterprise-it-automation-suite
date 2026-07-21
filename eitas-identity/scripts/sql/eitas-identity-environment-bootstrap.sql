\set ON_ERROR_STOP on

-- Paramètres psql obligatoires :
-- realm_name
-- admin_username
-- organization_name
-- organization_alias
-- organization_description
-- root_group_id
-- role_group_id
-- organization_id
-- organization_group_id
-- now_ms

BEGIN;

-- =========================================================
-- 1. Groupe racine EITAS Roles
-- =========================================================

INSERT INTO keycloak_group (
  id,
  name,
  parent_group,
  realm_id,
  type,
  description,
  org_id,
  created_timestamp,
  last_modified_timestamp
)
SELECT
  :'root_group_id',
  'EITAS Roles',
  ' ',
  r.id,
  0,
  NULL,
  NULL,
  :now_ms::bigint,
  :now_ms::bigint
FROM realm AS r
WHERE r.name=:'realm_name'
  AND NOT EXISTS (
    SELECT 1
    FROM keycloak_group AS existing
    WHERE existing.realm_id=r.id
      AND existing.parent_group=' '
      AND existing.name='EITAS Roles'
      AND existing.type=0
  );

-- =========================================================
-- 2. Sous-groupe UltraAdmin
-- =========================================================

INSERT INTO keycloak_group (
  id,
  name,
  parent_group,
  realm_id,
  type,
  description,
  org_id,
  created_timestamp,
  last_modified_timestamp
)
SELECT
  :'role_group_id',
  'UltraAdmin',
  root_group.id,
  r.id,
  0,
  NULL,
  NULL,
  :now_ms::bigint,
  :now_ms::bigint
FROM realm AS r
JOIN keycloak_group AS root_group
  ON root_group.realm_id=r.id
 AND root_group.parent_group=' '
 AND root_group.name='EITAS Roles'
 AND root_group.type=0
WHERE r.name=:'realm_name'
  AND NOT EXISTS (
    SELECT 1
    FROM keycloak_group AS existing
    WHERE existing.realm_id=r.id
      AND existing.parent_group=root_group.id
      AND existing.name='UltraAdmin'
      AND existing.type=0
  );

-- =========================================================
-- 3. Rôle realm UltraAdmin attribué au sous-groupe
-- =========================================================

INSERT INTO group_role_mapping (
  role_id,
  group_id
)
SELECT
  role.id,
  role_group.id
FROM realm AS r
JOIN keycloak_role AS role
  ON role.realm_id=r.id
 AND role.name='UltraAdmin'
 AND role.client_role=false
JOIN keycloak_group AS root_group
  ON root_group.realm_id=r.id
 AND root_group.parent_group=' '
 AND root_group.name='EITAS Roles'
 AND root_group.type=0
JOIN keycloak_group AS role_group
  ON role_group.realm_id=r.id
 AND role_group.parent_group=root_group.id
 AND role_group.name='UltraAdmin'
 AND role_group.type=0
WHERE r.name=:'realm_name'
  AND NOT EXISTS (
    SELECT 1
    FROM group_role_mapping AS existing
    WHERE existing.role_id=role.id
      AND existing.group_id=role_group.id
  );

-- =========================================================
-- 4. Administrateur membre du sous-groupe UltraAdmin
-- =========================================================

INSERT INTO user_group_membership (
  group_id,
  user_id,
  membership_type
)
SELECT
  role_group.id,
  user_account.id,
  'UNMANAGED'
FROM realm AS r
JOIN user_entity AS user_account
  ON user_account.realm_id=r.id
 AND user_account.username=:'admin_username'
JOIN keycloak_group AS root_group
  ON root_group.realm_id=r.id
 AND root_group.parent_group=' '
 AND root_group.name='EITAS Roles'
 AND root_group.type=0
JOIN keycloak_group AS role_group
  ON role_group.realm_id=r.id
 AND role_group.parent_group=root_group.id
 AND role_group.name='UltraAdmin'
 AND role_group.type=0
WHERE r.name=:'realm_name'
  AND NOT EXISTS (
    SELECT 1
    FROM user_group_membership AS existing
    WHERE existing.group_id=role_group.id
      AND existing.user_id=user_account.id
  );

-- =========================================================
-- 5. Groupe technique de l’organisation
-- Créé uniquement lorsque l’alias n’existe pas encore.
-- =========================================================

INSERT INTO keycloak_group (
  id,
  name,
  parent_group,
  realm_id,
  type,
  description,
  org_id,
  created_timestamp,
  last_modified_timestamp
)
SELECT
  :'organization_group_id',
  :'organization_id',
  ' ',
  r.id,
  1,
  NULL,
  NULL,
  :now_ms::bigint,
  :now_ms::bigint
FROM realm AS r
WHERE r.name=:'realm_name'
  AND NOT EXISTS (
    SELECT 1
    FROM org AS existing
    WHERE existing.realm_id=r.id
      AND existing.alias=:'organization_alias'
  );

-- =========================================================
-- 6. Organisation
-- =========================================================

INSERT INTO org (
  id,
  enabled,
  realm_id,
  group_id,
  name,
  description,
  alias,
  redirect_url
)
SELECT
  :'organization_id',
  true,
  r.id,
  :'organization_group_id',
  :'organization_name',
  NULLIF(:'organization_description', ''),
  :'organization_alias',
  NULL
FROM realm AS r
WHERE r.name=:'realm_name'
  AND NOT EXISTS (
    SELECT 1
    FROM org AS existing
    WHERE existing.realm_id=r.id
      AND existing.alias=:'organization_alias'
  );

-- Les valeurs descriptives restent synchronisées lors d’une réapplication.

UPDATE org AS organization
SET
  enabled=true,
  name=:'organization_name',
  description=NULLIF(:'organization_description', ''),
  redirect_url=NULL
FROM realm AS r
WHERE organization.realm_id=r.id
  AND r.name=:'realm_name'
  AND organization.alias=:'organization_alias'
  AND (
    organization.enabled IS DISTINCT FROM true
    OR organization.name IS DISTINCT FROM :'organization_name'
    OR coalesce(organization.description, '')
       IS DISTINCT FROM :'organization_description'
    OR organization.redirect_url IS NOT NULL
  );

-- Finalisation de la relation circulaire organisation/groupe technique.

UPDATE keycloak_group AS organization_group
SET
  name=organization.id,
  parent_group=' ',
  realm_id=organization.realm_id,
  type=1,
  description=NULL,
  org_id=organization.id,
  last_modified_timestamp=:now_ms::bigint
FROM org AS organization
JOIN realm AS r
  ON r.id=organization.realm_id
WHERE r.name=:'realm_name'
  AND organization.alias=:'organization_alias'
  AND organization_group.id=organization.group_id
  AND (
    organization_group.name IS DISTINCT FROM organization.id
    OR organization_group.parent_group IS DISTINCT FROM ' '
    OR organization_group.realm_id IS DISTINCT FROM organization.realm_id
    OR organization_group.type IS DISTINCT FROM 1
    OR organization_group.description IS NOT NULL
    OR organization_group.org_id IS DISTINCT FROM organization.id
  );

-- =========================================================
-- 7. Administrateur membre de l’organisation
-- =========================================================

INSERT INTO user_group_membership (
  group_id,
  user_id,
  membership_type
)
SELECT
  organization.group_id,
  user_account.id,
  'UNMANAGED'
FROM realm AS r
JOIN org AS organization
  ON organization.realm_id=r.id
 AND organization.alias=:'organization_alias'
JOIN user_entity AS user_account
  ON user_account.realm_id=r.id
 AND user_account.username=:'admin_username'
WHERE r.name=:'realm_name'
  AND NOT EXISTS (
    SELECT 1
    FROM user_group_membership AS existing
    WHERE existing.group_id=organization.group_id
      AND existing.user_id=user_account.id
  );

COMMIT;
