SELECT line
FROM (
  SELECT
    'realm|' || r.name || '|' ||
    coalesce(r.default_locale,'') || '|' ||
    r.internationalization_enabled::text || '|' ||
    coalesce(r.login_theme,'') || '|' ||
    coalesce(r.account_theme,'') || '|' ||
    coalesce(r.admin_theme,'') AS line
  FROM realm AS r
  WHERE r.name IN ('master','eitas')

  UNION ALL

  SELECT
    'locale|' || r.name || '|' || rsl.value
  FROM realm_supported_locales AS rsl
  JOIN realm AS r
    ON r.id=rsl.realm_id
  WHERE r.name IN ('master','eitas')

  UNION ALL

  SELECT
    'action|' || r.name || '|' ||
    rap.alias || '|' || rap.name
  FROM required_action_provider AS rap
  JOIN realm AS r
    ON r.id=rap.realm_id
  WHERE r.name IN ('master','eitas')

  UNION ALL

  SELECT
    'scope|' || r.name || '|' ||
    cs.name || '|' || coalesce(cs.description,'')
  FROM client_scope AS cs
  JOIN realm AS r
    ON r.id=cs.realm_id
  WHERE r.name IN ('master','eitas')

    UNION ALL

    SELECT
      'feature|eitas|allow_user_managed_access|' ||
      r.allow_user_managed_access::text
    FROM realm AS r
    WHERE r.name='eitas'

    UNION ALL

    SELECT
      'feature|eitas|' || ra.name || '|' || ra.value
    FROM realm_attribute AS ra
    JOIN realm AS r
      ON r.id=ra.realm_id
    WHERE r.name='eitas'
      AND ra.name IN (
        'organizationsEnabled',
        'verifiableCredentialsEnabled'
      )

  UNION ALL

  SELECT
    'mapping|' || r.name || '|' ||
    c.client_id || '|' || kr.name
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
) AS profile
ORDER BY line;
