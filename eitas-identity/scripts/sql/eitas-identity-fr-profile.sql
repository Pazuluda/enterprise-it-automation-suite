-- EITAS Identity — profil français de production
-- Application hors ligne uniquement, service Keycloak arrêté.
-- Le script est idempotent et n’utilise aucun identifiant UUID fixe.

BEGIN;

UPDATE realm
SET
  default_locale = 'fr',
  internationalization_enabled = true
WHERE name IN ('master', 'eitas');

UPDATE realm
SET
  login_theme = 'eitas',
  account_theme = 'eitas-account',
  admin_theme = NULL
WHERE name = 'eitas';

UPDATE realm
SET
  login_theme = 'eitas',
  account_theme = 'eitas-account',
  admin_theme = 'eitas-admin'
WHERE name = 'master';


-- Fonctionnalités communes de l’espace personnel EITAS Identity.
UPDATE realm
SET allow_user_managed_access = true
WHERE name = 'eitas';

DELETE FROM realm_attribute
WHERE realm_id = (
  SELECT id
  FROM realm
  WHERE name = 'eitas'
)
AND name IN (
  'organizationsEnabled',
  'verifiableCredentialsEnabled'
);

INSERT INTO realm_attribute (
  realm_id,
  name,
  value
)
SELECT
  r.id,
  feature.name,
  'true'
FROM realm AS r
CROSS JOIN (
  VALUES
    ('organizationsEnabled'),
    ('verifiableCredentialsEnabled')
) AS feature(name)
WHERE r.name = 'eitas';

DELETE FROM realm_supported_locales
WHERE realm_id IN (
  SELECT id
  FROM realm
  WHERE name IN ('master', 'eitas')
);

INSERT INTO realm_supported_locales (
  realm_id,
  value
)
SELECT
  r.id,
  locale.value
FROM realm AS r
CROSS JOIN (
  VALUES ('en'), ('fr')
) AS locale(value)
WHERE r.name IN ('master', 'eitas');

UPDATE required_action_provider AS rap SET name='Configurer les codes de récupération' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='CONFIGURE_RECOVERY_AUTHN_CODES';
UPDATE required_action_provider AS rap SET name='Configurer l’authentification mobile' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='CONFIGURE_TOTP';
UPDATE required_action_provider AS rap SET name='Supprimer le compte' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='delete_account';
UPDATE required_action_provider AS rap SET name='Supprimer un moyen d’authentification' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='delete_credential';
UPDATE required_action_provider AS rap SET name='Lier un fournisseur d’identité' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='idp_link';
UPDATE required_action_provider AS rap SET name='Accepter les conditions générales' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='TERMS_AND_CONDITIONS';
UPDATE required_action_provider AS rap SET name='Mettre à jour l’adresse e-mail' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='UPDATE_EMAIL';
UPDATE required_action_provider AS rap SET name='Mettre à jour le mot de passe' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='UPDATE_PASSWORD';
UPDATE required_action_provider AS rap SET name='Mettre à jour le profil' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='UPDATE_PROFILE';
UPDATE required_action_provider AS rap SET name='Mettre à jour la langue de l’utilisateur' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='update_user_locale';
UPDATE required_action_provider AS rap SET name='Vérifier l’adresse e-mail' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='VERIFY_EMAIL';
UPDATE required_action_provider AS rap SET name='Vérifier le profil' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='VERIFY_PROFILE';
UPDATE required_action_provider AS rap SET name='Enregistrer une clé de sécurité WebAuthn' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='webauthn-register';
UPDATE required_action_provider AS rap SET name='Enregistrer une clé WebAuthn sans mot de passe' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='eitas' AND rap.alias='webauthn-register-passwordless';
UPDATE required_action_provider AS rap SET name='Configurer les codes de récupération' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='CONFIGURE_RECOVERY_AUTHN_CODES';
UPDATE required_action_provider AS rap SET name='Configurer l’authentification mobile' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='CONFIGURE_TOTP';
UPDATE required_action_provider AS rap SET name='Supprimer le compte' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='delete_account';
UPDATE required_action_provider AS rap SET name='Supprimer un moyen d’authentification' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='delete_credential';
UPDATE required_action_provider AS rap SET name='Lier un fournisseur d’identité' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='idp_link';
UPDATE required_action_provider AS rap SET name='Accepter les conditions générales' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='TERMS_AND_CONDITIONS';
UPDATE required_action_provider AS rap SET name='Mettre à jour l’adresse e-mail' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='UPDATE_EMAIL';
UPDATE required_action_provider AS rap SET name='Mettre à jour le mot de passe' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='UPDATE_PASSWORD';
UPDATE required_action_provider AS rap SET name='Mettre à jour le profil' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='UPDATE_PROFILE';
UPDATE required_action_provider AS rap SET name='Mettre à jour la langue de l’utilisateur' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='update_user_locale';
UPDATE required_action_provider AS rap SET name='Vérifier l’adresse e-mail' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='VERIFY_EMAIL';
UPDATE required_action_provider AS rap SET name='Vérifier le profil' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='VERIFY_PROFILE';
UPDATE required_action_provider AS rap SET name='Enregistrer une clé de sécurité WebAuthn' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='webauthn-register';
UPDATE required_action_provider AS rap SET name='Enregistrer une clé WebAuthn sans mot de passe' FROM realm AS r WHERE r.id=rap.realm_id AND r.name='master' AND rap.alias='webauthn-register-passwordless';

