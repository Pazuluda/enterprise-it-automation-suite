import {
  getObjectDn,
  getParentDn,
} from './adExplorerCore'

function normalizeSnapshotDn(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
}

function getSnapshotObjectType(item) {
  return String(
    item?.object_class ||
    item?.type ||
    ''
  )
    .trim()
    .toLowerCase()
}

function normalizeSnapshotItem(item) {
  if (!item || typeof item !== 'object') {
    return null
  }

  const distinguishedName = String(
    getObjectDn(item) || ''
  ).trim()

  if (!distinguishedName) {
    return null
  }

  const objectType = getSnapshotObjectType(item)

  return {
    ...item,
    distinguished_name:
      item.distinguished_name ||
      distinguishedName,
    dn:
      item.dn ||
      distinguishedName,
    object_class:
      item.object_class ||
      objectType,
    type:
      item.type ||
      objectType,
  }
}

function compareSnapshotItems(first, second) {
  const typeOrder = {
    ou: 0,
    organizationalunit: 0,
    group: 1,
    user: 2,
    computer: 3,
  }

  const firstType = getSnapshotObjectType(first)
  const secondType = getSnapshotObjectType(second)

  const firstRank =
    typeOrder[firstType] ?? 10

  const secondRank =
    typeOrder[secondType] ?? 10

  if (firstRank !== secondRank) {
    return firstRank - secondRank
  }

  const firstLabel = String(
    first?.display_name ||
    first?.name ||
    first?.sam_account_name ||
    getObjectDn(first) ||
    ''
  )

  const secondLabel = String(
    second?.display_name ||
    second?.name ||
    second?.sam_account_name ||
    getObjectDn(second) ||
    ''
  )

  return firstLabel.localeCompare(
    secondLabel,
    'fr',
    {
      sensitivity: 'base',
    }
  )
}

function normalizeAdSnapshot(payload) {
  if (
    !payload ||
    typeof payload !== 'object' ||
    Array.isArray(payload)
  ) {
    return null
  }

  const baseDn = String(
    payload.base_dn ||
    payload.baseDn ||
    ''
  ).trim()

  if (!baseDn) {
    return null
  }

  const sourceItems = Array.isArray(
    payload.items
  )
    ? payload.items
    : []

  const seen = new Set()
  const items = []

  sourceItems.forEach(sourceItem => {
    const item = normalizeSnapshotItem(
      sourceItem
    )

    if (!item) {
      return
    }

    const distinguishedName = normalizeSnapshotDn(
      getObjectDn(item)
    )

    if (
      distinguishedName &&
      seen.has(distinguishedName)
    ) {
      return
    }

    if (distinguishedName) {
      seen.add(distinguishedName)
    }

    items.push(item)
  })

  return {
    ...payload,
    base_dn: baseDn,
    items,
    count: items.length,
  }
}

function getAdSnapshotItems(snapshot) {
  return Array.isArray(snapshot?.items)
    ? snapshot.items
    : []
}

function isAdSnapshotUsable(snapshot) {
  return Boolean(
    snapshot &&
    typeof snapshot === 'object' &&
    String(snapshot.base_dn || '').trim() &&
    Array.isArray(snapshot.items) &&
    snapshot.is_stale !== true
  )
}

function adSnapshotCoversDn(
  snapshot,
  distinguishedName
) {
  if (!isAdSnapshotUsable(snapshot)) {
    return false
  }

  const targetDn = normalizeSnapshotDn(
    distinguishedName
  )

  const baseDn = normalizeSnapshotDn(
    snapshot.base_dn
  )

  if (!targetDn || !baseDn) {
    return false
  }

  return (
    targetDn === baseDn ||
    targetDn.endsWith(`,${baseDn}`)
  )
}

function getAdSnapshotOus(snapshot) {
  if (!isAdSnapshotUsable(snapshot)) {
    return []
  }

  return getAdSnapshotItems(snapshot)
    .filter(item => {
      const objectType =
        getSnapshotObjectType(item)

      return (
        objectType === 'ou' ||
        objectType ===
          'organizationalunit'
      )
    })
    .sort(compareSnapshotItems)
}

function getAdSnapshotChildren(
  snapshot,
  distinguishedName
) {
  if (
    !adSnapshotCoversDn(
      snapshot,
      distinguishedName
    )
  ) {
    return null
  }

  const parentKey = normalizeSnapshotDn(
    distinguishedName
  )

  return getAdSnapshotItems(snapshot)
    .filter(item => {
      const itemParentDn = getParentDn(
        getObjectDn(item)
      )

      return (
        normalizeSnapshotDn(
          itemParentDn
        ) === parentKey
      )
    })
    .sort(compareSnapshotItems)
}

