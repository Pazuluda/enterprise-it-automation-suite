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

export {
  adSnapshotCoversDn,
  findAdSnapshotObject,
  getAdSnapshotChildren,
  getAdSnapshotItems,
  getAdSnapshotOus,
  isAdSnapshotUsable,
  normalizeAdSnapshot,
}
