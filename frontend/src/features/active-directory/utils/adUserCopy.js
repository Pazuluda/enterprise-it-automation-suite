const EITAS_DN =
  'OU=EITAS,DC=API,DC=LOCAL'

export const COPY_USER_PROFILE_FIELDS =
  Object.freeze({
    description: Object.freeze([
      'description',
      'Description',
    ]),
    title: Object.freeze([
      'title',
      'Title',
    ]),
    department: Object.freeze([
      'department',
      'Department',
    ]),
    division: Object.freeze([
      'division',
      'Division',
    ]),
    company: Object.freeze([
      'company',
      'Company',
    ]),
    manager: Object.freeze([
      'manager',
      'Manager',
    ]),
    office: Object.freeze([
      'office',
      'Office',
      'physicalDeliveryOfficeName',
      'physical_delivery_office_name',
    ]),
    telephone_number: Object.freeze([
      'telephone_number',
      'telephoneNumber',
      'TelephoneNumber',
      'phone',
    ]),
    mobile: Object.freeze([
      'mobile',
      'Mobile',
    ]),
    street_address: Object.freeze([
      'street_address',
      'streetAddress',
      'StreetAddress',
    ]),
    postal_code: Object.freeze([
      'postal_code',
      'postalCode',
      'PostalCode',
    ]),
    city: Object.freeze([
      'city',
      'l',
    ]),
    state: Object.freeze([
      'state',
      'st',
    ]),
  })

export const COPY_USER_NEVER_FORM_FIELDS =
  Object.freeze([
    'memberOf',
    'member_of',
    'groups',
    'primaryGroupID',
    'primary_group_id',
    'primary_group_dn',

    'password',
    'new_password',
    'unicodePwd',
    'pwdLastSet',
    'password_last_set',
    'passwordNeverExpires',
    'password_never_expires',
    'cannotChangePassword',
    'cannot_change_password',

    'mail',
    'email',
    'employeeID',
    'employee_id',
    'employeeNumber',
    'employee_number',

    'objectGUID',
    'object_guid',
    'objectSid',
    'object_sid',
    'sid',

    'whenCreated',
    'whenChanged',
    'created_at',
    'updated_at',

    'lastLogon',
    'last_logon',
    'lastLogonDate',
    'badPwdCount',
    'bad_logon_count',
    'logonCount',

    'msDS-HABSeniorityIndex',
    'hab_seniority_index',
  ])

function pickText(source, aliases) {
  for (const alias of aliases) {
    const value = source?.[alias]

    if (
      value === null
      || value === undefined
    ) {
      continue
    }

    const text = String(value).trim()

    if (text) {
      return text
    }
  }

  return ''
}

function getObjectDn(source) {
  return pickText(source, [
    'distinguished_name',
    'distinguishedName',
    'dn',
    'DistinguishedName',
  ])
}

function splitLdapDn(value) {
  const source = String(value || '')
  const parts = []

  let current = ''
  let escaped = false

  for (const character of source) {
    if (escaped) {
      current += character
      escaped = false
      continue
    }

    if (character === '\\') {
      current += character
      escaped = true
      continue
    }

    if (character === ',') {
      if (current.trim()) {
        parts.push(current.trim())
      }

      current = ''
      continue
    }

    current += character
  }

  if (current.trim()) {
    parts.push(current.trim())
  }

  return parts
}

function isEitasManagedDn(value) {
  const dn = String(value || '')
    .trim()
    .toUpperCase()

  const root = EITAS_DN.toUpperCase()

  return (
    dn === root
    || dn.endsWith(`,${root}`)
  )
}

function isSafeOuDn(value) {
  const dn = String(value || '').trim()

  if (
    !dn
    || !isEitasManagedDn(dn)
  ) {
    return false
  }

  const firstPart = String(
    splitLdapDn(dn)[0] || ''
  )
    .trim()
    .toUpperCase()

  return firstPart.startsWith('OU=')
}

function getObjectClasses(source) {
  const raw =
    source?.objectClass
    ?? source?.object_class
    ?? source?.objectClasses
    ?? source?.object_classes
    ?? []

  const values = Array.isArray(raw)
    ? raw
    : String(raw || '').split(/[,\s]+/)

  return values
    .map(value =>
      String(value || '')
        .trim()
        .toLowerCase()
    )
    .filter(Boolean)
}

export function isCopyableUserSource(source) {
  if (
    !source
    || typeof source !== 'object'
  ) {
    return false
  }

  const type = String(
    source.type
    || source.object_type
    || source.objectType
    || ''
  )
    .trim()
    .toLowerCase()

  const classes = getObjectClasses(source)

  if (
    type === 'computer'
    || classes.includes('computer')
  ) {
    return false
  }

  if (
    type === 'contact'
    || type === 'group'
    || type === 'organizationalunit'
    || type === 'ou'
  ) {
    return false
  }

  if (type === 'user') {
    return true
  }

  return classes.includes('user')
}

export function getCopyUserSourceParentDn(
  source
) {
  const sourceDn = getObjectDn(source)

  if (
    !sourceDn
    || !isEitasManagedDn(sourceDn)
  ) {
    return EITAS_DN
  }

  const parts = splitLdapDn(sourceDn)

  if (parts.length < 2) {
    return EITAS_DN
  }

  const parentDn = parts
    .slice(1)
    .join(',')
    .trim()

  return isSafeOuDn(parentDn)
    ? parentDn
    : EITAS_DN
}

export function buildCopiedUserProfile(
  source
) {
  if (!isCopyableUserSource(source)) {
    throw new Error(
      'La source de copie doit être '
      + 'un utilisateur Active Directory.'
    )
  }

  return Object.fromEntries(
    Object.entries(
      COPY_USER_PROFILE_FIELDS
    ).map(([target, aliases]) => [
      target,
      pickText(source, aliases),
    ])
  )
}

export function buildCopyUserPreparation(
  source,
  {
    targetOuDn = '',
  } = {}
) {
  if (!isCopyableUserSource(source)) {
    throw new Error(
      'La source de copie doit être '
      + 'un utilisateur Active Directory.'
    )
  }

  const sourceDn = getObjectDn(source)

  const requestedOuDn = String(
    targetOuDn || ''
  ).trim()

  const safeTargetOuDn =
    isSafeOuDn(requestedOuDn)
      ? requestedOuDn
      : getCopyUserSourceParentDn(source)

  return {
    source: {
      distinguished_name: sourceDn,
      display_name: pickText(source, [
        'display_name',
        'displayName',
        'name',
      ]),
      sam_account_name: pickText(source, [
        'sam_account_name',
        'samAccountName',
        'sAMAccountName',
      ]),
    },
    form: {
      first_name: '',
      last_name: '',
      sam_account_name: '',
      user_principal_name: '',
      temporary_password: '',
      target_ou_dn: safeTargetOuDn,
      enabled: false,
      force_change_at_logon: true,
      ...buildCopiedUserProfile(source),
    },
  }
}
