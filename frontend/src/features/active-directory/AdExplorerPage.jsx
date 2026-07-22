import {
  useEffect,
  useMemo,
  useRef,
  useState } from 'react'

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
  splitLdapDn,
  getOuLabelFromDn,
  } from './utils/adExplorerCore'

import ObjectDetailsPanel from './components/ObjectDetailsPanel'
import AdObjectPropertiesModal from './components/AdObjectPropertiesModal'
import AdActivityModal from './components/AdActivityModal'
import AdHistoryDetailModal from './components/AdHistoryDetailModal'
import TestCleanupModal from './components/TestCleanupModal'
import AdminCreationModal from './components/AdminCreationModal'
import AddMemberModal from './components/AddMemberModal'
import AdContextMenu from './components/AdContextMenu'
import UpdateObjectModal from './components/UpdateObjectModal'
import CreateUserModal from './components/CreateUserModal'
import CreateComputerModal from './components/CreateComputerModal'
import DeleteObjectModal from './components/DeleteObjectModal'
import AccountActionModal from './components/AccountActionModal'
import MoveObjectModal from './components/MoveObjectModal'
import RenameObjectModal from './components/RenameObjectModal'
import useAdActivity from './hooks/useAdActivity'
import useTestCleanup from './hooks/useTestCleanup'
import useAdAdminCreation from './hooks/useAdAdminCreation'
import useAdGroupMembers from './hooks/useAdGroupMembers'
import useAdObjectDeletion from './hooks/useAdObjectDeletion'
import useAdAccountActions from './hooks/useAdAccountActions'
import useAdComputerCreation from './hooks/useAdComputerCreation'
import useAdUserCreation from './hooks/useAdUserCreation'
import useAdObjectRename from './hooks/useAdObjectRename'
import useAdObjectUpdate from './hooks/useAdObjectUpdate'
import useAdObjectMove from './hooks/useAdObjectMove'
import useAdSnapshot from './hooks/useAdSnapshot'
import {
  dedupeCreateUserOuOptions,
  getCreateUserSearchBaseDn,
  sortCreateUserOuOptions,
} from './utils/adCreationOptions'

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

  const adSnapshot = useAdSnapshot({
    apiFetch,
    intervalMs: 5000,
  })

  const adDomainCatalog = useAdSnapshot({
    apiFetch,
    endpoint: '/api/ad-domain-catalog',
    intervalMs: 15000,
    invalidMessage:
      'Catalogue Active Directory du domaine invalide.',
    loadErrorMessage:
      'Chargement du catalogue Active Directory du domaine impossible.',
  })

  const groupMembers = useAdGroupMembers({
    setMessage,
    setStatus,
    setContextMenu,
    adSnapshot,
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

  const objectDeletion = useAdObjectDeletion({
    setMessage,
    setStatus,
    setContextMenu,
    setSelectedObject,
    selectedNode,
    viewType,
    setLoading,
    runAdAdminJob,
    loadTree,
    loadNodeContent,
    loadAdAdminHistory,
    loadComputersView,
    normalizeDeleteConfirmationDn,
    cleanAdHistoryText,
  })

  const {
    openDeleteObject,
  } = objectDeletion
  const [adAgentMode, setAdAgentMode] = useState('Inconnu')

  const accountActions = useAdAccountActions({
    setMessage,
    setStatus,
    setContextMenu,
    adAgentMode,
    viewType,
    runAdAdminJob,
    loadComputersView,
    getSelectedAccountEnabledState,
  })

  const {
    prepareAccountAction,
  } = accountActions

  const computerCreation = useAdComputerCreation({
    adAgentMode,
    loadAdAgentMode,
    runAdAdminJob,
    loadComputersView,
    setMessage,
    cleanAdHistoryText,
    isComputerManagedDn,
    COMPUTERS_DN,
  })

  const {
    openCreateComputerModal,
  } = computerCreation
  const [adAgentModeLoading, setAdAgentModeLoading] = useState(false)
  const [adminLoading, setAdminLoading] = useState(false)
  const [adminSuccess, setAdminSuccess] = useState('')

  const adAdminCreation = useAdAdminCreation({
    apiFetch,
    setMessage,
    setStatus,
    setContextMenu,
    loadAdAgentMode,
    waitForAdExplorerJob,
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
    splitLdapDn,
  })

  const {
    getAdminCreationOuDisplayLabel,
    normalizeAdminCreationOptions,
    getCreateAdminParentDn,
    openCreateOu,
    openCreateGroup,
  } = adAdminCreation

  const userCreation = useAdUserCreation({
    apiFetch,
    waitForAdExplorerJob,
    isOuDn,
    getSuggestedSamAccountName,
    getSuggestedUserPrincipalName,
    normalizeAdminCreationOptions,
    getCreateAdminParentDn,
    getAdminCreationOuDisplayLabel,
    loadAdAgentMode,
    isAdProductionMode,
    runAdAdminJob,
    loadTree,
    loadNodeContent,
    loadAdAdminHistory,
    setMessage,
    setStatus,
    setContextMenu,
    setAdminSuccess,
    selectedNode,
    viewType,
  })

  const {
    openCreateUser,
  } = userCreation

  const objectRename = useAdObjectRename({
    setMessage,
    setStatus,
    setContextMenu,
    setLoading,
    runAdAdminJob,
    loadTree,
    loadComputersView,
    loadNodeContent,
    loadAdAdminHistory,
    selectedNode,
    viewType,
  })

  const {
    openRenameObject,
  } = objectRename

  const objectUpdate = useAdObjectUpdate({
    setMessage,
    setStatus,
    setContextMenu,
    setLoading,
    runJob,
    adDomainCatalog,
    runAdAdminJob,
    loadTree,
    loadComputersView,
    loadNodeContent,
    loadAdAdminHistory,
    selectedNode,
    viewType,
    getMemberCandidateTitle: groupMembers.getMemberCandidateTitle,
  })

  const {
    openUpdateObject,
  } = objectUpdate

  const objectMove = useAdObjectMove({
    apiFetch,
    treeItems,
    setSelectedObject,
    setMessage,
    setStatus,
    setContextMenu,
    adminLoading,
    setAdminLoading,
    loadAdAgentMode,
    waitForAdExplorerJob,
    getOuPathLabelFromDn,
    isOuDn,
    confirmProductionAdAction,
    runAdAdminJob,
    loadTree,
    loadComputersView,
    loadNodeContent,
    loadAdAdminHistory,
    selectedNode,
    viewType,
  })

  const {
    openMoveObject,
  } = objectMove
  const [globalAdSearch, setGlobalAdSearch] = useState('')
  const [globalAdSearchLoading, setGlobalAdSearchLoading] = useState(false)
  const testCleanup = useTestCleanup({
    apiFetch,
    selectedNode,
    waitForAdExplorerJob,
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

  async function loadTree(options = {}) {
    const snapshotOus =
      await adSnapshot.getOus({
        force: Boolean(options.forceRefresh),
      })

    if (Array.isArray(snapshotOus)) {
      setTreeItems(snapshotOus)
      return snapshotOus
    }

    const ous = await runJob(
      'list_ous',
      {
        limit: 500,
      }
    )

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

    const snapshotItems =
      await adSnapshot.getChildren(
        baseDn,
        {
          force: forceRefresh,
        }
      )

    if (Array.isArray(snapshotItems)) {
      setLoading(false)
      setViewItems([...snapshotItems])
      setStatus(
        `Snapshot Active Directory : ${snapshotItems.length} objet(s)`
      )
      return snapshotItems
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
        loadTree({
          forceRefresh: true,
        }),
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

  async function loadGroupMembers(
    target = selectedObject,
    options = {}
  ) {
    if (
      !target ||
      !isGroupObject(target)
    ) {
      return
    }

    const identity =
      target.sam_account_name ||
      target.name ||
      getObjectDn(target)

    if (!identity) {
      setMembersError(
        'Identité groupe introuvable.'
      )
      return
    }

    const forceJob =
      Boolean(options.forceJob)

    setMembersLoading(true)
    setMembersError('')

    try {
      let members = null

      if (!forceJob) {
        members =
          await adSnapshot.getGroupMembers(
            target,
            {
              force: Boolean(
                options.forceSnapshot
              ),
            }
          )
      }

      if (!Array.isArray(members)) {
        const parentDn =
          getParentDn(
            getObjectDn(target)
          ) ||
          GROUPS_DN

        members = await runJob(
          'get_group_members',
          {
            query: identity,
            baseDn: parentDn,
            limit: 500,
          }
        )
      }

      setObjectMembers(members)

      if (!options.silent) {
        setMessage?.(
          `Membres chargés pour ${
            target.name ||
            identity
          }.`
        )
      }

      return members
    } catch (err) {
      setObjectMembers([])

      setMembersError(
        err.message ||
        'Impossible de charger les membres du groupe.'
      )

      setMessage?.(
        err.message ||
        'Impossible de charger les membres du groupe.'
      )

      return null
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

  async function searchInOuSimple(
    target,
    forcedQuery = ''
  ) {
    const base =
      target ||
      selectedNode

    const baseDn =
      getObjectDn(base)

    if (!baseDn) {
      setStatus(
        'DN introuvable pour cette recherche.'
      )
      return
    }

    const query =
      forcedQuery ||
      window.prompt(
        `Rechercher dans :\n${baseDn}`
      )

    if (
      !query ||
      !query.trim()
    ) {
      return
    }

    const search = query.trim()

    setContextMenu(null)
    setLoading(true)

    try {
      let uniqueResults =
        await adSnapshot.search({
          query: search,
          baseDn,
          recursive: true,
          limit: 2000,
          types: [
            'ou',
            'group',
            'user',
          ],
        })

      if (!Array.isArray(uniqueResults)) {
        const jobs =
          await Promise.allSettled([
            runJob(
              'list_ous',
              {
                baseDn,
                recursive: true,
                limit: 500,
              }
            ),
            runJob(
              'list_groups',
              {
                baseDn,
                recursive: true,
                limit: 1000,
              }
            ),
            runJob(
              'search_users',
              {
                query: search,
                baseDn,
                recursive: true,
                limit: 500,
              }
            ),
          ])

        const collected = []

        jobs.forEach(
          (
            result,
            index
          ) => {
            if (
              result.status !==
              'fulfilled'
            ) {
              return
            }

            const items =
              extractExplorerItems(
                result.value
              )

            if (index === 2) {
              collected.push(
                ...items
              )
            } else {
              collected.push(
                ...items.filter(item =>
                  itemMatchesOuSearch(
                    item,
                    search
                  )
                )
              )
            }
          }
        )

        const seen = new Set()

        uniqueResults =
          collected.filter(item => {
            const key =
              getObjectDn(item) ||
              item?.sam_account_name ||
              item?.name

            if (!key) {
              return true
            }

            if (seen.has(key)) {
              return false
            }

            seen.add(key)
            return true
          })
      }

      setSelectedNode({
        name:
          `Recherche : ${search}`,
        type: 'search',
        distinguished_name: baseDn,
        dn: baseDn,
        canonical_name:
          `Recherche dans ${baseDn}`,
      })

      setViewType('search')
      setViewItems(uniqueResults)
      setSelectedObject(null)
      setObjectMembers([])
      setMembersError('')

      setStatus(
        `${uniqueResults.length} résultat(s) trouvé(s)`
      )
    } catch (err) {
      setStatus(
        err.message ||
        'Erreur pendant la recherche AD.'
      )
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
      let items = await adDomainCatalog.search({
        query: '',
        baseDn: DOMAIN_DN,
        recursive: true,
        types: ['computer'],
        limit: 1000,
      })

      const loadedFromCatalog =
        Array.isArray(items)

      if (!loadedFromCatalog) {
        const computers = await runJob(
          'list_computers',
          {
            query: '',
            baseDn: DOMAIN_DN,
            recursive: true,
            limit: 1000
          }
        )

        items = extractExplorerItems(
          computers
        )
      }

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
        loadedFromCatalog
          ? `${items.length} ordinateur(s) chargé(s) depuis le catalogue du domaine`
          : `${items.length} ordinateur(s) Active Directory chargé(s)`
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

      let results = await adDomainCatalog.search({
        query,
        baseDn,
        recursive: true,
        types: [
          'user',
          'group',
          'computer',
        ],
        limit: 2000,
      })

      const loadedFromCatalog =
        Array.isArray(results)

      if (!loadedFromCatalog) {
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

        results = []

        if (usersResult.status === 'fulfilled') {
          results.push(
            ...extractExplorerItems(
              usersResult.value
            )
          )
        }

        if (groupsResult.status === 'fulfilled') {
          const groups = extractExplorerItems(
            groupsResult.value
          )

          results.push(
            ...groups.filter(group => [
              group?.name,
              group?.sam_account_name,
              group?.description,
              group?.distinguished_name,
              group?.dn
            ]
              .filter(Boolean)
              .some(value =>
                String(value)
                  .toLowerCase()
                  .includes(lowered)
              )
            )
          )
        }

        if (computersResult.status === 'fulfilled') {
          results.push(
            ...extractExplorerItems(
              computersResult.value
            )
          )
        }
      }

      const seen = new Set()

      const uniqueResults = results.filter(item => {
        const key =
          getObjectDn(item) ||
          item?.sam_account_name ||
          item?.name

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

      setStatus(
        loadedFromCatalog
          ? `${uniqueResults.length} résultat(s) pour ${query} depuis le catalogue du domaine`
          : `${uniqueResults.length} résultat(s) pour ${query}`
      )
    } catch (error) {
      setStatus(
        error.message ||
        'Recherche globale AD impossible.'
      )
    } finally {
      setGlobalAdSearchLoading(false)
    }
  }



  function normalizeDeleteConfirmationDn(value) {
    return String(value || '')
      .trim()
      .toUpperCase()
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


  useEffect(() => {
    if (
      !adSnapshot.snapshotRevision ||
      !adSnapshot.snapshotIsUsable
    ) {
      return
    }

    nodeContentCacheRef.current.clear()

    const snapshotOus =
      adSnapshot.getOusSync()

    setTreeItems(snapshotOus)

    const selectedNodeDn =
      getObjectDn(selectedNode)

    if (
      !adSnapshot.canServeDn(
        selectedNodeDn
      ) ||
      viewType === 'computers' ||
      viewType === 'search'
    ) {
      return
    }

    const snapshotItems =
      adSnapshot.getChildrenSync(
        selectedNodeDn
      )

    if (!Array.isArray(snapshotItems)) {
      return
    }

    nodeContentRequestIdRef.current += 1
    setViewItems([...snapshotItems])

    setSelectedObject(previous => {
      if (!previous) {
        return null
      }

      const previousDn = String(
        getObjectDn(previous) || ''
      ).toLowerCase()

      if (!previousDn) {
        return null
      }

      return (
        snapshotItems.find(item =>
          String(
            getObjectDn(item) || ''
          ).toLowerCase() === previousDn
        ) ||
        null
      )
    })
  }, [adSnapshot.snapshotRevision])

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

                          openProperties(item)
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



      <CreateUserModal
        creation={{
          ...userCreation,
          getAdAgentModeLabel,
          isAdProductionMode,
          getAdminCreationOuDisplayLabel,
        }}
      />

      <CreateComputerModal
        creation={{
          ...computerCreation,
          getAdAgentModeLabel,
          isAdProductionMode,
          computerOuOptions,
          getOuLabelFromDn,
          COMPUTERS_DN,
          adAgentModeLoading,
        }}
      />

      <AdObjectPropertiesModal
        object={propertiesModal}
        selectedNode={selectedNode}
        onClose={() => setPropertiesModal(null)}
        update={{
          ...objectUpdate,
          loading,
          getMemberCandidateTitle:
            groupMembers.getMemberCandidateTitle,
          getMemberCandidateSubtitle:
            groupMembers.getMemberCandidateSubtitle,
        }}
        details={{
          memberItems: objectMembers,
          membersLoading,
          membersError,
          historyItems: adAdminHistory,
          historyLoading: adAdminHistoryLoading,
          historyError: adAdminHistoryError,
          historyFilter: adAdminHistoryFilter,
          onHistoryFilterChange:
            setAdAdminHistoryFilter,
          onOpenHistoryJob: job => {
            setPropertiesModal(null)
            setSelectedAdAdminHistoryJob(job)
          },
          onLoadHistory: () =>
            loadAdAdminHistory(),
          onCopyDn: target =>
            copyText(getObjectDn(target))
              .then(() =>
                setMessage?.('DN copié.')
              ),
          onExplore: target => {
            setPropertiesModal(null)
            loadNodeContent(
              target,
              getNodeKind(target)
            )
          },
          onCreateOu: target => {
            setPropertiesModal(null)
            openCreateOu(target)
          },
          onCreateGroup: target => {
            setPropertiesModal(null)
            openCreateGroup(target)
          },
          onOpenMoveObject: target => {
            setPropertiesModal(null)
            openMoveObject(target)
          },
          onOpenUpdateObject: target => {
            setPropertiesModal(null)
            openUpdateObject(target)
          },
          onOpenRenameObject: target => {
            setPropertiesModal(null)
            openRenameObject(target)
          },
          onOpenDeleteObject: target => {
            setPropertiesModal(null)
            openDeleteObject(target)
          },
          onPrepareAccountAction: (
            action,
            target
          ) => {
            setPropertiesModal(null)
            prepareAccountAction(
              action,
              target
            )
          },
          onLoadMembers: target =>
            loadGroupMembers(target),
          onOpenAddMember: target => {
            setPropertiesModal(null)
            openAddMemberModal(target)
          },
          onRemoveMember: (
            group,
            member
          ) =>
            removeGroupMember(
              group,
              member
            ),
        }}
      />

      <DeleteObjectModal
        deletion={{
          ...objectDeletion,
          loading,
        }}
      />

      <MoveObjectModal
        move={{
          ...objectMove,
          adminLoading,
          isAdProductionMode,
          getAdAgentModeLabel,
          adAgentModeLoading,
        }}
      />

      <RenameObjectModal
        rename={{
          ...objectRename,
          loading,
        }}
      />

      <UpdateObjectModal
        update={{
          ...objectUpdate,
          loading,
          getMemberCandidateTitle: groupMembers.getMemberCandidateTitle,
          getMemberCandidateSubtitle: groupMembers.getMemberCandidateSubtitle,
        }}
      />

      <AccountActionModal
        account={{
          ...accountActions,
          adAgentMode,
        }}
      />

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
