import { useEffect, useMemo, useState } from 'react'

const DOMAIN_DN = 'DC=API,DC=LOCAL'
const USERS_DN = `OU=Users,OU=EITAS,${DOMAIN_DN}`
const GROUPS_DN = `OU=Groups,OU=EITAS,${DOMAIN_DN}`

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
  return item?.description || 'Groupe EITAS lab'
}

function getObjectType(item) {
  if (item?.type === 'group' || item?.scope || item?.category) return 'Groupe de sécurité'
  if (item?.type === 'user' || item?.user_principal_name) return 'Utilisateur'
  if (item?.type === 'ou') return 'Unité d’organisation'
  return item?.type || 'Objet AD'
}


function getObjectDn(item) {
  return item?.distinguished_name || item?.dn || ''
}

function isOuObject(item) {
  const dn = String(getObjectDn(item)).toUpperCase()
  return item?.type === 'ou' || dn.startsWith('OU=')
}

function formatAdValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Oui' : 'Non'
  return String(value)
}

function formatGroupScope(value) {
  const map = {
    0: 'DomainLocal',
    1: 'Global',
    2: 'Universal',
    DomainLocal: 'DomainLocal',
    Global: 'Global',
    Universal: 'Universal'
  }

  return map[value] || value
}

function formatGroupCategory(value) {
  const map = {
    0: 'Distribution',
    1: 'Security',
    Distribution: 'Distribution',
    Security: 'Security'
  }

  return map[value] || value
}

