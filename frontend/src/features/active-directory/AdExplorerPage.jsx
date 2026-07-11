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

function getParentDn(dn) {
  const value = String(dn || '')
  const index = value.indexOf(',')

  if (index === -1) return ''

  return value.slice(index + 1)
}


function cleanAdHistoryText(value) {
  return String(value || '')
    .replaceAll('dÃ©jÃ ', 'déjà')
    .replaceAll('dÃ©jÃ ', 'déjà')
    .replaceAll('ajoutÃ©', 'ajouté')
    .replaceAll('retirÃ©', 'retiré')
    .replaceAll('crÃ©Ã©', 'créé')
    .replaceAll('Ã©', 'é')
    .replaceAll('Ã¨', 'è')
    .replaceAll('Ãª', 'ê')
    .replaceAll('Ã ', 'à')
    .replaceAll('Ã ', 'à')
    .replaceAll('Ã§', 'ç')
}

function formatAdHistoryAction(action) {
  return {
    create_ou: 'Création OU',
    create_group: 'Création groupe',
    add_group_member: 'Ajout membre',
    remove_group_member: 'Retrait membre'
  }[action] || action || 'Action AD'
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

  if (job?.action === 'create_group') {
    return `Groupe ${payload.name || output.name || group} créé`
  }

  if (job?.action === 'create_ou') {
    return `OU ${payload.name || output.name || 'AD'} créée`
  }

  return cleanAdHistoryText(output.message || job?.message || '—')
}


