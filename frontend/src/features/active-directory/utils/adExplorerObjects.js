const DOMAIN_DN = 'DC=API,DC=LOCAL'
const EITAS_DN = `OU=EITAS,${DOMAIN_DN}`
const USERS_DN = `OU=Users,${EITAS_DN}`
const GROUPS_DN = `OU=Groups,${EITAS_DN}`
const COMPUTERS_DN = `OU=Computers,${EITAS_DN}`

function isEitasManagedDn(value) {
  const dn = String(value || '')
    .trim()
    .toLowerCase()

  const allowedBase = EITAS_DN.toLowerCase()

  return (
    dn === allowedBase ||
    dn.endsWith(`,${allowedBase}`)
  )
}

function isEitasManagedObject(item) {
  return isEitasManagedDn(getObjectDn(item))
}

function normalizeBaseDn(value) {
  const clean = String(value || '').trim()
  if (!clean) return ''
  if (/^(OU|DC|CN)=/i.test(clean)) return clean

  if (/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(clean)) {
    return clean
      .split('.')
      .filter(Boolean)
      .map(part => `DC=${part.toUpperCase()}`)
      .join(',')
  }

  return clean
}

function getOuDepth(item) {
  const dn = String(item?.distinguished_name || '')
  const ouParts = dn.split(',').filter(part => part.trim().toUpperCase().startsWith('OU='))
  return Math.max(0, ouParts.length - 1)
}

function buildOuTree(items) {
  return items
    .filter(item => String(item?.distinguished_name || '').startsWith('OU='))
    .map(item => ({
      ...item,
      depth: getOuDepth(item)
    }))
    .sort((a, b) => {
      const pathA = a.canonical_name || a.distinguished_name || a.name || ''
      const pathB = b.canonical_name || b.distinguished_name || b.name || ''
      return pathA.localeCompare(pathB)
    })
}

function objectIcon(item) {
  const name = String(item?.name || '').toLowerCase()

  if (name.includes('group')) return '📁'
  if (name.includes('user')) return '📁'
  if (name.includes('disabled')) return '📁'
  if (name.includes('domain controller')) return '📁'
  if (name.includes('computer')) return '📁'
  return '📁'
}

function getNodeKind(item) {
  const dn = String(item?.distinguished_name || '')
  const name = String(item?.name || '').toLowerCase()

  if (name.includes('group')) return 'groups'
  if (name.includes('user')) return 'users'
  if (dn.includes('OU=Groups')) return 'groups'
  if (dn.includes('OU=Users')) return 'users'
  return 'ou'
}

function extractExplorerItems(value) {
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.items)) return value.items
  if (Array.isArray(value?.result?.items)) return value.result.items
  if (Array.isArray(value?.output?.items)) return value.output.items
  return []
}

function getObjectName(item) {
  return item?.name || item?.display_name || item?.sam_account_name || '-'
}

function getGroupDescription(item) {
  if (getObjectType(item) === 'Ordinateur') {
    return (
      item?.description ||
      [
        item?.operating_system,
        item?.operating_system_version
      ]
        .filter(Boolean)
        .join(' ') ||
      item?.dns_host_name ||
      'Ordinateur Active Directory'
    )
  }

  if (getObjectType(item) === 'Utilisateur') {
    return (
      item?.description ||
      item?.user_principal_name ||
      'Utilisateur Active Directory'
    )
  }

  return item?.description || 'Objet Active Directory'
}

function getObjectType(item) {
  const rawType = String(
    item?.type ||
    item?.object_class ||
    item?.objectClass ||
    ''
  ).toLowerCase()

  if (rawType === 'computer-container') {
    return 'Conteneur d’ordinateurs'
  }

  if (
    rawType === 'computer' ||
    item?.dns_host_name ||
    item?.dnsHostName
  ) {
    return 'Ordinateur'
  }

  if (
    item?.type === 'group' ||
    item?.scope ||
    item?.category
  ) {
    return 'Groupe de sécurité'
  }

  if (
    item?.type === 'user' ||
    item?.user_principal_name
  ) {
    return 'Utilisateur'
  }

  if (item?.type === 'ou') {
    return 'Unité d’organisation'
  }

  return item?.type || 'Objet AD'
}


function getObjectDn(item) {
  return item?.distinguished_name || item?.dn || ''
}

function isOuObject(item) {
  const dn = String(getObjectDn(item)).trim().toUpperCase()

  if (dn) {
    return dn.startsWith('OU=')
  }

  return String(item?.type || '').toLowerCase() === 'ou'
}

function formatAdValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Oui' : 'Non'
  return String(value)
}

function formatGroupScope(value) {
  const map = {
    0: 'Domaine local',
    1: 'Globale',
    2: 'Universelle',
    DomainLocal: 'Domaine local',
    Global: 'Globale',
    Universal: 'Universelle'
  }

  return map[value] || value
}

function formatGroupCategory(value) {
  const map = {
    0: 'Distribution',
    1: 'Sécurité',
    Distribution: 'Distribution',
    Security: 'Sécurité'
  }

  return map[value] || value
}

