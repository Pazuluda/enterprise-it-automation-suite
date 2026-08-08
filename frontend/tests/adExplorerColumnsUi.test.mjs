import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

import {
  AD_EXPLORER_COLUMNS,
  DEFAULT_AD_EXPLORER_COLUMN_IDS,
  getAdExplorerColumnValue,
  loadAdExplorerColumnPreferences,
  loadAdExplorerSortPreference,
  normalizeAdExplorerColumnIds,
  normalizeAdExplorerSort,
  saveAdExplorerColumnPreferences,
  saveAdExplorerSortPreference,
  sortAdExplorerItems,
} from '../src/features/active-directory/utils/adExplorerColumns.js'

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

function createStorage() {
  const values = new Map()

  return {
    getItem(key) {
      return values.has(key)
        ? values.get(key)
        : null
    },
    setItem(key, value) {
      values.set(key, String(value))
    }
  }
}

test('C6.2 keeps name as a required visible column', () => {
  assert.deepEqual(
    normalizeAdExplorerColumnIds([
      'mail',
      'mail',
      'unknown'
    ]),
    ['name', 'mail']
  )

  const nameColumn =
    AD_EXPLORER_COLUMNS.find(
      column => column.id === 'name'
    )

  assert.equal(nameColumn.required, true)
})

test('C6.2 exposes useful normalized AD columns', () => {
  const ids = new Set(
    AD_EXPLORER_COLUMNS.map(
      column => column.id
    )
  )

  for (const required of [
    'name',
    'type',
    'description',
    'display_name',
    'sam_account_name',
    'user_principal_name',
    'mail',
    'dns_host_name',
    'operating_system',
    'enabled',
    'group_scope',
    'group_category',
    'canonical_name',
    'distinguished_name'
  ]) {
    assert.ok(ids.has(required), required)
  }
})

test('C6.2 reads aliases and formats boolean enabled values', () => {
  const item = {
    samAccountName: 'l.ve',
    userPrincipalName: 'liam.ve@api.local',
    canonicalName: 'API.LOCAL/EITAS/Users/Liam Ve',
    enabled: false
  }

  assert.equal(
    getAdExplorerColumnValue(
      item,
      'sam_account_name'
    ),
    'l.ve'
  )

  assert.equal(
    getAdExplorerColumnValue(
      item,
      'user_principal_name'
    ),
    'liam.ve@api.local'
  )

  assert.equal(
    getAdExplorerColumnValue(
      item,
      'canonical_name'
    ),
    'API.LOCAL/EITAS/Users/Liam Ve'
  )

  assert.equal(
    getAdExplorerColumnValue(
      item,
      'enabled'
    ),
    'Non'
  )
})

test('C6.2 sorts ascending and descending with empty values last', () => {
  const items = [
    { name: 'PC-10' },
    { name: '' },
    { name: 'PC-2' },
    { name: 'Alpha' }
  ]

  const getValue = (
    item,
    columnId
  ) => item[columnId]

  assert.deepEqual(
    sortAdExplorerItems(
      items,
      {
        columnId: 'name',
        direction: 'asc'
      },
      getValue
    ).map(item => item.name),
    [
      'Alpha',
      'PC-2',
      'PC-10',
      ''
    ]
  )

  assert.deepEqual(
    sortAdExplorerItems(
      items,
      {
        columnId: 'name',
        direction: 'desc'
      },
      getValue
    ).map(item => item.name),
    [
      'PC-10',
      'PC-2',
      'Alpha',
      ''
    ]
  )
})

test('C6.2 persists columns and sort safely', () => {
  const storage = createStorage()

  saveAdExplorerColumnPreferences(
    storage,
    [
      'name',
      'mail',
      'distinguished_name'
    ]
  )

  saveAdExplorerSortPreference(
    storage,
    {
      columnId: 'mail',
      direction: 'desc'
    }
  )

  assert.deepEqual(
    loadAdExplorerColumnPreferences(
      storage
    ),
    [
      'name',
      'mail',
      'distinguished_name'
    ]
  )

  assert.deepEqual(
    loadAdExplorerSortPreference(
      storage
    ),
    {
      columnId: 'mail',
      direction: 'desc'
    }
  )

  assert.deepEqual(
    normalizeAdExplorerSort({
      columnId: 'unknown',
      direction: 'desc'
    }),
    {
      columnId: 'name',
      direction: 'asc'
    }
  )
})

test('C6.2 wires the display options menu and persistent state', () => {
  assert.ok(
    page.includes(
      'loadAdExplorerColumnPreferences'
    )
  )

  assert.ok(
    page.includes(
      'saveAdExplorerColumnPreferences'
    )
  )

  assert.ok(
    page.includes(
      'columnOptionsOpen'
    )
  )

  assert.ok(
    page.includes(
      'Colonnes affichées'
    )
  )

  assert.ok(
    page.includes(
      'resetAdExplorerColumns'
    )
  )

  assert.ok(
    page.includes(
      'eitas_ad_explorer_columns_v1'
    ) === false
  )
})

test('C6.2 renders configurable headers and sortable rows', () => {
  assert.ok(
    page.includes(
      'visibleColumns.map(column =>'
    )
  )

  assert.ok(
    page.includes(
      'toggleAdExplorerSort'
    )
  )

  assert.ok(
    page.includes(
      'getAdExplorerSortIndicator'
    )
  )

  assert.ok(
    page.includes(
      'gridTemplateColumns:'
    )
  )

  assert.ok(
    page.includes(
      'aria-sort='
    )
  )

  assert.ok(
    css.includes(
      '.aduc-column-options-menu'
    )
  )

  assert.ok(
    css.includes(
      '.aduc-table-header-button'
    )
  )
})

assert.deepEqual(
  DEFAULT_AD_EXPLORER_COLUMN_IDS,
  [
    'name',
    'type',
    'description'
  ]
)

console.log(
  'C6.2 AD EXPLORER COLUMNS + SORT: OK'
)