function ObjectDetailsPanel({ object, selectedNode, memberItems, membersLoading, membersError, historyItems, historyLoading, historyError, historyFilter, onHistoryFilterChange, onLoadHistory, onCopyDn, onExplore, onCreateOu, onCreateGroup, onLoadMembers, onOpenAddMember, onRemoveMember }) {
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
                  <div className={`aduc-admin-history-row ${job.success ? 'success' : 'failed'}`} key={job.id}>
                    <span />
                    <div>
                      <strong>{formatAdHistoryAction(job.action)}</strong>
                      <small>{job.agent_name || job.claimed_by || 'Agent non assigné'} • {formatAdHistoryStatus(job)}</small>
                      <em>{formatAdHistoryMessage(job)}</em>
                    </div>
                  </div>
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
  await navigator.clipboard.writeText(String(value || ''))
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
  const [adminForm, setAdminForm] = useState({
    name: '',
    description: '',
    sam_account_name: '',
    group_scope: 'Global',
    group_category: 'Security'
  })
  const [adminLoading, setAdminLoading] = useState(false)
  const [adAdminHistory, setAdAdminHistory] = useState([])
  const [adAdminHistoryLoading, setAdAdminHistoryLoading] = useState(false)
  const [adAdminHistoryError, setAdAdminHistoryError] = useState('')
  const [adAdminHistoryFilter, setAdAdminHistoryFilter] = useState('all')

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
        base_dn: normalizeBaseDn(options.baseDn || ''),
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
    setLoading(true)
    setContextMenu(null)

    try {
      setSelectedNode(node)
      setSelectedObject(null)
      setObjectMembers([])
      setMembersError('')
      setViewType(kind)

      let items = []

      if (kind === 'groups') {
        items = await runJob('list_groups', {
          baseDn: node.distinguished_name,
          limit: 500
        })
      } else if (kind === 'users') {
        items = await runJob('search_users', {
          query: '',
          baseDn: node.distinguished_name,
          limit: 500
        })
      } else {
        items = await runJob('list_ous', {
          baseDn: node.distinguished_name,
          limit: 500
        })
      }

      setViewItems(items)
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

  function actionSoon(label) {
    setContextMenu(null)
    setMessage?.(`${label} : prochaine étape, création/modification AD sécurisée via job agent.`)
  }

  async function openProperties(target) {
    setContextMenu(null)
    await copyText(target.distinguished_name || target.sam_account_name || target.name)
    setMessage?.('DN / identifiant copié. Propriétés détaillées à venir.')
  }


  function openCreateOu(target = selectedNode) {
    const parentDn = target?.distinguished_name || selectedNode?.distinguished_name || USERS_DN

    setContextMenu(null)
    setAdminForm({
      name: '',
      description: '',
      sam_account_name: '',
      group_scope: 'Global',
      group_category: 'Security'
    })
    setAdminModal({
      action: 'create_ou',
      title: 'Créer une OU',
      parent_dn: parentDn
    })
  }

  function openCreateGroup(target = selectedNode) {
    const parentDn = target?.distinguished_name || selectedNode?.distinguished_name || GROUPS_DN

    setContextMenu(null)
    setAdminForm({
      name: '',
      description: '',
      sam_account_name: '',
      group_scope: 'Global',
      group_category: 'Security'
    })
    setAdminModal({
      action: 'create_group',
      title: 'Créer un groupe',
      parent_dn: parentDn
    })
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

  async function submitAdAdminJob(event) {
    event.preventDefault()

    if (!adminModal) return

    const name = adminForm.name.trim()
    const description = adminForm.description.trim()
    const sam = adminForm.sam_account_name.trim() || name

    if (!name) {
      setMessage?.('Nom obligatoire.')
      return
    }

    setAdminLoading(true)

    try {
      const payload = {
        action: adminModal.action,
        parent_dn: adminModal.parent_dn,
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
              <button type="button" onClick={() => actionSoon('Nouveau')}>＋ Nouveau</button>
              <button type="button" onClick={() => openCreateOu(selectedNode)}>📁 Créer une OU</button>
              <button type="button" onClick={() => openCreateGroup(selectedNode)}>👥 Créer un groupe</button>
              <button type="button" onClick={() => actionSoon('Modifier')}>✎ Modifier</button>
              <button type="button" className="danger" onClick={() => actionSoon('Supprimer')}>🗑 Supprimer</button>
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
                onLoadHistory={() => loadAdAdminHistory()}
                onCopyDn={target => copyText(getObjectDn(target)).then(() => setMessage?.('DN copié.'))}
                onExplore={target => loadNodeContent(target, getNodeKind(target))}
                onCreateOu={target => openCreateOu(target)}
                onCreateGroup={target => openCreateGroup(target)}
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
              Emplacement cible
              <input value={adminModal.parent_dn} readOnly />
            </label>

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

            <div className="aduc-modal-warning">
              <strong>Production AD</strong>
              <span>Cette action sera exécutée par l’agent Windows sur SRV-DC01.</span>
            </div>

            <footer>
              <button type="button" onClick={() => setAdminModal(null)}>Annuler</button>
              <button type="submit" disabled={adminLoading}>
                {adminLoading ? 'Création...' : adminModal.action === 'create_ou' ? 'Créer l’OU' : 'Créer le groupe'}
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
          <button type="button" onClick={() => actionSoon('Déplacer')}>📂 Déplacer...</button>
          <button type="button" onClick={() => setMessage?.('Recherche dans cette OU à venir.')}>🔎 Rechercher...</button>

          <hr />

          <button type="button" onClick={() => actionSoon('Nouveau')}>＋ Nouveau ›</button>
          <button type="button" onClick={() => openCreateOu(selectedNode)}>📁 Créer une OU</button>
          <button type="button" onClick={() => openCreateGroup(selectedNode)}>👥 Créer un groupe</button>

          <hr />

          <button type="button" onClick={() => actionSoon('Modifier')}>✎ Modifier</button>
          <button type="button" onClick={() => actionSoon('Renommer')}>A↕ Renommer</button>
          <button type="button" className="danger" onClick={() => actionSoon('Supprimer')}>🗑 Supprimer</button>
          <button type="button" onClick={() => loadNodeContent(selectedNode, viewType)}>⟳ Actualiser</button>
          <button type="button" onClick={() => copyText(contextMenu.target?.distinguished_name || '').then(() => setMessage?.('DN copié.'))}>⎙ Exporter / Copier DN</button>

          <hr />

          <button type="button" onClick={() => openProperties(contextMenu.target)}>ⓘ Propriétés</button>
        </div>
      )}
    </div>
  )
}
