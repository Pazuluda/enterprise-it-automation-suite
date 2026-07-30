function normalizeObjectClass(value) {
  return String(value || '').trim().toLowerCase()
}

export function isUserObject(value) {
  if (!value || typeof value !== 'object') {
    return false
  }

  return normalizeObjectClass(
    value.type || value.object_class
  ) === 'user'
}

function getUserIdentity(value) {
  if (!value || typeof value !== 'object') {
    return ''
  }

  return String(
    value.distinguished_name
      || value.dn
      || value.sam_account_name
      || value.user_principal_name
      || ''
  ).trim()
}

export function buildAdUserDetailsJobPayload(value) {
  if (!isUserObject(value)) {
    return null
  }

  const identity = getUserIdentity(value)

  if (!identity) {
    return null
  }

  return {
    action: 'get_user',
    query: identity,
    created_by: 'react-admin',
  }
}

export function extractAdUserDetails(job) {
  if (
    !job
    || job.status !== 'completed'
    || job.success !== true
  ) {
    return null
  }

  const item = job.result?.item

  if (!item || typeof item !== 'object' || Array.isArray(item)) {
    return null
  }

  return item
}

export function mergeAdUserDetails(initial, details) {
  if (!initial || typeof initial !== 'object') {
    return details && typeof details === 'object'
      ? { ...details }
      : initial
  }

  if (!details || typeof details !== 'object') {
    return initial
  }

  return {
    ...initial,
    ...details,
  }
}