function getObjectMetaRows(item) {
  if (!item) return []

  const rows = [
    { label: 'Nom', value: getObjectName(item) },
    { label: 'Type', value: getObjectType(item) },
    { label: 'Nom de compte SAM', value: item?.sam_account_name },
    { label: 'UPN', value: item?.user_principal_name },
    {
      label: 'Nom DNS',
      value: item?.dns_host_name || item?.dnsHostName
    },
    {
      label: 'Adresse IPv4',
      value: item?.ipv4_address || item?.ipv4Address
    },
    {
      label: 'Système',
      value: item?.operating_system || item?.operatingSystem
    },
    {
      label: 'Version du système',
      value:
        item?.operating_system_version ||
        item?.operatingSystemVersion
    },
    { label: 'Portée', value: isGroupObject(item) && item?.group_scope !== undefined ? formatGroupScope(item.group_scope) : '' },
    { label: 'Catégorie', value: isGroupObject(item) && item?.group_category !== undefined ? formatGroupCategory(item.group_category) : '' },
    { label: 'Description', value: item?.description },
    { label: 'DN', value: getObjectDn(item), long: true }
  ]

  return rows.filter(row => row.value !== undefined && row.value !== null && row.value !== '')
}


function isGroupObject(item) {
  const type = getObjectType(item)
  return item?.type === 'group' || type.includes('Groupe')
}

function getRenameDefaultName(item) {
  return item?.name || item?.sam_account_name || ''
}

function getParentDn(dn) {
  const value = String(dn || '')
  const index = value.indexOf(',')

  if (index === -1) return ''

  return value.slice(index + 1)
}


function getAdDnPartLabel(part) {
  return String(part || '')
    .replace(/^(OU|DC|CN)=/i, '')
    .replace(/\\,/g, ',')
    .trim()
}


function buildAdCanonicalName(dn) {
  const parts = String(dn || '')
    .split(',')
    .map(part => part.trim())
    .filter(Boolean)

  const domainParts = parts
    .filter(part => /^DC=/i.test(part))
    .map(getAdDnPartLabel)

  const ouParts = parts
    .filter(part => /^OU=/i.test(part))
    .reverse()
    .map(getAdDnPartLabel)

  return [
    domainParts.join('.'),
    ...ouParts
  ]
    .filter(Boolean)
    .join('/')
}


function buildAdNavigationNode(dn) {
  const cleanDn = String(dn || '').trim()

  if (!cleanDn) {
    return null
  }

  const firstPart = cleanDn
    .split(',')[0]
    ?.trim()

  const isDomain =
    /^DC=/i.test(firstPart)

  const name = isDomain
    ? buildAdCanonicalName(cleanDn)
    : getAdDnPartLabel(firstPart)

  return {
    name: name || cleanDn,
    type: isDomain ? 'domain' : 'ou',
    distinguished_name: cleanDn,
    dn: cleanDn,
    canonical_name:
      buildAdCanonicalName(cleanDn)
  }
}


function buildAdBreadcrumbs(dn) {
  const cleanDn = String(dn || '').trim()

  if (!cleanDn) {
    return []
  }

  const parts = cleanDn
    .split(',')
    .map(part => part.trim())
    .filter(Boolean)

  const domainParts = parts.filter(
    part => /^DC=/i.test(part)
  )

  if (domainParts.length === 0) {
    return []
  }

  const domainDn = domainParts.join(',')

  const domainLabel = domainParts
    .map(getAdDnPartLabel)
    .join('.')

  const breadcrumbs = [
    {
      label: domainLabel || domainDn,
      dn: domainDn,
      node: buildAdNavigationNode(domainDn)
    }
  ]

  const ouPartsFromRoot = parts
    .filter(part => /^OU=/i.test(part))
    .reverse()

  ouPartsFromRoot.forEach((part, index) => {
    const currentOuDn = [
      ...ouPartsFromRoot
        .slice(0, index + 1)
        .reverse(),
      ...domainParts
    ].join(',')

    breadcrumbs.push({
      label: getAdDnPartLabel(part),
      dn: currentOuDn,
      node: buildAdNavigationNode(currentOuDn)
    })
  })

  return breadcrumbs
}

export {
  DOMAIN_DN,
  EITAS_DN,
  USERS_DN,
  GROUPS_DN,
  COMPUTERS_DN,
  isEitasManagedDn,
  isEitasManagedObject,
  normalizeBaseDn,
  getOuDepth,
  buildOuTree,
  objectIcon,
  getNodeKind,
  extractExplorerItems,
  getObjectName,
  getGroupDescription,
  getObjectType,
  getObjectDn,
  isOuObject,
  formatAdValue,
  formatGroupScope,
  formatGroupCategory,
  getObjectMetaRows,
  isGroupObject,
  getRenameDefaultName,
  getParentDn,
  getAdDnPartLabel,
  buildAdCanonicalName,
  buildAdNavigationNode,
  buildAdBreadcrumbs,
}
