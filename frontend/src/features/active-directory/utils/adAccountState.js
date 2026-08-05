const TRUE_VALUES = new Set([
  '1',
  'true',
  'yes',
  'oui',
])

const FALSE_VALUES = new Set([
  '0',
  'false',
  'no',
  'non',
])

export function normalizeAdBoolean(value) {
  if (value === true || value === false) {
    return value
  }

  if (
    value === null
    || value === undefined
    || String(value).trim() === ''
  ) {
    return null
  }

  const normalized = String(value)
    .trim()
    .toLowerCase()

  if (TRUE_VALUES.has(normalized)) {
    return true
  }

  if (FALSE_VALUES.has(normalized)) {
    return false
  }

  return null
}

export function getAdAccountField(
  account,
  names,
) {
  for (const name of names) {
    const value = account?.[name]

    if (
      value !== null
      && value !== undefined
      && String(value).trim() !== ''
    ) {
      return value
    }
  }

  return null
}

export function getAdAccountEnabledState(account) {
  const enabled = normalizeAdBoolean(
    getAdAccountField(
      account,
      [
        'enabled',
        'Enabled',
      ],
    ),
  )

  if (enabled !== null) {
    return enabled
  }

  const disabled = normalizeAdBoolean(
    getAdAccountField(
      account,
      [
        'disabled',
        'Disabled',
      ],
    ),
  )

  if (disabled !== null) {
    return !disabled
  }

  return null
}

export function getAdAccountLockedState(account) {
  return normalizeAdBoolean(
    getAdAccountField(
      account,
      [
        'locked_out',
        'lockedOut',
        'LockedOut',
      ],
    ),
  )
}

export function getAdAccountPasswordExpiredState(
  account,
) {
  return normalizeAdBoolean(
    getAdAccountField(
      account,
      [
        'password_expired',
        'passwordExpired',
        'PasswordExpired',
      ],
    ),
  )
}

export function getAdAccountStatus(account) {
  if (getAdAccountLockedState(account) === true) {
    return 'Verrouillé'
  }

  const enabled =
    getAdAccountEnabledState(account)

  if (enabled === false) {
    return 'Désactivé'
  }

  if (
    getAdAccountPasswordExpiredState(account)
    === true
  ) {
    return 'MDP expiré'
  }

  if (enabled === true) {
    return 'Activé'
  }

  return 'État inconnu'
}

export function getAdAccountStatusClass(account) {
  const status = getAdAccountStatus(account)

  if (status === 'Verrouillé') {
    return 'locked'
  }

  if (status === 'Désactivé') {
    return 'disabled'
  }

  if (status === 'MDP expiré') {
    return 'expired'
  }

  if (status === 'Activé') {
    return 'enabled'
  }

  return 'unknown'
}

export function getAdAccountToggleAction(account) {
  const enabled =
    getAdAccountEnabledState(account)

  if (enabled === true) {
    return 'disable_account'
  }

  if (enabled === false) {
    return 'enable_account'
  }

  return null
}
