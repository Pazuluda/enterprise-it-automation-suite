const EITAS_ROLES = Object.freeze([
  'Viewer',
  'Operator',
  'ADAdmin',
  'SecurityAdmin',
  'Auditor',
  'UltraAdmin'
])

const ROLE_GROUPS = Object.freeze({
  portalRead: Object.freeze([
    'Viewer',
    'Operator',
    'ADAdmin',
    'SecurityAdmin',
    'Auditor',
    'UltraAdmin'
  ]),

  operator: Object.freeze([
    'Operator',
    'UltraAdmin'
  ]),

  activeDirectory: Object.freeze([
    'ADAdmin',
    'UltraAdmin'
  ]),

  security: Object.freeze([
    'SecurityAdmin',
    'UltraAdmin'
  ]),

  audit: Object.freeze([
    'Auditor',
    'UltraAdmin'
  ]),

  // Une page avec ce groupe reste accessible à toute personne
  // authentifiée, même si aucun rôle métier n'est encore attribué.
  authenticated: Object.freeze([])
})

const PAGE_ROLE_MATRIX = Object.freeze({
  overview: ROLE_GROUPS.portalRead,
  requests: ROLE_GROUPS.portalRead,

  newRequest: ROLE_GROUPS.operator,
  csvImport: ROLE_GROUPS.operator,
  offboarding: ROLE_GROUPS.operator,
  modification: ROLE_GROUPS.operator,

  templates: ROLE_GROUPS.security,
  agentOps: ROLE_GROUPS.security,
  agentMode: ROLE_GROUPS.security,
  workers: ROLE_GROUPS.security,

  adChecks: ROLE_GROUPS.activeDirectory,
  adExplorer: ROLE_GROUPS.activeDirectory,

  audit: ROLE_GROUPS.audit,

  settings: ROLE_GROUPS.authenticated
})

const ACTION_ROLE_MATRIX = Object.freeze({
  requestCreate: ROLE_GROUPS.operator,
  requestApprove: ROLE_GROUPS.operator,
  requestReject: ROLE_GROUPS.operator,
  requestRetry: ROLE_GROUPS.operator,

  templateAdmin: ROLE_GROUPS.security,
  agentAdministration: ROLE_GROUPS.security,
  workerSupervision: ROLE_GROUPS.security,

  adRead: ROLE_GROUPS.activeDirectory,
  adWrite: ROLE_GROUPS.activeDirectory,
  adCheck: ROLE_GROUPS.activeDirectory,

  auditRead: ROLE_GROUPS.audit,

  sessionManagement: ROLE_GROUPS.authenticated
})

const DEFAULT_PAGE_ORDER = Object.freeze([
  'overview',
  'requests',
  'newRequest',
  'csvImport',
  'offboarding',
  'modification',
  'adExplorer',
  'adChecks',
  'templates',
  'agentOps',
  'agentMode',
  'workers',
  'audit',
  'settings'
])

function normalizeRoles(value) {
  const source = Array.isArray(value)
    ? value
    : Array.isArray(value?.roles)
      ? value.roles
      : value instanceof Set
        ? Array.from(value)
        : []

  return Array.from(
    new Set(
      source
        .filter(role => typeof role === 'string')
        .map(role => role.trim())
        .filter(Boolean)
    )
  )
}

function hasAnyRole(userRoles, requiredRoles) {
  const expected = Array.isArray(requiredRoles)
    ? requiredRoles
    : []

  // Groupe vide = utilisateur Keycloak authentifié,
  // sans exigence supplémentaire de rôle métier.
  if (expected.length === 0) {
    return true
  }

  const currentRoles = new Set(normalizeRoles(userRoles))

  return expected.some(role => currentRoles.has(role))
}

function hasRole(userRoles, requiredRole) {
  if (typeof requiredRole !== 'string' || !requiredRole.trim()) {
    return false
  }

  return normalizeRoles(userRoles).includes(requiredRole.trim())
}

function canAccessPage(pageKey, userRoles) {
  if (!Object.hasOwn(PAGE_ROLE_MATRIX, pageKey)) {
    return false
  }

  return hasAnyRole(
    userRoles,
    PAGE_ROLE_MATRIX[pageKey]
  )
}

function canPerform(actionKey, userRoles) {
  if (!Object.hasOwn(ACTION_ROLE_MATRIX, actionKey)) {
    return false
  }

  return hasAnyRole(
    userRoles,
    ACTION_ROLE_MATRIX[actionKey]
  )
}

function getVisiblePages(userRoles) {
  return DEFAULT_PAGE_ORDER.filter(pageKey =>
    canAccessPage(pageKey, userRoles)
  )
}

function getDefaultPage(userRoles, preferredPage = 'overview') {
  if (canAccessPage(preferredPage, userRoles)) {
    return preferredPage
  }

  return getVisiblePages(userRoles)[0] || 'settings'
}

export {
  ACTION_ROLE_MATRIX,
  DEFAULT_PAGE_ORDER,
  EITAS_ROLES,
  PAGE_ROLE_MATRIX,
  ROLE_GROUPS,
  canAccessPage,
  canPerform,
  getDefaultPage,
  getVisiblePages,
  hasAnyRole,
  hasRole,
  normalizeRoles
}
