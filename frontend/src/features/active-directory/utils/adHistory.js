const AD_ADMIN_ACTION_LABELS = Object.freeze({
  create_ou: 'Créer une OU',
  create_container: 'Créer un conteneur',
  create_group: 'Créer un groupe',
  create_user: 'Créer un utilisateur',
  create_computer: 'Créer un ordinateur',
  create_contact: 'Créer un contact',
  add_group_member: 'Ajouter un membre au groupe',
  remove_group_member: 'Retirer un membre du groupe',
  move_object: 'Déplacer un objet',
  rename_object: 'Renommer un objet',
  delete_object: 'Supprimer un objet',
  update_object_properties: 'Modifier les propriétés',
  reset_password: 'Réinitialiser le mot de passe',
  disable_account: 'Désactiver le compte',
  enable_account: 'Activer le compte',
  unlock_account: 'Déverrouiller le compte'
})

const AD_ADMIN_STATUS_LABELS = Object.freeze({
  completed: 'Terminé',
  failed: 'Échec',
  processing: 'En cours',
  pending: 'En attente',
  claimed: 'Pris en charge',
  queued: 'En file d’attente',
  unknown: 'Inconnu'
})

const AD_ADMIN_TEXT_REPLACEMENTS = Object.freeze([
  ['dÃ©jÃ\u00a0', 'déjà'],
  ['dÃ©jÃ ', 'déjà '],
  ['dÃ©jÃ', 'déjà'],
  ['ajoutÃ©', 'ajouté'],
  ['retirÃ©', 'retiré'],
  ['crÃ©Ã©', 'créé'],
  ['crÃ©Ã©e', 'créée'],
  ['dÃ©placÃ©', 'déplacé'],
  ['renommÃ©', 'renommé'],
  ['supprimÃ©', 'supprimé'],
  ['modifiÃ©', 'modifié'],
  ['rÃ©initialisÃ©', 'réinitialisé'],
  ['dÃ©sactivÃ©', 'désactivé'],
  ['activÃ©', 'activé'],
  ['dÃ©verrouillÃ©', 'déverrouillé'],
  ['Ã‰', 'É'],
  ['Ã€', 'À'],
  ['Ã‡', 'Ç'],
  ['Ã©', 'é'],
  ['Ã¨', 'è'],
  ['Ãª', 'ê'],
  ['Ã«', 'ë'],
  ['Ã ', 'à'],
  ['Ã¢', 'â'],
  ['Ã§', 'ç'],
  ['Ã®', 'î'],
  ['Ã¯', 'ï'],
  ['Ã´', 'ô'],
  ['Ã¶', 'ö'],
  ['Ã¹', 'ù'],
  ['Ã»', 'û'],
  ['Ã¼', 'ü'],
  ['â€™', '’'],
  ['â€œ', '“'],
  ['â€\u009d', '”'],
  ['â€“', '–'],
  ['â€”', '—'],
  ['â€¢', '•'],
  ['â€¦', '…'],
  ['Â ', ' '],
  ['Â', '']
])

function cleanAdHistoryText(value) {
  let text = String(value ?? '')

  for (
    const [broken, corrected]
    of AD_ADMIN_TEXT_REPLACEMENTS
  ) {
    text = text.split(broken).join(corrected)
  }

  return text
    .replace(/\bdeja\b/gi, 'déjà')
    .replace(/déjà\s+/gi, 'déjà ')
    .trim()
}

function formatAdHistoryAction(action) {
  const key = String(action || '').trim()

  return (
    AD_ADMIN_ACTION_LABELS[key]
    || cleanAdHistoryText(key)
    || 'Action Active Directory'
  )
}

function formatAdHistoryDate(value) {
  if (!value) return '—'

  try {
    return new Date(value).toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return value
  }
}

function formatAdHistoryStatus(job) {
  let status = String(
    job?.status || 'unknown'
  ).toLowerCase()

  if (
    status === 'failed'
    || job?.success === false
  ) {
    status = 'failed'
  } else if (
    status === 'completed'
    || job?.success === true
  ) {
    status = 'completed'
  }

  return (
    AD_ADMIN_STATUS_LABELS[status]
    || cleanAdHistoryText(status)
    || AD_ADMIN_STATUS_LABELS.unknown
  )
}

