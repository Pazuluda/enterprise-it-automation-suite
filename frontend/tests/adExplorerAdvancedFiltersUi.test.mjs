import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

import {
  DEFAULT_AD_EXPLORER_FILTERS,
  createAdExplorerFilterCondition,
  filterAdExplorerItems,
  getAdExplorerActiveFilterCount,
  getAdExplorerObjectKind,
  loadAdExplorerFilterPreferences,
  normalizeAdExplorerFilters,
  saveAdExplorerFilterPreferences,
} from '../src/features/active-directory/utils/adExplorerFilters.js'

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

const getValue = (item, columnId) =>
  item[columnId] ?? ''

const getType = item =>
  item.type || item.object_class || ''

test('C6.3 normalizes safe defaults and conditions', () => {
  assert.deepEqual(
    normalizeAdExplorerFilters(null),
    DEFAULT_AD_EXPLORER_FILTERS
  )

  const normalized = normalizeAdExplorerFilters({
    type: 'invalid',
    enabled: 'invalid',
    conditions: [
      {
        id: 'one',
        columnId: 'mail',
        operator: 'contains',
        value: 'api.local'
      },
      {
        id: 'two',
        columnId: 'invalid',
        operator: 'invalid',
        value: 'x'
      }
    ]
  })

  assert.equal(normalized.type, 'all')
  assert.equal(normalized.enabled, 'all')
  assert.equal(normalized.conditions[0].columnId, 'mail')
  assert.equal(normalized.conditions[1].columnId, 'name')
  assert.equal(normalized.conditions[1].operator, 'contains')
})

test('C6.3 recognizes the supported object kinds', () => {
  assert.equal(
    getAdExplorerObjectKind(
      { object_class: 'user' },
      getType
    ),
    'user'
  )
  assert.equal(
    getAdExplorerObjectKind(
      { object_class: 'group' },
      getType
    ),
    'group'
  )
  assert.equal(
    getAdExplorerObjectKind(
      { object_class: 'computer' },
      getType
    ),
    'computer'
  )
  assert.equal(
    getAdExplorerObjectKind(
      { object_class: 'organizationalUnit' },
      getType
    ),
    'ou'
  )
  assert.equal(
    getAdExplorerObjectKind(
      { object_class: 'container' },
      getType
    ),
    'container'
  )
  assert.equal(
    getAdExplorerObjectKind(
      { object_class: 'contact' },
      getType
    ),
    'contact'
  )
})

test('C6.3 filters by object type', () => {
  const items = [
    { name: 'Liam', type: 'Utilisateur' },
    { name: 'GG_IT', type: 'Groupe de sécurité' },
    { name: 'PC-01', type: 'Ordinateur' },
  ]

  const result = filterAdExplorerItems(
    items,
    {
      type: 'group',
      enabled: 'all',
      conditions: []
    },
    getValue,
    getType
  )

  assert.deepEqual(
    result.map(item => item.name),
    ['GG_IT']
  )
})

test('C6.3 filters enabled disabled and unknown states', () => {
  const items = [
    { name: 'A', enabled: 'Oui' },
    { name: 'B', enabled: 'Non' },
    { name: 'C', enabled: '' },
  ]

  for (const [state, expected] of [
    ['enabled', ['A']],
    ['disabled', ['B']],
    ['unknown', ['C']],
  ]) {
    assert.deepEqual(
      filterAdExplorerItems(
        items,
        {
          type: 'all',
          enabled: state,
          conditions: []
        },
        getValue,
        getType
      ).map(item => item.name),
      expected
    )
  }
})

test('C6.3 supports text comparison operators', () => {
  const items = [
    { name: 'Liam Ve', mail: 'liam.ve@api.local' },
    { name: 'Nina Moreau', mail: 'nina@example.net' },
  ]

  const cases = [
    ['contains', 'api.local', ['Liam Ve']],
    ['equals', 'nina@example.net', ['Nina Moreau']],
    ['not_equals', 'nina@example.net', ['Liam Ve']],
    ['starts_with', 'liam.', ['Liam Ve']],
    ['ends_with', '.net', ['Nina Moreau']],
  ]

  for (const [operator, value, expected] of cases) {
    assert.deepEqual(
      filterAdExplorerItems(
        items,
        {
          type: 'all',
          enabled: 'all',
          conditions: [
            {
              id: 'one',
              columnId: 'mail',
              operator,
              value
            }
          ]
        },
        getValue,
        getType
      ).map(item => item.name),
      expected
    )
  }
})

