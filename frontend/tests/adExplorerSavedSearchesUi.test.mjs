import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

import {
  MAX_AD_EXPLORER_SAVED_SEARCHES,
  addAdExplorerSavedSearch,
  createAdExplorerSavedSearch,
  loadAdExplorerSavedSearches,
  normalizeAdExplorerSavedSearches,
  removeAdExplorerSavedSearch,
  replaceAdExplorerSavedSearch,
  saveAdExplorerSavedSearches,
} from '../src/features/active-directory/utils/adExplorerSavedSearches.js'

const page = fs.readFileSync(
  new URL(
    '../src/features/active-directory/AdExplorerPage.jsx',
    import.meta.url
  ),
  'utf8'
)

const css = fs.readFileSync(
  new URL(
    '../src/styles/07-active-directory.css',
    import.meta.url
  ),
  'utf8'
)

function memoryStorage() {
  const values = new Map()

  return {
    getItem(key) {
      return values.has(key)
        ? values.get(key)
        : null
    },
    setItem(key, value) {
      values.set(key, String(value))
    },
  }
}

function candidate(overrides = {}) {
  return {
    id: 'saved-1',
    name: 'Utilisateurs Liam',
    query: 'Liam',
    columnIds: [
      'name',
      'mail',
      'sam_account_name',
    ],
    sort: {
      columnId: 'mail',
      direction: 'desc',
    },
    filters: {
      type: 'user',
      enabled: 'enabled',
      conditions: [],
    },
    ...overrides,
  }
}

test('C6.4 normalizes a complete saved search', () => {
  const saved =
    createAdExplorerSavedSearch(candidate())

  assert.equal(saved.name, 'Utilisateurs Liam')
  assert.equal(saved.query, 'Liam')
  assert.deepEqual(
    saved.columnIds,
    ['name', 'mail', 'sam_account_name']
  )
  assert.equal(saved.sort.columnId, 'mail')
  assert.equal(saved.sort.direction, 'desc')
  assert.equal(saved.filters.type, 'user')
})

test('C6.4 rejects an empty saved-search name', () => {
  assert.equal(
    createAdExplorerSavedSearch(
      candidate({ name: '   ' })
    ),
    null
  )
})

test('C6.4 keeps unique names and ids', () => {
  const result =
    normalizeAdExplorerSavedSearches([
      candidate(),
      candidate({
        id: 'saved-2',
        name: 'utilisateurs liam',
      }),
    ])

  assert.equal(result.length, 1)
})

test('C6.4 limits saved searches to 20', () => {
  const source = Array.from(
    { length: 30 },
    (_, index) =>
      candidate({
        id: `saved-${index}`,
        name: `Recherche ${index}`,
      })
  )

  assert.equal(
    normalizeAdExplorerSavedSearches(source).length,
    MAX_AD_EXPLORER_SAVED_SEARCHES
  )
})

test('C6.4 persists saved searches safely', () => {
  const storage = memoryStorage()

  saveAdExplorerSavedSearches(
    storage,
    [candidate()]
  )

  const loaded =
    loadAdExplorerSavedSearches(storage)

  assert.equal(loaded.length, 1)
  assert.equal(loaded[0].query, 'Liam')
})

test('C6.4 refuses duplicate names on add', () => {
  const result = addAdExplorerSavedSearch(
    [candidate()],
    candidate({
      id: 'saved-2',
      name: 'UTILISATEURS LIAM',
    })
  )

  assert.match(result.error, /Remplacer/)
  assert.equal(result.searches.length, 1)
})

test('C6.4 explicitly replaces a saved search', () => {
  const result =
    replaceAdExplorerSavedSearch(
      [candidate()],
      'saved-1',
      candidate({
        query: 'VPN',
        columnIds: ['name', 'description'],
      })
    )

  assert.equal(result.error, '')
  assert.equal(result.searches[0].query, 'VPN')
  assert.equal(
    result.searches[0].name,
    'Utilisateurs Liam'
  )
})

test('C6.4 removes a saved search', () => {
  assert.equal(
    removeAdExplorerSavedSearch(
      [candidate()],
      'saved-1'
    ).length,
    0
  )
})

test('C6.4 wires the saved-search state and panel', () => {
  assert.match(
    page,
    /loadAdExplorerSavedSearches/
  )
  assert.match(page, /Recherches enregistrées/)
  assert.match(page, /Enregistrer/)
  assert.match(page, /Remplacer/)
  assert.match(page, /Supprimer/)
})

test('C6.4 restores filters columns and sort', () => {
  assert.match(
    page,
    /setVisibleColumnIds\(saved\.columnIds\)/
  )
  assert.match(
    page,
    /setViewSort\(saved\.sort\)/
  )
  assert.match(
    page,
    /setAdvancedFilters\(saved\.filters\)/
  )
})

test('C6.4 relaunches unified search when loading', () => {
  assert.match(
    page,
    /runGlobalAdSearch\(null,\s*saved\.query\)/
  )
  assert.match(
    page,
    /runJob\(\s*'search_objects'/
  )
})

test('C6.4 keeps saved-search menu above the table', () => {
  assert.match(
    css,
    /\.aduc-saved-searches-menu/
  )
  assert.match(css, /z-index:\s*120/)
})
