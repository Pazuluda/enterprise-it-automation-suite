export const AD_EXPLORER_COLUMNS_STORAGE_KEY =
  'eitas_ad_explorer_columns_v1'

export const AD_EXPLORER_SORT_STORAGE_KEY =
  'eitas_ad_explorer_sort_v1'

export const DEFAULT_AD_EXPLORER_COLUMN_IDS = [
  'name',
  'type',
  'description'
]

export const AD_EXPLORER_COLUMNS = [
  {
    id: 'name',
    label: 'Nom',
    required: true,
    width: 'minmax(220px, 1.2fr)'
  },
  {
    id: 'type',
    label: 'Type',
    width: 'minmax(150px, 0.85fr)'
  },
  {
    id: 'description',
    label: 'Description',
    width: 'minmax(220px, 1.35fr)'
  },
  {
    id: 'display_name',
    label: 'Nom d’affichage',
    width: 'minmax(190px, 1fr)'
  },
  {
    id: 'sam_account_name',
    label: 'Compte SAM',
    width: 'minmax(150px, 0.9fr)'
  },
  {
    id: 'user_principal_name',
    label: 'UPN',
    width: 'minmax(220px, 1.2fr)'
  },
  {
    id: 'mail',
    label: 'E-mail',
    width: 'minmax(210px, 1.1fr)'
  },
  {
    id: 'dns_host_name',
    label: 'Nom DNS',
    width: 'minmax(220px, 1.15fr)'
  },
  {
    id: 'operating_system',
    label: 'Système',
    width: 'minmax(180px, 1fr)'
  },
  {
    id: 'enabled',
    label: 'Activé',
    width: 'minmax(100px, 0.55fr)'
  },
  {
    id: 'group_scope',
    label: 'Étendue',
    width: 'minmax(120px, 0.65fr)'
  },
  {
    id: 'group_category',
    label: 'Catégorie',
    width: 'minmax(130px, 0.7fr)'
  },
  {
    id: 'canonical_name',
    label: 'Nom canonique',
    width: 'minmax(260px, 1.45fr)'
  },
  {
    id: 'distinguished_name',
    label: 'DN',
    width: 'minmax(320px, 1.8fr)'
  }
]

const columnById = new Map(
  AD_EXPLORER_COLUMNS.map(column => [
    column.id,
    column
  ])
)

function firstValue(item, aliases) {
  for (const alias of aliases) {
    const value = item?.[alias]

    if (
      value !== undefined
      && value !== null
      && String(value).trim() !== ''
    ) {
      return value
    }
  }

  return ''
}

export function getAdExplorerColumnDefinition(columnId) {
  return columnById.get(columnId) || null
}

export function normalizeAdExplorerColumnIds(value) {
  const source = Array.isArray(value)
    ? value
    : []

  const known = new Set()
  const result = []

  for (const columnId of source) {
    if (
      typeof columnId !== 'string'
      || !columnById.has(columnId)
      || known.has(columnId)
    ) {
      continue
    }

    known.add(columnId)
    result.push(columnId)
  }

  if (!known.has('name')) {
    result.unshift('name')
  }

  return result
}

