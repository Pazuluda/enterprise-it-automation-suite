import {
  getOuLabelFromDn,
  splitLdapDn,
} from './adExplorerCore'

export function getCreateUserSearchBaseDn(dn) {
  const parts = splitLdapDn(dn)
  const firstDcIndex = parts.findIndex(part => /^DC=/i.test(part))

  if (firstDcIndex === -1) {
    return String(dn || '').trim()
  }

  const domainSuffix = parts.slice(firstDcIndex).join(',')
  const beforeDc = parts.slice(0, firstDcIndex)
  const ouParts = beforeDc.filter(part => /^OU=/i.test(part))

  if (ouParts.length > 0) {
    return `${ouParts[ouParts.length - 1]},${domainSuffix}`
  }

  return domainSuffix
}

export function getCreateUserOuItemsFromJob(job) {
  const output = job?.output || job?.result || job?.details || job || {}

  if (Array.isArray(output)) return output
  if (Array.isArray(output.items)) return output.items
  if (Array.isArray(output.objects)) return output.objects
  if (Array.isArray(output.ous)) return output.ous
  if (Array.isArray(output.organizational_units)) return output.organizational_units
  if (Array.isArray(output.data)) return output.data

  return []
}

export function dedupeCreateUserOuOptions(options) {
  const seen = new Set()
  const result = []

  for (const option of options) {
    const dn = String(option?.dn || option?.distinguished_name || option?.distinguishedName || '').trim()

    if (!dn) {
      continue
    }

    const key = dn.toUpperCase()

    if (seen.has(key)) {
      continue
    }

    seen.add(key)

    result.push({
      dn,
      label: option?.label || option?.name || option?.Name || getOuLabelFromDn(dn)
    })
  }

  return result
}

export function sortCreateUserOuOptions(options) {
  return [...options].sort((a, b) => {
    const aUsers = /(^|,)OU=Users,/i.test(a.dn)
    const bUsers = /(^|,)OU=Users,/i.test(b.dn)

    if (aUsers !== bUsers) {
      return aUsers ? -1 : 1
    }

    return String(a.label || '').localeCompare(String(b.label || ''), 'fr', { sensitivity: 'base' })
  })
}