function formatAdHistoryMessage(job) {
  const output = job?.output || {}
  const payload = job?.payload || {}
  const group = output.group || payload.group_identity || 'groupe'
  const member = output.member || payload.member_identity || 'membre'

  if (job?.action === 'add_group_member' && output.already_member) {
    return `${member} est déjà membre de ${group}`
  }

  if (job?.action === 'add_group_member') {
    return `${member} ajouté au groupe ${group}`
  }

  if (job?.action === 'remove_group_member') {
    return `${member} retiré du groupe ${group}`
  }
  if (job?.action === 'move_object') {
    const objectName = output.object || payload.object_identity || 'Objet AD'
    const target = output.target_parent_dn || payload.target_parent_dn || 'destination'
    return `${objectName} déplacé vers ${target}`
  }


  if (job?.action === 'create_group') {
    return `Groupe ${payload.name || output.name || group} créé`
  }

  if (job?.action === 'create_ou') {
    return `OU ${payload.name || output.name || 'AD'} créée`
  }

  if (job?.action === 'create_container') {
    return `Conteneur ${payload.name || output.name || 'AD'} créé`
  }

  if (job?.action === 'create_contact') {
    return `Contact ${payload.name || output.name || 'AD'} créé`
  }

  return cleanAdHistoryText(output.message || job?.message || '—')
}



function normalizeAdHistoryIdentity(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
}

function getAdHistoryObjectIdentities(job) {
  const identities = []

  function add(value) {
    const normalized =
      normalizeAdHistoryIdentity(value)

    if (
      normalized
      && !identities.includes(normalized)
    ) {
      identities.push(normalized)
    }
  }

  function collect(source) {
    if (
      !source
      || typeof source !== 'object'
    ) {
      return
    }

    [
      'object_identity',
      'objectIdentity',
      'object_dn',
      'objectDn',
      'distinguished_name',
      'distinguishedName',
      'dn',
      'new_dn',
      'newDn',
      'group_identity',
      'groupIdentity',
      'member_identity',
      'memberIdentity',
    ].forEach(key => add(source?.[key]))
  }

  const payload =
    job?.payload
    && typeof job.payload === 'object'
      ? job.payload
      : {}

  collect(payload)
  collect(job?.output)
  collect(job?.result)

  const action = String(
    job?.action || payload?.action || ''
  ).trim()

  const objectIdentity = String(
    payload?.object_identity
    || payload?.objectIdentity
    || payload?.object_dn
    || payload?.objectDn
    || ''
  ).trim()

  if (
    action === 'rename_object'
    && objectIdentity.includes(',')
  ) {
    const commaIndex =
      objectIdentity.indexOf(',')

    const currentRdn =
      objectIdentity.slice(0, commaIndex)

    const equalsIndex =
      currentRdn.indexOf('=')

    const newName = String(
      payload?.new_name
      || payload?.newName
      || ''
    ).trim()

    if (
      equalsIndex > 0
      && newName
    ) {
      const prefix =
        currentRdn.slice(0, equalsIndex)

      const parentDn =
        objectIdentity.slice(commaIndex + 1)

      add(
        `${prefix}=${newName},${parentDn}`
      )
    }
  }

  if (
    action === 'move_object'
    && objectIdentity.includes(',')
  ) {
    const commaIndex =
      objectIdentity.indexOf(',')

    const currentRdn =
      objectIdentity.slice(0, commaIndex)

    const targetParentDn = String(
      payload?.target_parent_dn
      || payload?.targetParentDn
      || ''
    ).trim()

    if (targetParentDn) {
      add(
        `${currentRdn},${targetParentDn}`
      )
    }
  }

  const createRdnByAction = {
    create_ou: 'OU',
    create_container: 'CN',
    create_group: 'CN',
    create_contact: 'CN',
    create_computer: 'CN',
    create_user: 'CN',
  }

  const createRdn =
    createRdnByAction[action]

  if (createRdn) {
    const parentDn = String(
      payload?.parent_dn
      || payload?.parentDn
      || payload?.target_parent_dn
      || payload?.targetParentDn
      || ''
    ).trim()

    const name = String(
      payload?.name
      || payload?.display_name
      || payload?.displayName
      || ''
    ).trim()

    if (
      parentDn
      && name
    ) {
      add(
        `${createRdn}=${name},${parentDn}`
      )
    }
  }

  return identities
}

function adHistoryJobMatchesObject(
  job,
  objectDn
) {
  const target =
    normalizeAdHistoryIdentity(objectDn)

  if (!target) {
    return false
  }

  return getAdHistoryObjectIdentities(
    job
  ).includes(target)
}

function formatAdHistorySummary(job) {
  return [
    `Action : ${formatAdHistoryAction(job?.action)}`,
    `Statut : ${formatAdHistoryStatus(job)}`,
    `Agent : ${job?.agent_name || job?.claimed_by || 'Agent non assigné'}`,
    `Résultat : ${formatAdHistoryMessage(job)}`
  ].join('\n')
}

function formatAdHistoryJson(value) {
  return cleanAdHistoryText(JSON.stringify(value || {}, null, 2))
}

export {
  AD_ADMIN_ACTION_LABELS,
  AD_ADMIN_STATUS_LABELS,
  AD_ADMIN_TEXT_REPLACEMENTS,
  cleanAdHistoryText,
  adHistoryJobMatchesObject,
  formatAdHistoryAction,
  formatAdHistoryDate,
  formatAdHistoryStatus,
  formatAdHistoryMessage,
  formatAdHistorySummary,
  formatAdHistoryJson,
}
