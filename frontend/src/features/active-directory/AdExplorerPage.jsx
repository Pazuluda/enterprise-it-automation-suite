import { useEffect, useMemo, useRef, useState } from 'react'

import {
  DOMAIN_DN,
  EITAS_DN,
  USERS_DN,
  GROUPS_DN,
  COMPUTERS_DN,
  isEitasManagedDn,
  isEitasManagedObject,
  normalizeBaseDn,
  buildOuTree,
  objectIcon,
  getNodeKind,
  extractExplorerItems,
  getObjectName,
  getGroupDescription,
  getObjectType,
  getObjectDn,
  isOuObject,
  isGroupObject,
  getParentDn,
  buildAdNavigationNode,
  buildAdBreadcrumbs,
  cleanAdHistoryText,
  copyText,
} from './utils/adExplorerCore'

import ObjectDetailsPanel from './components/ObjectDetailsPanel'
import AdActivityModal from './components/AdActivityModal'
import AdHistoryDetailModal from './components/AdHistoryDetailModal'
import TestCleanupModal from './components/TestCleanupModal'
import AdminCreationModal from './components/AdminCreationModal'
import AddMemberModal from './components/AddMemberModal'
import AdContextMenu from './components/AdContextMenu'
import useAdActivity from './hooks/useAdActivity'
import useTestCleanup from './hooks/useTestCleanup'
import useAdAdminCreation from './hooks/useAdAdminCreation'
import useAdGroupMembers from './hooks/useAdGroupMembers'

