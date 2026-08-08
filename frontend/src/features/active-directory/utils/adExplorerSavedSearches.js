import {
  normalizeAdExplorerColumnIds,
  normalizeAdExplorerSort,
} from './adExplorerColumns.js'

import {
  normalizeAdExplorerFilters,
} from './adExplorerFilters.js'

export const AD_EXPLORER_SAVED_SEARCHES_STORAGE_KEY =
  'eitas_ad_explorer_saved_searches_v1'

export const MAX_AD_EXPLORER_SAVED_SEARCHES = 20

function normalizeName(value) {
  return String(value ?? '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 80)
}

function normalizeQuery(value) {
  return String(value ?? '')
    .trim()
    .slice(0, 256)
}

function normalizeId(value, fallback) {
  const candidate = String(value ?? '')
    .trim()
    .slice(0, 100)

  return candidate || fallback
}

export function createAdExplorerSavedSearch(
  value,
  fallbackId = `saved-${Date.now()}`
) {
  const source =
    value && typeof value === 'object'
      ? value
      : {}

  const name = normalizeName(source.name)

  if (!name) {
    return null
  }

  return {
    id: normalizeId(source.id, fallbackId),
    name,
    query: normalizeQuery(source.query),
    columnIds: normalizeAdExplorerColumnIds(
      source.columnIds
    ),
    sort: normalizeAdExplorerSort(source.sort),
    filters: normalizeAdExplorerFilters(
      source.filters
    ),
  }
}

export function normalizeAdExplorerSavedSearches(
  value
) {
  const source = Array.isArray(value)
    ? value
    : []

  const seenIds = new Set()
  const seenNames = new Set()
  const result = []

  for (let index = 0; index < source.length; index += 1) {
    if (
      result.length >=
      MAX_AD_EXPLORER_SAVED_SEARCHES
    ) {
      break
    }

    const normalized =
      createAdExplorerSavedSearch(
        source[index],
        `saved-${index + 1}`
      )

    if (!normalized) {
      continue
    }

    const idKey = normalized.id.toLocaleLowerCase('fr')
    const nameKey =
      normalized.name.toLocaleLowerCase('fr')

    if (
      seenIds.has(idKey)
      || seenNames.has(nameKey)
    ) {
      continue
    }

    seenIds.add(idKey)
    seenNames.add(nameKey)
    result.push(normalized)
  }

  return result
}

export function loadAdExplorerSavedSearches(
  storage
) {
  if (!storage?.getItem) {
    return []
  }

  try {
    const raw = storage.getItem(
      AD_EXPLORER_SAVED_SEARCHES_STORAGE_KEY
    )

    if (!raw) {
      return []
    }

    return normalizeAdExplorerSavedSearches(
      JSON.parse(raw)
    )
  } catch {
    return []
  }
}

export function saveAdExplorerSavedSearches(
  storage,
  searches
) {
  if (!storage?.setItem) {
    return
  }

  storage.setItem(
    AD_EXPLORER_SAVED_SEARCHES_STORAGE_KEY,
    JSON.stringify(
      normalizeAdExplorerSavedSearches(
        searches
      )
    )
  )
}

export function addAdExplorerSavedSearch(
  searches,
  candidate
) {
  const current =
    normalizeAdExplorerSavedSearches(searches)

  const normalized =
    createAdExplorerSavedSearch(candidate)

  if (!normalized) {
    return {
      searches: current,
      error: 'Le nom de la recherche est obligatoire.',
    }
  }

  const duplicate = current.some(
    item =>
      item.name.localeCompare(
        normalized.name,
        'fr',
        { sensitivity: 'base' }
      ) === 0
  )

  if (duplicate) {
    return {
      searches: current,
      error:
        'Une recherche porte déjà ce nom. Utilisez Remplacer.',
    }
  }

  if (
    current.length >=
    MAX_AD_EXPLORER_SAVED_SEARCHES
  ) {
    return {
      searches: current,
      error:
        'Le maximum de 20 recherches enregistrées est atteint.',
    }
  }

  return {
    searches: [...current, normalized],
    error: '',
  }
}

export function replaceAdExplorerSavedSearch(
  searches,
  searchId,
  candidate
) {
  const current =
    normalizeAdExplorerSavedSearches(searches)

  const index = current.findIndex(
    item => item.id === searchId
  )

  if (index < 0) {
    return {
      searches: current,
      error: 'Recherche enregistrée introuvable.',
    }
  }

  const normalized =
    createAdExplorerSavedSearch({
      ...candidate,
      id: current[index].id,
      name: current[index].name,
    })

  if (!normalized) {
    return {
      searches: current,
      error: 'Recherche enregistrée invalide.',
    }
  }

  const next = [...current]
  next[index] = normalized

  return {
    searches: next,
    error: '',
  }
}

export function removeAdExplorerSavedSearch(
  searches,
  searchId
) {
  return normalizeAdExplorerSavedSearches(
    searches
  ).filter(
    item => item.id !== searchId
  )
}