function getObjectMetaRows(item) {
  if (!item) return []

  const rows = [
    { label: 'Nom', value: getObjectName(item) },
    { label: 'Type', value: getObjectType(item) },
    { label: 'SamAccountName', value: item?.sam_account_name },
    { label: 'UPN', value: item?.user_principal_name },
    { label: 'Scope', value: item?.group_scope !== undefined ? formatGroupScope(item.group_scope) : '' },
    { label: 'Catégorie', value: item?.group_category !== undefined ? formatGroupCategory(item.group_category) : '' },
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


function cleanAdHistoryText(value) {
  return String(value || '')
    .replaceAll('dÃ©jÃ ', 'déjà')
    .replaceAll('dÃ©jÃ', 'déjà')
    .replaceAll('dÃ©jÃ ', 'déjà ')
    .replaceAll('ajoutÃ©', 'ajouté')
    .replaceAll('retirÃ©', 'retiré')
    .replaceAll('crÃ©Ã©', 'créé')
    .replaceAll('Ã©', 'é')
    .replaceAll('Ã¨', 'è')
    .replaceAll('Ãª', 'ê')
    .replaceAll('Ã ', 'à')
    .replaceAll('Ã ', 'à')
    .replaceAll('Ã§', 'ç')
    .replaceAll(' deja ', ' déjà ')
    .replaceAll(' deja  ', ' déjà ')
    .replaceAll('deja', 'déjà')
    .replace(/déjà\s+dans/g, 'déjà dans')
    .replaceAll('déjà    dans', 'déjà dans')
    .replaceAll('déjà   dans', 'déjà dans')
    .replaceAll('déjà  dans', 'déjà dans')
}

function formatAdHistoryAction(action) {
  return {
    create_ou: 'Création OU',
    create_group: 'Création groupe',
    add_group_member: 'Ajout membre',
    remove_group_member: 'Retrait membre',
    move_object: 'Déplacement objet',
    rename_object: 'Renommage objet',
    delete_object: 'Suppression objet',
    update_object_properties: 'Modification propriétés'
  }[action] || action || 'Action AD'
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
  if (job?.status === 'completed' && job?.success) return 'terminé'
  if (job?.status === 'failed' || job?.success === false) return 'échec'
  if (job?.status === 'processing') return 'en cours'
  if (job?.status === 'pending') return 'en attente'
  return job?.status || 'statut inconnu'
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

  return cleanAdHistoryText(output.message || job?.message || '—')
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

function ObjectDetailsPanel({ object, selectedNode, memberItems, membersLoading, membersError, historyItems, historyLoading, historyError, historyFilter, onHistoryFilterChange, onOpenHistoryJob, onLoadHistory, onCopyDn, onExplore, onCreateOu, onCreateGroup, onOpenMoveObject, onLoadMembers, onOpenAddMember, onRemoveMember }) {
  const displayed = object || selectedNode
  const hasObject = Boolean(displayed)
  const rows = getObjectMetaRows(displayed)
  const dn = getObjectDn(displayed)
  const type = getObjectType(displayed)
  const isOu = isOuObject(displayed)
  const isGroup = isGroupObject(displayed)
  const members = Array.isArray(memberItems) ? memberItems : []
  const history = Array.isArray(historyItems) ? historyItems : []
  const filteredHistory = history.filter(job => {
    if (historyFilter === 'all') return true
    if (historyFilter === 'members') return ['add_group_member', 'remove_group_member'].includes(job.action)
    if (historyFilter === 'create') return ['create_ou', 'create_group'].includes(job.action)
    if (historyFilter === 'failed') return job.status === 'failed' || job.success === false
    return true
  })

  return (
    <aside className="aduc-details-pane">
      <div className="aduc-details-header">
        <span className={`aduc-object-avatar ${isOu ? 'ou' : isGroup ? 'group' : type.includes('Utilisateur') ? 'user' : ''}`}>
          {isOu ? '📁' : isGroup ? '👥' : type.includes('Utilisateur') ? '👤' : 'ⓘ'}
        </span>

        <div>
          <h3>{hasObject ? getObjectName(displayed) : 'Aucun objet sélectionné'}</h3>
          <p>{hasObject ? type : 'Clique un objet pour afficher ses propriétés.'}</p>
        </div>
      </div>

      {hasObject ? (
        <>
          <div className="aduc-details-actions">
            <button
              type="button"
              onClick={() => onCopyDn(displayed)}
              disabled={!dn}
            >
              Copier DN
            </button>

            {isGroup && (
              <button
                type="button"
                onClick={() => onLoadMembers(displayed)}
                disabled={membersLoading}
              >
                {membersLoading ? 'Chargement...' : 'Voir membres'}
              </button>
            )}

            {isOu && (
              <button
                type="button"
                onClick={() => onExplore(displayed)}
              >
                Explorer cette OU
              </button>
            )}
          </div>

          <div className="aduc-details-grid">
            {rows.map(row => (
              <div className={row.long ? 'long' : ''} key={row.label}>
                <span>{row.label}</span>
                <strong>{formatAdValue(row.value)}</strong>
              </div>
            ))}
          </div>

          {isGroup && (
            <div className="aduc-members-card">
              <div className="aduc-members-head">
                <div>
                  <h4>Membres du groupe</h4>
                  <span>{membersLoading ? 'Chargement...' : `${members.length} membre(s)`}</span>
                </div>

                <div className="aduc-members-buttons">
                  <button
                    type="button"
                    onClick={() => onOpenAddMember(displayed)}
                    disabled={membersLoading}
                    title="Ajouter un membre"
                  >
                    ＋
                  </button>

                  <button
                    type="button"
                    onClick={() => onLoadMembers(displayed)}
                    disabled={membersLoading}
                    title="Actualiser les membres"
                  >
                    ⟳
                  </button>
                </div>
              </div>

              {membersError ? (
                <p className="aduc-members-error">{membersError}</p>
              ) : membersLoading ? (
                <p className="aduc-members-empty">Chargement des membres depuis SRV-DC01...</p>
              ) : members.length === 0 ? (
                <p className="aduc-members-empty">Aucun membre dans ce groupe.</p>
              ) : (
                <div className="aduc-members-list">
                  {members.map((member, index) => (
                    <div className="aduc-member-row" key={member.distinguished_name || member.sam_account_name || index}>
                      <span>{member.type === 'group' ? '👥' : member.type === 'user' ? '👤' : 'ⓘ'}</span>
                      <div>
                        <strong>{member.name || member.sam_account_name || 'Membre AD'}</strong>
                        <small>{member.sam_account_name || member.distinguished_name || '—'}</small>
                      </div>
                      <button
                        type="button"
                        className="aduc-member-remove"
                        onClick={() => onRemoveMember(displayed, member)}
                        disabled={membersLoading}
                        title="Retirer du groupe"
                      >
                        Retirer
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}


          <div className="aduc-admin-history-card">
            <div className="aduc-admin-history-head">
              <div>
                <h4>Historique AD Admin</h4>
                <span>{historyLoading ? 'Chargement...' : `${filteredHistory.length}/${history.length} action(s)`}</span>
              </div>

              <button type="button" onClick={onLoadHistory} disabled={historyLoading}>
                ⟳ Actualiser
              </button>
            </div>

            <div className="aduc-admin-history-filters">
              {[
                ['all', 'Tout'],
                ['members', 'Membres'],
                ['create', 'Créations'],
                ['failed', 'Échecs']
              ].map(([value, label]) => (
                <button
                  type="button"
                  key={value}
                  className={historyFilter === value ? 'active' : ''}
                  onClick={() => onHistoryFilterChange(value)}
                >
                  {label}
                </button>
              ))}
            </div>

            {historyError ? (
              <p className="aduc-admin-history-error">{historyError}</p>
            ) : filteredHistory.length === 0 ? (
              <p className="aduc-admin-history-empty">Aucune action AD Admin récente.</p>
            ) : (
              <div className="aduc-admin-history-list">
                {filteredHistory.slice(0, 8).map(job => (
                  <button
                    type="button"
                    className={`aduc-admin-history-row ${job.success ? 'success' : 'failed'}`}
                    key={job.id}
                    onClick={() => onOpenHistoryJob(job)}
                  >
                    <span />
                    <div>
                      <strong>{formatAdHistoryAction(job.action)}</strong>
                      <small>{job.agent_name || job.claimed_by || 'Agent non assigné'} • {formatAdHistoryStatus(job)}</small>
                      <em>{formatAdHistoryMessage(job)}</em>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="aduc-details-quick">
            <button type="button" onClick={() => onCreateOu(isOu ? displayed : selectedNode)}>
              ＋ OU ici
            </button>
            <button type="button" onClick={() => onCreateGroup(isOu ? displayed : selectedNode)}>
              ＋ Groupe ici
            </button>

            {object && (
              <button type="button" onClick={() => onOpenMoveObject(displayed)}>
                ↪ Déplacer
              </button>
            )}
          </div>
        </>
      ) : (
        <div className="aduc-details-empty">
          Sélectionne une OU, un utilisateur ou un groupe dans la liste centrale.
        </div>
      )}
    </aside>
  )
}


async function copyText(value) {
  const text = String(value ?? '')

  if (navigator?.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // Fallback below
    }
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '0'
  document.body.appendChild(textarea)

  textarea.focus()
  textarea.select()
  textarea.setSelectionRange(0, textarea.value.length)

  try {
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)

    if (!ok) {
      throw new Error('Copie refusée par le navigateur')
    }

    return true
  } catch (err) {
    document.body.removeChild(textarea)
    throw err
  }
}

export default function AdExplorerPage({ apiFetch, setMessage }) {
  const [treeItems, setTreeItems] = useState([])
  const [viewItems, setViewItems] = useState([])
  const [selectedNode, setSelectedNode] = useState({
    name: 'Groups',
    distinguished_name: GROUPS_DN,
    canonical_name: 'API.LOCAL/EITAS/Groups'
  })

  const [viewType, setViewType] = useState('groups')
  const [selectedObject, setSelectedObject] = useState(null)
  const [newObjectModal, setNewObjectModal] = useState(null)
  const [propertiesModal, setPropertiesModal] = useState(null)
  const [searchOuModal, setSearchOuModal] = useState(null)
  const [searchOuQuery, setSearchOuQuery] = useState('')
  const [objectMembers, setObjectMembers] = useState([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [membersError, setMembersError] = useState('')
  const [memberModal, setMemberModal] = useState(null)
  const [memberIdentity, setMemberIdentity] = useState('')
  const [memberSearchResults, setMemberSearchResults] = useState([])
  const [memberSearchLoading, setMemberSearchLoading] = useState(false)
  const [memberSearchError, setMemberSearchError] = useState('')
  const [selectedMemberCandidate, setSelectedMemberCandidate] = useState(null)
  const [memberSubmitError, setMemberSubmitError] = useState('')
  const [memberActionLoading, setMemberActionLoading] = useState(false)
  const [treeFilter, setTreeFilter] = useState('')
  const [viewFilter, setViewFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('Connexion au contrôleur de domaine : SRV-DC01.API.LOCAL')
  const [contextMenu, setContextMenu] = useState(null)
  const [adminModal, setAdminModal] = useState(null)
  const [adAgentMode, setAdAgentMode] = useState('Inconnu')
  const [adAgentModeLoading, setAdAgentModeLoading] = useState(false)
  const [adminOuOptions, setAdminOuOptions] = useState([])
  const [adminOuLoading, setAdminOuLoading] = useState(false)
  const [createUserModal, setCreateUserModal] = useState(null)
  const [createUserLoading, setCreateUserLoading] = useState(false)
  const [createUserOuOptions, setCreateUserOuOptions] = useState([])
  const [createUserOuLoading, setCreateUserOuLoading] = useState(false)
  const [createUserForm, setCreateUserForm] = useState({
    first_name: '',
    last_name: '',
    sam_account_name: '',
    temporary_password: 'TempP@ssw0rd!2026',
    description: '',
    target_ou_dn: '',
    enabled: false
  })
  const [adminForm, setAdminForm] = useState({
    name: '',
    description: '',
    sam_account_name: '',
    group_scope: 'Global',
    group_category: 'Security'
  })
  const [adminLoading, setAdminLoading] = useState(false)
  const [moveModal, setMoveModal] = useState(null)
  const [renameModal, setRenameModal] = useState(null)
  const [deleteModal, setDeleteModal] = useState(null)
  const [updateModal, setUpdateModal] = useState(null)
  const [updateForm, setUpdateForm] = useState({ description: '' })
  const [updateOriginalForm, setUpdateOriginalForm] = useState({ description: '' })
  const [deleteConfirmDn, setDeleteConfirmDn] = useState('')
  const [renameNewName, setRenameNewName] = useState('')
  const [moveTargetDn, setMoveTargetDn] = useState('')
  const [globalAdSearch, setGlobalAdSearch] = useState('')
  const [globalAdSearchLoading, setGlobalAdSearchLoading] = useState(false)
  const [testCleanupModal, setTestCleanupModal] = useState(false)
  const [testCleanupLoading, setTestCleanupLoading] = useState(false)
  const [testCleanupItems, setTestCleanupItems] = useState([])
  const [testCleanupError, setTestCleanupError] = useState('')
  const [testCleanupDeletingDn, setTestCleanupDeletingDn] = useState('')
  const [testCleanupResults, setTestCleanupResults] = useState({})
  const [adAdminHistory, setAdAdminHistory] = useState([])
  const [adAdminHistoryLoading, setAdAdminHistoryLoading] = useState(false)
  const [adAdminHistoryError, setAdAdminHistoryError] = useState('')
  const [adAdminHistoryFilter, setAdAdminHistoryFilter] = useState('all')
  const [selectedAdAdminHistoryJob, setSelectedAdAdminHistoryJob] = useState(null)

  const filteredTree = useMemo(() => {
    const filter = treeFilter.trim().toLowerCase()
    const items = buildOuTree(treeItems)

    if (!filter) return items

    return items.filter(item =>
      JSON.stringify(item).toLowerCase().includes(filter)
    )
  }, [treeItems, treeFilter])

  const filteredViewItems = useMemo(() => {
    const filter = viewFilter.trim().toLowerCase()

    if (!filter) return viewItems

    return viewItems.filter(item =>
      JSON.stringify(item).toLowerCase().includes(filter)
    )
  }, [viewItems, viewFilter])

  async function runJob(action, options = {}) {
    const created = await apiFetch('/api/ad-explorer/jobs', {
      method: 'POST',
      body: JSON.stringify({
        action,
        query: options.query || '',
        base_dn: normalizeBaseDn(options.baseDn || options.base_dn || options.baseDN || ''),
        limit: options.limit || 200,
        recursive: options.recursive || false,
        include_disabled: true,
        created_by: 'react-admin'
      })
    })

    const jobId = created.job.id

    for (let attempt = 0; attempt < 45; attempt += 1) {
      const job = await apiFetch(`/api/ad-explorer/jobs/${jobId}`)

      if (job.status === 'completed' || job.status === 'failed') {
        if (!job.success) {
          throw new Error(job.message || job.output || 'Erreur Active Directory')
        }

        return Array.isArray(job.result?.items) ? job.result.items : []
      }

      await new Promise(resolve => setTimeout(resolve, 450))
    }

    throw new Error('Timeout : l’agent Windows n’a pas répondu.')
  }

  async function loadTree() {
    const ous = await runJob('list_ous', { limit: 500 })
    setTreeItems(ous)
    return ous
  }

  async function loadNodeContent(node = selectedNode, kind = getNodeKind(node)) {
    if (!node) return

    const baseDn = getObjectDn(node)

    setLoading(true)
    setContextMenu(null)

    try {
      setSelectedNode(node)
      setSelectedObject(null)
      setObjectMembers([])
      setMembersError('')
      setViewType(kind)

      if (!baseDn) {
        setViewItems([])
        setStatus('DN introuvable pour cet objet AD.')
        return
      }

      const [ousResult, groupsResult, usersResult] = await Promise.allSettled([
        runJob('list_ous', {
          baseDn,
          recursive: false,
          limit: 500
        }),
        runJob('list_groups', {
          baseDn,
          recursive: false,
          limit: 500
        }),
        runJob('search_users', {
          query: '',
          baseDn,
          recursive: false,
          limit: 500
        })
      ])

      const items = []

      if (ousResult.status === 'fulfilled') {
        items.push(...extractExplorerItems(ousResult.value))
      }

      if (groupsResult.status === 'fulfilled') {
        items.push(...extractExplorerItems(groupsResult.value))
      }

      if (usersResult.status === 'fulfilled') {
        items.push(...extractExplorerItems(usersResult.value))
      }

      const seen = new Set()
      const uniqueItems = items.filter(item => {
        const key = getObjectDn(item) || item?.sam_account_name || item?.name

        if (!key) return true
        if (seen.has(key)) return false

        seen.add(key)
        return true
      })

      setViewItems(uniqueItems)
      setStatus(`Connexion au contrôleur de domaine : SRV-DC01.API.LOCAL`)
    } catch (err) {
      setViewItems([])
      setStatus(err.message || 'Erreur Active Directory')
      setMessage?.(err.message || 'Erreur Active Directory')
    } finally {
      setLoading(false)
    }
  }

  async function loadAdAdminHistory() {
    setAdAdminHistoryLoading(true)
    setAdAdminHistoryError('')

    try {
      const data = await apiFetch('/api/ad-admin/jobs?limit=20')
      setAdAdminHistory(Array.isArray(data.jobs) ? data.jobs : [])
    } catch (err) {
      setAdAdminHistoryError(err.message || 'Impossible de charger l’historique AD Admin.')
    } finally {
      setAdAdminHistoryLoading(false)
    }
  }

  async function refreshAll() {
    setLoading(true)

    try {
      await loadTree()
      await loadNodeContent(selectedNode, viewType)
    } catch (err) {
      setStatus(err.message || 'Erreur Active Directory')
      setMessage?.(err.message || 'Erreur Active Directory')
    } finally {
      setLoading(false)
    }
  }

  async function loadGroupMembers(target = selectedObject, options = {}) {
    if (!target || !isGroupObject(target)) return

    const identity = target.sam_account_name || target.name || getObjectDn(target)

    if (!identity) {
      setMembersError('Identité groupe introuvable.')
      return
    }

    setMembersLoading(true)
    setMembersError('')

    try {
      const parentDn = getParentDn(getObjectDn(target)) || GROUPS_DN

      const members = await runJob('get_group_members', {
        query: identity,
        baseDn: parentDn,
        limit: 500
      })

      setObjectMembers(members)
      if (!options.silent) setMessage?.(`Membres chargés pour ${target.name || identity}.`)
    } catch (err) {
      setObjectMembers([])
      setMembersError(err.message || 'Impossible de charger les membres du groupe.')
      setMessage?.(err.message || 'Impossible de charger les membres du groupe.')
    } finally {
      setMembersLoading(false)
    }
  }

  function selectObject(item) {
    setSelectedObject(item)
    setObjectMembers([])
    setMembersError('')

    if (isGroupObject(item)) {
      loadGroupMembers(item)
    }
  }

  function openContextMenu(event, target, targetType = 'tree') {
    event.preventDefault()
    event.stopPropagation()

    const menuWidth = 260
    const menuHeight = 470

    const x = Math.min(event.clientX, window.innerWidth - menuWidth - 12)
    const y = Math.min(event.clientY, window.innerHeight - menuHeight - 12)

    setContextMenu({
      x: Math.max(12, x),
      y: Math.max(12, y),
      target,
      targetType
    })
  }

  function closeContextMenu() {
    setContextMenu(null)
  }

  function openNewObjectMenu(target) {
    const base = target || selectedNode

    if (!getObjectDn(base)) {
      setStatus('DN introuvable pour créer un nouvel objet.')
      return
    }

    setContextMenu(null)
    setNewObjectModal(base)
  }

  function actionSoon(label) {
    setContextMenu(null)
    setMessage?.(`${label} : prochaine étape, création/modification AD sécurisée via job agent.`)
  }


  function getPropertiesRows(target) {
    if (!target) return []

    return [
      ['Nom', target.name],
      ['Type', getObjectType(target)],
      ['SAM', target.sam_account_name || target.samAccountName],
      ['UPN', target.user_principal_name || target.userPrincipalName],
      ['Display Name', target.displayName || target.display_name],
      ['Description', target.description],
      ['Mail', target.mail || target.email],
      ['Poste', target.title || target.job_title],
      ['Département', target.department],
      ['Société', target.company],
      ['Téléphone', target.telephoneNumber || target.telephone_number || target.phone],
      ['Bureau', target.physicalDeliveryOfficeName || target.office],
      ['DN', getObjectDn(target)],
      ['Canonical Name', target.canonical_name || target.canonicalName],
    ].filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
  }


  function itemMatchesOuSearch(item, query) {
    const q = query.toLowerCase()

    return [
      item?.name,
      item?.sam_account_name,
      item?.samAccountName,
      item?.description,
      item?.displayName,
      item?.display_name,
      item?.mail,
      item?.email,
      item?.distinguished_name,
      item?.dn,
      item?.canonical_name
    ]
      .filter(Boolean)
      .some(value => String(value).toLowerCase().includes(q))
  }

  function openSearchOuModal(target) {
    const base = target || selectedNode
    const baseDn = getObjectDn(base)

    if (!baseDn) {
      setStatus('DN introuvable pour cette recherche.')
      return
    }

    setContextMenu(null)
    setSearchOuModal(base)
    setSearchOuQuery('')
  }

  async function submitSearchOuModal(event) {
    event.preventDefault()

    if (!searchOuQuery.trim()) {
      setStatus('Saisis un texte à rechercher.')
      return
    }

    await searchInOuSimple(searchOuModal || selectedNode, searchOuQuery.trim())
    setSearchOuModal(null)
    setSearchOuQuery('')
  }

  async function searchInOuSimple(target, forcedQuery = '') {
    const base = target || selectedNode
    const baseDn = getObjectDn(base)

    if (!baseDn) {
      setStatus('DN introuvable pour cette recherche.')
      return
    }

    const query = forcedQuery || window.prompt(`Rechercher dans :\n${baseDn}`)

    if (!query || !query.trim()) {
      return
    }

    const search = query.trim()

    setContextMenu(null)
    setLoading(true)

    try {
      const jobs = await Promise.allSettled([
        runJob('list_ous', { baseDn, recursive: true, limit: 500 }),
        runJob('list_groups', { baseDn, recursive: true, limit: 1000 }),
        runJob('search_users', { query: search, baseDn, recursive: true, limit: 500 })
      ])

      const collected = []

      jobs.forEach((result, index) => {
        if (result.status !== 'fulfilled') return

        const items = extractExplorerItems(result.value)

        if (index === 2) {
          collected.push(...items)
        } else {
          collected.push(...items.filter(item => itemMatchesOuSearch(item, search)))
        }
      })

      const seen = new Set()
      const uniqueResults = collected.filter(item => {
        const key = getObjectDn(item) || item?.sam_account_name || item?.name

        if (!key) return true
        if (seen.has(key)) return false

        seen.add(key)
        return true
      })

      setSelectedNode({
        name: `Recherche : ${search}`,
        type: 'search',
        distinguished_name: baseDn,
        dn: baseDn,
        canonical_name: `Recherche dans ${baseDn}`
      })

      setViewType('search')
      setViewItems(uniqueResults)
      setSelectedObject(null)
      setObjectMembers([])
      setMembersError('')
      setStatus(`${uniqueResults.length} résultat(s) trouvé(s)`)
    } catch (err) {
      setStatus(err.message || 'Erreur pendant la recherche AD.')
    } finally {
      setLoading(false)
    }
  }

  async function openProperties(target) {
    setContextMenu(null)

    if (!target) {
      setStatus('Aucun objet sélectionné.')
      return
    }

    setSelectedObject(target)
    setPropertiesModal(target)
  }


  async function runGlobalAdSearch(event) {
    event?.preventDefault?.()

    const query = globalAdSearch.trim()

    if (!query) {
      setStatus('Recherche AD vide.')
      return
    }

    setGlobalAdSearchLoading(true)
    setStatus(`Recherche globale AD : ${query}...`)

    try {
      const baseDn = 'OU=EITAS,DC=API,DC=LOCAL'
      const lowered = query.toLowerCase()

      const [usersResult, groupsResult] = await Promise.allSettled([
        runJob('search_users', {
          query,
          baseDn,
          recursive: true,
          limit: 100
        }),
        runJob('list_groups', {
          baseDn,
          recursive: true,
          limit: 500
        })
      ])

      const results = []

      if (usersResult.status === 'fulfilled') {
        results.push(...extractExplorerItems(usersResult.value))
      }

      if (groupsResult.status === 'fulfilled') {
        const groups = extractExplorerItems(groupsResult.value)

        results.push(...groups.filter(group => [
          group?.name,
          group?.sam_account_name,
          group?.description,
          group?.distinguished_name,
          group?.dn
        ]
          .filter(Boolean)
          .some(value => String(value).toLowerCase().includes(lowered))
        ))
      }

      const seen = new Set()
      const uniqueResults = results.filter(item => {
        const key = getObjectDn(item) || item?.sam_account_name || item?.name

        if (!key) return true
        if (seen.has(key)) return false

        seen.add(key)
        return true
      })

      setSelectedNode({
        name: `Recherche globale : ${query}`,
        type: 'search',
        distinguished_name: baseDn,
        dn: baseDn
      })

      setViewType('search')
      setViewItems(uniqueResults)
      setSelectedObject(null)
      setObjectMembers([])
      setMembersError('')

      setStatus(`${uniqueResults.length} résultat(s) pour ${query}`)
    } catch (err) {
      setStatus(err.message || 'Recherche globale AD impossible.')
    } finally {
      setGlobalAdSearchLoading(false)
    }
  }

  

function getAdAttributeValue(item, ...names) {
    for (const name of names) {
      const value = item?.[name]

      if (value !== undefined && value !== null) {
        return String(value)
      }
    }

    return ''
  }

  function openUpdateObject(target) {
    if (!target) {
      setStatus('Aucun objet sélectionné pour la modification.')
      return
    }

    const dn = getObjectDn(target)

    if (!dn) {
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    const form = {
      description: getAdAttributeValue(target, 'description'),
      displayName: getAdAttributeValue(target, 'displayName', 'display_name', 'display_name_value'),
      mail: getAdAttributeValue(target, 'mail', 'email'),
      title: getAdAttributeValue(target, 'title', 'job_title'),
      department: getAdAttributeValue(target, 'department'),
      company: getAdAttributeValue(target, 'company'),
      telephoneNumber: getAdAttributeValue(target, 'telephoneNumber', 'telephone_number', 'phone'),
      physicalDeliveryOfficeName: getAdAttributeValue(target, 'physicalDeliveryOfficeName', 'office')
    }

    setContextMenu(null)
    setUpdateModal(target)
    setUpdateForm(form)
    setUpdateOriginalForm(form)
  }

  function updateObjectFormField(name, value) {
    setUpdateForm(previous => ({
      ...previous,
      [name]: value
    }))
  }

  async function submitUpdateObject(event) {
    event.preventDefault()

    if (!updateModal) return

    const objectDn = getObjectDn(updateModal)

    if (!objectDn) {
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    const properties = {}

    Object.entries(updateForm).forEach(([key, value]) => {
      const currentValue = value || ''
      const originalValue = updateOriginalForm?.[key] || ''

      if (currentValue !== originalValue) {
        properties[key] = currentValue
      }
    })

    if (Object.keys(properties).length === 0) {
      setStatus('Aucune modification à enregistrer.')
      return
    }

    setLoading(true)

    try {
      const job = await runAdAdminJob({
        action: 'update_object_properties',
        object_identity: objectDn,
        properties,
        created_by: 'react-admin'
      })

      const message = cleanAdHistoryText(job?.message || job?.output?.message || 'Propriétés objet AD modifiées')
      setStatus(message)
      setUpdateModal(null)

      await loadTree()

      if (selectedNode) {
        await loadNodeContent(selectedNode, viewType)
      }

      await loadAdAdminHistory()
    } catch (err) {
      setStatus(err.message || 'Erreur pendant la modification AD.')
    } finally {
      setLoading(false)
    }
  }

  function openDeleteObject(target) {
    if (!target) {
      setStatus('Aucun objet sélectionné pour la suppression.')
      return
    }

    const dn = getObjectDn(target)

    if (!dn) {
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    setContextMenu(null)
    setDeleteModal(target)
    setDeleteConfirmDn(dn)
  }

  async function submitDeleteObject(event) {
    event.preventDefault()

    if (!deleteModal) return

    const objectDn = getObjectDn(deleteModal)
    const confirmDn = deleteConfirmDn.trim()

    if (!objectDn) {
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    if (confirmDn !== objectDn) {
      setStatus('Confirmation DN incorrecte. Suppression annulée.')
      return
    }

    setLoading(true)

    try {
      const job = await runAdAdminJob({
        action: 'delete_object',
        object_identity: objectDn,
        confirm_dn: confirmDn,
        created_by: 'react-admin'
      })

      const message = cleanAdHistoryText(job?.message || job?.output?.message || 'Objet AD supprimé')
      setStatus(message)
      setDeleteModal(null)
      setDeleteConfirmDn('')

      await loadTree()

      if (selectedNode) {
        await loadNodeContent(selectedNode, viewType)
      }

      await loadAdAdminHistory()
    } catch (err) {
      setStatus(err.message || 'Erreur pendant la suppression AD.')
    } finally {
      setLoading(false)
    }
  }

  function openRenameObject(target) {
    if (!target) {
      setStatus('Aucun objet sélectionné pour le renommage.')
      return
    }

    const dn = getObjectDn(target)

    if (!dn) {
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    setContextMenu(null)
    setRenameModal(target)
    setRenameNewName(getRenameDefaultName(target))
  }

  async function submitRenameObject(event) {
    event.preventDefault()

    if (!renameModal) return

    const objectDn = getObjectDn(renameModal)
    const newName = renameNewName.trim()

    if (!objectDn) {
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    if (!newName) {
      setStatus('Le nouveau nom est obligatoire.')
      return
    }

    if (newName === getRenameDefaultName(renameModal)) {
      setStatus('Le nouveau nom est identique au nom actuel.')
      return
    }

    setLoading(true)

    try {
      const job = await runAdAdminJob({
        action: 'rename_object',
        object_identity: objectDn,
        new_name: newName,
        created_by: 'react-admin'
      })

      const message = cleanAdHistoryText(job?.message || job?.output?.message || 'Objet AD renommé')
      setStatus(message)
      setRenameModal(null)
      setRenameNewName('')

      await loadTree()

      if (selectedNode) {
        await loadNodeContent(selectedNode, viewType)
      }

      await loadAdAdminHistory()
    } catch (err) {
      setStatus(err.message || 'Erreur pendant le renommage AD.')
    } finally {
      setLoading(false)
    }
  }

  function openMoveObject(target) {
    const dn = getObjectDn(target)

    if (!target || !dn) {
      setStatus('Aucun objet AD valide à déplacer.')
      return
    }

    setMoveModal(target)
    setMoveTargetDn('')
  }

  function normalizeCreateUserPart(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '.')
      .replace(/^\.+|\.+$/g, '')
  }

  function getSuggestedSamAccountName(firstName, lastName) {
    const first = normalizeCreateUserPart(firstName)
    const last = normalizeCreateUserPart(lastName)

    if (!first || !last) {
      return ''
    }

    return `${first}.${last}`.slice(0, 20)
  }

  function validateCreateUserForm(form) {
    const errors = []
    const firstName = form.first_name.trim()
    const lastName = form.last_name.trim()
    const sam = form.sam_account_name.trim()
    const password = form.temporary_password.trim()

    if (!firstName) errors.push('Le prénom est obligatoire.')
    if (!lastName) errors.push('Le nom est obligatoire.')

    if (!sam) {
      errors.push('L’identifiant est obligatoire. Format conseillé : prenom.nom')
    } else {
      if (sam.length > 20) {
        errors.push('L’identifiant AD ne doit pas dépasser 20 caractères.')
      }

      if (!/^[a-zA-Z0-9._-]+$/.test(sam)) {
        errors.push('L’identifiant ne doit contenir que lettres, chiffres, point, tiret ou underscore. Pas d’espace, pas d’accent.')
      }

      const expected = getSuggestedSamAccountName(firstName, lastName)

      if (expected && sam.toLowerCase() !== expected.toLowerCase()) {
        errors.push(`Format conseillé pour cet utilisateur : ${expected}`)
      }
    }

    if (!password) {
      errors.push('Le mot de passe temporaire est obligatoire.')
    } else {
      if (password.length < 12) {
        errors.push('Le mot de passe doit faire au moins 12 caractères.')
      }

      if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/[0-9]/.test(password) || !/[^a-zA-Z0-9]/.test(password)) {
        errors.push('Le mot de passe doit contenir minuscule, majuscule, chiffre et caractère spécial.')
      }

      const lowerPassword = password.toLowerCase()
      if (
        firstName && lowerPassword.includes(firstName.toLowerCase())
        || lastName && lowerPassword.includes(lastName.toLowerCase())
        || sam && lowerPassword.includes(sam.toLowerCase())
      ) {
        errors.push('Le mot de passe ne doit pas contenir le prénom, le nom ou l’identifiant.')
      }
    }

    return errors
  }

  function getCreateUserFriendlyError(message) {
    const raw = String(message || '')
    const lower = raw.toLowerCase()

    if (lower.includes('spécifications de longueur') || lower.includes('specifications de longueur') || lower.includes('complexité') || lower.includes('complexite') || lower.includes('historique du domaine')) {
      return [
        'Mot de passe refusé par la stratégie du domaine.',
        '',
        'Utilise un mot de passe temporaire plus fort :',
        '- minimum 12 caractères',
        '- une majuscule',
        '- une minuscule',
        '- un chiffre',
        '- un caractère spécial',
        '- ne pas reprendre le prénom, le nom ou l’identifiant',
        '',
        'Exemple de format : Temp!2026-User'
      ].join('\n')
    }

    if (lower.includes('nom déjà utilisé') || lower.includes('nom deja utilise') || lower.includes('already exists') || lower.includes('deja existant') || lower.includes('déjà existant')) {
      return [
        'Impossible de créer cet utilisateur : un objet AD existe déjà avec ce nom ou cet identifiant.',
        '',
        'Essaie avec un identifiant unique au format prénom.nom.',
        'Exemple : test.reactou2'
      ].join('\n')
    }

    if (lower.includes('ou cible')) {
      return 'OU cible invalide ou introuvable. Choisis une OU existante dans la liste.'
    }

    return raw || 'Erreur inconnue pendant la création utilisateur.'
  }

  function splitLdapDn(dn) {
    return String(dn || '')
      .split(',')
      .map(part => part.trim())
      .filter(Boolean)
  }

  function isOuDn(dn) {
    return /^OU=/i.test(String(dn || '').trim())
  }

  function getOuNameFromRdn(rdn) {
    return String(rdn || '').replace(/^OU=/i, '')
  }

  function getDomainSuffixFromDn(dn) {
    const parts = splitLdapDn(dn)
    const firstDcIndex = parts.findIndex(part => /^DC=/i.test(part))

    if (firstDcIndex === -1) {
      return ''
    }

    return parts.slice(firstDcIndex).join(',')
  }

  function getCreateUserSearchBaseDn(dn) {
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

  function getOuLabelFromDn(dn) {
    const cleanDn = String(dn || '').trim()

    if (!cleanDn) {
      return 'OU inconnue'
    }

    const firstOuMatch = cleanDn.match(/^OU=([^,]+)/i)
    return firstOuMatch ? firstOuMatch[1] : cleanDn
  }

  function getOuPathLabelFromDn(dn, baseDn = '') {
    const dnOuParts = splitLdapDn(dn).filter(part => /^OU=/i.test(part))
    const baseOuParts = splitLdapDn(baseDn).filter(part => /^OU=/i.test(part))

    if (dnOuParts.length === 0) {
      return getOuLabelFromDn(dn)
    }

    let labelParts = [...dnOuParts]

    while (
      labelParts.length > 0
      && baseOuParts.length > 0
      && labelParts[labelParts.length - 1].toUpperCase() === baseOuParts[baseOuParts.length - 1].toUpperCase()
    ) {
      labelParts.pop()
      baseOuParts.pop()
    }

    const names = labelParts
      .reverse()
      .map(getOuNameFromRdn)
      .filter(Boolean)

    if (names.length === 0) {
      return getOuLabelFromDn(dn)
    }

    return names.join(' / ')
  }

  function getFallbackCreateUserOuOptions(baseDn = '') {
    const fallbackDn = baseDn || getCreateUserSearchBaseDn(getObjectDn(selectedNode))

    if (!fallbackDn) {
      return []
    }

    return [{
      dn: fallbackDn,
      label: isOuDn(fallbackDn) ? getOuLabelFromDn(fallbackDn) : fallbackDn
    }]
  }

  function getCreateUserOuItemsFromJob(job) {
    const output = job?.output || job?.result || job?.details || job || {}

    if (Array.isArray(output)) return output
    if (Array.isArray(output.items)) return output.items
    if (Array.isArray(output.objects)) return output.objects
    if (Array.isArray(output.ous)) return output.ous
    if (Array.isArray(output.organizational_units)) return output.organizational_units
    if (Array.isArray(output.data)) return output.data

    return []
  }

  function dedupeCreateUserOuOptions(options) {
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

  function sortCreateUserOuOptions(options) {
    return [...options].sort((a, b) => {
      const aUsers = /(^|,)OU=Users,/i.test(a.dn)
      const bUsers = /(^|,)OU=Users,/i.test(b.dn)

      if (aUsers !== bUsers) {
        return aUsers ? -1 : 1
      }

      return String(a.label || '').localeCompare(String(b.label || ''), 'fr', { sensitivity: 'base' })
    })
  }

  async function waitForAdExplorerJob(jobId) {
    for (let index = 0; index < 24; index += 1) {
      await new Promise(resolve => setTimeout(resolve, 500))

      const job = await apiFetch(`/api/ad-explorer/jobs/${jobId}`)

      if (job?.status === 'completed') {
        return job
      }

      if (job?.status === 'failed') {
        throw new Error(job?.message || 'Job AD Explorer échoué')
      }
    }

    throw new Error('Job AD Explorer trop long')
  }

  async function listOuChildrenForCreateUser(baseDn) {
    const created = await apiFetch('/api/ad-explorer/jobs', {
      method: 'POST',
      body: JSON.stringify({
        action: 'list_ous',
        base_dn: baseDn,
        baseDn,
        parent_dn: baseDn,
        created_by: 'react-create-user-ou-loader'
      })
    })

    const jobId = created?.job?.id

    if (!jobId) {
      throw new Error('Job list_ous introuvable')
    }

    const completedJob = await waitForAdExplorerJob(jobId)
    return getCreateUserOuItemsFromJob(completedJob)
  }

  async function loadCreateUserOuOptions(initialDn = '') {
    const searchBaseDn = getCreateUserSearchBaseDn(
      initialDn
      || createUserForm.target_ou_dn
      || getObjectDn(createUserModal?.target)
      || getObjectDn(selectedNode)
    )

    if (!searchBaseDn) {
      setCreateUserOuOptions([])
      return
    }

    setCreateUserOuLoading(true)

    try {
      const created = await apiFetch('/api/ad-explorer/jobs', {
        method: 'POST',
        body: JSON.stringify({
          action: 'list_ou_tree',
          base_dn: searchBaseDn,
          baseDn: searchBaseDn,
          created_by: 'react-create-user-ou-tree'
        })
      })

      const jobId = created?.job?.id

      if (!jobId) {
        throw new Error('Job list_ou_tree introuvable')
      }

      const completedJob = await waitForAdExplorerJob(jobId)
      const items = getCreateUserOuItemsFromJob(completedJob)

      const options = sortCreateUserOuOptions(dedupeCreateUserOuOptions(
        items
          .map(item => {
            const dn = getObjectDn(item)

            return {
              dn,
              label: item?.path_label || item?.pathLabel || item?.label || item?.name || item?.Name || getOuLabelFromDn(dn)
            }
          })
          .filter(option => option.dn)
      ))

      setCreateUserOuOptions(options.length ? options : getFallbackCreateUserOuOptions(searchBaseDn))

      const preferred = options.find(option => /(^| \/ )Users( \/ |$)/i.test(option.label))
        || options.find(option => /^Users$/i.test(getOuLabelFromDn(option.dn)))
        || options[0]

      if (preferred) {
        setCreateUserForm(current => {
          const currentDn = String(current.target_ou_dn || '').trim()
          const exists = options.some(option => option.dn.toUpperCase() === currentDn.toUpperCase())

          const currentIsSearchBase = currentDn && currentDn.toUpperCase() === searchBaseDn.toUpperCase()

          if (exists && currentDn && !currentIsSearchBase) {
            return current
          }

          return {
            ...current,
            target_ou_dn: preferred.dn
          }
        })
      }
    } catch (error) {
      console.warn('Impossible de charger l’arbre OU AD', error)
      setCreateUserOuOptions(getFallbackCreateUserOuOptions(searchBaseDn))
    } finally {
      setCreateUserOuLoading(false)
    }
  }

  async function loadAdAgentMode() {
    setAdAgentModeLoading(true)

    try {
      const data = await apiFetch('/api/agent/mode')
      setAdAgentMode(data?.mode || 'Inconnu')
    } catch (error) {
      console.warn('Impossible de charger le mode agent', error)
      setAdAgentMode('Inconnu')
    } finally {
      setAdAgentModeLoading(false)
    }
  }

  function getAdAgentModeLabel() {
    if (adAgentModeLoading) {
      return 'Chargement du mode agent...'
    }

    return `Mode agent : ${adAgentMode || 'Inconnu'}`
  }

  function isAdProductionMode() {
    return String(adAgentMode || '').toLowerCase() === 'production'
  }

  async function confirmProductionAdAction(actionLabel, targetLabel = '') {
    if (!isAdProductionMode()) {
      return true
    }

    const details = targetLabel ? `\n\nCible : ${targetLabel}` : ''

    return window.confirm(
      `ATTENTION : mode Production AD.\n\n${actionLabel} sera exécutée réellement dans Active Directory.${details}\n\nContinuer ?`
    )
  }


  function openCreateUser(target = selectedNode) {
    loadAdAgentMode()
    const base = target || selectedNode
    const targetDn = getObjectDn(base)

    if (!targetDn) {
      window.alert('OU cible introuvable.')
      return
    }

    const defaultUserOuDn = getCreateUserSearchBaseDn(targetDn) || targetDn

    setCreateUserForm({
      first_name: '',
      last_name: '',
      sam_account_name: '',
      temporary_password: 'TempP@ssw0rd!2026',
      description: '',
      target_ou_dn: defaultUserOuDn,
      enabled: false
    })

    setCreateUserModal({
      target: base,
      target_ou_dn: defaultUserOuDn
    })

    setCreateUserOuOptions(getFallbackCreateUserOuOptions())
    window.setTimeout(() => {
      loadCreateUserOuOptions(defaultUserOuDn)
    }, 0)
  }

  async function submitCreateUser(event) {
    event.preventDefault()

    if (!createUserModal) {
      return
    }

    const firstName = createUserForm.first_name.trim()
    const lastName = createUserForm.last_name.trim()
    const samAccountName = createUserForm.sam_account_name.trim()
    const temporaryPassword = createUserForm.temporary_password.trim()
    const targetOuDn = createUserForm.target_ou_dn.trim() || createUserModal.target_ou_dn || getObjectDn(createUserModal.target)

    const validationErrors = validateCreateUserForm(createUserForm)

    if (!targetOuDn) {
      validationErrors.push('OU cible obligatoire.')
    }

    if (validationErrors.length > 0) {
      window.alert(`Création utilisateur impossible :\n\n${validationErrors.join('\n')}`)
      return
    }

    if (!(await confirmProductionAdAction('La création utilisateur', `${firstName} ${lastName} (${samAccountName}) dans ${targetOuDn}`))) {
      return
    }

    setCreateUserLoading(true)

    try {
      const created = await apiFetch('/api/ad-admin/jobs', {
        method: 'POST',
        body: JSON.stringify({
          action: 'create_user',
          first_name: firstName,
          last_name: lastName,
          sam_account_name: samAccountName,
          target_ou_dn: targetOuDn,
          temporary_password: temporaryPassword,
          description: createUserForm.description.trim(),
          enabled: Boolean(createUserForm.enabled),
          created_by: 'react-ad-explorer'
        })
      })

      const jobId = created?.job?.id

      if (!jobId) {
        throw new Error('Job création utilisateur introuvable.')
      }

      for (let index = 0; index < 30; index += 1) {
        await new Promise(resolve => setTimeout(resolve, 1000))

        const job = await apiFetch(`/api/ad-admin/jobs/${jobId}`)

        if (job?.status === 'completed') {
          setCreateUserModal(null)
          window.alert(job?.message || 'Création utilisateur terminée.')
          return
        }

        if (job?.status === 'failed') {
          throw new Error(job?.message || 'Création utilisateur échouée.')
        }
      }

      throw new Error('Création utilisateur trop longue, vérifie l’historique des jobs.')
    } catch (error) {
      window.alert(getCreateUserFriendlyError(error?.message || 'Erreur pendant la création utilisateur.'))
    } finally {
      setCreateUserLoading(false)
    }
  }

  function getCreateAdminParentDn(target = selectedNode) {
    const targetDn = getObjectDn(target)

    if (!targetDn) {
      return ''
    }

    const parts = splitLdapDn(targetDn)

    if (parts.length === 0) {
      return ''
    }

    if (/^OU=/i.test(parts[0])) {
      return targetDn
    }

    return parts.slice(1).join(',')
  }

  function getPreferredOuForAction(options, action, currentDn = '') {
    const safeOptions = Array.isArray(options) ? options : []
    const wantedDn = String(currentDn || '').trim()

    const exactCurrent = safeOptions.find(option =>
      String(option.dn || '').toUpperCase() === wantedDn.toUpperCase()
    )

    if (action === 'create_group') {
      return safeOptions.find(option => /(^| \/ )Groups( \/ |$)/i.test(option.label))
        || safeOptions.find(option => /(^|,)OU=Groups,/i.test(option.dn))
        || exactCurrent
        || safeOptions[0]
    }

    if (action === 'create_user') {
      return safeOptions.find(option => /(^| \/ )Users( \/ |$)/i.test(option.label))
        || safeOptions.find(option => /(^|,)OU=Users,/i.test(option.dn))
        || exactCurrent
        || safeOptions[0]
    }

    return exactCurrent || safeOptions[0]
  }

  async function loadAdminOuOptions(parentDn = '') {
    const searchBaseDn = getCreateUserSearchBaseDn(parentDn) || parentDn

    if (!searchBaseDn) {
      setAdminOuOptions([])
      return
    }

    setAdminOuLoading(true)

    try {
      const created = await apiFetch('/api/ad-explorer/jobs', {
        method: 'POST',
        body: JSON.stringify({
          action: 'list_ou_tree',
          base_dn: searchBaseDn,
          baseDn: searchBaseDn,
          created_by: 'react-admin-create-ou-tree'
        })
      })

      const jobId = created?.job?.id

      if (!jobId) {
        throw new Error('Job list_ou_tree introuvable')
      }

      const completedJob = await waitForAdExplorerJob(jobId)
      const items = getCreateUserOuItemsFromJob(completedJob)

      const options = sortCreateUserOuOptions(dedupeCreateUserOuOptions(
        items
          .map(item => {
            const dn = getObjectDn(item)

            return {
              dn,
              label: item?.path_label || item?.pathLabel || item?.label || item?.name || item?.Name || getOuLabelFromDn(dn)
            }
          })
          .filter(option => option.dn)
      ))

      const finalOptions = options.length ? options : getFallbackCreateUserOuOptions(searchBaseDn)

      setAdminOuOptions(finalOptions)

      setAdminForm(current => {
        const currentDn = String(current.parent_dn || '').trim()
        const exists = finalOptions.some(option => option.dn.toUpperCase() === currentDn.toUpperCase())

        if (exists && currentDn) {
          return current
        }

        const preferred = getPreferredOuForAction(finalOptions, adminModal?.action, parentDn)

        return {
          ...current,
          parent_dn: preferred?.dn || parentDn
        }
      })
    } catch (error) {
      console.warn('Impossible de charger l’arbre OU AD pour création OU/groupe', error)
      setAdminOuOptions(getFallbackCreateUserOuOptions(searchBaseDn))
    } finally {
      setAdminOuLoading(false)
    }
  }

  function openCreateOu(target = selectedNode) {
    loadAdAgentMode()
    const parentDn = getCreateAdminParentDn(target)

    if (!parentDn) {
      setMessage?.('Sélectionne une OU de destination avant de créer une OU.')
      return
    }

    const searchBaseDn = getCreateUserSearchBaseDn(parentDn) || parentDn

    setContextMenu(null)
    setAdminForm({
      name: '',
      description: '',
      sam_account_name: '',
      group_scope: 'Global',
      group_category: 'Security',
      parent_dn: parentDn
    })
    setAdminModal({
      action: 'create_ou',
      title: 'Créer une OU',
      parent_dn: parentDn,
      search_base_dn: searchBaseDn
    })

    setAdminOuOptions(getFallbackCreateUserOuOptions(searchBaseDn))
    window.setTimeout(() => loadAdminOuOptions(parentDn), 0)
  }

  function openCreateGroup(target = selectedNode) {
    loadAdAgentMode()
    const parentDn = getCreateAdminParentDn(target)

    if (!parentDn) {
      setMessage?.('Sélectionne une OU de destination avant de créer un groupe.')
      return
    }

    const searchBaseDn = getCreateUserSearchBaseDn(parentDn) || parentDn

    setContextMenu(null)
    setAdminForm({
      name: '',
      description: '',
      sam_account_name: '',
      group_scope: 'Global',
      group_category: 'Security',
      parent_dn: parentDn
    })
    setAdminModal({
      action: 'create_group',
      title: 'Créer un groupe',
      parent_dn: parentDn,
      search_base_dn: searchBaseDn
    })

    setAdminOuOptions(getFallbackCreateUserOuOptions(searchBaseDn))
    window.setTimeout(() => loadAdminOuOptions(parentDn), 0)
  }

  async function runAdAdminJob(payload) {
    const created = await apiFetch('/api/ad-admin/jobs', {
      method: 'POST',
      body: JSON.stringify({
        ...payload,
        created_by: 'react-admin'
      })
    })

    const job = await pollAdAdminJob(created.job.id)

    if (!job.success) {
      throw new Error(job.message || 'Action AD Admin en erreur.')
    }

    return job
  }

  async function pollAdAdminJob(jobId) {
    for (let attempt = 0; attempt < 75; attempt += 1) {
      const job = await apiFetch(`/api/ad-admin/jobs/${jobId}`)

      if (job.status === 'completed' || job.status === 'failed') {
        return job
      }

      await new Promise(resolve => setTimeout(resolve, 800))
    }

    throw new Error('Job créé mais l’agent principal n’a pas encore répondu.')
  }

  async function waitForAdAdminJobInBackground(jobId) {
    try {
      const finalJob = await pollAdAdminJob(jobId)

      if (!finalJob.success) {
        setMessage?.(finalJob.message || finalJob.output || 'Création AD en erreur.')
        return
      }

      setMessage?.(finalJob.message || 'Action AD terminée.')

      await loadTree()
      await loadNodeContent(selectedNode, viewType)
    } catch (err) {
      setMessage?.(`Job AD Admin créé, en attente de l’agent principal : ${jobId}`)
    }
  }

  function openAddMemberModal(group) {
    if (!group || !isGroupObject(group)) {
      setMessage?.('Sélectionne un groupe avant d’ajouter un membre.')
      return
    }

    resetMemberPicker()
    setMemberModal(group)
  }


  function resetMemberPicker() {
    setMemberIdentity('')
    setMemberSearchResults([])
    setMemberSearchLoading(false)
    setMemberSearchError('')
    setSelectedMemberCandidate(null)
    setMemberSubmitError('')
  }

  function closeMemberModal() {
    setMemberModal(null)
    resetMemberPicker()
  }

  function decorateMemberCandidate(candidate, kind) {
    return {
      ...candidate,
      _member_candidate_kind: kind,
      _member_candidate_label: kind === 'group' ? 'Groupe AD' : 'Utilisateur AD'
    }
  }

  function getMemberCandidateKindLabel(candidate) {
    return candidate?._member_candidate_label || (
      isGroupObject(candidate) ? 'Groupe AD' : 'Utilisateur AD'
    )
  }

  function getMemberCandidateIdentity(candidate) {
    return String(
      candidate?.sam_account_name ||
      candidate?.samAccountName ||
      candidate?.user_principal_name ||
      candidate?.upn ||
      candidate?.name ||
      candidate?.distinguished_name ||
      candidate?.dn ||
      ''
    )
  }

  function getMemberCandidateTitle(candidate) {
    return String(candidate?.display_name || candidate?.name || candidate?.sam_account_name || 'Utilisateur')
  }

  function getMemberCandidateSubtitle(candidate) {
    const parts = [
      candidate?.sam_account_name,
      candidate?.user_principal_name || candidate?.upn,
      candidate?.distinguished_name || candidate?.dn
    ].filter(Boolean)

    return parts.join(' • ')
  }

  function cleanAdAdminMessage(value) {
    return String(value || '')
      .replaceAll('dÃ©jÃ ', 'déjà')
      .replaceAll('Ã©', 'é')
      .replaceAll('Ã¨', 'è')
      .replaceAll('Ãª', 'ê')
      .replaceAll('Ã ', 'à')
      .replaceAll('Ã§', 'ç')
      .replaceAll('Ã´', 'ô')
      .replaceAll('Ã»', 'û')
  }

  function selectMemberCandidate(candidate) {
    const identity = getMemberCandidateIdentity(candidate)

    setSelectedMemberCandidate(candidate)
    setMemberIdentity(identity)
    setMemberSearchError('')
  }

  async function searchMemberCandidates() {
    const query = memberIdentity.trim()

    setSelectedMemberCandidate(null)
    setMemberSearchError('')
    setMemberSubmitError('')

    if (query.length < 2) {
      setMemberSearchResults([])
      setMemberSearchError('Tape au moins 2 caractères pour rechercher un utilisateur ou un groupe.')
      return
    }

    setMemberSearchLoading(true)

    try {
      const [users, groups] = await Promise.all([
        runJob('search_users', {
          query,
          baseDn: 'OU=Users,OU=EITAS,DC=API,DC=LOCAL',
          limit: 50,
          recursive: true
        }),
        runJob('list_groups', {
          baseDn: 'OU=Groups,OU=EITAS,DC=API,DC=LOCAL',
          limit: 500,
          recursive: true
        })
      ])

      const normalizedQuery = query.toLowerCase()

      const matchingGroups = groups.filter(group =>
        [
          group?.name,
          group?.sam_account_name,
          group?.samAccountName,
          group?.description,
          group?.distinguished_name,
          group?.dn
        ]
          .filter(Boolean)
          .some(value => String(value).toLowerCase().includes(normalizedQuery))
      )

      const decoratedUsers = users.map(user => decorateMemberCandidate(user, 'user'))
      const decoratedGroups = matchingGroups.map(group => decorateMemberCandidate(group, 'group'))

      const results = [...decoratedUsers, ...decoratedGroups]

      setMemberSearchResults(results)

      if (!results.length) {
        setMemberSearchError('Aucun utilisateur ou groupe trouvé.')
      }
    } catch (error) {
      setMemberSearchResults([])
      setMemberSearchError(error.message || 'Recherche utilisateur/groupe impossible.')
    } finally {
      setMemberSearchLoading(false)
    }
  }


  async function submitAddMember(event) {
    event.preventDefault()

    if (!memberModal) return

    const identity = selectedMemberCandidate ? getMemberCandidateIdentity(selectedMemberCandidate).trim() : memberIdentity.trim()

    if (memberSearchResults.length > 0 && !selectedMemberCandidate) {
      setMemberSearchError('Sélectionne un utilisateur ou un groupe exact dans la liste avant d’ajouter.')
      setMessage?.('Sélectionne un utilisateur ou un groupe exact dans la liste avant d’ajouter.')
      return
    }

    if (!identity) {
      setMessage?.('Identifiant utilisateur ou groupe obligatoire.')
      return
    }

    setMemberActionLoading(true)

    try {
      const job = await runAdAdminJob({
        action: 'add_group_member',
        group_identity: memberModal.sam_account_name || memberModal.name || getObjectDn(memberModal),
        member_identity: identity
      })

      const output = job?.output || {}
      const groupName = output.group || memberModal.sam_account_name || memberModal.name || getObjectDn(memberModal)
      const memberName = output.member || (selectedMemberCandidate ? getMemberCandidateTitle(selectedMemberCandidate) : identity)
      const rawMessage = cleanAdAdminMessage(output.message || job?.message || '')

      await loadGroupMembers(memberModal, { silent: true })

      if (output.already_member || rawMessage.toLowerCase().includes('déjà')) {
        setMemberSubmitError(`${memberName} est déjà membre de ${groupName}.`)
        setMessage?.(`${memberName} est déjà membre de ${groupName}.`)
        return
      }

      setMessage?.(`${memberName} ajouté à ${groupName}.`)
      closeMemberModal()
    } catch (err) {
      setMessage?.(err.message || 'Impossible d’ajouter le membre.')
    } finally {
      setMemberActionLoading(false)
    }
  }

  async function removeGroupMember(group, member) {
    if (!group || !member) return

    const memberLabel = member.sam_account_name || member.name || getObjectDn(member)
    const groupLabel = group.sam_account_name || group.name || getObjectDn(group)

    if (!window.confirm(`Retirer ${memberLabel} du groupe ${groupLabel} ?`)) {
      return
    }

    setMemberActionLoading(true)

    try {
      await runAdAdminJob({
        action: 'remove_group_member',
        group_identity: groupLabel,
        member_identity: memberLabel
      })

      setMessage?.(`Membre ${memberLabel} retiré de ${groupLabel}.`)
      await loadGroupMembers(group)
    } catch (err) {
      setMessage?.(err.message || 'Impossible de retirer le membre.')
    } finally {
      setMemberActionLoading(false)
    }
  }

  async function submitMoveObject(event) {
    event.preventDefault()

    if (!moveModal) {
      return
    }

    const objectDn = getObjectDn(moveModal)
    const targetParentDn = moveTargetDn.trim()

    if (!objectDn) {
      setStatus('Objet AD invalide.')
      return
    }

    if (!targetParentDn) {
      setStatus('DN de destination obligatoire.')
      return
    }

    setAdminLoading(true)
    setStatus('')

    try {
      const job = await runAdAdminJob({
        action: 'move_object',
        object_identity: objectDn,
        target_parent_dn: targetParentDn,
        created_by: 'react-admin'
      })

      const output = job?.output || {}
      setMessage?.(cleanAdHistoryText(output.message || job?.message || 'Objet AD déplacé.'))

      setMoveModal(null)
      setMoveTargetDn('')

      await loadTree()

      if (selectedNode) {
        await loadNodeContent(selectedNode, viewType)
      }

      await loadAdAdminHistory()
    } catch (err) {
      setStatus(err.message || 'Impossible de déplacer cet objet AD.')
    } finally {
      setAdminLoading(false)
    }
  }

  async function submitAdAdminJob(event) {
    event.preventDefault()

    if (!adminModal) return

    const name = adminForm.name.trim()
    const description = adminForm.description.trim()
    const sam = adminForm.sam_account_name.trim() || name
    const parentDn = String(adminForm.parent_dn || adminModal.parent_dn || '').trim()

    if (!name) {
      setMessage?.('Nom obligatoire.')
      return
    }

    if (!parentDn) {
      setMessage?.('Emplacement de création obligatoire.')
      return
    }

    const actionLabel = adminModal.action === 'create_ou'
      ? 'La création de l’OU'
      : 'La création du groupe'

    if (!(await confirmProductionAdAction(actionLabel, `${name} dans ${parentDn}`))) {
      return
    }

    setAdminLoading(true)

    try {
      const payload = {
        action: adminModal.action,
        parent_dn: parentDn,
        name,
        description,
        created_by: 'react-admin'
      }

      if (adminModal.action === 'create_group') {
        payload.sam_account_name = sam
        payload.group_scope = adminForm.group_scope
        payload.group_category = adminForm.group_category
      }

      const created = await apiFetch('/api/ad-admin/jobs', {
        method: 'POST',
        body: JSON.stringify(payload)
      })

      setMessage?.(`Job AD Admin créé : ${created.job.id}. Attente de l’agent principal.`)
      setAdminModal(null)
      setAdminLoading(false)

      waitForAdAdminJobInBackground(created.job.id)
    } catch (err) {
      setMessage?.(err.message || 'Erreur création AD.')
      setAdminLoading(false)
    }
  }

  function getTestCleanupIdentity(item) {
    return String(
      item?.sam_account_name
      || item?.samAccountName
      || item?.name
      || item?.display_name
      || item?.displayName
      || ''
    ).trim()
  }

  function getTestCleanupReason(item) {
    const identity = getTestCleanupIdentity(item)
    const dn = getObjectDn(item)
    const combined = `${identity} ${dn}`.toLowerCase()

    if (/^gg_tmp_/i.test(identity)) return 'Groupe temporaire GG_TMP_*'
    if (/^tmp_/i.test(identity)) return 'Objet temporaire TMP_*'
    if (/^test_/i.test(identity)) return 'Objet test TEST_*'
    if (/^test[._-]/i.test(identity)) return 'Identifiant test.*'
    if (/(^|,)(cn|ou)=tmp_/i.test(dn)) return 'DN temporaire TMP_*'
    if (/(^|,)(cn|ou)=test_/i.test(dn)) return 'DN test TEST_*'
    if (combined.includes('tmp_react_dest')) return 'Objet créé pendant les tests React'

    return 'Objet détecté comme test'
  }

  function isPotentialTestCleanupObject(item) {
    const identity = getTestCleanupIdentity(item)
    const dn = getObjectDn(item)
    const combined = `${identity} ${dn}`

    return (
      /^gg_tmp_/i.test(identity)
      || /^tmp_/i.test(identity)
      || /^test_/i.test(identity)
      || /^test[._-]/i.test(identity)
      || /(^|,)(cn|ou)=tmp_/i.test(dn)
      || /(^|,)(cn|ou)=test_/i.test(dn)
      || /tmp_react_dest/i.test(combined)
    )
  }

  async function runTestCleanupExplorerJob(action, payload = {}) {
    const created = await apiFetch('/api/ad-explorer/jobs', {
      method: 'POST',
      body: JSON.stringify({
        action,
        ...payload,
        created_by: 'react-test-cleanup-scanner'
      })
    })

    const jobId = created?.job?.id

    if (!jobId) {
      throw new Error(`Job ${action} introuvable`)
    }

    const completedJob = await waitForAdExplorerJob(jobId)
    return getCreateUserOuItemsFromJob(completedJob)
  }

  async function scanTestCleanupObjects() {
    const selectedDn = getObjectDn(selectedNode)
    const baseDn = getCreateUserSearchBaseDn(selectedDn || DOMAIN_DN) || selectedDn || DOMAIN_DN

    setTestCleanupLoading(true)
    setTestCleanupError('')
    setTestCleanupResults({})

    try {
      const jobs = await Promise.allSettled([
        runTestCleanupExplorerJob('list_ou_tree', {
          base_dn: baseDn,
          baseDn,
          limit: 2000
        }),
        runTestCleanupExplorerJob('list_groups', {
          base_dn: baseDn,
          baseDn,
          recursive: true,
          limit: 2000
        }),
        runTestCleanupExplorerJob('search_users', {
          query: 'test',
          base_dn: baseDn,
          baseDn,
          recursive: true,
          limit: 1000
        }),
        runTestCleanupExplorerJob('search_users', {
          query: 'tmp',
          base_dn: baseDn,
          baseDn,
          recursive: true,
          limit: 1000
        })
      ])

      const rawItems = []

      for (const job of jobs) {
        if (job.status === 'fulfilled' && Array.isArray(job.value)) {
          rawItems.push(...job.value)
        }
      }

      const seen = new Set()
      const filtered = rawItems
        .filter(isPotentialTestCleanupObject)
        .filter(item => {
          const key = (getObjectDn(item) || getTestCleanupIdentity(item)).toUpperCase()

          if (!key) return false
          if (seen.has(key)) return false

          seen.add(key)
          return true
        })
        .map(item => ({
          ...item,
          cleanup_reason: getTestCleanupReason(item)
        }))
        .sort((a, b) => {
          const typeA = String(a?.type || a?.objectClass || '').localeCompare(String(b?.type || b?.objectClass || ''), 'fr')
          if (typeA !== 0) return typeA

          return getTestCleanupIdentity(a).localeCompare(getTestCleanupIdentity(b), 'fr', { sensitivity: 'base' })
        })

      setTestCleanupItems(filtered)
      setStatus(`${filtered.length} objet(s) de test détecté(s).`)
    } catch (error) {
      setTestCleanupItems([])
      setTestCleanupError(error?.message || 'Scan des objets de test impossible.')
    } finally {
      setTestCleanupLoading(false)
    }
  }

  function isTestCleanupOu(item) {
    const dn = getObjectDn(item)
    const type = String(item?.type || item?.objectClass || '').toLowerCase()

    return type === 'ou'
      || type.includes('organizational')
      || /^OU=/i.test(String(dn || '').trim())
  }

  function normalizeOuEmptyCheckOutput(job) {
    const raw = job?.output || job?.result || job?.data || {}

    if (typeof raw === 'string') {
      try {
        return JSON.parse(raw)
      } catch {
        return { message: raw }
      }
    }

    return raw
  }

  async function checkTestCleanupOuEmpty(item) {
    const dn = getObjectDn(item)

    if (!dn) {
      throw new Error('DN introuvable pour cette OU.')
    }

    const created = await apiFetch('/api/ad-explorer/jobs', {
      method: 'POST',
      body: JSON.stringify({
        action: 'check_ou_empty',
        ou_dn: dn,
        base_dn: dn,
        created_by: 'react-test-cleanup-ou-check'
      })
    })

    const jobId = created?.job?.id

    if (!jobId) {
      throw new Error('Job check_ou_empty introuvable.')
    }

    const job = await waitForAdExplorerJob(jobId)
    const output = normalizeOuEmptyCheckOutput(job)

    if (!job.success) {
      throw new Error(output?.error || job.message || 'Verification de l OU impossible.')
    }

    return {
      isEmpty: Boolean(output?.is_empty ?? output?.isEmpty),
      childCount: Number(output?.child_count ?? output?.childCount ?? 0),
      children: Array.isArray(output?.children) ? output.children : [],
      message: output?.message || job.message || ''
    }
  }

  async function deleteTestCleanupObject(item) {
    const dn = getObjectDn(item)
    const identity = getTestCleanupIdentity(item) || item?.name || 'Objet AD'

    if (!dn) {
      setTestCleanupError('DN introuvable pour cet objet.')
      return
    }

    setTestCleanupDeletingDn(dn)
    setTestCleanupError('')
    setTestCleanupResults(current => ({
      ...current,
      [dn]: {
        type: 'pending',
        message: 'Action en cours...'
      }
    }))

    try {
      const modeData = await apiFetch('/api/agent/mode')
      const currentMode = modeData?.mode || adAgentMode || 'Inconnu'
      const isProduction = String(currentMode).toLowerCase() === 'production'
      const isOu = isTestCleanupOu(item)

      setAdAgentMode(currentMode)

      if (isOu) {
        setTestCleanupResults(current => ({
          ...current,
          [dn]: {
            type: 'pending',
            message: 'Verification que l OU est vide...'
          }
        }))

        const check = await checkTestCleanupOuEmpty(item)

        if (!check.isEmpty) {
          const message = `OU non vide : ${check.childCount} objet(s) enfant(s). Suppression bloquee.`

          setTestCleanupResults(current => ({
            ...current,
            [dn]: {
              type: 'error',
              message
            }
          }))

          setTestCleanupError(message)
          return
        }

        setTestCleanupResults(current => ({
          ...current,
          [dn]: {
            type: 'pending',
            message: 'OU vide verifiee. Suppression possible.'
          }
        }))
      }

      if (isProduction) {
        const warning = isOu
          ? `ATTENTION : mode Production AD.\n\nOU vide verifiee.\n\nSuppression reelle de l OU :\n${identity}\n\n${dn}\n\nContinuer ?`
          : `ATTENTION : mode Production AD.\n\nSuppression reelle de l objet :\n${identity}\n\n${dn}\n\nContinuer ?`

        const ok = window.confirm(warning)

        if (!ok) {
          setTestCleanupResults(current => ({
            ...current,
            [dn]: {
              type: 'muted',
              message: 'Action annulee.'
            }
          }))
          return
        }
      }

      const job = await runAdAdminJob({
        action: 'delete_object',
        object_identity: dn,
        confirm_dn: dn
      })

      const message = isProduction
        ? 'Suppression Production OK.'
        : isOu
          ? 'OU vide verifiee. Simulation OK — aucun objet AD reel n a ete supprime.'
          : 'Simulation OK — aucun objet AD reel n a ete supprime.'

      setStatus(job?.message || message)

      setTestCleanupResults(current => ({
        ...current,
        [dn]: {
          type: 'success',
          message
        }
      }))

      if (isProduction) {
        setTestCleanupItems(current => current.filter(entry => getObjectDn(entry) !== dn))
      }
    } catch (error) {
      const message = error?.message || `Suppression impossible : ${identity}`

      setTestCleanupResults(current => ({
        ...current,
        [dn]: {
          type: 'error',
          message
        }
      }))

      setTestCleanupError(message)
    } finally {
      setTestCleanupDeletingDn('')
    }
  }

  function openTestCleanupScanner() {
    loadAdAgentMode()
    setTestCleanupModal(true)
    setTestCleanupItems([])
    setTestCleanupError('')
    scanTestCleanupObjects()
  }

  useEffect(() => {
    refreshAll()
    loadAdAdminHistory()
  }, [])

  return (
    <div className="aduc-shell" onClick={closeContextMenu}>
      <div className="aduc-window">
        <header className="aduc-titlebar">
          <div>
            <strong>EITAS</strong>
            <span>Console Active Directory</span>
          </div>

          <div>
            <button type="button" onClick={refreshAll}>⟳ Actualiser</button>
            <button type="button" onClick={() => actionSoon('Plus d’actions')}>⋮ Plus d’actions</button>
            <span>Administrator ▾</span>
          </div>
        </header>

        <div className="aduc-layout">
          <aside className="aduc-sidebar">
            <div className="aduc-brand">
              <div>E</div>
              <strong>EITAS</strong>
            </div>

            <nav>
              <button type="button" onClick={() => setMessage?.('Console Active Directory ouverte.')}>
                Tableau de bord
              </button>

              <button
                type="button"
                className={selectedNode?.distinguished_name === USERS_DN ? 'active' : ''}
                onClick={() => loadNodeContent({
                  name: 'Users',
                  distinguished_name: USERS_DN,
                  canonical_name: 'API.LOCAL/EITAS/Users'
                }, 'users')}
              >
                Utilisateurs
              </button>

              <button
                type="button"
                className={selectedNode?.distinguished_name === GROUPS_DN ? 'active' : ''}
                onClick={() => loadNodeContent({
                  name: 'Groups',
                  distinguished_name: GROUPS_DN,
                  canonical_name: 'API.LOCAL/EITAS/Groups'
                }, 'groups')}
              >
                Groupes
              </button>

              <button type="button" onClick={() => setMessage?.('Ordinateurs AD : prochaine étape.')}>
                Ordinateurs
              </button>

              <button
                type="button"
                className={viewType === 'ou' ? 'active' : ''}
                onClick={() => loadNodeContent({
                  name: 'API.LOCAL',
                  distinguished_name: DOMAIN_DN,
                  canonical_name: 'API.LOCAL'
                }, 'ou')}
              >
                Unités d’organisation
              </button>

              <button type="button" onClick={() => setMessage?.('GPO : future extension.')}>
                GPO
              </button>

              <button type="button" onClick={() => setMessage?.('Rapports AD : future extension.')}>
                Rapports
              </button>

              <button type="button" onClick={() => setMessage?.('Paramètres AD : future extension.')}>
                Paramètres
              </button>
            </nav>

            <small>« Réduire le menu</small>
          </aside>

          <main className="aduc-main">
            <section className="aduc-toolbar">
              <button type="button" onClick={() => openNewObjectMenu(contextMenu?.target || selectedNode)}>＋ Nouveau</button>
              <button type="button" onClick={() => openCreateOu(selectedNode)}>📁 Créer une OU</button>
              <button type="button" onClick={() => openCreateGroup(selectedNode)}>👥 Créer un groupe</button>
              <button type="button" onClick={() => {
              setContextMenu(null)
              openUpdateObject(contextMenu?.target || selectedObject || selectedNode)
            }}>✎ Modifier</button>
              <button type="button" className="danger" onClick={() => {
              setContextMenu(null)
              openDeleteObject(contextMenu?.target || selectedObject || selectedNode)
            }}>🗑 Supprimer</button>
              <button type="button" onClick={openTestCleanupScanner}>🧹 Nettoyage tests</button>
              <button type="button" onClick={refreshAll}>⟳ Actualiser</button>
            </section>

            <section className="aduc-console">
              <div className="aduc-tree-pane">
                <div className="aduc-pane-head">
                  <h3>Arborescence Active Directory</h3>
                  <input
                    value={treeFilter}
                    onChange={event => setTreeFilter(event.target.value)}
                    placeholder="Filtrer l’arborescence..."
                  />
                </div>

          <form className="aduc-global-search-panel" onSubmit={runGlobalAdSearch}>
            <div>
              <strong>Recherche globale AD</strong>
              <span>Cherche dans les groupes et utilisateurs de OU=EITAS.</span>
            </div>

            <input
              value={globalAdSearch}
              onChange={event => setGlobalAdSearch(event.target.value)}
              placeholder="Ex : GG_MOVE_TEST, Liam, VPN..."
            />

            <button type="submit" disabled={globalAdSearchLoading || !globalAdSearch.trim()}>
              {globalAdSearchLoading ? 'Recherche...' : 'Rechercher dans AD'}
            </button>
          </form>


                <div className="aduc-tree">
                  <button
                    type="button"
                    className="aduc-root"
                    onContextMenu={event => openContextMenu(event, { name: 'API.LOCAL', distinguished_name: DOMAIN_DN }, 'tree')}
                    onClick={() => loadNodeContent({ name: 'API.LOCAL', distinguished_name: DOMAIN_DN, canonical_name: 'API.LOCAL' }, 'ou')}
                  >
                    ▾ 🌐 API.LOCAL
                  </button>

                  <button type="button" className="aduc-node system">› 📁 BuiltIn</button>
                  <button type="button" className="aduc-node system">› 📁 Computers</button>
                  <button type="button" className="aduc-node system">› 📁 Domain Controllers</button>

                  {filteredTree.map((item, index) => {
                    const kind = getNodeKind(item)
                    const selected = selectedNode?.distinguished_name === item.distinguished_name

                    return (
                      <button
                        type="button"
                        key={item.distinguished_name || index}
                        className={`aduc-node ${selected ? 'selected' : ''}`}
                        style={{ paddingLeft: `${18 + Math.min(item.depth, 5) * 22}px` }}
                        onClick={() => loadNodeContent(item, kind)}
                        onContextMenu={event => openContextMenu(event, item, 'tree')}
                      >
                        <span>{objectIcon(item)}</span>
                        <strong>{item.name}</strong>
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="aduc-list-pane">
                <div className="aduc-list-head">
                  <div>
                    <h3>{selectedNode?.name || 'Objet AD'} <span>({filteredViewItems.length} objet{filteredViewItems.length > 1 ? 's' : ''})</span></h3>
                    <small>{selectedNode?.canonical_name || selectedNode?.distinguished_name || '-'}</small>
                  </div>

                  <div>
                    <input
                      value={viewFilter}
                      onChange={event => setViewFilter(event.target.value)}
                      placeholder="Rechercher dans cette vue..."
                    />
                    <button type="button">⌕</button>
                    <button type="button">≡</button>
                  </div>
                </div>

                <div className="aduc-table">
                  <div className="aduc-table-row header">
                    <span>Nom</span>
                    <span>Type</span>
                    <span>Description</span>
                  </div>

                  {loading ? (
                    <div className="aduc-empty">Chargement depuis SRV-DC01...</div>
                  ) : filteredViewItems.length === 0 ? (
                    <div className="aduc-empty">Aucun objet dans cette vue.</div>
                  ) : (
                    filteredViewItems.map((item, index) => (
                      <div
                        key={item.distinguished_name || item.sam_account_name || index}
                        className={`aduc-table-row ${getObjectDn(selectedObject) && getObjectDn(selectedObject) === getObjectDn(item) ? 'selected-object' : ''}`}
                        onClick={() => selectObject(item)}
                        onDoubleClick={() => {
                          if (getObjectType(item).includes('Groupe')) {
                            loadNodeContent(item, 'groups')
                          }
                        }}
                        onContextMenu={event => openContextMenu(event, item, 'object')}
                      >
                        <span>
                          <i>{getObjectType(item).includes('Groupe') ? '👥' : getObjectType(item).includes('Utilisateur') ? '👤' : '📁'}</i>
                          {getObjectName(item)}
                        </span>
                        <span>{getObjectType(item)}</span>
                        <span>{getGroupDescription(item)}</span>
                      </div>
                    ))
                  )}
                </div>

                <footer className="aduc-list-footer">
                  <span>{filteredViewItems.length} objet(s)</span>
                  <span>Affichage 1 - {filteredViewItems.length} sur {filteredViewItems.length}</span>
                </footer>
              </div>

              <ObjectDetailsPanel
                object={selectedObject}
                selectedNode={selectedNode}
                memberItems={objectMembers}
                membersLoading={membersLoading}
                membersError={membersError}
                historyItems={adAdminHistory}
                historyLoading={adAdminHistoryLoading}
                historyError={adAdminHistoryError}
                historyFilter={adAdminHistoryFilter}
                onHistoryFilterChange={setAdAdminHistoryFilter}
                onOpenHistoryJob={setSelectedAdAdminHistoryJob}
                onLoadHistory={() => loadAdAdminHistory()}
                onCopyDn={target => copyText(getObjectDn(target)).then(() => setMessage?.('DN copié.'))}
                onExplore={target => loadNodeContent(target, getNodeKind(target))}
                onCreateOu={target => openCreateOu(target)}
                onCreateGroup={target => openCreateGroup(target)}
                onOpenMoveObject={target => openMoveObject(target)}
                onLoadMembers={target => loadGroupMembers(target)}
                onOpenAddMember={target => openAddMemberModal(target)}
                onRemoveMember={(group, member) => removeGroupMember(group, member)}
              />
            </section>
          </main>
        </div>

        <footer className="aduc-status">
          <span className={status.includes('Erreur') ? 'bad' : 'ok'} />
          <strong>{status}</strong>
          <em>API.LOCAL</em>
        </footer>
      </div>



      {selectedAdAdminHistoryJob && (
        <div className="aduc-modal-backdrop" onClick={() => setSelectedAdAdminHistoryJob(null)}>
          <div className="aduc-modal aduc-history-detail-modal" onClick={event => event.stopPropagation()}>
            <header>
              <div>
                <span>Historique AD Admin</span>
                <h3>{formatAdHistoryAction(selectedAdAdminHistoryJob.action)}</h3>
              </div>

              <button type="button" onClick={() => setSelectedAdAdminHistoryJob(null)}>×</button>
            </header>

            <div className="aduc-history-detail-grid">
              <div>
                <span>Statut</span>
                <strong>{formatAdHistoryStatus(selectedAdAdminHistoryJob)}</strong>
              </div>

              <div>
                <span>Agent</span>
                <strong>{selectedAdAdminHistoryJob.agent_name || selectedAdAdminHistoryJob.claimed_by || 'Agent non assigné'}</strong>
              </div>

              <div>
                <span>Créée le</span>
                <strong>{formatAdHistoryDate(selectedAdAdminHistoryJob.created_at)}</strong>
              </div>

              <div>
                <span>Terminée le</span>
                <strong>{formatAdHistoryDate(selectedAdAdminHistoryJob.completed_at)}</strong>
              </div>
            </div>

            <div className="aduc-history-detail-message">
              <div className="aduc-history-detail-message-head">
                <span>Résultat</span>
                <button
                  type="button"
                  onClick={() => copyText(formatAdHistorySummary(selectedAdAdminHistoryJob)).then(() => setMessage?.('Résumé copié.'))}
                >
                  Copier résumé
                </button>
              </div>

              <strong>{formatAdHistoryMessage(selectedAdAdminHistoryJob)}</strong>
            </div>

            <div className="aduc-history-detail-json">
              <div className="aduc-history-detail-json-title">
                <h4>Payload envoyé</h4>
                <button
                  type="button"
                  onClick={() => copyText(formatAdHistoryJson(selectedAdAdminHistoryJob.payload || {})).then(() => setMessage?.('Payload copié.'))}
                >
                  Copier
                </button>
              </div>
              <pre>{formatAdHistoryJson(selectedAdAdminHistoryJob.payload || {})}</pre>
            </div>

            <div className="aduc-history-detail-json">
              <div className="aduc-history-detail-json-title">
                <h4>Output agent Windows</h4>
                <button
                  type="button"
                  onClick={() => copyText(formatAdHistoryJson(selectedAdAdminHistoryJob.output || {})).then(() => setMessage?.('Output agent copié.'))}
                >
                  Copier
                </button>
              </div>
              <pre>{formatAdHistoryJson(selectedAdAdminHistoryJob.output || {})}</pre>
            </div>
          </div>
        </div>
      )}

      {newObjectModal && (
        <div
          className="aduc-modal-backdrop"
          onClick={event => {
            if (event.target === event.currentTarget) {
              setNewObjectModal(null)
            }
          }}
        >
          <div
            className="aduc-new-object-modal"
            onClick={event => event.stopPropagation()}
            onKeyDown={event => event.stopPropagation()}
          >
            <div className="aduc-modal-header">
              <div>
                <h3>Nouvel objet AD</h3>
                <p>{getObjectDn(newObjectModal)}</p>
              </div>
              <button type="button" onClick={() => setNewObjectModal(null)}>×</button>
            </div>

            <div className="aduc-new-object-grid">
              <button
                type="button"
                onClick={() => {
                  const target = newObjectModal
                  setNewObjectModal(null)
                  openCreateOu(target)
                }}
              >
                <strong>📁 Créer une OU</strong>
                <span>Ajouter une unité d’organisation sous cette OU.</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  const target = newObjectModal
                  setNewObjectModal(null)
                  openCreateGroup(target)
                }}
              >
                <strong>👥 Créer un groupe</strong>
                <span>Créer un groupe de sécurité dans cette OU.</span>
              </button>

              <button
                type="button"
                className="aduc-new-object-card"
                onClick={() => {
                  const target = newObjectModal
                  setNewObjectModal(null)
                  openCreateUser(target)
                }}
              >
                <strong>👤 Créer un utilisateur</strong>
                <span>Créer un compte utilisateur dans cette OU.</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {searchOuModal && (
        <div
          className="aduc-modal-backdrop"
          onClick={event => {
            if (event.target === event.currentTarget) {
              setSearchOuModal(null)
            }
          }}
        >
          <form
            className="aduc-search-ou-modal"
            onSubmit={submitSearchOuModal}
            onClick={event => event.stopPropagation()}
            onKeyDown={event => event.stopPropagation()}
          >
            <div className="aduc-modal-header">
              <div>
                <h3>Rechercher dans cette OU</h3>
                <p>{getObjectDn(searchOuModal)}</p>
              </div>
              <button type="button" onClick={() => setSearchOuModal(null)}>×</button>
            </div>

            <label>
              Recherche
              <input
                value={searchOuQuery}
                onChange={event => setSearchOuQuery(event.target.value)}
                placeholder="Nom, groupe, utilisateur, description, DN..."
                autoFocus
              />
            </label>

            <div className="aduc-modal-actions">
              <button type="button" onClick={() => setSearchOuModal(null)}>
                Annuler
              </button>
              <button type="submit" disabled={!searchOuQuery.trim()}>
                Rechercher
              </button>
            </div>
          </form>
        </div>
      )}

      {propertiesModal && (
        <div
          className="aduc-modal-backdrop"
          onClick={event => {
            if (event.target === event.currentTarget) {
              setPropertiesModal(null)
            }
          }}
        >
          <div
            className="aduc-properties-modal"
            onClick={event => event.stopPropagation()}
            onKeyDown={event => event.stopPropagation()}
          >
            <div className="aduc-modal-header">
              <div>
                <h3>Propriétés AD</h3>
                <p>{getObjectDn(propertiesModal)}</p>
              </div>
              <button type="button" onClick={() => setPropertiesModal(null)}>×</button>
            </div>

            <div className="aduc-properties-summary">
              <div className="aduc-properties-icon">ⓘ</div>
              <div>
                <strong>{propertiesModal.name || propertiesModal.sam_account_name || 'Objet AD'}</strong>
                <span>{getObjectType(propertiesModal)}</span>
              </div>
            </div>

            <div className="aduc-properties-actions">
              <button type="button" onClick={() => copyText(getObjectDn(propertiesModal)).then(() => setMessage?.('DN copié.'))}>
                Copier DN
              </button>
              <button type="button" onClick={() => copyText(JSON.stringify(propertiesModal, null, 2)).then(() => setMessage?.('JSON copié.'))}>
                Copier JSON
              </button>
            </div>

            <div className="aduc-properties-grid">
              {getPropertiesRows(propertiesModal).map(([label, value]) => (
                <div className="aduc-properties-row" key={label}>
                  <span>{label}</span>
                  <strong>{String(value)}</strong>
                </div>
              ))}
            </div>

            <details className="aduc-properties-raw">
              <summary>JSON brut</summary>
              <pre>{JSON.stringify(propertiesModal, null, 2)}</pre>
            </details>
          </div>
        </div>
      )}

      {updateModal && (
        <div
          className="aduc-modal-backdrop"
          onClick={event => {
            if (event.target === event.currentTarget) {
              setUpdateModal(null)
            }
          }}
        >
          <form
            className="aduc-update-object-modal"
            onSubmit={submitUpdateObject}
            onClick={event => event.stopPropagation()}
            onKeyDown={event => event.stopPropagation()}
          >
            <div className="aduc-modal-header">
              <div>
                <h3>Modifier objet AD</h3>
                <p>{getObjectDn(updateModal)}</p>
              </div>
              <button type="button" onClick={() => setUpdateModal(null)}>×</button>
            </div>

            <div className="aduc-update-grid">
              <label className="aduc-update-full">
                Description
                <textarea
                  value={updateForm.description || ''}
                  onChange={event => updateObjectFormField('description', event.target.value)}
                  placeholder="Description de l’objet AD"
                  rows={4}
                  autoFocus
                />
              </label>

              <label>
                Nom affiché
                <input
                  value={updateForm.displayName || ''}
                  onChange={event => updateObjectFormField('displayName', event.target.value)}
                  placeholder="displayName"
                />
              </label>

              <label>
                Mail
                <input
                  value={updateForm.mail || ''}
                  onChange={event => updateObjectFormField('mail', event.target.value)}
                  placeholder="utilisateur@domaine.local"
                />
              </label>

              <label>
                Poste
                <input
                  value={updateForm.title || ''}
                  onChange={event => updateObjectFormField('title', event.target.value)}
                  placeholder="Technicien support"
                />
              </label>

              <label>
                Département
                <input
                  value={updateForm.department || ''}
                  onChange={event => updateObjectFormField('department', event.target.value)}
                  placeholder="Support"
                />
              </label>

              <label>
                Société
                <input
                  value={updateForm.company || ''}
                  onChange={event => updateObjectFormField('company', event.target.value)}
                  placeholder="Entreprise"
                />
              </label>

              <label>
                Téléphone
                <input
                  value={updateForm.telephoneNumber || ''}
                  onChange={event => updateObjectFormField('telephoneNumber', event.target.value)}
                  placeholder="+33..."
                />
              </label>

              <label>
                Bureau
                <input
                  value={updateForm.physicalDeliveryOfficeName || ''}
                  onChange={event => updateObjectFormField('physicalDeliveryOfficeName', event.target.value)}
                  placeholder="Pau / Bureau 1"
                />
              </label>
            </div>

            <div className="aduc-modal-actions">
              <button type="button" onClick={() => setUpdateModal(null)}>
                Annuler
              </button>
              <button type="submit">
                Enregistrer
              </button>
            </div>
          </form>
        </div>
      )}

      {deleteModal && (
        <div className="aduc-modal-backdrop" onClick={() => setDeleteModal(null)}>
          <form className="aduc-delete-object-modal" onSubmit={submitDeleteObject} onClick={event => event.stopPropagation()}>
            <div className="aduc-modal-header">
              <div>
                <h3>Supprimer objet AD</h3>
                <p>{getObjectDn(deleteModal)}</p>
              </div>
              <button type="button" onClick={() => setDeleteModal(null)}>×</button>
            </div>

            <div className="aduc-delete-danger">
              Suppression réelle dans Active Directory. Le DN est pré-rempli automatiquement, vérifie simplement qu’il correspond bien à l’objet ciblé.
            </div>

            <label>
              DN confirmé
              <input
                value={deleteConfirmDn}
                onChange={event => setDeleteConfirmDn(event.target.value)}
                placeholder="DN complet de l’objet AD"
                autoFocus
              />
            </label>

            {deleteConfirmDn.trim() && deleteConfirmDn.trim() !== getObjectDn(deleteModal) && (
              <div className="aduc-delete-warning">
                Le DN saisi ne correspond pas. La suppression sera bloquée.
              </div>
            )}

            <div className="aduc-modal-actions">
              <button type="button" onClick={() => setDeleteModal(null)}>
                Annuler
              </button>
              <button
                type="submit"
                className="danger"
                disabled={deleteConfirmDn.trim() !== getObjectDn(deleteModal)}
              >
                Supprimer définitivement
              </button>
            </div>
          </form>
        </div>
      )}

      {renameModal && (
        <div className="aduc-modal-backdrop" onClick={() => setRenameModal(null)}>
          <form className="aduc-rename-object-modal" onSubmit={submitRenameObject} onClick={event => event.stopPropagation()}>
            <div className="aduc-modal-header">
              <div>
                <h3>Renommer objet AD</h3>
                <p>{getObjectDn(renameModal)}</p>
              </div>
              <button type="button" onClick={() => setRenameModal(null)}>×</button>
            </div>

            <label>
              Nouveau nom
              <input
                value={renameNewName}
                onChange={event => setRenameNewName(event.target.value)}
                placeholder="Exemple : GG_MOVE_TEST_RENAMED"
                autoFocus
              />
            </label>

            {renameNewName.trim() === getRenameDefaultName(renameModal) && (
              <div className="aduc-rename-warning">
                Le nouveau nom est identique au nom actuel.
              </div>
            )}

            <div className="aduc-modal-actions">
              <button type="button" onClick={() => setRenameModal(null)}>
                Annuler
              </button>
              <button
                type="submit"
                disabled={!renameNewName.trim() || renameNewName.trim() === getRenameDefaultName(renameModal)}
              >
                Renommer
              </button>
            </div>
          </form>
        </div>
      )}

      {moveModal && (
        <div className="aduc-modal-backdrop" onClick={() => setMoveModal(null)}>
          <form className="aduc-modal aduc-move-object-modal" onSubmit={submitMoveObject} onClick={event => event.stopPropagation()}>
            <header>
              <div>
                <span>Explorateur Active Directory</span>
                <h3>Déplacer un objet AD</h3>
              </div>

              <button type="button" onClick={() => setMoveModal(null)}>×</button>
            </header>

            <label>
              Objet à déplacer
              <input value={getObjectName(moveModal)} readOnly />
            </label>

            <label>
              DN actuel
              <textarea value={getObjectDn(moveModal)} readOnly rows={3} />
            </label>

            <label>
              DN de la destination
              <input
                value={moveTargetDn}
                onChange={event => setMoveTargetDn(event.target.value)}
                placeholder="OU=Groups,OU=EITAS,DC=API,DC=LOCAL"
                autoFocus
              />
            </label>

            <div className="aduc-move-quick-targets">
              <button type="button" onClick={() => setMoveTargetDn('OU=Groups,OU=EITAS,DC=API,DC=LOCAL')}>
                Groups
              </button>
              <button type="button" onClick={() => setMoveTargetDn('OU=Users,OU=EITAS,DC=API,DC=LOCAL')}>
                Users
              </button>
              <button type="button" onClick={() => setMoveTargetDn('OU=MoveTest,OU=EITAS,DC=API,DC=LOCAL')}>
                MoveTest
              </button>
            </div>

            {moveTargetDn.trim() && moveTargetDn.trim().toLowerCase() === getParentDn(getObjectDn(moveModal)).toLowerCase() && (
              <p className="aduc-move-warning">
                La destination choisie est déjà l’emplacement actuel de cet objet.
              </p>
            )}

            <p className="aduc-move-help">
              Indique le DN du conteneur ou de l’OU de destination. L’objet sera déplacé avec Move-ADObject côté SRV-DC01.
            </p>

            <footer>
              <button type="button" onClick={() => setMoveModal(null)}>
                Annuler
              </button>

              <button
                type="submit"
                disabled={
                  adminLoading ||
                  !moveTargetDn.trim() ||
                  moveTargetDn.trim().toLowerCase() === getParentDn(getObjectDn(moveModal)).toLowerCase()
                }
              >
                {adminLoading ? 'Déplacement...' : 'Déplacer'}
              </button>
            </footer>
          </form>
        </div>
      )}

      {createUserModal && (
        <div className="aduc-modal-backdrop" onClick={() => setCreateUserModal(null)}>
          <form
            className="aduc-modal"
            onSubmit={submitCreateUser}
            onClick={event => event.stopPropagation()}
            onKeyDown={event => event.stopPropagation()}
          >
            <header className="aduc-modal-header">
              <div>
                <strong>👤 Créer un utilisateur</strong>
                <p>{createUserModal.target_ou_dn}</p>
              </div>
              <button type="button" onClick={() => setCreateUserModal(null)}>×</button>
            </header>

            <label>
              Prénom
              <input
                value={createUserForm.first_name}
                onChange={event => setCreateUserForm(current => ({ ...current, first_name: event.target.value }))}
                placeholder="Ex : Liam"
                autoFocus
              />
            </label>

            <label>
              Nom
              <input
                value={createUserForm.last_name}
                onChange={event => setCreateUserForm(current => ({ ...current, last_name: event.target.value }))}
                placeholder="Ex : Test"
              />
            </label>

            <label>
              Identifiant
              <input
                value={createUserForm.sam_account_name}
                onChange={event => setCreateUserForm(current => ({ ...current, sam_account_name: event.target.value }))}
                placeholder="Ex : liam.test"
              />
            </label>

            <label>
              OU de destination
              <select
                key={createUserOuOptions.map(option => option.dn).join('|') || 'loading-ou-tree'}
                value={createUserForm.target_ou_dn}
                disabled={createUserOuLoading}
                onChange={event => setCreateUserForm(current => ({ ...current, target_ou_dn: event.target.value }))}
              >
                {createUserOuLoading && (
                  <option value={createUserForm.target_ou_dn}>
                    Chargement de l’arbre Active Directory...
                  </option>
                )}

                {!createUserOuLoading && !dedupeCreateUserOuOptions(createUserOuOptions.length ? createUserOuOptions : getFallbackCreateUserOuOptions()).some(option => option.dn === createUserForm.target_ou_dn) && (
                  <option value={createUserForm.target_ou_dn}>
                    {getOuLabelFromDn(createUserForm.target_ou_dn)} — personnalisé
                  </option>
                )}

                {!createUserOuLoading && dedupeCreateUserOuOptions(createUserOuOptions.length ? createUserOuOptions : getFallbackCreateUserOuOptions()).map(option => (
                  <option key={option.dn} value={option.dn}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <details className="aduc-create-user-advanced-dn">
              <summary>DN personnalisé / avancé</summary>
              <input
                value={createUserForm.target_ou_dn}
                onChange={event => setCreateUserForm(current => ({ ...current, target_ou_dn: event.target.value }))}
                placeholder="OU=Support,OU=Users,OU=EITAS,DC=API,DC=LOCAL"
              />
            </details>

            <p className="aduc-create-user-ou-hint">
              {createUserOuLoading
                ? 'Chargement de l’arbre des OU depuis Active Directory...'
                : `${createUserOuOptions.length} OU détectée${createUserOuOptions.length > 1 ? 's' : ''} dans l’arbre AD.`}
            </p>

            <label>
              Mot de passe temporaire
              <input
                type="password"
                autoComplete="new-password"
                value={createUserForm.temporary_password}
                onChange={event => setCreateUserForm(current => ({ ...current, temporary_password: event.target.value }))}
              />
            </label>

            <label>
              Description
              <textarea
                rows={3}
                value={createUserForm.description}
                onChange={event => setCreateUserForm(current => ({ ...current, description: event.target.value }))}
                placeholder="Description optionnelle"
              />
            </label>

            <label>
              <input
                type="checkbox"
                checked={createUserForm.enabled}
                onChange={event => setCreateUserForm(current => ({ ...current, enabled: event.target.checked }))}
              />
              {' '}Activer le compte directement
            </label>

            <div className={isAdProductionMode() ? "aduc-modal-warning" : "aduc-modal-warning aduc-modal-warning-safe"}>
              <strong>{getAdAgentModeLabel()}</strong>
              <span>
                {isAdProductionMode()
                  ? "Cette création utilisateur modifiera réellement Active Directory."
                  : "Cette création utilisateur sera simulée, aucun compte AD réel ne sera créé."}
              </span>
            </div>

            <footer className="aduc-modal-actions">
              <button type="button" onClick={() => setCreateUserModal(null)}>Annuler</button>
              <button type="submit" disabled={createUserLoading || createUserOuLoading || adAgentModeLoading}>
                {createUserLoading
                  ? 'Création...'
                  : createUserOuLoading
                    ? 'Chargement des OU...'
                    : adAgentModeLoading
                      ? 'Vérification mode...'
                      : 'Créer utilisateur'}
              </button>
            </footer>
          </form>
        </div>
      )}

      {testCleanupModal && (
        <div className="aduc-modal-backdrop" onClick={() => setTestCleanupModal(false)}>
          <section className="aduc-modal aduc-test-cleanup-modal" onClick={event => event.stopPropagation()}>
            <header>
              <div>
                <span>Maintenance Active Directory</span>
                <h3>Nettoyage des objets de test</h3>
              </div>

              <button type="button" onClick={() => setTestCleanupModal(false)}>×</button>
            </header>

            <div className="aduc-test-cleanup-summary">
              <strong>{testCleanupLoading ? 'Scan en cours...' : `${testCleanupItems.length} objet(s) détecté(s)`}</strong>
              <span>Patterns : TMP_*, TEST_*, GG_TMP_*, test.*</span>
            </div>

            {testCleanupError && (
              <div className="aduc-member-submit-error">
                {testCleanupError}
              </div>
            )}

            {!testCleanupLoading && !testCleanupError && testCleanupItems.length === 0 && (
              <div className="aduc-empty-state">
                Aucun objet de test détecté dans l’arbre AD courant.
              </div>
            )}

            {testCleanupItems.length > 0 && (
              <div className="aduc-test-cleanup-list">
                {testCleanupItems.map((item, index) => (
                  <article key={getObjectDn(item) || `${getTestCleanupIdentity(item)}-${index}`} className="aduc-test-cleanup-item">
                    <div className="aduc-test-cleanup-icon">{objectIcon(item)}</div>

                    <div>
                      <strong>{getTestCleanupIdentity(item) || item?.name || 'Objet AD'}</strong>
                      <span>{item?.type || item?.objectClass || 'objet'} · {item.cleanup_reason}</span>
                      <code>{getObjectDn(item)}</code>

                      {testCleanupResults[getObjectDn(item)] && (
                        <em className={`aduc-test-cleanup-result ${testCleanupResults[getObjectDn(item)].type}`}>
                          {testCleanupResults[getObjectDn(item)].message}
                        </em>
                      )}
                    </div>

                    <button
                      type="button"
                      className="aduc-test-cleanup-delete"
                      disabled={testCleanupDeletingDn === getObjectDn(item)}
                      onClick={() => deleteTestCleanupObject(item)}
                    >
                      {testCleanupDeletingDn === getObjectDn(item)
                        ? 'Suppression...'
                        : isAdProductionMode()
                          ? isTestCleanupOu(item) ? 'Supprimer OU' : 'Supprimer'
                          : 'Simuler'}
                    </button>
                  </article>
                ))}
              </div>
            )}

            <footer className="aduc-modal-actions">
              <button type="button" onClick={() => setTestCleanupModal(false)}>Fermer</button>
              <button type="button" onClick={scanTestCleanupObjects} disabled={testCleanupLoading}>
                {testCleanupLoading ? 'Scan...' : 'Relancer le scan'}
              </button>
            </footer>
          </section>
        </div>
      )}

      {adminModal && (
        <div className="aduc-modal-backdrop" onClick={() => setAdminModal(null)}>
          <form className="aduc-modal" onSubmit={submitAdAdminJob} onClick={event => event.stopPropagation()}>
            <header>
              <div>
                <span>Administration Active Directory</span>
                <h3>{adminModal.title}</h3>
              </div>

              <button type="button" onClick={() => setAdminModal(null)}>×</button>
            </header>

            <label>
              Emplacement de création
              <select
                key={adminOuOptions.map(option => option.dn).join('|') || 'admin-ou-loading'}
                value={adminForm.parent_dn || adminModal.parent_dn}
                disabled={adminOuLoading}
                onChange={event => setAdminForm(current => ({ ...current, parent_dn: event.target.value }))}
              >
                {adminOuLoading && (
                  <option value={adminForm.parent_dn || adminModal.parent_dn}>
                    Chargement de l’arbre Active Directory...
                  </option>
                )}

                {!adminOuLoading && !adminOuOptions.some(option => option.dn === (adminForm.parent_dn || adminModal.parent_dn)) && (
                  <option value={adminForm.parent_dn || adminModal.parent_dn}>
                    {getOuLabelFromDn(adminForm.parent_dn || adminModal.parent_dn)} — personnalisé
                  </option>
                )}

                {!adminOuLoading && adminOuOptions.map(option => (
                  <option key={option.dn} value={option.dn}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <details className="aduc-create-user-advanced-dn">
              <summary>DN personnalisé / avancé</summary>
              <input
                value={adminForm.parent_dn || ''}
                onChange={event => setAdminForm(current => ({ ...current, parent_dn: event.target.value }))}
                placeholder="OU=Groups,OU=EITAS,DC=API,DC=LOCAL"
              />
            </details>

            <p className="aduc-create-user-ou-hint">
              {adminOuLoading
                ? 'Chargement de l’arbre des OU depuis Active Directory...'
                : `${adminOuOptions.length} OU détectée${adminOuOptions.length > 1 ? 's' : ''} dans l’arbre AD.`}
            </p>

            <label>
              Nom
              <input
                value={adminForm.name}
                onChange={event => setAdminForm(current => ({
                  ...current,
                  name: event.target.value,
                  sam_account_name: adminModal.action === 'create_group' ? event.target.value : current.sam_account_name
                }))}
                placeholder={adminModal.action === 'create_ou' ? 'Ex : Finance' : 'Ex : GG_Finance_RW'}
                autoFocus
              />
            </label>

            {adminModal.action === 'create_group' && (
              <>
                <label>
                  SamAccountName
                  <input
                    value={adminForm.sam_account_name}
                    onChange={event => setAdminForm(current => ({ ...current, sam_account_name: event.target.value }))}
                    placeholder="Ex : GG_Finance_RW"
                  />
                </label>

                <div className="aduc-modal-grid">
                  <label>
                    Scope
                    <select
                      value={adminForm.group_scope}
                      onChange={event => setAdminForm(current => ({ ...current, group_scope: event.target.value }))}
                    >
                      <option value="Global">Global</option>
                      <option value="Universal">Universal</option>
                      <option value="DomainLocal">DomainLocal</option>
                    </select>
                  </label>

                  <label>
                    Type
                    <select
                      value={adminForm.group_category}
                      onChange={event => setAdminForm(current => ({ ...current, group_category: event.target.value }))}
                    >
                      <option value="Security">Sécurité</option>
                      <option value="Distribution">Distribution</option>
                    </select>
                  </label>
                </div>
              </>
            )}

            <label>
              Description
              <textarea
                value={adminForm.description}
                onChange={event => setAdminForm(current => ({ ...current, description: event.target.value }))}
                placeholder="Description optionnelle"
              />
            </label>

            <div className={isAdProductionMode() ? "aduc-modal-warning" : "aduc-modal-warning aduc-modal-warning-safe"}>
              <strong>{getAdAgentModeLabel()}</strong>
              <span>
                {isAdProductionMode()
                  ? "Cette action modifiera réellement Active Directory via l’agent Windows."
                  : "Cette action sera simulée, aucun objet AD réel ne sera créé ou modifié."}
              </span>
            </div>

            <footer>
              <button type="button" onClick={() => setAdminModal(null)}>Annuler</button>
              <button type="submit" disabled={adminLoading || adminOuLoading || adAgentModeLoading}>
                {adminLoading
                  ? 'Création...'
                  : adminOuLoading
                    ? 'Chargement des OU...'
                    : adAgentModeLoading
                      ? 'Vérification mode...'
                      : adminModal.action === 'create_ou' ? 'Créer l’OU' : 'Créer le groupe'}
              </button>
            </footer>
          </form>
        </div>
      )}

      {memberModal && (
        <div className="aduc-modal-backdrop" onClick={closeMemberModal}>
          <form className="aduc-modal aduc-member-modal" onSubmit={submitAddMember} onClick={event => event.stopPropagation()}>
            <header>
              <div>
                <span>Administration Active Directory</span>
                <h3>Ajouter un membre</h3>
              </div>

              <button type="button" onClick={closeMemberModal}>×</button>
            </header>

            <label>
              Groupe cible
              <input value={memberModal.sam_account_name || memberModal.name || getObjectDn(memberModal)} readOnly />
            </label>

            <label>
              Utilisateur ou groupe à ajouter
              <div className="aduc-member-picker-row">
                <input
                  value={memberIdentity}
                  onChange={event => {
                    setMemberIdentity(event.target.value)
                    setSelectedMemberCandidate(null)
                    setMemberSearchError('')
                    setMemberSubmitError('')
                  }}
                  placeholder="Ex : l.ve, liam, GG_Support_RW..."
                  autoFocus
                />
                <button
                  type="button"
                  className="aduc-member-search-button"
                  onClick={searchMemberCandidates}
                  disabled={memberSearchLoading || memberIdentity.trim().length < 2}
                >
                  {memberSearchLoading ? 'Recherche...' : 'Rechercher'}
                </button>
              </div>
            </label>

            {memberSearchError && (
              <div className="aduc-member-search-error">
                {memberSearchError}
              </div>
            )}

            {memberSearchResults.length > 0 && (
              <div className="aduc-member-search-results">
                {memberSearchResults.map(candidate => {
                  const identity = getMemberCandidateIdentity(candidate)
                  const selected = selectedMemberCandidate && getMemberCandidateIdentity(selectedMemberCandidate) === identity

                  return (
                    <button
                      type="button"
                      key={identity}
                      data-kind-label={getMemberCandidateKindLabel(candidate)}
                      className={selected ? 'is-selected' : ''}
                      onClick={() => selectMemberCandidate(candidate)}
                    >
                      <strong>{getMemberCandidateTitle(candidate)}</strong>
                      <small>{getMemberCandidateSubtitle(candidate)}</small>
                    </button>
                  )
                })}
              </div>
            )}

            <div className="aduc-modal-warning">
              <strong>Production AD</strong>
              <span>Cette action ajoutera l’utilisateur ou le groupe sélectionné dans le groupe via l’agent Windows.</span>
            </div>

            {memberSubmitError && (
              <div className="aduc-member-submit-error">
                <strong>Impossible d’ajouter ce membre</strong>
                <span>{memberSubmitError}</span>
              </div>
            )}

            <footer>
              <button type="button" onClick={closeMemberModal}>Annuler</button>
              <button type="submit" disabled={memberActionLoading}>
                {memberActionLoading ? 'Ajout...' : 'Ajouter le membre'}
              </button>
            </footer>
          </form>
        </div>
      )}

      {contextMenu && (
        <div
          className="aduc-context-menu"
          style={{
            left: contextMenu.x,
            top: contextMenu.y
          }}
          onClick={event => event.stopPropagation()}
        >
          <button type="button" onClick={() => actionSoon('Délégation de contrôle')}>👥 Délégation de contrôle...</button>
          <button
              type="button"
              onClick={() => {
                setContextMenu(null)
                openMoveObject(contextMenu?.target || contextMenu?.item || contextMenu?.object || selectedObject || selectedNode)
              }}
            >
              📁 Déplacer...
            </button>
          <button
            type="button"
            onClick={() => openSearchOuModal(contextMenu?.target || selectedObject || selectedNode)}
          >
            🔎 Rechercher...
          </button>

          <hr />

          <button type="button" onClick={() => openNewObjectMenu(contextMenu?.target || selectedNode)}>＋ Nouveau ›</button>
          <button type="button" onClick={() => openCreateOu(selectedNode)}>📁 Créer une OU</button>
          <button type="button" onClick={() => openCreateGroup(selectedNode)}>👥 Créer un groupe</button>

          <hr />

          <button type="button" onClick={() => {
              setContextMenu(null)
              openUpdateObject(contextMenu?.target || selectedObject || selectedNode)
            }}>✎ Modifier</button>
          <button
            type="button"
            onClick={() => {
              setContextMenu(null)
              openRenameObject(contextMenu.target || selectedObject || selectedNode)
            }}
          >
            A↕ Renommer
          </button>
          <button type="button" className="danger" onClick={() => {
              setContextMenu(null)
              openDeleteObject(contextMenu?.target || selectedObject || selectedNode)
            }}>🗑 Supprimer</button>
          <button type="button" onClick={() => loadNodeContent(selectedNode, viewType)}>⟳ Actualiser</button>
          <button type="button" onClick={() => copyText(contextMenu.target?.distinguished_name || '').then(() => setMessage?.('DN copié.'))}>⎙ Exporter / Copier DN</button>

          <hr />

          <button type="button" onClick={() => openProperties(contextMenu.target)}>ⓘ Propriétés</button>
        </div>
      )}
    </div>
  )
}
