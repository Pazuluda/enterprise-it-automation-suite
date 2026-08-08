import {
  AD_EXPLORER_COLUMNS,
} from './adExplorerColumns.js'

export const AD_EXPLORER_FILTERS_STORAGE_KEY =
  'eitas_ad_explorer_filters_v1'

export const DEFAULT_AD_EXPLORER_FILTERS = {
  type: 'all',
  enabled: 'all',
  conditions: []
}

export const AD_EXPLORER_TYPE_OPTIONS = [
  { value: 'all', label: 'Tous les types' },
  { value: 'user', label: 'Utilisateurs' },
  { value: 'group', label: 'Groupes' },
  { value: 'computer', label: 'Ordinateurs' },
  { value: 'ou', label: 'Unités d’organisation' },
  { value: 'container', label: 'Conteneurs' },
  { value: 'contact', label: 'Contacts' },
]

export const AD_EXPLORER_FILTER_OPERATOR_OPTIONS = [
  { value: 'contains', label: 'contient' },
  { value: 'equals', label: 'est égal à' },
  { value: 'not_equals', label: 'est différent de' },
  { value: 'starts_with', label: 'commence par' },
  { value: 'ends_with', label: 'se termine par' },
  { value: 'present', label: 'est renseigné' },
  { value: 'absent', label: 'est vide' },
]

const knownColumnIds = new Set(
  AD_EXPLORER_COLUMNS.map(column => column.id)
)

const knownTypes = new Set(
  AD_EXPLORER_TYPE_OPTIONS.map(option => option.value)
)

const knownOperators = new Set(
  AD_EXPLORER_FILTER_OPERATOR_OPTIONS.map(
    option => option.value
  )
)

const knownEnabledStates = new Set([
  'all',
  'enabled',
  'disabled',
  'unknown',
])

function normalizeText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLocaleLowerCase('fr')
}

export function createAdExplorerFilterCondition(
  id = 'filter-1'
) {
  return {
    id: String(id || 'filter-1'),
    columnId: 'name',
    operator: 'contains',
    value: '',
  }
}

function normalizeCondition(value, index) {
  if (!value || typeof value !== 'object') {
    return null
  }

  const columnId = knownColumnIds.has(value.columnId)
    ? value.columnId
    : 'name'

  const operator = knownOperators.has(value.operator)
    ? value.operator
    : 'contains'

  const id = String(
    value.id || `filter-${index + 1}`
  ).slice(0, 80)

  const rawValue = (
    operator === 'present'
    || operator === 'absent'
  )
    ? ''
    : String(value.value ?? '').slice(0, 256)

  return {
    id,
    columnId,
    operator,
    value: rawValue,
  }
}

export function normalizeAdExplorerFilters(value) {
  const source =
    value && typeof value === 'object'
      ? value
      : DEFAULT_AD_EXPLORER_FILTERS

  const conditions = Array.isArray(source.conditions)
    ? source.conditions
        .slice(0, 8)
        .map(normalizeCondition)
        .filter(Boolean)
    : []

  return {
    type: knownTypes.has(source.type)
      ? source.type
      : 'all',
    enabled: knownEnabledStates.has(source.enabled)
      ? source.enabled
      : 'all',
    conditions,
  }
}

export function getAdExplorerActiveFilterCount(filters) {
  const normalized =
    normalizeAdExplorerFilters(filters)

  return (
    (normalized.type === 'all' ? 0 : 1)
    + (normalized.enabled === 'all' ? 0 : 1)
    + normalized.conditions.length
  )
}

export function getAdExplorerObjectKind(
  item,
  getObjectType
) {
  const displayType = normalizeText(
    getObjectType?.(item)
    || item?.type
    || item?.object_class
    || item?.objectClass
  )

  const rawClass = normalizeText(
    item?.object_class
    || item?.objectClass
    || item?.type
  )

  const combined = `${displayType} ${rawClass}`

  if (
    combined.includes('computer')
    || combined.includes('ordinateur')
    || combined.includes('controleur de domaine')
  ) {
    return 'computer'
  }

  if (combined.includes('contact')) {
    return 'contact'
  }

  if (
    combined.includes('organizationalunit')
    || combined.includes('unite d’organisation')
    || combined.includes("unite d'organisation")
    || displayType === 'ou'
    || rawClass === 'ou'
  ) {
    return 'ou'
  }

  if (
    combined.includes('group')
    || combined.includes('groupe')
  ) {
    return 'group'
  }

  if (
    combined.includes('user')
    || combined.includes('utilisateur')
  ) {
    return 'user'
  }

  if (
    combined.includes('container')
    || combined.includes('conteneur')
  ) {
    return 'container'
  }

  return 'other'
}

function getEnabledState(item, getValue) {
  const normalized = normalizeText(
    getValue?.(item, 'enabled')
  )

  if (
    normalized === 'oui'
    || normalized === 'true'
    || normalized === '1'
    || normalized === 'active'
    || normalized === 'activee'
  ) {
    return 'enabled'
  }

  if (
    normalized === 'non'
    || normalized === 'false'
    || normalized === '0'
    || normalized === 'desactive'
    || normalized === 'desactivee'
  ) {
    return 'disabled'
  }

  return 'unknown'
}

function conditionMatches(item, condition, getValue) {
  const rawValue = getValue?.(
    item,
    condition.columnId
  )

  const actual = normalizeText(rawValue)
  const expected = normalizeText(condition.value)

  switch (condition.operator) {
    case 'present':
      return actual !== ''

    case 'absent':
      return actual === ''

    case 'equals':
      return actual === expected

    case 'not_equals':
      return actual !== expected

    case 'starts_with':
      return actual.startsWith(expected)

    case 'ends_with':
      return actual.endsWith(expected)

    case 'contains':
    default:
      return actual.includes(expected)
  }
}

export function filterAdExplorerItems(
  items,
  filters,
  getValue,
  getObjectType
) {
  const source = Array.isArray(items)
    ? items
    : []

  const normalized =
    normalizeAdExplorerFilters(filters)

  return source.filter(item => {
    if (
      normalized.type !== 'all'
      && getAdExplorerObjectKind(
        item,
        getObjectType
      ) !== normalized.type
    ) {
      return false
    }

    if (
      normalized.enabled !== 'all'
      && getEnabledState(
        item,
        getValue
      ) !== normalized.enabled
    ) {
      return false
    }

    return normalized.conditions.every(
      condition =>
        conditionMatches(
          item,
          condition,
          getValue
        )
    )
  })
}

export function loadAdExplorerFilterPreferences(storage) {
  if (!storage?.getItem) {
    return normalizeAdExplorerFilters(
      DEFAULT_AD_EXPLORER_FILTERS
    )
  }

  try {
    const raw = storage.getItem(
      AD_EXPLORER_FILTERS_STORAGE_KEY
    )

    if (!raw) {
      return normalizeAdExplorerFilters(
        DEFAULT_AD_EXPLORER_FILTERS
      )
    }

    return normalizeAdExplorerFilters(
      JSON.parse(raw)
    )
  } catch {
    return normalizeAdExplorerFilters(
      DEFAULT_AD_EXPLORER_FILTERS
    )
  }
}

export function saveAdExplorerFilterPreferences(
  storage,
  filters
) {
  if (!storage?.setItem) {
    return
  }

  storage.setItem(
    AD_EXPLORER_FILTERS_STORAGE_KEY,
    JSON.stringify(
      normalizeAdExplorerFilters(filters)
    )
  )
}
