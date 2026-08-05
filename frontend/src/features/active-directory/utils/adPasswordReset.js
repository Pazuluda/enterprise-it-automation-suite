export const DEFAULT_AD_PASSWORD_RESET_OPTIONS =
  Object.freeze({
    forceChangeAtLogon: true,
    unlockAfterReset: true,
  })

export function normalizeAdPasswordResetBoolean(
  value,
  defaultValue,
) {
  if (value === true || value === false) {
    return value
  }

  if (
    value === null
    || value === undefined
    || String(value).trim() === ''
  ) {
    return defaultValue
  }

  const normalized = String(value)
    .trim()
    .toLowerCase()

  if (['1', 'true', 'yes', 'oui'].includes(normalized)) {
    return true
  }

  if (['0', 'false', 'no', 'non'].includes(normalized)) {
    return false
  }

  return defaultValue
}

export function createAdPasswordResetDraft() {
  return {
    temporaryPassword: '',
    showPassword: false,
    forceChangeAtLogon:
      DEFAULT_AD_PASSWORD_RESET_OPTIONS.forceChangeAtLogon,
    unlockAfterReset:
      DEFAULT_AD_PASSWORD_RESET_OPTIONS.unlockAfterReset,
  }
}

export function getAdPasswordResetInputType(
  showPassword,
) {
  return showPassword ? 'text' : 'password'
}

export function buildAdPasswordResetPayload(draft) {
  const temporaryPassword = String(
    draft?.temporaryPassword || ''
  ).trim()

  if (!temporaryPassword) {
    throw new Error(
      'Mot de passe temporaire obligatoire.'
    )
  }

  return {
    temporary_password: temporaryPassword,
    force_change_at_logon:
      normalizeAdPasswordResetBoolean(
        draft?.forceChangeAtLogon,
        true,
      ),
    unlock_after_reset:
      normalizeAdPasswordResetBoolean(
        draft?.unlockAfterReset,
        true,
      ),
  }
}

export function buildAdPasswordResetSafeSummary(
  draft,
) {
  return {
    force_change_at_logon:
      normalizeAdPasswordResetBoolean(
        draft?.forceChangeAtLogon,
        true,
      ),
    unlock_after_reset:
      normalizeAdPasswordResetBoolean(
        draft?.unlockAfterReset,
        true,
      ),
  }
}
