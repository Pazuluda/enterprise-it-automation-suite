const LDAP_SUPPORTED_VALUE_TYPES =
  Object.freeze([
    'single_text',
    'boolean',
    'integer32',
    'integer64',
  ])

const LDAP_INTEGER_BOUNDS =
  Object.freeze({
    integer32: Object.freeze({
      minimum: -2147483648,
      maximum: 2147483647,
    }),
    integer64: Object.freeze({
      minimum: Number.MIN_SAFE_INTEGER,
      maximum: Number.MAX_SAFE_INTEGER,
    }),
  })

function normalizeLdapValueType(valueType) {
  const normalized = String(
    valueType || ''
  )
    .trim()
    .toLowerCase()

  if (
    !LDAP_SUPPORTED_VALUE_TYPES.includes(
      normalized
    )
  ) {
    throw new Error(
      `Type de valeur LDAP non pris en charge : ${
        normalized || 'inconnu'
      }.`
    )
  }

  return normalized
}

function parseLdapTypedInputValue(
  valueType,
  rawValue
) {
  const normalizedType =
    normalizeLdapValueType(valueType)

  if (normalizedType === 'single_text') {
    if (typeof rawValue !== 'string') {
      throw new Error(
        'Une chaîne de caractères est obligatoire.'
      )
    }

    return rawValue
  }

  if (normalizedType === 'boolean') {
    if (typeof rawValue === 'boolean') {
      return rawValue
    }

    const normalized = String(
      rawValue ?? ''
    )
      .trim()
      .toLowerCase()

    if (normalized === 'true') {
      return true
    }

    if (normalized === 'false') {
      return false
    }

    throw new Error(
      'Une valeur booléenne est obligatoire.'
    )
  }

  if (
    typeof rawValue === 'number' &&
    Number.isSafeInteger(rawValue)
  ) {
    return rawValue
  }

  if (typeof rawValue !== 'string') {
    throw new Error(
      'Une valeur entière est obligatoire.'
    )
  }

  const normalized = rawValue.trim()

  if (!/^-?\d+$/.test(normalized)) {
    throw new Error(
      'Une valeur entière est obligatoire.'
    )
  }

  const numericValue = Number(normalized)

  if (!Number.isSafeInteger(numericValue)) {
    throw new Error(
      'Cet entier dépasse la précision sûre de JavaScript.'
    )
  }

  return numericValue
}

function normalizeLdapTypedEditorValue({
  valueType,
  value,
  minLength = 0,
  maxLength = null,
  minValue = null,
  maxValue = null,
}) {
  const normalizedType =
    normalizeLdapValueType(valueType)

  if (normalizedType === 'single_text') {
    if (typeof value !== 'string') {
      throw new Error(
        'Une chaîne de caractères est obligatoire.'
      )
    }

    const normalizedValue = value.trim()

    if (!normalizedValue) {
      throw new Error(
        'La valeur ne peut pas être vide avec l’opération set.'
      )
    }

    if (
      normalizedValue.includes(
        String.fromCharCode(0)
      ) ||
      normalizedValue.includes('\r') ||
      normalizedValue.includes('\n')
    ) {
      throw new Error(
        'La valeur contient un caractère interdit.'
      )
    }

    if (
      minLength > 0 &&
      normalizedValue.length < minLength
    ) {
      throw new Error(
        'La valeur est trop courte.'
      )
    }

    if (
      Number.isInteger(maxLength) &&
      normalizedValue.length > maxLength
    ) {
      throw new Error(
        'La valeur est trop longue.'
      )
    }

    return normalizedValue
  }

  if (normalizedType === 'boolean') {
    if (typeof value !== 'boolean') {
      throw new Error(
        'Une valeur booléenne est obligatoire.'
      )
    }

    return value
  }

  if (!Number.isSafeInteger(value)) {
    throw new Error(
      'Une valeur entière sûre est obligatoire.'
    )
  }

  const hardBounds =
    LDAP_INTEGER_BOUNDS[normalizedType]

  const effectiveMinimum =
    Number.isSafeInteger(minValue)
      ? Math.max(
          hardBounds.minimum,
          minValue
        )
      : hardBounds.minimum

  const effectiveMaximum =
    Number.isSafeInteger(maxValue)
      ? Math.min(
          hardBounds.maximum,
          maxValue
        )
      : hardBounds.maximum

  if (
    effectiveMinimum >
    effectiveMaximum
  ) {
    throw new Error(
      'Les bornes numériques sont incohérentes.'
    )
  }

  if (value < effectiveMinimum) {
    throw new Error(
      'La valeur est inférieure au minimum autorisé.'
    )
  }

  if (value > effectiveMaximum) {
    throw new Error(
      'La valeur dépasse le maximum autorisé.'
    )
  }

  return value
}

function formatLdapTypedEditorValue(
  valueType,
  value
) {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return '—'
  }

  const normalizedType =
    normalizeLdapValueType(valueType)

  if (normalizedType === 'boolean') {
    return value ? 'Oui' : 'Non'
  }

  return String(value)
}

export {
  LDAP_INTEGER_BOUNDS,
  LDAP_SUPPORTED_VALUE_TYPES,
  formatLdapTypedEditorValue,
  normalizeLdapTypedEditorValue,
  normalizeLdapValueType,
  parseLdapTypedInputValue,
}