test('C6.3 supports present and absent values', () => {
  const items = [
    { name: 'With mail', mail: 'a@api.local' },
    { name: 'Without mail', mail: '' },
  ]

  assert.deepEqual(
    filterAdExplorerItems(
      items,
      {
        type: 'all',
        enabled: 'all',
        conditions: [
          {
            id: 'one',
            columnId: 'mail',
            operator: 'present',
            value: 'ignored'
          }
        ]
      },
      getValue,
      getType
    ).map(item => item.name),
    ['With mail']
  )

  assert.deepEqual(
    filterAdExplorerItems(
      items,
      {
        type: 'all',
        enabled: 'all',
        conditions: [
          {
            id: 'one',
            columnId: 'mail',
            operator: 'absent',
            value: ''
          }
        ]
      },
      getValue,
      getType
    ).map(item => item.name),
    ['Without mail']
  )
})

test('C6.3 combines multiple criteria with AND', () => {
  const items = [
    {
      name: 'Liam',
      type: 'Utilisateur',
      enabled: 'Oui',
      mail: 'liam@api.local'
    },
    {
      name: 'Nina',
      type: 'Utilisateur',
      enabled: 'Oui',
      mail: 'nina@example.net'
    },
    {
      name: 'Disabled',
      type: 'Utilisateur',
      enabled: 'Non',
      mail: 'disabled@api.local'
    }
  ]

  const result = filterAdExplorerItems(
    items,
    {
      type: 'user',
      enabled: 'enabled',
      conditions: [
        {
          id: 'mail-domain',
          columnId: 'mail',
          operator: 'ends_with',
          value: '@api.local'
        }
      ]
    },
    getValue,
    getType
  )

  assert.deepEqual(
    result.map(item => item.name),
    ['Liam']
  )
})

test('C6.3 counts active filters and supports individual conditions', () => {
  const condition =
    createAdExplorerFilterCondition('custom')

  assert.equal(condition.id, 'custom')

  assert.equal(
    getAdExplorerActiveFilterCount({
      type: 'user',
      enabled: 'enabled',
      conditions: [
        condition,
        {
          id: 'second',
          columnId: 'mail',
          operator: 'present',
          value: ''
        }
      ]
    }),
    4
  )
})

test('C6.3 persists filters safely', () => {
  const storage = createStorage()

  saveAdExplorerFilterPreferences(
    storage,
    {
      type: 'user',
      enabled: 'enabled',
      conditions: [
        {
          id: 'mail',
          columnId: 'mail',
          operator: 'contains',
          value: 'api.local'
        }
      ]
    }
  )

  assert.deepEqual(
    loadAdExplorerFilterPreferences(storage),
    {
      type: 'user',
      enabled: 'enabled',
      conditions: [
        {
          id: 'mail',
          columnId: 'mail',
          operator: 'contains',
          value: 'api.local'
        }
      ]
    }
  )
})

test('C6.3 wires advanced filters into the Explorer UI', () => {
  for (const marker of [
    'loadAdExplorerFilterPreferences',
    'saveAdExplorerFilterPreferences',
    'filterAdExplorerItems',
    'advancedFilterCount',
    'Filtres avancés',
    '+ Ajouter un critère',
    'Effacer tout',
    'Supprimer ce critère',
  ]) {
    assert.ok(
      page.includes(marker),
      marker
    )
  }

  assert.ok(
    page.includes(
      'Les critères sont combinés'
    )
  )

  assert.ok(
    css.includes(
      '/* C6.3 - filtres avances AD Explorer */'
    )
  )

  assert.ok(
    css.includes(
      '.aduc-filter-options-menu'
    )
  )
})

console.log('C6.3 ADVANCED FILTERS UI: OK')