function findAdSnapshotObject(
  snapshot,
  distinguishedName
) {
  if (!isAdSnapshotUsable(snapshot)) {
    return null
  }

  const targetDn = normalizeSnapshotDn(
    distinguishedName
  )

  if (!targetDn) {
    return null
  }

  return (
    getAdSnapshotItems(snapshot)
      .find(item =>
        normalizeSnapshotDn(
          getObjectDn(item)
        ) === targetDn
      ) ||
    null
  )
}


function searchAdSnapshot(
  snapshot,
  options = {}
) {
  const baseDn = String(
    options.baseDn ||
    options.base_dn ||
    snapshot?.base_dn ||
    ''
  ).trim()

  if (
    !isAdSnapshotUsable(snapshot) ||
    !adSnapshotCoversDn(
      snapshot,
      baseDn
    )
  ) {
    return null
  }

  const query = String(
    options.query || ''
  )
    .trim()
    .toLowerCase()

  const recursive =
    options.recursive !== false

  const cleanLimit = Math.max(
    1,
    Number(options.limit) || 1000
  )

  const requestedTypes = Array.isArray(
    options.types
  )
    ? options.types
    : []

  const allowedTypes = new Set(
    requestedTypes
      .map(value =>
        String(value || '')
          .trim()
          .toLowerCase()
      )
      .map(value =>
        value === 'organizationalunit'
          ? 'ou'
          : value
      )
      .filter(Boolean)
  )

  const baseKey =
    normalizeSnapshotDn(baseDn)

  const fields = [
    'name',
    'display_name',
    'displayName',
    'sam_account_name',
    'samAccountName',
    'user_principal_name',
    'userPrincipalName',
    'upn',
    'mail',
    'email',
    'description',
    'title',
    'department',
    'division',
    'company',
    'dns_host_name',
    'dnsHostName',
    'distinguished_name',
    'dn',
    'canonical_name',
  ]

  return getAdSnapshotItems(snapshot)
    .filter(item => {
      const itemDn =
        normalizeSnapshotDn(
          getObjectDn(item)
        )

      if (
        !itemDn ||
        itemDn === baseKey
      ) {
        return false
      }

      const insideBase = recursive
        ? itemDn.endsWith(
            `,${baseKey}`
          )
        : normalizeSnapshotDn(
            getParentDn(itemDn)
          ) === baseKey

      if (!insideBase) {
        return false
      }

      const rawType =
        getSnapshotObjectType(item)

      const objectType =
        rawType === 'organizationalunit'
          ? 'ou'
          : rawType

      if (
        allowedTypes.size > 0 &&
        !allowedTypes.has(objectType)
      ) {
        return false
      }

      if (!query) {
        return true
      }

      return fields.some(field => {
        const value = item?.[field]

        if (
          value === undefined ||
          value === null
        ) {
          return false
        }

        return String(value)
          .toLowerCase()
          .includes(query)
      })
    })
    .sort(compareSnapshotItems)
    .slice(0, cleanLimit)
}

function getAdSnapshotGroupMembers(
  snapshot,
  target
) {
  if (!isAdSnapshotUsable(snapshot)) {
    return null
  }

  const targetDn = String(
    getObjectDn(target) || ''
  ).trim()

  if (
    !targetDn ||
    !adSnapshotCoversDn(
      snapshot,
      targetDn
    )
  ) {
    return null
  }

  const targetIdentity = String(
    target?.sam_account_name ||
    target?.samAccountName ||
    target?.name ||
    ''
  )
    .trim()
    .toLowerCase()

  const group =
    findAdSnapshotObject(
      snapshot,
      targetDn
    ) ||
    getAdSnapshotItems(snapshot)
      .find(item => {
        const objectType =
          getSnapshotObjectType(item)

        if (objectType !== 'group') {
          return false
        }

        const candidateIdentity = String(
          item?.sam_account_name ||
          item?.samAccountName ||
          item?.name ||
          ''
        )
          .trim()
          .toLowerCase()

        return (
          targetIdentity &&
          candidateIdentity ===
            targetIdentity
        )
      })

  if (
    !group ||
    !Array.isArray(group.members)
  ) {
    return null
  }

  const resolvedMembers = []
  const seen = new Set()

  for (const memberValue of group.members) {
    const memberDn = String(
      typeof memberValue === 'string'
        ? memberValue
        : getObjectDn(memberValue)
    ).trim()

    if (!memberDn) {
      return null
    }

    const member =
      findAdSnapshotObject(
        snapshot,
        memberDn
      )

    if (!member) {
      return null
    }

    const memberKey =
      normalizeSnapshotDn(memberDn)

    if (seen.has(memberKey)) {
      continue
    }

    seen.add(memberKey)
    resolvedMembers.push(member)
  }

  return resolvedMembers
    .sort(compareSnapshotItems)
}

export {
  adSnapshotCoversDn,
  findAdSnapshotObject,
  getAdSnapshotGroupMembers,
  getAdSnapshotChildren,
  getAdSnapshotItems,
  getAdSnapshotOus,
  isAdSnapshotUsable,
  normalizeAdSnapshot,
  searchAdSnapshot,
}