export default function AdExplorerPage({ apiFetch, setMessage }) {
  const [treeItems, setTreeItems] = useState([])
  const [viewItems, setViewItems] = useState([])
  const [selectedNode, setSelectedNode] = useState({
    name: 'EITAS',
    distinguished_name: EITAS_DN,
    canonical_name: 'API.LOCAL/EITAS'
  })

  const [viewType, setViewType] = useState('ou')
  const [selectedObject, setSelectedObject] = useState(null)
  const [newObjectModal, setNewObjectModal] = useState(null)
  const [propertiesModal, setPropertiesModal] = useState(null)
  const [searchOuModal, setSearchOuModal] = useState(null)
  const [searchOuQuery, setSearchOuQuery] = useState('')
  const [objectMembers, setObjectMembers] = useState([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [membersError, setMembersError] = useState('')
  const [treeFilter, setTreeFilter] = useState('')
  const [viewFilter, setViewFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const nodeContentCacheRef = useRef(new Map())
  const nodeContentPromisesRef = useRef(new Map())
  const nodeContentRequestIdRef = useRef(0)
  const [status, setStatus] = useState('Connexion au contrôleur de domaine : SRV-DC01.API.LOCAL')
  const [contextMenu, setContextMenu] = useState(null)

  const groupMembers = useAdGroupMembers({
    setMessage,
    setStatus,
    setContextMenu,
    runJob,
    runAdAdminJob,
    loadGroupMembers,
    openProperties,
    selectedObject,
    cleanAdAdminMessage,
  })

  const {
    openAddMemberModal,
    removeGroupMember,
  } = groupMembers
  const [adAgentMode, setAdAgentMode] = useState('Inconnu')
  const [adAgentModeLoading, setAdAgentModeLoading] = useState(false)
  const [createUserModal, setCreateUserModal] = useState(null)
  const [createUserLoading, setCreateUserLoading] = useState(false)
  const [createUserOuOptions, setCreateUserOuOptions] = useState([])
  const [createUserOuLoading, setCreateUserOuLoading] = useState(false)
  const [createUserError, setCreateUserError] = useState('')
  const [createUserConfirm, setCreateUserConfirm] = useState('')
  const [createUserForm, setCreateUserForm] = useState({
    first_name: '',
    last_name: '',
    sam_account_name: '',
    user_principal_name: '',
    temporary_password: '',
    description: '',
    target_ou_dn: '',
    enabled: false,
    force_change_at_logon: true
  })
  const [adminLoading, setAdminLoading] = useState(false)
  const [adminSuccess, setAdminSuccess] = useState('')

  const adAdminCreation = useAdAdminCreation({
    apiFetch,
    setMessage,
    setStatus,
    setContextMenu,
    loadAdAgentMode,
    waitForAdExplorerJob,
    getCreateUserOuItemsFromJob,
    getFallbackCreateUserOuOptions,
    getPreferredOuForAction,
    confirmProductionAdAction,
    runAdAdminJob,
    loadTree,
    loadComputersView,
    loadNodeContent,
    loadAdAdminHistory,
    selectedNode,
    viewType,
    adminLoading,
    setAdminLoading,
    setAdminSuccess,
    getOuPathLabelFromDn,
    isOuDn,
    dedupeCreateUserOuOptions,
    sortCreateUserOuOptions,
    splitLdapDn,
  })

  const {
    getAdminCreationOuDisplayLabel,
    openCreateOu,
    openCreateGroup,
  } = adAdminCreation
  const [moveModal, setMoveModal] = useState(null)
  const [renameModal, setRenameModal] = useState(null)
  const [deleteModal, setDeleteModal] = useState(null)
  const [updateModal, setUpdateModal] = useState(null)
  const [updateForm, setUpdateForm] = useState({ description: '' })
  const [updateOriginalForm, setUpdateOriginalForm] = useState({ description: '' })
  const [managerSearchQuery, setManagerSearchQuery] = useState('')
  const [managerSearchResults, setManagerSearchResults] = useState([])
  const [managerSearchLoading, setManagerSearchLoading] = useState(false)
  const [managerSearchError, setManagerSearchError] = useState('')
  const [deleteConfirmDn, setDeleteConfirmDn] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [renameNewName, setRenameNewName] = useState('')
  const [moveTargetDn, setMoveTargetDn] = useState('')
  const [moveOuOptions, setMoveOuOptions] = useState([])
  const [moveOuLoading, setMoveOuLoading] = useState(false)
  const [moveOuError, setMoveOuError] = useState('')
  const [globalAdSearch, setGlobalAdSearch] = useState('')
  const [globalAdSearchLoading, setGlobalAdSearchLoading] = useState(false)
  const testCleanup = useTestCleanup({
    apiFetch,
    selectedNode,
    getCreateUserSearchBaseDn,
    waitForAdExplorerJob,
    getCreateUserOuItemsFromJob,
    setStatus,
    adAgentMode,
    setAdAgentMode,
    runAdAdminJob,
    loadAdAgentMode,
  })

  const {
    testCleanupModal,
    setTestCleanupModal,
    openTestCleanupScanner,
  } = testCleanup
  const [adAdminHistory, setAdAdminHistory] = useState([])
  const [adAdminHistoryLoading, setAdAdminHistoryLoading] = useState(false)
  const [adAdminHistoryError, setAdAdminHistoryError] = useState('')
  const [adAdminHistoryFilter, setAdAdminHistoryFilter] = useState('all')
  const [selectedAdAdminHistoryJob, setSelectedAdAdminHistoryJob] = useState(null)
  const adActivity = useAdActivity({
    adAdminHistory,
    refreshAdAdminHistoryQuietly,
  })

  const {
    adActivityModal,
    setAdActivityModal,
    openAdActivityCenter,
  } = adActivity
  const [accountActionModal, setAccountActionModal] = useState(null)
  const [accountActionPassword, setAccountActionPassword] = useState('')
  const [accountActionConfirm, setAccountActionConfirm] = useState('')
  const [accountActionLoading, setAccountActionLoading] = useState(false)
  const [createComputerModal, setCreateComputerModal] = useState(false)
  const [createComputerLoading, setCreateComputerLoading] = useState(false)
  const [createComputerError, setCreateComputerError] = useState('')
  const [createComputerConfirm, setCreateComputerConfirm] = useState('')
  const [createComputerForm, setCreateComputerForm] = useState({
    name: '',
    target_ou_dn: COMPUTERS_DN,
    description: '',
    location: '',
    enabled: false
  })

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

  function isComputerManagedDn(value) {
    const dn = String(value || '')
      .trim()
      .toUpperCase()

    const computerBaseDn =
      COMPUTERS_DN.toUpperCase()

    return (
      dn === computerBaseDn
      || dn.endsWith(`,${computerBaseDn}`)
    )
  }

  const computerOuOptions = useMemo(() => {
    const byDn = new Map()

    const addOu = item => {
      const dn = String(
        item?.distinguished_name
        || item?.distinguishedName
        || item?.dn
        || ''
      ).trim()

      if (!/^OU=/i.test(dn)) return
      if (!isComputerManagedDn(dn)) return

      const key = dn.toUpperCase()

      if (!byDn.has(key)) {
        byDn.set(key, {
          dn,
          label: getOuLabelFromDn(dn)
        })
      }
    }

    addOu({
      distinguished_name: COMPUTERS_DN
    })

    treeItems.forEach(addOu)

    return Array.from(byDn.values()).sort((a, b) => {
      if (a.dn === COMPUTERS_DN) return -1
      if (b.dn === COMPUTERS_DN) return 1

      return a.label.localeCompare(
        b.label,
        'fr',
        { sensitivity: 'base' }
      )
    })
  }, [treeItems])

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

  async function loadNodeContent(
    node = selectedNode,
    kind = getNodeKind(node),
    options = {}
  ) {
    if (!node) return

    const baseDn = getObjectDn(node)
    const forceRefresh = Boolean(options.forceRefresh)
    const requestId = nodeContentRequestIdRef.current + 1

    nodeContentRequestIdRef.current = requestId

    setContextMenu(null)
    setSelectedNode(node)
    setSelectedObject(null)
    setObjectMembers([])
    setMembersError('')
    setViewType(kind)

    if (!baseDn) {
      setLoading(false)
      setViewItems([])
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    const cacheKey = normalizeBaseDn(baseDn)
      .trim()
      .toUpperCase()

    if (forceRefresh) {
      nodeContentCacheRef.current.clear()
    }

    const cachedItems = forceRefresh
      ? null
      : nodeContentCacheRef.current.get(cacheKey)

    if (Array.isArray(cachedItems)) {
      setLoading(false)
      setViewItems([...cachedItems])
      setStatus(
        'Connexion au contrôleur de domaine : SRV-DC01.API.LOCAL'
      )
      return
    }

    setLoading(true)

    let contentPromise = forceRefresh
      ? null
      : nodeContentPromisesRef.current.get(cacheKey)

    if (!contentPromise) {
      contentPromise = (async () => {
        const items = []

        try {
          const children = await runJob('list_children', {
            baseDn,
            recursive: false,
            limit: 500
          })

          items.push(
            ...extractExplorerItems(children)
          )
        } catch (childrenError) {
          const errorMessage = String(
            childrenError?.message || ''
          )

          const unsupportedAction =
            errorMessage.includes('non supportée') ||
            errorMessage.includes('non supportee') ||
            errorMessage.includes(
              'Action AD Explorer invalide'
            )

          if (!unsupportedAction) {
            throw childrenError
          }

          const [
            ousResult,
            groupsResult,
            usersResult
          ] = await Promise.allSettled([
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

          if (ousResult.status === 'fulfilled') {
            items.push(
              ...extractExplorerItems(ousResult.value)
            )
          }

          if (groupsResult.status === 'fulfilled') {
            items.push(
              ...extractExplorerItems(groupsResult.value)
            )
          }

          if (usersResult.status === 'fulfilled') {
            items.push(
              ...extractExplorerItems(usersResult.value)
            )
          }
        }

        const seen = new Set()

        return items.filter(item => {
          const key =
            getObjectDn(item) ||
            item?.sam_account_name ||
            item?.name

          if (!key) return true
          if (seen.has(key)) return false

          seen.add(key)
          return true
        })
      })()

      nodeContentPromisesRef.current.set(
        cacheKey,
        contentPromise
      )
    }

    try {
      const uniqueItems = await contentPromise

      if (
        nodeContentPromisesRef.current.get(cacheKey) ===
        contentPromise
      ) {
        nodeContentPromisesRef.current.delete(cacheKey)
      }

      if (
        requestId !==
        nodeContentRequestIdRef.current
      ) {
        return
      }

      nodeContentCacheRef.current.set(
        cacheKey,
        uniqueItems
      )

      setViewItems([...uniqueItems])
      setStatus(
        'Connexion au contrôleur de domaine : SRV-DC01.API.LOCAL'
      )
    } catch (err) {
      if (
        nodeContentPromisesRef.current.get(cacheKey) ===
        contentPromise
      ) {
        nodeContentPromisesRef.current.delete(cacheKey)
      }

      if (
        requestId !==
        nodeContentRequestIdRef.current
      ) {
        return
      }

      setViewItems([])
      setStatus(
        err.message || 'Erreur Active Directory'
      )
      setMessage?.(
        err.message || 'Erreur Active Directory'
      )
    } finally {
      if (
        requestId ===
        nodeContentRequestIdRef.current
      ) {
        setLoading(false)
      }
    }
  }

  async function loadAdAdminHistory() {
    setAdAdminHistoryLoading(true)
    setAdAdminHistoryError('')

    try {
      const data = await apiFetch('/api/ad-admin/jobs?limit=50')
      setAdAdminHistory(Array.isArray(data.jobs) ? data.jobs : [])
    } catch (err) {
      setAdAdminHistoryError(err.message || 'Impossible de charger l’historique AD Admin.')
    } finally {
      setAdAdminHistoryLoading(false)
    }
  }

  async function refreshAdAdminHistoryQuietly() {
    try {
      const data = await apiFetch('/api/ad-admin/jobs?limit=50')
      setAdAdminHistory(Array.isArray(data.jobs) ? data.jobs : [])
      setAdAdminHistoryError('')
    } catch {
      // Historique non bloquant.
    }
  }

  async function refreshAll() {
    setLoading(true)

    try {
      await Promise.all([
        loadTree(),
        loadNodeContent(
          selectedNode,
          viewType,
          { forceRefresh: true }
        ),
        refreshAdAdminHistoryQuietly()
      ])
    } catch (err) {
      setStatus(
        err.message || 'Erreur Active Directory'
      )
      setMessage?.(
        err.message || 'Erreur Active Directory'
      )
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


  function navigateToAdDn(dn) {
    const node = buildAdNavigationNode(dn)

    if (!node) {
      return
    }

    setViewFilter('')

    loadNodeContent(
      node,
      getNodeKind(node)
    )
  }


  function navigateToParentNode() {
    const currentDn = getObjectDn(selectedNode)

    if (
      !currentDn
      || currentDn.toUpperCase()
        === DOMAIN_DN.toUpperCase()
    ) {
      return
    }

    const parentDn = getParentDn(currentDn)

    if (!parentDn) {
      return
    }

    navigateToAdDn(parentDn)
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

  async function loadComputersView() {
    setLoading(true)
    setStatus(
      'Chargement des ordinateurs Active Directory...'
    )

    try {
      const computers = await runJob(
        'list_computers',
        {
          query: '',
          baseDn: DOMAIN_DN,
          recursive: true,
          limit: 1000
        }
      )

      const items = extractExplorerItems(computers)

      setSelectedNode({
        name: 'Ordinateurs',
        type: 'computer-container',
        distinguished_name: DOMAIN_DN,
        dn: DOMAIN_DN,
        canonical_name: 'API.LOCAL/Ordinateurs'
      })

      setViewType('computers')
      setViewItems(items)

      setSelectedObject(previous => {
        if (!previous) return null

        const previousDn = String(
          getObjectDn(previous) || ''
        ).toLowerCase()

        if (!previousDn) return null

        return (
          items.find(item =>
            String(
              getObjectDn(item) || ''
            ).toLowerCase() === previousDn
          ) || null
        )
      })

      setObjectMembers([])
      setMembersError('')

      setStatus(
        `${items.length} ordinateur(s) Active Directory chargé(s)`
      )
    } catch (error) {
      setViewItems([])
      setSelectedObject(null)

      setStatus(
        error.message ||
        'Chargement des ordinateurs Active Directory impossible.'
      )
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
      const baseDn = DOMAIN_DN
      const lowered = query.toLowerCase()

      const [
        usersResult,
        groupsResult,
        computersResult
      ] = await Promise.allSettled([
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
        }),
        runJob('search_computers', {
          query,
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

      if (computersResult.status === 'fulfilled') {
        results.push(
          ...extractExplorerItems(
            computersResult.value
          )
        )
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

  function isUpdateUserTarget(target) {
    const objectClass = String(
      target?.objectClass
      || target?.object_class
      || target?.type
      || ''
    ).toLowerCase()

    return objectClass.includes('user')
      || getObjectType(target)
        .toLowerCase()
        .includes('utilisateur')
  }
  function isUpdateComputerTarget(target) {
    const objectClass = String(
      target?.objectClass
      || target?.object_class
      || target?.type
      || ''
    ).trim().toLowerCase()

    return objectClass === 'computer'
      || getObjectType(target) === 'Ordinateur'
  }

  function openUpdateObject(target) {
    if (!isEitasManagedObject(target)) {
      const message =
        'Action bloquée : cet objet est hors du périmètre OU=EITAS et reste accessible uniquement en lecture.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

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
      description: getAdAttributeValue(
        target,
        'description'
      ),
      location: getAdAttributeValue(
        target,
        'location'
      ),
      displayName: getAdAttributeValue(
        target,
        'displayName',
        'display_name',
        'display_name_value'
      ),
      mail: getAdAttributeValue(
        target,
        'mail',
        'email'
      ),
      title: getAdAttributeValue(
        target,
        'title',
        'job_title'
      ),
      department: getAdAttributeValue(
        target,
        'department',
        'service'
      ),
      division: getAdAttributeValue(
        target,
        'division',
        'business_unit',
        'businessUnit'
      ),
      company: getAdAttributeValue(
        target,
        'company'
      ),
      physicalDeliveryOfficeName: getAdAttributeValue(
        target,
        'physicalDeliveryOfficeName',
        'office'
      ),
      employeeID: getAdAttributeValue(
        target,
        'employeeID',
        'employee_id',
        'EmployeeID'
      ),
      employeeNumber: getAdAttributeValue(
        target,
        'employeeNumber',
        'employee_number'
      ),
      manager: getAdAttributeValue(
        target,
        'manager',
        'manager_dn',
        'managerDn'
      ),
      telephoneNumber: getAdAttributeValue(
        target,
        'telephoneNumber',
        'telephone_number',
        'phone'
      ),
      mobile: getAdAttributeValue(
        target,
        'mobile',
        'mobilePhone'
      ),
      streetAddress: getAdAttributeValue(
        target,
        'streetAddress',
        'street_address'
      ),
      postalCode: getAdAttributeValue(
        target,
        'postalCode',
        'postal_code'
      ),
      l: getAdAttributeValue(
        target,
        'l',
        'city'
      ),
      st: getAdAttributeValue(
        target,
        'st',
        'state'
      ),
      co: getAdAttributeValue(
        target,
        'co',
        'country'
      )
    }

    resetManagerPicker()
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

  function resetManagerPicker() {
    setManagerSearchQuery('')
    setManagerSearchResults([])
    setManagerSearchLoading(false)
    setManagerSearchError('')
  }

  function getManagerCandidateDn(candidate) {
    return String(
      candidate?.distinguished_name ||
      candidate?.dn ||
      ''
    )
  }

  function selectManagerCandidate(candidate) {
    const managerDn = getManagerCandidateDn(candidate)

    if (!managerDn) {
      setManagerSearchError(
        'Le Distinguished Name de cet utilisateur est introuvable.'
      )
      return
    }

    updateObjectFormField('manager', managerDn)
    setManagerSearchQuery('')
    setManagerSearchResults([])
    setManagerSearchError('')
  }

  function clearManagerSelection() {
    updateObjectFormField('manager', '')
    resetManagerPicker()
  }

  async function searchManagerCandidates() {
    const query = managerSearchQuery.trim()

    setManagerSearchResults([])
    setManagerSearchError('')

    if (query.length < 2) {
      setManagerSearchError(
        'Tape au moins 2 caractères pour rechercher un manager.'
      )
      return
    }

    setManagerSearchLoading(true)

    try {
      const users = await runJob('search_users', {
        query,
        baseDn: 'DC=API,DC=LOCAL',
        limit: 50,
        recursive: true
      })

      const currentDn = String(
        getObjectDn(updateModal) || ''
      ).toLowerCase()

      const currentSam = String(
        updateModal?.sam_account_name ||
        updateModal?.samAccountName ||
        ''
      ).toLowerCase()

      const results = users
        .filter(candidate => {
          const candidateDn = getManagerCandidateDn(candidate)

          if (!candidateDn) return false

          const enabledValue =
            candidate?.enabled ??
            candidate?.Enabled

          const isDisabled =
            enabledValue === false ||
            enabledValue === 0 ||
            String(enabledValue || '')
              .trim()
              .toLowerCase() === 'false'

          if (isDisabled) return false

          const candidateSam = String(
            candidate?.sam_account_name ||
            candidate?.samAccountName ||
            ''
          ).toLowerCase()

          const isCurrentObject =
            candidateDn.toLowerCase() === currentDn ||
            (
              currentSam &&
              candidateSam &&
              candidateSam === currentSam
            )

          return !isCurrentObject
        })
        .sort((first, second) =>
          getMemberCandidateTitle(first).localeCompare(
            getMemberCandidateTitle(second),
            'fr',
            { sensitivity: 'base' }
          )
        )

      setManagerSearchResults(results)

      if (!results.length) {
        setManagerSearchError(
          'Aucun autre utilisateur Active Directory actif trouvé.'
        )
      }
    } catch (error) {
      setManagerSearchResults([])
      setManagerSearchError(
        error.message ||
        'Recherche de manager impossible.'
      )
    } finally {
      setManagerSearchLoading(false)
    }
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
      resetManagerPicker()

      await loadTree()

      if (viewType === 'computers') {
        await loadComputersView()
      } else if (selectedNode) {
        await loadNodeContent(
          selectedNode,
          viewType,
          { forceRefresh: true }
        )
      }

      await loadAdAdminHistory()
    } catch (err) {
      setStatus(err.message || 'Erreur pendant la modification AD.')
    } finally {
      setLoading(false)
    }
  }

  function normalizeDeleteConfirmationDn(value) {
    return String(value || '')
      .trim()
      .toUpperCase()
  }

  function openDeleteObject(target) {
    if (!isEitasManagedObject(target)) {
      const message =
        'Action bloquée : cet objet est hors du périmètre OU=EITAS et reste accessible uniquement en lecture.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

    if (!target) {
      const message =
        'Aucun objet sélectionné pour la suppression.'

      setStatus(message)
      setMessage?.(message)
      return
    }

    const dn = getObjectDn(target)

    if (!dn) {
      const message =
        'DN introuvable pour cet objet Active Directory.'

      setStatus(message)
      setMessage?.(message)
      return
    }

    setContextMenu(null)
    setDeleteModal(target)
    setDeleteConfirmDn('')
    setDeleteError('')
  }

  async function submitDeleteObject(event) {
    event?.preventDefault?.()

    if (!deleteModal) {
      setDeleteError(
        'Objet cible introuvable. Ferme puis rouvre la fenêtre.'
      )
      return
    }

    const objectDn = String(
      getObjectDn(deleteModal) || ''
    ).trim()

    const confirmDn = String(
      deleteConfirmDn || ''
    ).trim()

    if (!objectDn) {
      const message =
        'DN introuvable pour cet objet Active Directory.'

      setDeleteError(message)
      setStatus(message)
      return
    }

    if (
      normalizeDeleteConfirmationDn(confirmDn)
      !== normalizeDeleteConfirmationDn(objectDn)
    ) {
      const message =
        'Le DN de confirmation ne correspond pas au DN de l’objet.'

      setDeleteError(message)
      setStatus(message)
      return
    }

    setLoading(true)
    setDeleteError('')
    setStatus('Suppression Active Directory en cours...')

    try {
      const job = await runAdAdminJob({
        action: 'delete_object',
        object_identity: objectDn,
        confirm_dn: objectDn,
        created_by: 'react-admin'
      })

      const message = cleanAdHistoryText(
        job?.message
        || job?.output?.message
        || 'Objet Active Directory supprimé.'
      )

      setStatus(message)
      setMessage?.(message)

      setDeleteModal(null)
      setDeleteConfirmDn('')
      setDeleteError('')
      setSelectedObject(null)

      await loadTree()

      if (viewType === 'computers') {
        await loadComputersView()
      } else if (selectedNode) {
        await loadNodeContent(
          selectedNode,
          viewType,
          { forceRefresh: true }
        )
      }

      await loadAdAdminHistory()
    } catch (error) {
      const message = cleanAdHistoryText(
        error?.message
        || 'Erreur pendant la suppression Active Directory.'
      )

      setDeleteError(message)
      setStatus(message)
      setMessage?.(message)
    } finally {
      setLoading(false)
    }
  }


  function openRenameObject(target) {
    if (!isEitasManagedObject(target)) {
      const message =
        'Action bloquée : cet objet est hors du périmètre OU=EITAS et reste accessible uniquement en lecture.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

    if (!target) {
      setStatus('Aucun objet sélectionné pour le renommage.')
      return
    }

    const dn = getObjectDn(target)

    if (!dn) {
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    const currentName = String(
      getObjectName(target) || ''
    ).trim()

    if (!currentName) {
      setStatus(
        'Nom actuel introuvable pour cet objet AD.'
      )
      setContextMenu(null)
      return
    }

    setContextMenu(null)
    setRenameNewName(currentName)
    setRenameModal(target)
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

    const currentName = String(
      getObjectName(renameModal) || ''
    ).trim()

    if (newName === currentName) {
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

      if (viewType === 'computers') {
        await loadComputersView()
      } else if (selectedNode) {
        await loadNodeContent(
          selectedNode,
          viewType,
          { forceRefresh: true }
        )
      }

      await loadAdAdminHistory()
    } catch (err) {
      setStatus(err.message || 'Erreur pendant le renommage AD.')
    } finally {
      setLoading(false)
    }
  }

  function getMoveCurrentParentDn(objectDn) {
    const parts = splitLdapDn(objectDn)

    if (parts.length < 2) {
      return ''
    }

    return parts.slice(1).join(',')
  }

  function isMoveDestinationBlocked(
    objectDn,
    targetParentDn
  ) {
    const objectKey = String(objectDn || '')
      .trim()
      .toUpperCase()

    const targetKey = String(targetParentDn || '')
      .trim()
      .toUpperCase()

    if (!objectKey || !targetKey) {
      return false
    }

    if (!isOuDn(objectDn)) {
      return false
    }

    return (
      targetKey === objectKey
      || targetKey.endsWith(`,${objectKey}`)
    )
  }

  function isManagedMoveDestination(dn) {
    const value = String(dn || '').trim()

    return (
      isEitasManagedDn(value)
      || value.toUpperCase() ===
        String(EITAS_DN).toUpperCase()
    )
  }

  function getMoveOuDisplayLabel(dn) {
    const cleanDn = String(dn || '').trim()

    if (!cleanDn) {
      return 'OU inconnue'
    }

    if (
      cleanDn.toUpperCase()
      === String(EITAS_DN).toUpperCase()
    ) {
      return 'EITAS'
    }

    const pathLabel = getOuPathLabelFromDn(
      cleanDn,
      EITAS_DN
    )

    if (!pathLabel) {
      return cleanDn
    }

    if (
      pathLabel.toUpperCase() === 'EITAS'
    ) {
      return 'EITAS'
    }

    return `EITAS / ${pathLabel}`
  }

  function buildMoveOuOptions(
    items,
    objectDn = ''
  ) {
    const currentParentDn =
      getMoveCurrentParentDn(objectDn)

    const currentParentKey = String(
      currentParentDn || ''
    )
      .trim()
      .toUpperCase()

    const sourceItems = [
      {
        dn: EITAS_DN
      },
      ...(Array.isArray(items) ? items : [])
    ]

    const options = sourceItems
      .map(item => {
        const dn = String(
          getObjectDn(item)
          || item?.dn
          || item?.distinguished_name
          || ''
        ).trim()

        if (!dn || !isOuDn(dn)) {
          return null
        }

        return {
          dn,
          label: getMoveOuDisplayLabel(dn)
        }
      })
      .filter(Boolean)
      .filter(option =>
        isManagedMoveDestination(option.dn)
      )
      .filter(option =>
        option.dn.toUpperCase()
        !== currentParentKey
      )
      .filter(option =>
        !isMoveDestinationBlocked(
          objectDn,
          option.dn
        )
      )

    return dedupeCreateUserOuOptions(options)
      .sort((a, b) =>
        String(a.label || '').localeCompare(
          String(b.label || ''),
          'fr',
          { sensitivity: 'base' }
        )
      )
  }

  function getMoveValidationError(
    target = moveModal,
    targetParentDn = moveTargetDn
  ) {
    const objectDn = getObjectDn(target)
    const destination = String(
      targetParentDn || ''
    ).trim()

    if (!objectDn) {
      return 'Objet Active Directory invalide.'
    }

    if (!destination) {
      return 'Choisis une OU de destination.'
    }

    if (!isOuDn(destination)) {
      return (
        'La destination doit être une unité '
        + 'd’organisation.'
      )
    }

    if (!isManagedMoveDestination(destination)) {
      return (
        'La destination doit appartenir au '
        + 'périmètre OU=EITAS.'
      )
    }

    const currentParentDn =
      getMoveCurrentParentDn(objectDn)

    if (
      currentParentDn
      && destination.toUpperCase()
        === currentParentDn.toUpperCase()
    ) {
      return (
        'Cet objet se trouve déjà dans cette OU.'
      )
    }

    if (
      isMoveDestinationBlocked(
        objectDn,
        destination
      )
    ) {
      return (
        'Une OU ne peut pas être déplacée '
        + 'dans elle-même ou dans une OU enfant.'
      )
    }

    return ''
  }

  async function loadMoveOuOptions(target) {
    const objectDn = getObjectDn(target)
    const currentParentDn =
      getMoveCurrentParentDn(objectDn)

    const fallbackOptions =
      buildMoveOuOptions(
        [
          ...treeItems,
          {
            dn: currentParentDn,
            label: getOuPathLabelFromDn(
              currentParentDn,
              EITAS_DN
            )
          }
        ],
        objectDn
      )

    setMoveOuOptions(fallbackOptions)
    setMoveOuLoading(true)
    setMoveOuError('')

    try {
      const created = await apiFetch(
        '/api/ad-explorer/jobs',
        {
          method: 'POST',
          body: JSON.stringify({
            action: 'list_ou_tree',
            base_dn: EITAS_DN,
            baseDn: EITAS_DN,
            created_by:
              'react-move-ou-selector'
          })
        }
      )

      const jobId = created?.job?.id

      if (!jobId) {
        throw new Error(
          'Job de chargement des OU introuvable.'
        )
      }

      const completedJob =
        await waitForAdExplorerJob(jobId)

      const items =
        getCreateUserOuItemsFromJob(
          completedJob
        )

      const options = buildMoveOuOptions(
        [
          ...treeItems,
          ...items,
          {
            dn: currentParentDn,
            label: getOuPathLabelFromDn(
              currentParentDn,
              EITAS_DN
            )
          }
        ],
        objectDn
      )

      setMoveOuOptions(
        options.length
          ? options
          : fallbackOptions
      )

      if (
        !options.length
        && !fallbackOptions.length
      ) {
        setMoveOuError(
          'Aucune OU de destination disponible.'
        )
      }
    } catch (error) {
      console.warn(
        'Chargement des OU de déplacement impossible',
        error
      )

      setMoveOuError(
        error?.message
        || 'Chargement des OU impossible.'
      )
    } finally {
      setMoveOuLoading(false)
    }
  }

  function closeMoveModal() {
    if (adminLoading) {
      return
    }

    setMoveModal(null)
    setMoveTargetDn('')
    setMoveOuOptions([])
    setMoveOuError('')
  }

  function openMoveObject(target) {
    if (!isEitasManagedObject(target)) {
      const message =
        'Action bloquée : cet objet est hors du périmètre OU=EITAS et reste accessible uniquement en lecture.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

    const objectDn = getObjectDn(target)

    if (!target || !objectDn) {
      setStatus(
        'Aucun objet AD valide à déplacer.'
      )
      return
    }

    const currentParentDn =
      getMoveCurrentParentDn(objectDn)

    setContextMenu(null)
    setMoveModal(target)
    setMoveTargetDn('')
    setMoveOuError('')

    setMoveOuOptions(
      buildMoveOuOptions(
        [
          ...treeItems,
          {
            dn: currentParentDn,
            label: getOuPathLabelFromDn(
              currentParentDn,
              EITAS_DN
            )
          }
        ],
        objectDn
      )
    )

    loadAdAgentMode()

    window.setTimeout(
      () => loadMoveOuOptions(target),
      0
    )
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

  function getDnsDomainNameFromDn(dn) {
    return splitLdapDn(dn)
      .filter(part => /^DC=/i.test(part))
      .map(part => part.replace(/^DC=/i, ''))
      .filter(Boolean)
      .join('.')
  }

  function getSuggestedUserPrincipalName(
    samAccountName,
    targetOuDn
  ) {
    const sam = String(
      samAccountName || ''
    ).trim()

    const domain =
      getDnsDomainNameFromDn(targetOuDn)
      || getDnsDomainNameFromDn(EITAS_DN)

    if (!sam || !domain) {
      return ''
    }

    return `${sam}@${domain}`
  }

  function validateCreateUserForm(form) {
    const errors = []

    const firstName = String(
      form?.first_name || ''
    ).trim()

    const lastName = String(
      form?.last_name || ''
    ).trim()

    const sam = String(
      form?.sam_account_name || ''
    ).trim()

    const upn = String(
      form?.user_principal_name || ''
    ).trim()

    const password = String(
      form?.temporary_password || ''
    ).trim()

    const targetOuDn = String(
      form?.target_ou_dn || ''
    ).trim()

    if (!firstName) {
      errors.push('Le prénom est obligatoire.')
    }

    if (!lastName) {
      errors.push('Le nom est obligatoire.')
    }

    if (!sam) {
      errors.push('L’identifiant AD est obligatoire.')
    } else {
      if (sam.length > 20) {
        errors.push(
          'L’identifiant AD ne doit pas dépasser '
          + '20 caractères.'
        )
      }

      if (!/^[A-Za-z0-9._-]+$/.test(sam)) {
        errors.push(
          'L’identifiant AD ne peut contenir que '
          + 'des lettres, chiffres, points, tirets '
          + 'ou underscores.'
        )
      }
    }

    if (!upn) {
      errors.push('L’UPN est obligatoire.')
    } else if (
      !/^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$/.test(upn)
    ) {
      errors.push(
        'L’UPN doit respecter le format '
        + 'utilisateur@domaine.'
      )
    }

    if (!targetOuDn) {
      errors.push('L’OU cible est obligatoire.')
    } else if (
      !isOuDn(targetOuDn)
      || !isEitasManagedDn(targetOuDn)
    ) {
      errors.push(
        'L’OU cible doit appartenir au périmètre '
        + 'sécurisé OU=EITAS.'
      )
    }

    if (!password) {
      errors.push(
        'Le mot de passe temporaire est obligatoire.'
      )
    } else {
      if (password.length < 12) {
        errors.push(
          'Le mot de passe doit faire au moins '
          + '12 caractères.'
        )
      }

      if (
        !/[a-z]/.test(password)
        || !/[A-Z]/.test(password)
        || !/[0-9]/.test(password)
        || !/[^A-Za-z0-9]/.test(password)
      ) {
        errors.push(
          'Le mot de passe doit contenir une '
          + 'minuscule, une majuscule, un chiffre '
          + 'et un caractère spécial.'
        )
      }

      const normalizedPassword =
        normalizeCreateUserPart(password)

      const forbiddenParts = [
        firstName,
        lastName,
        sam
      ]
        .map(normalizeCreateUserPart)
        .filter(Boolean)

      if (
        forbiddenParts.some(part =>
          normalizedPassword.includes(part)
        )
      ) {
        errors.push(
          'Le mot de passe ne doit pas contenir '
          + 'le prénom, le nom ou l’identifiant.'
        )
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
    const searchBaseDn = EITAS_DN

    setCreateUserOuLoading(true)

    try {
      const created = await apiFetch(
        '/api/ad-explorer/jobs',
        {
          method: 'POST',
          body: JSON.stringify({
            action: 'list_ou_tree',
            base_dn: searchBaseDn,
            baseDn: searchBaseDn,
            created_by:
              'react-create-user-ou-tree'
          })
        }
      )

      const jobId = created?.job?.id

      if (!jobId) {
        throw new Error(
          'Job list_ou_tree introuvable'
        )
      }

      const completedJob =
        await waitForAdExplorerJob(jobId)

      const items =
        getCreateUserOuItemsFromJob(
          completedJob
        )

      let options =
        normalizeAdminCreationOptions(items)
          .filter(option =>
            !splitLdapDn(option.dn).some(part =>
              /^OU=(Groups|Computers)$/i.test(part)
            )
          )

      if (!options.length) {
        options =
          normalizeAdminCreationOptions([
            {
              distinguished_name: EITAS_DN
            }
          ])
      }

      setCreateUserOuOptions(options)

      const requestedDn = String(
        initialDn
        || createUserForm.target_ou_dn
        || ''
      ).trim()

      const requested = options.find(option =>
        option.dn.toUpperCase()
        === requestedDn.toUpperCase()
      )

      const usersOption =
        options.find(option =>
          /(^| \/ )Users( \/ |$)/i.test(
            option.label
          )
        )
        || options.find(option =>
          /^Users$/i.test(
            getOuLabelFromDn(option.dn)
          )
        )

      const requestedIsEitasRoot =
        requested?.dn?.toUpperCase()
        === String(EITAS_DN).toUpperCase()

      const preferred =
        (
          requested
          && !requestedIsEitasRoot
            ? requested
            : null
        )
        || usersOption
        || requested
        || options[0]


      if (preferred) {
        setCreateUserForm(current => {
          const currentUpn = String(
            current.user_principal_name || ''
          ).trim()

          const previousAutomaticUpn =
            getSuggestedUserPrincipalName(
              current.sam_account_name,
              current.target_ou_dn
            )

          const upnWasAutomatic =
            !currentUpn
            || currentUpn.toLowerCase()
              === previousAutomaticUpn.toLowerCase()

          return {
            ...current,
            target_ou_dn: preferred.dn,
            user_principal_name:
              upnWasAutomatic
                ? getSuggestedUserPrincipalName(
                    current.sam_account_name,
                    preferred.dn
                  )
                : current.user_principal_name
          }
        })
      }
    } catch (error) {
      console.warn(
        'Impossible de charger les OU EITAS',
        error
      )

      const fallback =
        normalizeAdminCreationOptions([
          {
            distinguished_name: EITAS_DN
          }
        ])

      setCreateUserOuOptions(fallback)

      setCreateUserForm(current => ({
        ...current,
        target_ou_dn:
          fallback[0]?.dn || EITAS_DN,
        user_principal_name:
          getSuggestedUserPrincipalName(
            current.sam_account_name,
            fallback[0]?.dn || EITAS_DN
          )
      }))

      setCreateUserError(
        'Chargement complet des OU impossible. '
        + 'La création reste limitée à OU=EITAS.'
      )
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


  function getEmptyCreateUserForm(
    targetOuDn = EITAS_DN
  ) {
    return {
      first_name: '',
      last_name: '',
      sam_account_name: '',
      user_principal_name: '',
      temporary_password: '',
      description: '',
      target_ou_dn: targetOuDn,
      enabled: false,
      force_change_at_logon: true
    }
  }

  function updateCreateUserField(name, value) {
    setCreateUserForm(current => {
      const next = {
        ...current,
        [name]: value
      }

      const previousSuggestedSam =
        getSuggestedSamAccountName(
          current.first_name,
          current.last_name
        )

      if (
        name === 'first_name'
        || name === 'last_name'
      ) {
        const nextSuggestedSam =
          getSuggestedSamAccountName(
            next.first_name,
            next.last_name
          )

        const currentSam = String(
          current.sam_account_name || ''
        ).trim()

        if (
          !currentSam
          || currentSam.toLowerCase()
            === previousSuggestedSam.toLowerCase()
        ) {
          next.sam_account_name =
            nextSuggestedSam
        }
      }

      const currentUpn = String(
        current.user_principal_name || ''
      ).trim()

      const previousAutomaticUpn =
        getSuggestedUserPrincipalName(
          current.sam_account_name,
          current.target_ou_dn
        )

      const upnWasAutomatic =
        !currentUpn
        || currentUpn.toLowerCase()
          === previousAutomaticUpn.toLowerCase()

      if (
        name !== 'user_principal_name'
        && upnWasAutomatic
      ) {
        next.user_principal_name =
          getSuggestedUserPrincipalName(
            next.sam_account_name,
            next.target_ou_dn
          )
      }

      return next
    })

    setCreateUserError('')
  }

  function getCreateUserDefaultOuDn(target) {
    const targetDn = getObjectDn(target)

    if (
      targetDn
      && isOuDn(targetDn)
      && isEitasManagedDn(targetDn)
    ) {
      return targetDn
    }

    const parentDn =
      getCreateAdminParentDn(target)

    if (
      parentDn
      && isEitasManagedDn(parentDn)
    ) {
      return parentDn
    }

    return EITAS_DN
  }

  function openCreateUser(target = selectedNode) {
    const base = target || selectedNode

    if (!isEitasManagedObject(base)) {
      const message =
        'Action bloquée : sélectionne un objet '
        + 'du périmètre OU=EITAS.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

    const defaultUserOuDn =
      getCreateUserDefaultOuDn(base)

    loadAdAgentMode()
    setContextMenu(null)
    setCreateUserError('')
    setCreateUserConfirm('')

    setCreateUserForm(
      getEmptyCreateUserForm(defaultUserOuDn)
    )

    setCreateUserOuOptions(
      normalizeAdminCreationOptions([
        {
          distinguished_name: defaultUserOuDn
        },
        {
          distinguished_name: EITAS_DN
        }
      ])
    )

    setCreateUserModal({
      target: base,
      target_ou_dn: defaultUserOuDn
    })

    window.setTimeout(
      () =>
        loadCreateUserOuOptions(
          defaultUserOuDn
        ),
      0
    )
  }

  function closeCreateUserModal() {
    if (createUserLoading) {
      return
    }

    setCreateUserModal(null)
    setCreateUserError('')
    setCreateUserConfirm('')
    setCreateUserOuOptions([])
    setCreateUserForm(
      getEmptyCreateUserForm('')
    )
  }

  async function submitCreateUser(event) {
    event.preventDefault()

    if (!createUserModal) {
      return
    }

    const firstName =
      createUserForm.first_name.trim()

    const lastName =
      createUserForm.last_name.trim()

    const samAccountName =
      createUserForm.sam_account_name.trim()

    const userPrincipalName =
      createUserForm.user_principal_name.trim()

    const targetOuDn =
      createUserForm.target_ou_dn.trim()

    const temporaryPassword =
      createUserForm.temporary_password.trim()

    const validationErrors =
      validateCreateUserForm(createUserForm)

    if (validationErrors.length > 0) {
      setCreateUserError(
        validationErrors.join('\n')
      )
      return
    }

    if (
      isAdProductionMode()
      && createUserConfirm !== 'PRODUCTION'
    ) {
      setCreateUserError(
        'Tape PRODUCTION pour confirmer '
        + 'la création réelle du compte.'
      )
      return
    }

    setCreateUserLoading(true)
    setCreateUserError('')

    try {
      const job = await runAdAdminJob({
        action: 'create_user',
        first_name: firstName,
        last_name: lastName,
        sam_account_name: samAccountName,
        user_principal_name:
          userPrincipalName,
        target_ou_dn: targetOuDn,
        temporary_password:
          temporaryPassword,
        description:
          createUserForm.description.trim(),
        enabled:
          Boolean(createUserForm.enabled),
        force_change_at_logon:
          Boolean(
            createUserForm.force_change_at_logon
          ),
        created_by:
          'react-ad-explorer'
      })

      const output = job?.output || {}

      const simulated =
        output?.simulated === true

      const destinationLabel =
        getAdminCreationOuDisplayLabel(
          targetOuDn
        )

      const message = cleanAdHistoryText(
        simulated
          ? `Simulation : ${firstName} ${lastName} serait créé dans ${destinationLabel}.`
          : `Utilisateur ${firstName} ${lastName} créé dans ${destinationLabel}.`
      )

      setCreateUserModal(null)
      setCreateUserError('')
      setCreateUserConfirm('')
      setCreateUserOuOptions([])
      setCreateUserForm(
        getEmptyCreateUserForm('')
      )

      await loadTree()

      if (selectedNode) {
        await loadNodeContent(
          selectedNode,
          viewType,
          { forceRefresh: true }
        )
      }

      await loadAdAdminHistory()

      setAdminSuccess(message)
      setStatus(message)
      setMessage?.(message)
    } catch (error) {
      const message =
        getCreateUserFriendlyError(
          error?.message
          || 'Erreur pendant la création utilisateur.'
        )

      setCreateUserError(message)
      setStatus(message)
      setMessage?.(message)
    } finally {
      setCreateUserLoading(false)
    }
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

  function resetCreateComputerForm() {
    setCreateComputerForm({
      name: '',
      target_ou_dn: COMPUTERS_DN,
      description: '',
      location: '',
      enabled: false
    })

    setCreateComputerConfirm('')
    setCreateComputerError('')
  }

  function openCreateComputerModal() {
    resetCreateComputerForm()
    setCreateComputerModal(true)
    loadAdAgentMode()
  }

  function closeCreateComputerModal() {
    if (createComputerLoading) return

    setCreateComputerModal(false)
    resetCreateComputerForm()
  }

  function updateCreateComputerField(name, value) {
    setCreateComputerForm(current => ({
      ...current,
      [name]: value
    }))

    setCreateComputerError('')
  }

  function getCreateComputerValidationError(
    form = createComputerForm
  ) {
    const name = String(form?.name || '')
      .trim()
      .toUpperCase()

    const targetOuDn = String(
      form?.target_ou_dn || ''
    ).trim()

    if (!name) {
      return 'Le nom de l’ordinateur est obligatoire.'
    }

    if (!/^[A-Z0-9-]{1,15}$/.test(name)) {
      return (
        'Le nom doit contenir 1 à 15 caractères : '
        + 'lettres A-Z, chiffres et tirets uniquement.'
      )
    }

    if (name.startsWith('-') || name.endsWith('-')) {
      return (
        'Le nom ne peut pas commencer ou finir '
        + 'par un tiret.'
      )
    }

    if (/^[0-9]+$/.test(name)) {
      return (
        'Le nom ne peut pas contenir uniquement '
        + 'des chiffres.'
      )
    }

    if (!targetOuDn) {
      return 'L’OU de destination est obligatoire.'
    }

    if (!/^OU=/i.test(targetOuDn)) {
      return 'La destination doit être une unité d’organisation.'
    }

    if (!isComputerManagedDn(targetOuDn)) {
      return (
        'La destination doit appartenir à '
        + 'OU=Computers,OU=EITAS.'
      )
    }

    return ''
  }

  async function submitCreateComputer(event) {
    event.preventDefault()

    const validationError =
      getCreateComputerValidationError()

    if (validationError) {
      setCreateComputerError(validationError)
      return
    }

    const name = createComputerForm.name
      .trim()
      .toUpperCase()

    const targetOuDn =
      createComputerForm.target_ou_dn.trim()

    const productionMode =
      String(adAgentMode).toLowerCase() === 'production'

    if (
      productionMode
      && createComputerConfirm !== 'PRODUCTION'
    ) {
      setCreateComputerError(
        'Tape PRODUCTION pour confirmer la création réelle.'
      )
      return
    }

    setCreateComputerLoading(true)
    setCreateComputerError('')

    try {
      const job = await runAdAdminJob({
        action: 'create_computer',
        name,
        target_ou_dn: targetOuDn,
        description:
          createComputerForm.description.trim(),
        location:
          createComputerForm.location.trim(),
        enabled:
          Boolean(createComputerForm.enabled),
        created_by: 'react-ad-explorer'
      })

      setCreateComputerModal(false)
      resetCreateComputerForm()

      await loadComputersView()

      setMessage?.(
        cleanAdHistoryText(
          job?.message
          || `${name} créé dans Active Directory.`
        )
      )
    } catch (error) {
      setCreateComputerError(
        cleanAdHistoryText(
          error?.message
          || 'Création de l’ordinateur impossible.'
        )
      )
    } finally {
      setCreateComputerLoading(false)
    }
  }


  function getAccountActionLabel(action) {
    const labels = {
      enable_account: 'Activer le compte',
      disable_account: 'Désactiver le compte',
      reset_password: 'Réinitialiser le mot de passe',
      unlock_account: 'Déverrouiller le compte'
    }

    return labels[action] || action
  }

  function getSelectedAccountEnabledState(target) {
    const candidates = [
      target?.enabled,
      target?.Enabled,
      target?.disabled === true ? false : null,
      target?.Disabled === true ? false : null
    ]

    for (const value of candidates) {
      if (value === true || String(value).toLowerCase() === 'true') return true
      if (value === false || String(value).toLowerCase() === 'false') return false
    }

    return null
  }

  function prepareAccountAction(action, target) {
    if (!isEitasManagedObject(target)) {
      const message =
        'Action bloquée : cet objet est hors du périmètre OU=EITAS et reste accessible uniquement en lecture.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

    const targetDn = getObjectDn(target)

    if (!targetDn) {
      setMessage?.('Impossible de préparer l’action : DN introuvable.')
      return
    }

    let resolvedAction = action

    if (action === 'toggle_enabled') {
      const enabled = getSelectedAccountEnabledState(target)

      if (enabled === null) {
        setMessage?.('État du compte inconnu : impossible de choisir automatiquement Activer/Désactiver.')
        return
      }

      resolvedAction = enabled ? 'disable_account' : 'enable_account'
    }

    setAccountActionModal({
      action: resolvedAction,
      target,
      targetName: getObjectName(target),
      targetDn
    })

    setAccountActionConfirm('')
    setAccountActionPassword('')
  }

  async function submitAccountAction() {
    if (!accountActionModal) return

    if (adAgentMode === 'Production' && accountActionConfirm !== 'PRODUCTION') {
      setMessage?.('Confirmation Production obligatoire : tape PRODUCTION.')
      return
    }

    if (accountActionModal.action === 'reset_password' && !accountActionPassword.trim()) {
      setMessage?.('Mot de passe temporaire obligatoire.')
      return
    }

    const payload = {
      action: accountActionModal.action,
      object_dn: accountActionModal.targetDn,
      created_by: 'react-admin'
    }

    if (accountActionModal.action === 'reset_password') {
      payload.temporary_password = accountActionPassword.trim()
      payload.force_change_at_logon = true
      payload.unlock_after_reset = true
    }

    try {
      setAccountActionLoading(true)
      await runAdAdminJob(payload)

      if (viewType === 'computers') {
        await loadComputersView()
      }

      setAccountActionModal(null)
      setAccountActionConfirm('')
      setMessage?.(`${getAccountActionLabel(accountActionModal.action)} envoyé à l’agent AD Admin.`)
    } catch (err) {
      setMessage?.(err?.message || 'Erreur action Compte ADUC.')
    } finally {
      setAccountActionLoading(false)
    }
  }

  async function runAdAdminJob(payload) {
    setAdminSuccess('')

    const created = await apiFetch('/api/ad-admin/jobs', {
      method: 'POST',
      body: JSON.stringify({
        ...payload,
        created_by: 'react-admin'
      })
    })

    const job = await pollAdAdminJob(created.job.id)
    await refreshAdAdminHistoryQuietly()

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
      await refreshAdAdminHistoryQuietly()

      if (!finalJob.success) {
        setMessage?.(finalJob.message || finalJob.output || 'Création AD en erreur.')
        return
      }

      setMessage?.(finalJob.message || 'Action AD terminée.')

      await loadTree()
      await loadNodeContent(
        selectedNode,
        viewType,
        { forceRefresh: true }
      )
    } catch (err) {
      setMessage?.(`Job AD Admin créé, en attente de l’agent principal : ${jobId}`)
    }
  }

  function cleanAdAdminMessage(value) {
    return cleanAdHistoryText(value)
  }

  async function submitMoveObject(event) {
    event.preventDefault()

    if (!moveModal) {
      return
    }

    const objectDn = getObjectDn(moveModal)
    const targetParentDn =
      moveTargetDn.trim()

    const validationError =
      getMoveValidationError(
        moveModal,
        targetParentDn
      )

    if (validationError) {
      setMoveOuError(validationError)
      setStatus(validationError)
      return
    }

    const confirmed =
      await confirmProductionAdAction(
        'Le déplacement de l’objet',
        `${getObjectName(moveModal)} vers ${targetParentDn}`
      )

    if (!confirmed) {
      return
    }

    setAdminLoading(true)
    setMoveOuError('')
    setStatus(
      'Déplacement Active Directory en cours...'
    )

    try {
      const job = await runAdAdminJob({
        action: 'move_object',
        object_identity: objectDn,
        target_parent_dn: targetParentDn,
        created_by: 'react-admin'
      })

      const output = job?.output || {}

      const message = cleanAdHistoryText(
        output.message
        || job?.message
        || 'Objet AD déplacé.'
      )

      setStatus(message)
      setMessage?.(message)

      setMoveModal(null)
      setMoveTargetDn('')
      setMoveOuOptions([])
      setMoveOuError('')
      setSelectedObject(null)

      await loadTree()

      if (viewType === 'computers') {
        await loadComputersView()
      } else if (selectedNode) {
        await loadNodeContent(
          selectedNode,
          viewType,
          { forceRefresh: true }
        )
      }

      await loadAdAdminHistory()
    } catch (error) {
      const message = cleanAdHistoryText(
        error?.message
        || 'Impossible de déplacer cet objet AD.'
      )

      setMoveOuError(message)
      setStatus(message)
      setMessage?.(message)
    } finally {
      setAdminLoading(false)
    }
  }


  useEffect(() => {
    refreshAll()
  }, [])

  const selectedNodeDn =
    getObjectDn(selectedNode)

  const adBreadcrumbs =
    buildAdBreadcrumbs(selectedNodeDn)

  const canNavigateToParent =
    Boolean(selectedNodeDn)
    && selectedNodeDn.toUpperCase()
      !== DOMAIN_DN.toUpperCase()
    && Boolean(getParentDn(selectedNodeDn))

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

              <button
                type="button"
                className={
                  viewType === 'computers'
                    ? 'active'
                    : ''
                }
                onClick={loadComputersView}
              >
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
                <button
                  type="button"
                  data-eitas-action="create-user-toolbar"
                  disabled={
                    !isEitasManagedObject(selectedNode)
                  }
                  title={
                    isEitasManagedObject(selectedNode)
                      ? 'Créer un utilisateur dans le périmètre EITAS'
                      : 'Sélectionne un objet du périmètre EITAS'
                  }
                  onClick={() =>
                    openCreateUser(selectedNode)
                  }
                >
                  👤 Créer un utilisateur
                </button>
              <button
                type="button"
                onClick={openCreateComputerModal}
              >
                💻 Créer un ordinateur
              </button>
              <button
                type="button"
                disabled={
                  !isEitasManagedObject(
                    contextMenu?.target ||
                    selectedObject ||
                    selectedNode
                  )
                }
                title={
                  isEitasManagedObject(
                    contextMenu?.target ||
                    selectedObject ||
                    selectedNode
                  )
                    ? 'Modifier l’objet sélectionné'
                    : 'Lecture seule : objet hors périmètre EITAS'
                }
                onClick={() => {
                  setContextMenu(null)
                  openUpdateObject(
                    contextMenu?.target ||
                    selectedObject ||
                    selectedNode
                  )
                }}
              >
                ✎ Modifier
              </button>
              <button
                type="button"
                className="danger"
                disabled={
                  !isEitasManagedObject(
                    contextMenu?.target ||
                    selectedObject ||
                    selectedNode
                  )
                }
                title={
                  isEitasManagedObject(
                    contextMenu?.target ||
                    selectedObject ||
                    selectedNode
                  )
                    ? 'Supprimer l’objet sélectionné'
                    : 'Lecture seule : objet hors périmètre EITAS'
                }
                onClick={() => {
                  setContextMenu(null)
                  openDeleteObject(
                    contextMenu?.target ||
                    selectedObject ||
                    selectedNode
                  )
                }}
              >
                🗑 Supprimer
              </button>
              <button type="button" onClick={openTestCleanupScanner}>🧹 Nettoyage tests</button>
              <button type="button" onClick={openAdActivityCenter}>📊 Activité AD</button>
              <button type="button" onClick={refreshAll}>⟳ Actualiser</button>
            </section>

            {adminSuccess && (
              <div
                className="aduc-admin-success-banner"
                role="status"
              >
                <span
                  className={
                    "aduc-admin-success-icon"
                  }
                >
                  ✓
                </span>

                <div>
                  <strong>
                    Création Active Directory terminée
                  </strong>

                  <p>{adminSuccess}</p>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    setAdminSuccess('')
                  }
                  aria-label={
                    "Fermer la confirmation"
                  }
                >
                  ×
                </button>
              </div>
            )}

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
              <span>Cherche dans tous les groupes et utilisateurs de API.LOCAL. Les objets hors OU=EITAS sont en lecture seule.</span>
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
                  <button
                    type="button"
                    className={`aduc-node system ${
                      viewType === 'computers'
                        ? 'selected'
                        : ''
                    }`}
                    onClick={loadComputersView}
                  >
                    › 💻 Computers
                  </button>
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
                  <div className="aduc-list-title">
                    <div className="aduc-list-navigation">
                      <button
                        type="button"
                        className="aduc-up-button"
                        onClick={navigateToParentNode}
                        disabled={!canNavigateToParent}
                        title={
                          canNavigateToParent
                            ? 'Remonter d’un niveau'
                            : 'Racine du domaine atteinte'
                        }
                      >
                        ↑ Remonter
                      </button>

                      <nav
                        className="aduc-breadcrumb"
                        aria-label={
                          "Chemin Active Directory"
                        }
                      >
                        {adBreadcrumbs.map(
                          (breadcrumb, index) => {
                            const isCurrent =
                              index
                              === adBreadcrumbs.length - 1

                            return (
                              <span
                                key={breadcrumb.dn}
                                className={
                                  isCurrent
                                    ? 'current'
                                    : ''
                                }
                              >
                                {index > 0 && (
                                  <i aria-hidden="true">
                                    ›
                                  </i>
                                )}

                                <button
                                  type="button"
                                  disabled={isCurrent}
                                  onClick={() =>
                                    navigateToAdDn(
                                      breadcrumb.dn
                                    )
                                  }
                                  title={
                                    breadcrumb.dn
                                  }
                                >
                                  {breadcrumb.label}
                                </button>
                              </span>
                            )
                          }
                        )}
                      </nav>
                    </div>

                    <h3>
                      {selectedNode?.name || 'Objet AD'}
                      {' '}
                      <span>
                        ({filteredViewItems.length}
                        {' '}
                        objet
                        {filteredViewItems.length > 1
                          ? 's'
                          : ''}
                        )
                      </span>
                    </h3>

                    <small>
                      {selectedNode?.canonical_name
                        || selectedNode
                          ?.distinguished_name
                        || '-'}
                    </small>
                  </div>

                  <div className="aduc-list-search">
                    <input
                      value={viewFilter}
                      onChange={event =>
                        setViewFilter(
                          event.target.value
                        )
                      }
                      placeholder={
                        "Rechercher dans cette vue..."
                      }
                    />

                    <button
                      type="button"
                      title="Rechercher"
                    >
                      ⌕
                    </button>

                    <button
                      type="button"
                      title="Options d’affichage"
                    >
                      ≡
                    </button>
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
                          if (isOuObject(item)) {
                            loadNodeContent(
                              item,
                              getNodeKind(item)
                            )
                            return
                          }

                          if (
                            getObjectType(item)
                              .includes('Groupe')
                          ) {
                            loadNodeContent(
                              item,
                              'groups'
                            )
                          }
                        }}
                        onContextMenu={event => openContextMenu(event, item, 'object')}
                      >
                        <span>
                          <i>
                            {getObjectType(item).includes('Groupe')
                              ? '👥'
                              : getObjectType(item).includes('Utilisateur')
                                ? '👤'
                                : getObjectType(item) === 'Ordinateur'
                                  ? '💻'
                                  : '📁'}
                          </i>
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
                onOpenUpdateObject={target => openUpdateObject(target)}
                onOpenRenameObject={target => openRenameObject(target)}
                onOpenDeleteObject={target => openDeleteObject(target)}
                onPrepareAccountAction={prepareAccountAction}
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



        {createUserModal && (
          <div
            className="aduc-modal-backdrop"
            data-eitas-modal="create-user"
            onClick={closeCreateUserModal}
          >
            <section
              className="aduc-modal aduc-create-user-modal"
              onClick={event =>
                event.stopPropagation()
              }
            >
              <header>
                <div>
                  <span>Active Directory</span>
                  <h3>Créer un utilisateur</h3>
                </div>

                <button
                  type="button"
                  onClick={closeCreateUserModal}
                  disabled={createUserLoading}
                  aria-label="Fermer"
                >
                  ×
                </button>
              </header>

              <form
                className="aduc-create-user-form"
                onSubmit={submitCreateUser}
              >
                <div
                  className={`aduc-account-action-warning ${
                    isAdProductionMode()
                      ? 'production'
                      : 'simulation'
                  }`}
                >
                  <strong>
                    {getAdAgentModeLabel()}
                  </strong>

                  <p>
                    {isAdProductionMode()
                      ? 'Le compte utilisateur sera réellement créé dans Active Directory.'
                      : 'Simulation active : aucun compte utilisateur réel ne sera créé.'}
                  </p>
                </div>

                <div className="aduc-create-user-grid">
                  <label>
                    <span>Prénom</span>

                    <input
                      type="text"
                      value={createUserForm.first_name}
                      onChange={event =>
                        updateCreateUserField(
                          'first_name',
                          event.target.value
                        )
                      }
                      autoFocus
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Nom</span>

                    <input
                      type="text"
                      value={createUserForm.last_name}
                      onChange={event =>
                        updateCreateUserField(
                          'last_name',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Identifiant AD</span>

                    <input
                      type="text"
                      value={
                        createUserForm.sam_account_name
                      }
                      onChange={event =>
                        updateCreateUserField(
                          'sam_account_name',
                          event.target.value.toLowerCase()
                        )
                      }
                      maxLength="20"
                      placeholder="prenom.nom"
                      autoComplete="off"
                      disabled={createUserLoading}
                    />

                    <small>
                      Maximum 20 caractères, sans espace
                      ni accent.
                    </small>
                  </label>

                  <label>
                    <span>UPN de connexion</span>

                    <input
                      type="text"
                      value={
                        createUserForm.user_principal_name
                      }
                      onChange={event =>
                        updateCreateUserField(
                          'user_principal_name',
                          event.target.value
                        )
                      }
                      placeholder="prenom.nom@API.LOCAL"
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label className="wide">
                    <span>OU de destination</span>

                    <select
                      value={
                        createUserForm.target_ou_dn
                      }
                      onChange={event =>
                        updateCreateUserField(
                          'target_ou_dn',
                          event.target.value
                        )
                      }
                      disabled={
                        createUserLoading
                        || createUserOuLoading
                      }
                    >
                      {createUserOuOptions.map(option => (
                        <option
                          key={option.dn}
                          value={option.dn}
                        >
                          {option.label}
                        </option>
                      ))}
                    </select>

                    <small>
                      Seules les OU situées sous
                      OU=EITAS sont proposées.
                    </small>
                  </label>

                  <label className="wide">
                    <span>
                      Mot de passe temporaire
                    </span>

                    <input
                      type="password"
                      value={
                        createUserForm.temporary_password
                      }
                      onChange={event =>
                        updateCreateUserField(
                          'temporary_password',
                          event.target.value
                        )
                      }
                      placeholder="Minimum 12 caractères"
                      autoComplete="new-password"
                      disabled={createUserLoading}
                    />

                    <small>
                      Majuscule, minuscule, chiffre et
                      caractère spécial obligatoires.
                    </small>
                  </label>

                  <label className="wide">
                    <span>Description</span>

                    <textarea
                      value={createUserForm.description}
                      onChange={event =>
                        updateCreateUserField(
                          'description',
                          event.target.value
                        )
                      }
                      rows="3"
                      placeholder="Fonction, service ou motif de création"
                      disabled={createUserLoading}
                    />
                  </label>
                </div>

                <div className="aduc-create-user-options">
                  <label className="aduc-create-user-toggle">
                    <input
                      type="checkbox"
                      checked={createUserForm.enabled}
                      onChange={event =>
                        updateCreateUserField(
                          'enabled',
                          event.target.checked
                        )
                      }
                      disabled={createUserLoading}
                    />

                    <span>
                      Activer immédiatement le compte
                    </span>
                  </label>

                  <label className="aduc-create-user-toggle">
                    <input
                      type="checkbox"
                      checked={
                        createUserForm
                          .force_change_at_logon
                      }
                      onChange={event =>
                        updateCreateUserField(
                          'force_change_at_logon',
                          event.target.checked
                        )
                      }
                      disabled={createUserLoading}
                    />

                    <span>
                      Exiger le changement du mot de
                      passe à la première connexion
                    </span>
                  </label>
                </div>

                <div className="aduc-create-user-summary">
                  <span>Compte préparé</span>

                  <strong>
                    {createUserForm.user_principal_name
                      || 'UPN en attente'}
                  </strong>

                  <small>
                    {getAdminCreationOuDisplayLabel(
                      createUserForm.target_ou_dn
                    )}
                  </small>
                </div>

                {isAdProductionMode() && (
                  <label className="aduc-create-user-production">
                    <span>
                      Confirmation Production
                    </span>

                    <input
                      type="text"
                      value={createUserConfirm}
                      onChange={event => {
                        setCreateUserConfirm(
                          event.target.value
                        )
                        setCreateUserError('')
                      }}
                      placeholder="Tape PRODUCTION"
                      autoComplete="off"
                      disabled={createUserLoading}
                    />

                    <small>
                      La saisie exacte est obligatoire
                      avant toute création réelle.
                    </small>
                  </label>
                )}

                {createUserError && (
                  <div
                    className="aduc-create-user-error"
                    role="alert"
                  >
                    {createUserError}
                  </div>
                )}

                <footer>
                  <button
                    type="button"
                    onClick={closeCreateUserModal}
                    disabled={createUserLoading}
                  >
                    Annuler
                  </button>

                  <button
                    type="submit"
                    disabled={
                      createUserLoading
                      || createUserOuLoading
                    }
                  >
                    {createUserLoading
                      ? 'Création en cours...'
                      : createUserOuLoading
                        ? 'Chargement des OU...'
                        : isAdProductionMode()
                          ? 'Créer dans Active Directory'
                          : 'Lancer la simulation'}
                  </button>
                </footer>
              </form>
            </section>
          </div>
        )}
      {createComputerModal && (
        <div
          className="aduc-modal-backdrop"
          onClick={closeCreateComputerModal}
        >
          <section
            className="aduc-modal aduc-create-computer-modal"
            onClick={event => event.stopPropagation()}
          >
            <header>
              <div>
                <span>Active Directory</span>
                <h3>Créer un ordinateur</h3>
              </div>

              <button
                type="button"
                onClick={closeCreateComputerModal}
                disabled={createComputerLoading}
              >
                ×
              </button>
            </header>

            <form
              className="aduc-create-computer-form"
              onSubmit={submitCreateComputer}
            >
              <div
                className={`aduc-account-action-warning ${
                  isAdProductionMode()
                    ? 'production'
                    : 'simulation'
                }`}
              >
                <strong>
                  {getAdAgentModeLabel()}
                </strong>

                <p>
                  {isAdProductionMode()
                    ? 'Le compte ordinateur sera réellement créé dans Active Directory.'
                    : 'Simulation active : aucun compte ordinateur réel ne sera créé.'}
                </p>
              </div>

              <div className="aduc-create-computer-grid">
                <label>
                  <span>Nom de l’ordinateur</span>

                  <input
                    type="text"
                    value={createComputerForm.name}
                    onChange={event =>
                      updateCreateComputerField(
                        'name',
                        event.target.value.toUpperCase()
                      )
                    }
                    maxLength="15"
                    placeholder="PC-EITAS-001"
                    autoFocus
                    disabled={createComputerLoading}
                  />

                  <small>
                    1 à 15 caractères : A-Z, chiffres et tirets.
                  </small>
                </label>

                <label>
                  <span>État initial du compte</span>

                  <select
                    value={
                      createComputerForm.enabled
                        ? 'enabled'
                        : 'disabled'
                    }
                    onChange={event =>
                      updateCreateComputerField(
                        'enabled',
                        event.target.value === 'enabled'
                      )
                    }
                    disabled={createComputerLoading}
                  >
                    <option value="disabled">
                      Désactivé — recommandé
                    </option>

                    <option value="enabled">
                      Activé
                    </option>
                  </select>
                </label>

                <label className="wide">
                  <span>OU de destination</span>

                  <select
                    value={createComputerForm.target_ou_dn}
                    onChange={event =>
                      updateCreateComputerField(
                        'target_ou_dn',
                        event.target.value
                      )
                    }
                    disabled={createComputerLoading}
                  >
                    {!computerOuOptions.some(
                      option =>
                        option.dn ===
                        createComputerForm.target_ou_dn
                    ) && (
                      <option
                        value={
                          createComputerForm.target_ou_dn
                        }
                      >
                        {getOuLabelFromDn(
                          createComputerForm.target_ou_dn
                        )} — personnalisée
                      </option>
                    )}

                    {computerOuOptions.map(option => (
                      <option
                        key={option.dn}
                        value={option.dn}
                      >
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <details className="wide aduc-create-user-advanced-dn">
                  <summary>
                    DN personnalisé / avancé
                  </summary>

                  <input
                    type="text"
                    className="mono"
                    value={createComputerForm.target_ou_dn}
                    onChange={event =>
                      updateCreateComputerField(
                        'target_ou_dn',
                        event.target.value
                      )
                    }
                    placeholder={COMPUTERS_DN}
                    disabled={createComputerLoading}
                  />
                </details>

                <label className="wide">
                  <span>Description</span>

                  <textarea
                    rows="3"
                    maxLength="1024"
                    value={createComputerForm.description}
                    onChange={event =>
                      updateCreateComputerField(
                        'description',
                        event.target.value
                      )
                    }
                    placeholder="Description du poste"
                    disabled={createComputerLoading}
                  />
                </label>

                <label>
                  <span>Emplacement physique</span>

                  <input
                    type="text"
                    maxLength="128"
                    value={createComputerForm.location}
                    onChange={event =>
                      updateCreateComputerField(
                        'location',
                        event.target.value
                      )
                    }
                    placeholder="Ex : Salle informatique"
                    disabled={createComputerLoading}
                  />
                </label>

                <div className="aduc-create-computer-summary">
                  <span>Compte généré</span>
                  <strong>
                    {createComputerForm.name
                      .trim()
                      .toUpperCase() || '—'}$
                  </strong>
                </div>

                {isAdProductionMode() && (
                  <label className="wide">
                    <span>Confirmation Production</span>

                    <input
                      type="text"
                      value={createComputerConfirm}
                      onChange={event => {
                        setCreateComputerConfirm(
                          event.target.value
                        )
                        setCreateComputerError('')
                      }}
                      placeholder="Tape PRODUCTION"
                      autoComplete="off"
                      disabled={createComputerLoading}
                    />

                    <small>
                      Cette confirmation est obligatoire
                      pour créer réellement le compte.
                    </small>
                  </label>
                )}
              </div>

              {createComputerError && (
                <div className="aduc-member-submit-error">
                  <strong>
                    Création impossible
                  </strong>

                  <span>{createComputerError}</span>
                </div>
              )}

              <footer className="aduc-modal-actions">
                <button
                  type="button"
                  onClick={closeCreateComputerModal}
                  disabled={createComputerLoading}
                >
                  Annuler
                </button>

                <button
                  type="submit"
                  className={
                    isAdProductionMode()
                      ? 'danger'
                      : ''
                  }
                  disabled={
                    createComputerLoading
                    || adAgentModeLoading
                    || Boolean(
                      getCreateComputerValidationError()
                    )
                    || (
                      isAdProductionMode()
                      && createComputerConfirm !== 'PRODUCTION'
                    )
                  }
                >
                  {createComputerLoading
                    ? 'Création...'
                    : adAgentModeLoading
                      ? 'Vérification du mode...'
                      : isAdProductionMode()
                        ? 'Créer en Production'
                        : 'Lancer la simulation'}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}

      {deleteModal && (
        <div
          className="aduc-modal-backdrop"
          onClick={() => {
            if (!loading) {
              setDeleteModal(null)
              setDeleteConfirmDn('')
              setDeleteError('')
            }
          }}
        >
          <section
            className="aduc-modal"
            onClick={event => event.stopPropagation()}
          >
            <header>
              <div>
                <span>Active Directory</span>
                <h3>Supprimer l’objet</h3>
              </div>

              <button
                type="button"
                onClick={() => {
                  setDeleteModal(null)
                  setDeleteConfirmDn('')
                  setDeleteError('')
                }}
                disabled={loading}
              >
                ×
              </button>
            </header>

            <form onSubmit={submitDeleteObject}>
              <div className="aduc-update-object-target">
                <div>
                  <span>Objet cible</span>
                  <strong>{getObjectName(deleteModal)}</strong>
                </div>

                <div>
                  <span>Type</span>
                  <strong>{getObjectType(deleteModal)}</strong>
                </div>

                <div className="wide">
                  <span>DN de l’objet</span>
                  <code>{getObjectDn(deleteModal)}</code>
                </div>
              </div>

              <div className="aduc-account-action-warning production">
                <strong>Suppression définitive</strong>

                <p>
                  Cette action supprimera réellement l’objet
                  dans Active Directory.
                </p>
              </div>

              <label className="aduc-account-action-field">
                <span>Confirmation par Distinguished Name</span>

                <input
                  type="text"
                  className="mono"
                  value={deleteConfirmDn}
                  onChange={event => {
                    setDeleteConfirmDn(event.target.value)
                    setDeleteError('')
                  }}
                  placeholder={getObjectDn(deleteModal)}
                  autoComplete="off"
                  autoFocus
                  disabled={loading}
                />

                <small>
                  Recopie le DN affiché au-dessus. La casse
                  des lettres n’a pas d’importance.
                </small>
              </label>

              {deleteError && (
                <div className="aduc-member-submit-error">
                  <strong>Suppression impossible</strong>
                  <span>{deleteError}</span>
                </div>
              )}

              <footer className="aduc-modal-actions">
                <button
                  type="button"
                  onClick={() => {
                    setDeleteModal(null)
                    setDeleteConfirmDn('')
                    setDeleteError('')
                  }}
                  disabled={loading}
                >
                  Annuler
                </button>

                <button
                  type="button"
                  className="danger"
                  onClick={submitDeleteObject}
                  disabled={
                    loading ||
                    !deleteConfirmDn.trim()
                  }
                >
                  {loading
                    ? 'Suppression...'
                    : 'Supprimer définitivement'}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}

      {moveModal && (
        <div
          className="aduc-modal-backdrop"
          onClick={closeMoveModal}
        >
          <section
            className="aduc-modal aduc-move-modal"
            onClick={event =>
              event.stopPropagation()
            }
          >
            <header>
              <div>
                <span>Active Directory</span>
                <h3>Déplacer l’objet</h3>
              </div>

              <button
                type="button"
                onClick={closeMoveModal}
                disabled={adminLoading}
              >
                ×
              </button>
            </header>

            <form onSubmit={submitMoveObject}>
              <div className="aduc-update-object-target">
                <div>
                  <span>Objet cible</span>
                  <strong>
                    {getObjectName(moveModal)}
                  </strong>
                </div>

                <div>
                  <span>Type</span>
                  <strong>
                    {getObjectType(moveModal)}
                  </strong>
                </div>

                <div className="wide">
                  <span>DN actuel</span>
                  <code>
                    {getObjectDn(moveModal)}
                  </code>
                </div>

                <div className="wide">
                  <span>OU actuelle</span>
                  <code>
                    {getMoveCurrentParentDn(
                      getObjectDn(moveModal)
                    )}
                  </code>
                </div>
              </div>

              <label className="aduc-account-action-field">
                <span>OU de destination</span>

                <select
                  key={
                    moveOuOptions
                      .map(option => option.dn)
                      .join('|')
                    || 'move-ou-loading'
                  }
                  value={moveTargetDn}
                  onChange={event => {
                    setMoveTargetDn(
                      event.target.value
                    )
                    setMoveOuError('')
                  }}
                  autoFocus
                  disabled={
                    adminLoading
                    || moveOuLoading
                  }
                >
                  <option value="" disabled>
                    {moveOuLoading
                      ? 'Chargement des OU...'
                      : 'Choisir une OU de destination'}
                  </option>

                  {!moveOuLoading
                    && moveTargetDn
                    && !moveOuOptions.some(
                      option =>
                        option.dn.toUpperCase()
                        === moveTargetDn
                          .toUpperCase()
                    )
                    && (
                    <option value={moveTargetDn}>
                      {getMoveOuDisplayLabel(
                        moveTargetDn
                      )} — personnalisée
                    </option>
                  )}

                  {moveOuOptions.map(option => (
                    <option
                      key={option.dn}
                      value={option.dn}
                    >
                      {option.label}
                    </option>
                  ))}
                </select>

                <small>
                  {moveOuLoading
                    ? 'Chargement de l’arbre Active Directory...'
                    : `${moveOuOptions.length} OU disponible${moveOuOptions.length > 1 ? 's' : ''}.`}
                </small>
              </label>

              <details className="aduc-create-user-advanced-dn">
                <summary>
                  DN personnalisé / avancé
                </summary>

                <input
                  type="text"
                  className="mono"
                  value={moveTargetDn}
                  onChange={event => {
                    setMoveTargetDn(
                      event.target.value
                    )
                    setMoveOuError('')
                  }}
                  placeholder="OU=Destination,OU=EITAS,DC=API,DC=LOCAL"
                  disabled={adminLoading}
                />
              </details>

              <div className="aduc-move-destination-summary">
                <span>Nouvel emplacement</span>

                <strong>
                  {moveTargetDn
                    ? getMoveOuDisplayLabel(
                        moveTargetDn
                      )
                    : 'Aucune destination'}
                </strong>

                <code>
                  {moveTargetDn || '—'}
                </code>
              </div>

              <div
                className={`aduc-account-action-warning ${
                  isAdProductionMode()
                    ? 'production'
                    : 'simulation'
                }`}
              >
                <strong>
                  {getAdAgentModeLabel()}
                </strong>

                <p>
                  {isAdProductionMode()
                    ? 'Le déplacement modifiera réellement Active Directory.'
                    : 'Simulation active : aucun objet réel ne sera déplacé.'}
                </p>
              </div>

              {moveOuError && (
                <div className="aduc-member-submit-error">
                  <strong>
                    Déplacement impossible
                  </strong>

                  <span>{moveOuError}</span>
                </div>
              )}

              <footer className="aduc-modal-actions">
                <button
                  type="button"
                  onClick={closeMoveModal}
                  disabled={adminLoading}
                >
                  Annuler
                </button>

                <button
                  type="submit"
                  disabled={
                    adminLoading
                    || moveOuLoading
                    || adAgentModeLoading
                    || Boolean(
                      getMoveValidationError()
                    )
                  }
                >
                  {adminLoading
                    ? 'Déplacement...'
                    : moveOuLoading
                      ? 'Chargement des OU...'
                      : adAgentModeLoading
                        ? 'Vérification du mode...'
                        : 'Déplacer'}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}

      {renameModal && (
        <div
          className="aduc-modal-backdrop"
          onClick={() => {
            if (!loading) {
              setRenameModal(null)
              setRenameNewName('')
            }
          }}
        >
          <section
            className="aduc-modal"
            onClick={event => event.stopPropagation()}
          >
            <header>
              <div>
                <span>Active Directory</span>
                <h3>Renommer l’objet</h3>
              </div>

              <button
                type="button"
                onClick={() => {
                  setRenameModal(null)
                  setRenameNewName('')
                }}
                disabled={loading}
              >
                ×
              </button>
            </header>

            <form onSubmit={submitRenameObject}>
              <div className="aduc-update-object-target">
                <div>
                  <span>Objet cible</span>
                  <strong>{getObjectName(renameModal)}</strong>
                </div>

                <div>
                  <span>Type</span>
                  <strong>{getObjectType(renameModal)}</strong>
                </div>

                <div className="wide">
                  <span>DN actuel</span>
                  <code>{getObjectDn(renameModal)}</code>
                </div>
              </div>

              <label className="aduc-account-action-field">
                <span>Nouveau nom</span>
                <input
                  type="text"
                  value={renameNewName}
                  onChange={event =>
                    setRenameNewName(event.target.value)
                  }
                  placeholder="Saisir le nouveau nom"
                  autoFocus
                  disabled={loading}
                />
              </label>

              <p className="aduc-update-object-help">
                Le renommage sera exécuté réellement dans Active
                Directory par le worker AD Admin.
              </p>

              <footer className="aduc-modal-actions">
                <button
                  type="button"
                  onClick={() => {
                    setRenameModal(null)
                    setRenameNewName('')
                  }}
                  disabled={loading}
                >
                  Annuler
                </button>

                <button
                  type="submit"
                  disabled={
                    loading ||
                    !renameNewName.trim() ||
                    renameNewName.trim() ===
                      String(getObjectName(renameModal) || '').trim()
                  }
                >
                  {loading
                    ? 'Renommage...'
                    : 'Renommer'}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}

      {updateModal && (
        <div
          className="aduc-modal-backdrop"
          onClick={() => !loading && setUpdateModal(null)}
        >
          <section
            className="aduc-modal aduc-update-object-modal"
            onClick={event => event.stopPropagation()}
          >
            <header>
              <div>
                <span>Active Directory</span>
                <h3>Modifier les propriétés</h3>
              </div>

              <button
                type="button"
                onClick={() => setUpdateModal(null)}
                disabled={loading}
              >
                ×
              </button>
            </header>

            <form onSubmit={submitUpdateObject}>
              <div className="aduc-update-object-target">
                <div>
                  <span>Objet cible</span>
                  <strong>{getObjectName(updateModal)}</strong>
                </div>

                <div>
                  <span>Type</span>
                  <strong>{getObjectType(updateModal)}</strong>
                </div>

                <div className="wide">
                  <span>DN</span>
                  <code>{getObjectDn(updateModal)}</code>
                </div>
              </div>

              <p className="aduc-update-object-help">
                Seuls les champs modifiés seront envoyés au worker.
                Vider un champ supprimera l’attribut correspondant
                dans Active Directory.
              </p>

              <div className="aduc-update-object-sections">
                <section>
                  <h4>Informations générales</h4>

                  <div className="aduc-update-object-grid">
                    {!isUpdateComputerTarget(updateModal) && (
                      <label>
                        <span>Nom d’affichage</span>
                        <input
                          type="text"
                          value={updateForm.displayName || ''}
                          onChange={event => updateObjectFormField(
                            'displayName',
                            event.target.value
                          )}
                          disabled={loading}
                        />
                      </label>
                    )}

                    {isUpdateComputerTarget(updateModal) && (
                      <label>
                        <span>Emplacement</span>
                        <input
                          type="text"
                          value={updateForm.location || ''}
                          onChange={event => updateObjectFormField(
                            'location',
                            event.target.value
                          )}
                          placeholder="Ex : Salle informatique"
                          disabled={loading}
                        />
                      </label>
                    )}

                    <label className="wide">
                      <span>Description</span>
                      <textarea
                        rows="3"
                        value={updateForm.description || ''}
                        onChange={event => updateObjectFormField(
                          'description',
                          event.target.value
                        )}
                        disabled={loading}
                      />
                    </label>
                  </div>
                </section>

                {isUpdateUserTarget(updateModal) && (
                  <>
                    {[
                      {
                        title: 'Organisation',
                        fields: [
                          ['title', 'Titre / poste'],
                          ['department', 'Service'],
                          ['division', 'Division'],
                          ['company', 'Société'],
                          [
                            'physicalDeliveryOfficeName',
                            'Bureau'
                          ]
                        ]
                      },
                      {
                        title: 'Informations RH',
                        fields: [
                          ['employeeID', 'Employee ID'],
                          [
                            'employeeNumber',
                            'Numéro employé'
                          ],
                          [
                            'manager',
                            'Manager — Distinguished Name',
                            true
                          ]
                        ]
                      },
                      {
                        title: 'Coordonnées',
                        fields: [
                          ['mail', 'E-mail'],
                          [
                            'telephoneNumber',
                            'Téléphone'
                          ],
                          ['mobile', 'Mobile'],
                          [
                            'streetAddress',
                            'Adresse',
                            true
                          ],
                          ['postalCode', 'Code postal'],
                          ['l', 'Ville'],
                          [
                            'st',
                            'Région / département'
                          ],
                          ['co', 'Pays']
                        ]
                      }
                    ].map(section => (
                      <section key={section.title}>
                        <h4>{section.title}</h4>

                        <div className="aduc-update-object-grid">
                          {section.fields.map(
                            ([name, label, wide]) => {
                              if (name === 'manager') {
                                return (
                                  <label
                                    key={name}
                                    className="wide aduc-manager-field"
                                  >
                                    <span>{label}</span>

                                    <div className="aduc-manager-current-row">
                                      <input
                                        className="mono"
                                        value={updateForm.manager || ''}
                                        placeholder="Aucun manager défini"
                                        readOnly
                                        disabled={loading}
                                      />

                                      <button
                                        type="button"
                                        className="aduc-manager-clear-button"
                                        onClick={clearManagerSelection}
                                        disabled={
                                          loading ||
                                          !updateForm.manager
                                        }
                                      >
                                        Retirer
                                      </button>
                                    </div>

                                    <div className="aduc-member-picker-row">
                                      <input
                                        value={managerSearchQuery}
                                        onChange={event => {
                                          setManagerSearchQuery(
                                            event.target.value
                                          )
                                          setManagerSearchResults([])
                                          setManagerSearchError('')
                                        }}
                                        onKeyDown={event => {
                                          if (event.key === 'Enter') {
                                            event.preventDefault()
                                            searchManagerCandidates()
                                          }
                                        }}
                                        placeholder="Nom, identifiant ou e-mail du manager..."
                                        disabled={
                                          loading ||
                                          managerSearchLoading
                                        }
                                      />

                                      <button
                                        type="button"
                                        className="aduc-member-search-button"
                                        onClick={searchManagerCandidates}
                                        disabled={
                                          loading ||
                                          managerSearchLoading ||
                                          managerSearchQuery.trim().length < 2
                                        }
                                      >
                                        {managerSearchLoading
                                          ? 'Recherche...'
                                          : 'Rechercher'}
                                      </button>
                                    </div>

                                    {managerSearchError && (
                                      <div className="aduc-member-search-error">
                                        {managerSearchError}
                                      </div>
                                    )}

                                    {managerSearchResults.length > 0 && (
                                      <div className="aduc-member-search-results aduc-manager-search-results">
                                        {managerSearchResults.map(
                                          candidate => {
                                            const candidateDn =
                                              getManagerCandidateDn(candidate)

                                            return (
                                              <button
                                                type="button"
                                                key={candidateDn}
                                                data-kind-label="Manager possible"
                                                onClick={() =>
                                                  selectManagerCandidate(
                                                    candidate
                                                  )
                                                }
                                              >
                                                <strong>
                                                  {getMemberCandidateTitle(
                                                    candidate
                                                  )}
                                                </strong>

                                                <small>
                                                  {getMemberCandidateSubtitle(
                                                    candidate
                                                  )}
                                                </small>
                                              </button>
                                            )
                                          }
                                        )}
                                      </div>
                                    )}

                                    <small>
                                      Recherche dans le domaine API.LOCAL.
                                      L’utilisateur en cours de modification
                                      est automatiquement exclu. Seuls
                                      les comptes actifs sont proposés.
                                    </small>
                                  </label>
                                )
                              }

                              return (
                                <label
                                  key={name}
                                  className={wide ? 'wide' : ''}
                                >
                                  <span>{label}</span>

                                  <input
                                    type={
                                      name === 'mail'
                                        ? 'email'
                                        : 'text'
                                    }
                                    value={updateForm[name] || ''}
                                    onChange={event =>
                                      updateObjectFormField(
                                        name,
                                        event.target.value
                                      )
                                    }
                                    disabled={loading}
                                  />
                                </label>
                              )
                            }
                          )}
                        </div>
                      </section>
                    ))}
                  </>
                )}
              </div>

              <footer className="aduc-modal-actions">
                <button
                  type="button"
                  onClick={() => setUpdateModal(null)}
                  disabled={loading}
                >
                  Annuler
                </button>

                <button
                  type="submit"
                  disabled={loading}
                >
                  {loading
                    ? 'Enregistrement...'
                    : 'Enregistrer les modifications'}
                </button>
              </footer>
            </form>
          </section>
        </div>
      )}
      {accountActionModal && (
        <div className="aduc-modal-backdrop" onClick={() => !accountActionLoading && setAccountActionModal(null)}>
          <section className="aduc-modal aduc-account-action-modal" onClick={event => event.stopPropagation()}>
            <header>
              <div>
                <span>Action Compte ADUC</span>
                <h3>{getAccountActionLabel(accountActionModal.action)}</h3>
              </div>

              <button type="button" onClick={() => setAccountActionModal(null)} disabled={accountActionLoading}>×</button>
            </header>

            <div className={`aduc-account-action-warning ${adAgentMode === 'Production' ? 'production' : 'simulation'}`}>
              <strong>Mode agent : {adAgentMode}</strong>
              <p>
                {adAgentMode === 'Production'
                  ? 'Cette action modifiera réellement Active Directory.'
                  : 'Simulation active : aucune modification réelle ne sera appliquée dans Active Directory.'}
              </p>
            </div>

            <div className="aduc-account-action-target">
              <div>
                <span>Objet cible</span>
                <strong>{accountActionModal.targetName}</strong>
              </div>

              <div>
                <span>DN</span>
                <code>{accountActionModal.targetDn}</code>
              </div>
            </div>

            {accountActionModal.action === 'reset_password' && (
              <label className="aduc-account-action-field">
                <span>Mot de passe temporaire</span>
                <input
                  type="text"
                  value={accountActionPassword}
                  onChange={event => setAccountActionPassword(event.target.value)}
                  placeholder="Mot de passe temporaire"
                  disabled={accountActionLoading}
                />
                <small>Le changement au prochain logon et le déverrouillage après reset seront demandés.</small>
              </label>
            )}

            {adAgentMode === 'Production' && (
              <label className="aduc-account-action-field">
                <span>Confirmation Production</span>
                <input
                  type="text"
                  value={accountActionConfirm}
                  onChange={event => setAccountActionConfirm(event.target.value)}
                  placeholder="Tape PRODUCTION"
                  disabled={accountActionLoading}
                />
              </label>
            )}

            <footer className="aduc-modal-actions">
              <button type="button" onClick={() => setAccountActionModal(null)} disabled={accountActionLoading}>
                Annuler
              </button>

              <button
                type="button"
                className={adAgentMode === 'Production' ? 'danger' : ''}
                onClick={submitAccountAction}
                disabled={accountActionLoading || (adAgentMode === 'Production' && accountActionConfirm !== 'PRODUCTION')}
              >
                {accountActionLoading ? 'Envoi...' : adAgentMode === 'Production' ? 'Confirmer en Production' : 'Lancer en Simulation'}
              </button>
            </footer>
          </section>
        </div>
      )}

      <AdActivityModal
        open={adActivityModal}
        activity={adActivity}
        loading={adAdminHistoryLoading}
        error={adAdminHistoryError}
        onClose={() => setAdActivityModal(false)}
        onRefresh={refreshAdAdminHistoryQuietly}
        onSelectJob={setSelectedAdAdminHistoryJob}
      />

            <AdHistoryDetailModal
        job={selectedAdAdminHistoryJob}
        activity={adActivity}
        onClose={() => setSelectedAdAdminHistoryJob(null)}
      />

      <TestCleanupModal
        open={testCleanupModal}
        cleanup={testCleanup}
        isProduction={isAdProductionMode()}
        onClose={() => setTestCleanupModal(false)}
      />

      <AdminCreationModal
        creation={{
          ...adAdminCreation,
          loading,
          adminLoading,
          adAgentModeLoading,
          getAdAgentModeLabel,
          isAdProductionMode,
        }}
      />

      <AddMemberModal
        member={groupMembers}
      />

      <AdContextMenu
        menu={{
          contextMenu,
          actionSoon,
          setContextMenu,
          openMoveObject,
          selectedObject,
          selectedNode,
          openSearchOuModal,
          openNewObjectMenu,
          openCreateOu,
          openCreateGroup,
          openCreateUser,
          openUpdateObject,
          openRenameObject,
          openDeleteObject,
          loadNodeContent,
          viewType,
          setMessage,
          openProperties,
        }}
      />

    </div>
  )
}