UPDATE client_scope AS cs SET description='Périmètre OpenID Connect ajoutant la valeur acr, référence de classe du contexte d’authentification, au jeton' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='acr';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect intégré : adresse' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='address';
UPDATE client_scope AS cs SET description='Niveau de référence de classe du contexte d’authentification' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='AuthnContextClassRef';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect ajoutant les revendications de base au jeton' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='basic';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect intégré : adresse e-mail' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='email';
UPDATE client_scope AS cs SET description='Périmètre intégré MicroProfile JWT' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='microprofile-jwt';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect intégré : accès hors ligne' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='offline_access';
UPDATE client_scope AS cs SET description='Revendications supplémentaires sur l’organisation à laquelle appartient le sujet' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='organization';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect intégré : téléphone' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='phone';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect intégré : profil' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='profile';
UPDATE client_scope AS cs SET description='Liste des rôles SAML' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='role_list';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect ajoutant les rôles de l’utilisateur au jeton d’accès' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='roles';
UPDATE client_scope AS cs SET description='Appartenance à une organisation' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='saml_organization';
UPDATE client_scope AS cs SET description='Périmètre spécifique aux clients utilisant des comptes de service' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='service_account';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect ajoutant les origines web autorisées au jeton d’accès' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='eitas' AND cs.name='web-origins';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect ajoutant la valeur acr, référence de classe du contexte d’authentification, au jeton' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='acr';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect intégré : adresse' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='address';
UPDATE client_scope AS cs SET description='Niveau de référence de classe du contexte d’authentification' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='AuthnContextClassRef';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect ajoutant les revendications de base au jeton' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='basic';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect intégré : adresse e-mail' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='email';
UPDATE client_scope AS cs SET description='Périmètre intégré MicroProfile JWT' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='microprofile-jwt';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect intégré : accès hors ligne' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='offline_access';
UPDATE client_scope AS cs SET description='Revendications supplémentaires sur l’organisation à laquelle appartient le sujet' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='organization';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect intégré : téléphone' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='phone';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect intégré : profil' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='profile';
UPDATE client_scope AS cs SET description='Liste des rôles SAML' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='role_list';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect ajoutant les rôles de l’utilisateur au jeton d’accès' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='roles';
UPDATE client_scope AS cs SET description='Appartenance à une organisation' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='saml_organization';
UPDATE client_scope AS cs SET description='Périmètre spécifique aux clients utilisant des comptes de service' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='service_account';
UPDATE client_scope AS cs SET description='Périmètre OpenID Connect ajoutant les origines web autorisées au jeton d’accès' FROM realm AS r WHERE r.id=cs.realm_id AND r.name='master' AND cs.name='web-origins';

INSERT INTO scope_mapping (
  client_id,
  role_id
)
SELECT
  c.id,
  kr.id
FROM client AS c
JOIN realm AS r
  ON r.id=c.realm_id
JOIN keycloak_role AS kr
  ON kr.realm_id=r.id
WHERE r.name='eitas'
  AND c.client_id='account-console'
  AND kr.name='UltraAdmin'
  AND kr.client_role=false
  AND NOT EXISTS (
    SELECT 1
    FROM scope_mapping AS sm
    WHERE sm.client_id=c.id
      AND sm.role_id=kr.id
  );

COMMIT;
