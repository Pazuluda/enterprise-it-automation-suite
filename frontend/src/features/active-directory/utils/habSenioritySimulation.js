const HAB_SIMULATION_ACTION =
  'simulate_hab_seniority_index'

const HAB_ATTRIBUTE_NAME =
  'msDS-HABSeniorityIndex'

const HAB_VALUE_TYPE = 'integer32'

const HAB_MINIMUM_VALUE = 0
const HAB_MAXIMUM_VALUE = 2147483647

function pickObjectValue(
  object,
  names
) {
  for (const name of names) {
    const value = object?.[name]

    if (
      value !== null &&
      value !== undefined &&
      String(value).trim() !== ''
    ) {
      return value
    }
  }

  return ''
}

function getHabObjectIdentity(object) {
  return String(
    pickObjectValue(
      object,
      [
        'distinguished_name',
        'distinguishedName',
        'dn',
      ]
    )
  ).trim()
}

function getHabObjectClass(object) {
  const value = String(
    pickObjectValue(
      object,
      [
        'object_class',
        'objectClass',
        'type',
      ]
    )
  )
    .trim()
    .toLowerCase()

  if (
    value === 'user' ||
    value.includes('utilisateur')
  ) {
    return 'user'
  }

  return value
}

function getHabCurrentValue(object) {
  const value =
    object?.hab_seniority_index
    ?? object?.msDS_HABSeniorityIndex
    ?? object?.[HAB_ATTRIBUTE_NAME]

  if (
    value === null ||
    value === undefined ||
    String(value).trim() === ''
  ) {
    return null
  }

  return normalizeHabInteger32(value)
}

function normalizeHabInteger32(value) {
  if (
    value === null ||
    value === undefined ||
    typeof value === 'boolean'
  ) {
    throw new Error(
      'La valeur HAB doit être un entier.'
    )
  }

  let normalized

  if (typeof value === 'number') {
    normalized = value
  } else {
    const text = String(value).trim()

    if (!/^\d+$/.test(text)) {
      throw new Error(
        'La valeur HAB doit être un entier positif ou nul.'
      )
    }

    normalized = Number(text)
  }

  if (
    !Number.isSafeInteger(normalized) ||
    normalized < HAB_MINIMUM_VALUE ||
    normalized > HAB_MAXIMUM_VALUE
  ) {
    throw new Error(
      'La valeur HAB doit être comprise entre '
      + `${HAB_MINIMUM_VALUE} et `
      + `${HAB_MAXIMUM_VALUE}.`
    )
  }

  return normalized
}

function normalizeHabOperation(operation) {
  const normalized = String(
    operation || ''
  )
    .trim()
    .toLowerCase()

  if (
    normalized !== 'set' &&
    normalized !== 'clear'
  ) {
    throw new Error(
      'L’opération HAB doit être set ou clear.'
    )
  }

  return normalized
}

function buildHabSenioritySimulationPayload({
  object,
  operation,
  value,
}) {
  const objectIdentity =
    getHabObjectIdentity(object)

  if (
    !objectIdentity.includes('=') ||
    !objectIdentity.includes(',')
  ) {
    throw new Error(
      'Le DN LDAP de l’utilisateur est invalide.'
    )
  }

  if (getHabObjectClass(object) !== 'user') {
    throw new Error(
      'La simulation HAB est limitée aux utilisateurs.'
    )
  }

  const normalizedOperation =
    normalizeHabOperation(operation)

  return {
    action: HAB_SIMULATION_ACTION,
    object_identity: objectIdentity,
    object_class: 'user',
    attribute_name: HAB_ATTRIBUTE_NAME,
    operation: normalizedOperation,
    value:
      normalizedOperation === 'set'
        ? normalizeHabInteger32(value)
        : null,
  }
}

function buildHabSenioritySimulationJobPayload({
  object,
  operation,
  value,
  createdBy = 'react-admin',
}) {
  const normalizedCreatedBy = String(
    createdBy || 'react-admin'
  ).trim()

  return {
    ...buildHabSenioritySimulationPayload({
      object,
      operation,
      value,
    }),
    created_by:
      normalizedCreatedBy || 'react-admin',
  }
}

function isHabSimulationMode(agentMode) {
  return String(agentMode || '')
    .trim()
    .toLowerCase() === 'simulation'
}

function getHabSimulationEligibility({
  object,
  agentMode,
  canManageActiveDirectory,
}) {
  if (!canManageActiveDirectory) {
    return {
      eligible: false,
      reason:
        'Le rôle ADAdmin ou UltraAdmin est requis.',
    }
  }

  if (getHabObjectClass(object) !== 'user') {
    return {
      eligible: false,
      reason:
        'La simulation HAB est limitée aux utilisateurs.',
    }
  }

  if (!getHabObjectIdentity(object)) {
    return {
      eligible: false,
      reason:
        'Le DN LDAP de l’utilisateur est indisponible.',
    }
  }

  if (!isHabSimulationMode(agentMode)) {
    return {
      eligible: false,
      reason:
        'La simulation HAB exige le mode Simulation.',
    }
  }

  return {
    eligible: true,
    reason: '',
  }
}

export {
  HAB_ATTRIBUTE_NAME,
  HAB_MAXIMUM_VALUE,
  HAB_MINIMUM_VALUE,
  HAB_SIMULATION_ACTION,
  HAB_VALUE_TYPE,
  buildHabSenioritySimulationJobPayload,
  buildHabSenioritySimulationPayload,
  getHabCurrentValue,
  getHabObjectClass,
  getHabObjectIdentity,
  getHabSimulationEligibility,
  isHabSimulationMode,
  normalizeHabInteger32,
  normalizeHabOperation,
}