export function getAdExplorerColumnValue(
  item,
  columnId,
  {
    getObjectName,
    getObjectType,
    getObjectDescription
  } = {}
) {
  switch (columnId) {
    case 'name':
      return (
        getObjectName?.(item)
        || firstValue(
          item,
          ['name', 'display_name', 'displayName']
        )
      )

    case 'type':
      return (
        getObjectType?.(item)
        || firstValue(
          item,
          ['type', 'object_class', 'objectClass']
        )
      )

    case 'description':
      return (
        getObjectDescription?.(item)
        || firstValue(item, ['description'])
      )

    case 'display_name':
      return firstValue(
        item,
        ['display_name', 'displayName']
      )

    case 'sam_account_name':
      return firstValue(
        item,
        ['sam_account_name', 'samAccountName']
      )

    case 'user_principal_name':
      return firstValue(
        item,
        ['user_principal_name', 'userPrincipalName']
      )

    case 'mail':
      return firstValue(
        item,
        ['mail', 'email']
      )

    case 'dns_host_name':
      return firstValue(
        item,
        ['dns_host_name', 'dNSHostName', 'dnsHostName']
      )

    case 'operating_system':
      return firstValue(
        item,
        ['operating_system', 'operatingSystem']
      )

    case 'enabled': {
      const value = firstValue(
        item,
        ['enabled']
      )

      if (value === '') {
        return ''
      }

      if (
        value === true
        || String(value).toLowerCase() === 'true'
      ) {
        return 'Oui'
      }

      if (
        value === false
        || String(value).toLowerCase() === 'false'
      ) {
        return 'Non'
      }

      return String(value)
    }

    case 'group_scope':
      return firstValue(
        item,
        ['group_scope', 'groupScope']
      )

    case 'group_category':
      return firstValue(
        item,
        ['group_category', 'groupCategory']
      )

    case 'canonical_name':
      return firstValue(
        item,
        ['canonical_name', 'canonicalName']
      )

    case 'distinguished_name':
      return firstValue(
        item,
        [
          'distinguished_name',
          'distinguishedName',
          'dn'
        ]
      )

    default:
      return ''
  }
}

export function normalizeAdExplorerSort(value) {
  const fallback = {
    columnId: 'name',
    direction: 'asc'
  }

  if (
    !value
    || typeof value !== 'object'
    || !columnById.has(value.columnId)
  ) {
    return fallback
  }

  return {
    columnId: value.columnId,
    direction:
      value.direction === 'desc'
        ? 'desc'
        : 'asc'
  }
}

export function sortAdExplorerItems(
  items,
  sort,
  getValue
) {
  const source = Array.isArray(items)
    ? [...items]
    : []

  const normalizedSort =
    normalizeAdExplorerSort(sort)

  const collator = new Intl.Collator(
    'fr',
    {
      numeric: true,
      sensitivity: 'base'
    }
  )

  source.sort((left, right) => {
    const leftValue = String(
      getValue(
        left,
        normalizedSort.columnId
      ) ?? ''
    ).trim()

    const rightValue = String(
      getValue(
        right,
        normalizedSort.columnId
      ) ?? ''
    ).trim()

    if (!leftValue && rightValue) {
      return 1
    }

    if (leftValue && !rightValue) {
      return -1
    }

    const compared = collator.compare(
      leftValue,
      rightValue
    )

    return normalizedSort.direction === 'desc'
      ? -compared
      : compared
  })

  return source
}

export function loadAdExplorerColumnPreferences(
  storage
) {
  try {
    const raw = storage?.getItem?.(
      AD_EXPLORER_COLUMNS_STORAGE_KEY
    )

    if (!raw) {
      return [
        ...DEFAULT_AD_EXPLORER_COLUMN_IDS
      ]
    }

    return normalizeAdExplorerColumnIds(
      JSON.parse(raw)
    )
  } catch {
    return [
      ...DEFAULT_AD_EXPLORER_COLUMN_IDS
    ]
  }
}

export function loadAdExplorerSortPreference(
  storage
) {
  try {
    const raw = storage?.getItem?.(
      AD_EXPLORER_SORT_STORAGE_KEY
    )

    if (!raw) {
      return normalizeAdExplorerSort(null)
    }

    return normalizeAdExplorerSort(
      JSON.parse(raw)
    )
  } catch {
    return normalizeAdExplorerSort(null)
  }
}

export function saveAdExplorerColumnPreferences(
  storage,
  columnIds
) {
  storage?.setItem?.(
    AD_EXPLORER_COLUMNS_STORAGE_KEY,
    JSON.stringify(
      normalizeAdExplorerColumnIds(columnIds)
    )
  )
}

export function saveAdExplorerSortPreference(
  storage,
  sort
) {
  storage?.setItem?.(
    AD_EXPLORER_SORT_STORAGE_KEY,
    JSON.stringify(
      normalizeAdExplorerSort(sort)
    )
  )
}
