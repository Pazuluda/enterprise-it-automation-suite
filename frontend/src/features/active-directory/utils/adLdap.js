export function splitLdapDn(dn) {
  return String(dn || '')
    .split(',')
    .map(part => part.trim())
    .filter(Boolean)
}

export function getOuLabelFromDn(dn) {
  const cleanDn = String(dn || '').trim()

  if (!cleanDn) {
    return 'OU inconnue'
  }

  const firstOuMatch = cleanDn.match(/^OU=([^,]+)/i)
  return firstOuMatch ? firstOuMatch[1] : cleanDn
}
