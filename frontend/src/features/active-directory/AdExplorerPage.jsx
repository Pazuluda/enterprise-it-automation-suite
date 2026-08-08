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
  DOMAIN_CONTROLLERS_DN,
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
  isContainerObject,
  isGroupObject,
  getParentDn,
  buildAdNavigationNode,
  buildAdBreadcrumbs,
  cleanAdHistoryText,
  copyText,
  splitLdapDn,
  getOuLabelFromDn,
  } from './utils/adExplorerCore'

import {
  AD_EXPLORER_COLUMNS,
  DEFAULT_AD_EXPLORER_COLUMN_IDS,
  getAdExplorerColumnDefinition,
  getAdExplorerColumnValue,
  loadAdExplorerColumnPreferences,
  loadAdExplorerSortPreference,
  normalizeAdExplorerColumnIds,
  saveAdExplorerColumnPreferences,
  saveAdExplorerSortPreference,
  sortAdExplorerItems,
} from './utils/adExplorerColumns'

import {
  AD_EXPLORER_FILTER_OPERATOR_OPTIONS,
  AD_EXPLORER_TYPE_OPTIONS,
  DEFAULT_AD_EXPLORER_FILTERS,
  createAdExplorerFilterCondition,
  filterAdExplorerItems,
  getAdExplorerActiveFilterCount,
  loadAdExplorerFilterPreferences,
  normalizeAdExplorerFilters,
  saveAdExplorerFilterPreferences,
} from './utils/adExplorerFilters'

import {
  addAdExplorerSavedSearch,
  loadAdExplorerSavedSearches,
  removeAdExplorerSavedSearch,
  replaceAdExplorerSavedSearch,
  saveAdExplorerSavedSearches,
} from './utils/adExplorerSavedSearches'
import {
  normalizeAdExplorerSelectionId,
  resolveAdExplorerSelection,
  selectAllAdExplorerSelection,
} from "./utils/adExplorerSelection"
import {
  isCopyableUserSource,
} from "./utils/adUserCopy"

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

import {
  buildAdUserDetailsJobPayload,
  extractAdUserDetails,
  mergeAdUserDetails,
} from './utils/adUserDetails'

export default function AdExplorerPage({ apiFetch, setMessage, canManageActiveDirectory }) {
  const [treeItems, setTreeItems] = useState([])
  const [viewItems, setViewItems] = useState([])
  const [selectedNode, setSelectedNode] = useState({
    name: 'EITAS',
    distinguished_name: EITAS_DN,
    canonical_name: 'API.LOCAL/EITAS'
  })

  const [viewType, setViewType] = useState('ou')
  const [selectedObject, setSelectedObject] = useState(null)
  const [selectedObjectIds, setSelectedObjectIds] = useState([])
  const [selectionAnchorId, setSelectionAnchorId] = useState("")
  const [newObjectModal, setNewObjectModal] = useState(null)
  const [propertiesModal, setPropertiesModal] = useState(null)
  const [searchOuModal, setSearchOuModal] = useState(null)
  const [searchOuQuery, setSearchOuQuery] = useState('')
  const [objectMembers, setObjectMembers] = useState([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [membersError, setMembersError] = useState('')
  const [membersMode, setMembersMode] = useState('direct')
  const [treeFilter, setTreeFilter] = useState('')
  const [viewFilter, setViewFilter] = useState('')
  const [visibleColumnIds, setVisibleColumnIds] =
    useState(() =>
      loadAdExplorerColumnPreferences(
        typeof window === 'undefined'
          ? null
          : window.localStorage
      )
    )
  const [viewSort, setViewSort] =
    useState(() =>
      loadAdExplorerSortPreference(
        typeof window === 'undefined'
          ? null
          : window.localStorage
      )
    )
  const [
    columnOptionsOpen,
    setColumnOptionsOpen
  ] = useState(false)
  const [
    advancedFilters,
    setAdvancedFilters
  ] = useState(() =>
    loadAdExplorerFilterPreferences(
      typeof window === 'undefined'
        ? null
        : window.localStorage
    )
  )
  const [
    filterOptionsOpen,
    setFilterOptionsOpen
  ] = useState(false)
  const [
    savedSearches,
    setSavedSearches
  ] = useState(() =>
    loadAdExplorerSavedSearches(
      typeof window === 'undefined'
        ? null
        : window.localStorage
    )
  )
  const [
    savedSearchesOpen,
    setSavedSearchesOpen
  ] = useState(false)
  const [
    savedSearchName,
    setSavedSearchName
  ] = useState('')
  const [
    savedSearchError,
    setSavedSearchError
  ] = useState('')
  const [loading, setLoading] = useState(false)
  const nodeContentCacheRef = useRef(new Map())
  const nodeContentPromisesRef = useRef(new Map())
  const nodeContentRequestIdRef = useRef(0)
  const propertiesDetailsRequestIdRef = useRef(0)
  const userDetailsCacheRef = useRef(new Map())
  const userDetailsPromisesRef = useRef(new Map())
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
    loadAdAgentMode,
    viewType,
    runAdAdminJob,
    loadComputersView,
    refreshAccountTarget,
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
    loadContactsView,
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
    adminParentItems: adSnapshot.snapshotItems,
  })

  const {
    getAdminCreationOuDisplayLabel,
    normalizeAdminCreationOptions,
    getCreateAdminParentDn,
    openCreateOu,
    openCreateContainer,
    openCreateContact,
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
    resolveUserUpdateTarget,
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
    openCopyUser,
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
    resolveUserUpdateTarget,
    resolveUserUpdateTargetSync,
    invalidateUserDetailsCache,
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

  const visibleColumns = useMemo(
    () =>
      visibleColumnIds
        .map(getAdExplorerColumnDefinition)
        .filter(Boolean),
    [visibleColumnIds]
  )

  const advancedFilterCount = useMemo(
    () =>
      getAdExplorerActiveFilterCount(
        advancedFilters
      ),
    [advancedFilters]
  )

  const filteredViewItems = useMemo(() => {
    const filter =
      viewFilter.trim().toLowerCase()

    const textFiltered = !filter
      ? [...viewItems]
      : viewItems.filter(item =>
          JSON.stringify(item)
            .toLowerCase()
            .includes(filter)
        )

    const getColumnValue = (
      item,
      columnId
    ) =>
      getAdExplorerColumnValue(
        item,
        columnId,
        {
          getObjectName,
          getObjectType,
          getObjectDescription:
            getGroupDescription,
        }
      )

    const advancedFiltered =
      filterAdExplorerItems(
        textFiltered,
        advancedFilters,
        getColumnValue,
        getObjectType
      )

    return sortAdExplorerItems(
      advancedFiltered,
      viewSort,
      getColumnValue
    )
  }, [
    viewItems,
    viewFilter,
    viewSort,
    advancedFilters
  ])

  const adExplorerGridTemplate =
    visibleColumns
      .map(column => column.width)
      .join(' ')

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    saveAdExplorerColumnPreferences(
      window.localStorage,
      visibleColumnIds
    )
  }, [visibleColumnIds])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    saveAdExplorerSortPreference(
      window.localStorage,
      viewSort
    )
  }, [viewSort])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    saveAdExplorerFilterPreferences(
      window.localStorage,
      advancedFilters
    )
  }, [advancedFilters])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    saveAdExplorerSavedSearches(
      window.localStorage,
      savedSearches
    )
  }, [savedSearches])

  useEffect(() => {
    if (selectedObject) {
      return
    }

    setSelectedObjectIds([])
    setSelectionAnchorId("")
  }, [selectedObject])

  function updateAdExplorerFilterField(
    field,
    value
  ) {
    setAdvancedFilters(previous =>
      normalizeAdExplorerFilters({
        ...previous,
        [field]: value
      })
    )
  }

  function addAdExplorerFilterCondition() {
    setAdvancedFilters(previous => {
      if (previous.conditions.length >= 8) {
        return previous
      }

      return normalizeAdExplorerFilters({
        ...previous,
        conditions: [
          ...previous.conditions,
          createAdExplorerFilterCondition(
            `filter-${Date.now()}`
          )
        ]
      })
    })
  }

  function updateAdExplorerFilterCondition(
    conditionId,
    field,
    value
  ) {
    setAdvancedFilters(previous =>
      normalizeAdExplorerFilters({
        ...previous,
        conditions: previous.conditions.map(
          condition => {
            if (condition.id !== conditionId) {
              return condition
            }

            const updated = {
              ...condition,
              [field]: value
            }

            if (
              field === 'operator'
              && (
                value === 'present'
                || value === 'absent'
              )
            ) {
              updated.value = ''
            }

            return updated
          }
        )
      })
    )
  }

  function removeAdExplorerFilterCondition(
    conditionId
  ) {
    setAdvancedFilters(previous =>
      normalizeAdExplorerFilters({
        ...previous,
        conditions: previous.conditions.filter(
          condition =>
            condition.id !== conditionId
        )
      })
    )
  }

  function resetAdExplorerFilters() {
    setAdvancedFilters(
      normalizeAdExplorerFilters(
        DEFAULT_AD_EXPLORER_FILTERS
      )
    )
  }

  function buildCurrentSavedSearch(name) {
    return {
      id:
        `saved-${Date.now()}-${Math.random()
          .toString(16)
          .slice(2, 8)}`,
      name,
      query: globalAdSearch,
      columnIds: visibleColumnIds,
      sort: viewSort,
      filters: advancedFilters,
    }
  }

  function saveCurrentAdExplorerSearch() {
    const result = addAdExplorerSavedSearch(
      savedSearches,
      buildCurrentSavedSearch(
        savedSearchName
      )
    )

    setSavedSearches(result.searches)
    setSavedSearchError(result.error)

    if (!result.error) {
      setSavedSearchName('')
      setStatus('Recherche enregistrée.')
    }
  }

  function replaceCurrentAdExplorerSearch(saved) {
    const result =
      replaceAdExplorerSavedSearch(
        savedSearches,
        saved.id,
        buildCurrentSavedSearch(saved.name)
      )

    setSavedSearches(result.searches)
    setSavedSearchError(result.error)

    if (!result.error) {
      setStatus(
        `Recherche ${saved.name} remplacée.`
      )
    }
  }

  function deleteAdExplorerSavedSearch(saved) {
    setSavedSearches(previous =>
      removeAdExplorerSavedSearch(
        previous,
        saved.id
      )
    )
    setSavedSearchError('')
  }

  async function loadAdExplorerSavedSearch(saved) {
    setVisibleColumnIds(saved.columnIds)
    setViewSort(saved.sort)
    setAdvancedFilters(saved.filters)
    setGlobalAdSearch(saved.query)
    setSavedSearchName(saved.name)
    setSavedSearchError('')
    setSavedSearchesOpen(false)

    if (saved.query) {
      await runGlobalAdSearch(null, saved.query)
      return
    }

    setStatus(
      `Recherche ${saved.name} restaurée.`
    )
  }

  function toggleAdExplorerColumn(columnId) {
    const definition =
      getAdExplorerColumnDefinition(columnId)

    if (!definition || definition.required) {
      return
    }

    setVisibleColumnIds(previous => {
      const active = previous.includes(columnId)

      return normalizeAdExplorerColumnIds(
        active
          ? previous.filter(
              value => value !== columnId
            )
          : [...previous, columnId]
      )
    })
  }

  function resetAdExplorerColumns() {
    setVisibleColumnIds([
      ...DEFAULT_AD_EXPLORER_COLUMN_IDS
    ])

    setViewSort({
      columnId: 'name',
      direction: 'asc'
    })
  }

  function toggleAdExplorerSort(columnId) {
    setViewSort(previous => {
      if (previous.columnId !== columnId) {
        return {
          columnId,
          direction: 'asc'
        }
      }

      return {
        columnId,
        direction:
          previous.direction === 'asc'
            ? 'desc'
            : 'asc'
      }
    })
  }

  function getAdExplorerSortIndicator(
    columnId
  ) {
    if (viewSort.columnId !== columnId) {
      return ''
    }

    return viewSort.direction === 'desc'
      ? ' ▼'
      : ' ▲'
  }

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

  async function runAdUserDetailsJobUncached(target) {
    const payload =
      buildAdUserDetailsJobPayload(target)

    if (!payload) {
      return null
    }

    const created = await apiFetch('/api/ad-explorer/jobs', {
      method: 'POST',
      body: JSON.stringify(payload),
    })

    const jobId = created?.job?.id

    if (!jobId) {
      throw new Error(
        'Job de détails utilisateur invalide.'
      )
    }

    for (
      let attempt = 0;
      attempt < 45;
      attempt += 1
    ) {
      const job = await apiFetch(
        `/api/ad-explorer/jobs/${jobId}`
      )

      if (
        job.status === 'completed'
        || job.status === 'failed'
      ) {
        if (!job.success) {
          throw new Error(
            job.message
            || 'Lecture détaillée utilisateur impossible.'
          )
        }

        const details =
          extractAdUserDetails(job)

        if (!details) {
          throw new Error(
            'Réponse utilisateur détaillée invalide.'
          )
        }

        return details
      }

      await new Promise(resolve =>
        setTimeout(resolve, 450)
      )
    }

    throw new Error(
      'Timeout : l’agent Windows n’a pas répondu.'
    )
  }



  function getUserDetailsIdentity(target) {
    const payload =
      buildAdUserDetailsJobPayload(target)

    return String(
      payload?.identity
      || getObjectDn(target)
      || ''
    )
      .trim()
      .toLowerCase()
  }

  function getUserDetailsRevision(target) {
    return String(
      target?.when_changed
      || target?.whenChanged
      || target?.uSNChanged
      || target?.usn_changed
      || target?.usnChanged
      || ''
    ).trim()
  }

  function getUserDetailsCacheKey(target) {
    const identity =
      getUserDetailsIdentity(target)

    if (!identity) {
      return ''
    }

    return (
      `${identity}|`
      + getUserDetailsRevision(target)
    )
  }

  function invalidateUserDetailsCache(
    target = null
  ) {
    const identity =
      getUserDetailsIdentity(target)

    if (!identity) {
      userDetailsCacheRef.current.clear()
      userDetailsPromisesRef.current.clear()
      return
    }

    for (
      const key
      of userDetailsCacheRef.current.keys()
    ) {
      if (
        key === identity
        || key.startsWith(`${identity}|`)
      ) {
        userDetailsCacheRef.current.delete(key)
      }
    }

    for (
      const key
      of userDetailsPromisesRef.current.keys()
    ) {
      if (
        key === identity
        || key.startsWith(`${identity}|`)
      ) {
        userDetailsPromisesRef.current.delete(key)
      }
    }
  }

  async function runAdUserDetailsJob(
    target,
    options = {}
  ) {
    const force = Boolean(options.force)
    const cacheKey =
      getUserDetailsCacheKey(target)

    if (
      !force
      && cacheKey
      && userDetailsCacheRef.current.has(
        cacheKey
      )
    ) {
      return userDetailsCacheRef.current.get(
        cacheKey
      )
    }

    if (
      !force
      && cacheKey
      && userDetailsPromisesRef.current.has(
        cacheKey
      )
    ) {
      return userDetailsPromisesRef.current.get(
        cacheKey
      )
    }

    const requestPromise = (
      async () => {
        const details =
          await runAdUserDetailsJobUncached(
            target
          )

        if (
          details
          && cacheKey
        ) {
          userDetailsCacheRef.current.set(
            cacheKey,
            details
          )
        }

        return details
      }
    )()

    if (cacheKey) {
      userDetailsPromisesRef.current.set(
        cacheKey,
        requestPromise
      )
    }

    try {
      return await requestPromise
    } finally {
      if (
        cacheKey
        && userDetailsPromisesRef.current.get(
          cacheKey
        ) === requestPromise
      ) {
        userDetailsPromisesRef.current.delete(
          cacheKey
        )
      }
    }
  }

  function prefetchUserDetails(target) {
    const identity =
      getUserDetailsIdentity(target)

    if (!identity) {
      return
    }

    void runAdUserDetailsJob(target)
      .then(details => {
        if (!details) {
          return
        }

        const mergeCurrent = current => {
          if (
            getUserDetailsIdentity(current)
            !== identity
          ) {
            return current
          }

          return mergeAdUserDetails(
            current,
            details
          )
        }

        setSelectedObject(mergeCurrent)
        setPropertiesModal(mergeCurrent)
      })
      .catch(() => {
        /*
         * Le prechargement est silencieux.
         * Une ouverture explicite conservera
         * la gestion normale des erreurs.
         */
      })
  }


  async function loadTree(options = {}) {
    const snapshotOus =
      await adSnapshot.getNavigationNodes({
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
      const data = await apiFetch('/api/ad-admin/jobs?limit=1000')
      setAdAdminHistory(Array.isArray(data.jobs) ? data.jobs : [])
    } catch (err) {
      setAdAdminHistoryError(err.message || 'Impossible de charger l’historique AD Admin.')
    } finally {
      setAdAdminHistoryLoading(false)
    }
  }

  async function refreshAdAdminHistoryQuietly() {
    try {
      const data = await apiFetch('/api/ad-admin/jobs?limit=1000')
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

    const recursive =
      options.recursive === undefined
        ? membersMode === 'recursive'
        : Boolean(options.recursive)

    const forceJob =
      Boolean(options.forceJob || recursive)

    setMembersMode(
      recursive ? 'recursive' : 'direct'
    )

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
            recursive,
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

  function getAdExplorerSelectionId(item) {
    return normalizeAdExplorerSelectionId(
      getObjectDn(item)
    )
  }

  function clearAdExplorerSelection() {
    setSelectedObjectIds([])
    setSelectionAnchorId("")
    setSelectedObject(null)
    setObjectMembers([])
    setMembersError("")
    setMembersMode("direct")
  }

  function activateAdExplorerPrimaryObject(item) {
    setSelectedObject(item || null)
    setObjectMembers([])
    setMembersError("")
    setMembersMode("direct")

    if (!item) {
      return
    }

    prefetchUserDetails(item)

    if (isGroupObject(item)) {
      loadGroupMembers(
        item,
        { recursive: false }
      )
    }
  }

  function selectObject(item) {
    const event = arguments[1] || null
    const visibleItems =
      arguments[2] || [item]

    const itemId =
      getAdExplorerSelectionId(item)

    if (!itemId) {
      setSelectedObjectIds([])
      setSelectionAnchorId("")
      activateAdExplorerPrimaryObject(item)
      return
    }

    const sourceItems =
      Array.isArray(visibleItems)
        ? visibleItems
        : [item]

    const next = resolveAdExplorerSelection({
      currentIds: selectedObjectIds,
      clickedId: itemId,
      anchorId: selectionAnchorId,
      visibleIds: sourceItems.map(
        getAdExplorerSelectionId
      ),
      ctrlKey: Boolean(event?.ctrlKey),
      metaKey: Boolean(event?.metaKey),
      shiftKey: Boolean(event?.shiftKey),
    })

    setSelectedObjectIds(next.ids)
    setSelectionAnchorId(next.anchorId)

    const primary =
      next.ids.includes(itemId)
        ? item
        : sourceItems.find(candidate =>
            next.ids.includes(
              getAdExplorerSelectionId(
                candidate
              )
            )
          ) || null

    if (primary === item) {
      setSelectedObject(item)
      setObjectMembers([])
      setMembersError("")
      setMembersMode("direct")

      prefetchUserDetails(item)

      if (isGroupObject(item)) {
        loadGroupMembers(item, { recursive: false })
      }

      return
    }

    activateAdExplorerPrimaryObject(
      primary
    )
  }

  function handleAdExplorerSelectionKeyDown(
    event
  ) {
    if (
      (event.ctrlKey || event.metaKey)
      && String(event.key || "")
        .toLowerCase() === "a"
    ) {
      const ids =
        selectAllAdExplorerSelection(
          filteredViewItems.map(
            getAdExplorerSelectionId
          )
        )

      if (ids.length === 0) {
        return
      }

      event.preventDefault()

      setSelectedObjectIds(ids)
      setSelectionAnchorId(ids[0])

      const currentId =
        getAdExplorerSelectionId(
          selectedObject
        )

      const primary =
        currentId
        && ids.includes(currentId)
          ? selectedObject
          : filteredViewItems[0] || null

      activateAdExplorerPrimaryObject(
        primary
      )

      return
    }

    if (
      event.key === "Escape"
      && selectedObjectIds.length > 0
    ) {
      event.preventDefault()
      clearAdExplorerSelection()
    }
  }


  function getSelectedAdExplorerObjects() {
    const selectedIds = new Set(
      selectedObjectIds
    )

    return filteredViewItems.filter(
      item =>
        selectedIds.has(
          getAdExplorerSelectionId(
            item
          )
        )
    )
  }

  function getAdExplorerSelectionName(item) {
    return String(
      item?.display_name
      || item?.displayName
      || item?.name
      || item?.cn
      || item?.sam_account_name
      || item?.samAccountName
      || getObjectDn(item)
      || ""
    ).trim()
  }

  function escapeAdExplorerSelectionCsv(value) {
    const text = String(
      value ?? ""
    )

    if (
      text.includes(";")
      || text.includes("\"")
      || text.includes("\n")
      || text.includes("\r")
    ) {
      return (
        "\""
        + text.replaceAll(
          "\"",
          "\"\""
        )
        + "\""
      )
    }

    return text
  }

  function buildAdExplorerSelectionText(
    selectedItems,
    format
  ) {
    if (format === "dn") {
      return selectedItems
        .map(getObjectDn)
        .filter(Boolean)
        .join("\n")
    }

    if (format === "name") {
      return selectedItems
        .map(
          getAdExplorerSelectionName
        )
        .filter(Boolean)
        .join("\n")
    }

    if (format === "csv") {
      const rows = [
        "Nom;Type;Compte SAM;E-mail;DN"
      ]

      for (const item of selectedItems) {
        rows.push(
          [
            getAdExplorerSelectionName(
              item
            ),
            String(
              item?.type
              || item?.object_type
              || item?.objectType
              || ""
            ),
            String(
              item?.sam_account_name
              || item?.samAccountName
              || item?.sAMAccountName
              || ""
            ),
            String(
              item?.mail
              || item?.email
              || item?.email_address
              || ""
            ),
            getObjectDn(item),
          ]
            .map(
              escapeAdExplorerSelectionCsv
            )
            .join(";")
        )
      }

      return rows.join("\n")
    }

    throw new Error(
      "Format de copie inconnu."
    )
  }

  async function copyAdExplorerSelection(
    format
  ) {
    const selectedItems =
      getSelectedAdExplorerObjects()

    if (selectedItems.length === 0) {
      const message =
        "Aucun objet selectionne a copier."

      setStatus(message)
      setMessage?.(message)
      return
    }

    try {
      const text =
        buildAdExplorerSelectionText(
          selectedItems,
          format
        )

      if (!text.trim()) {
        throw new Error(
          "Aucune donnee a copier."
        )
      }

      await copyText(text)

      const label =
        format === "dn"
          ? "DN"
          : format === "name"
            ? "noms"
            : "CSV"

      const message =
        selectedItems.length
        + " objet(s) : "
        + label
        + " copie(s) dans le presse-papiers."

      setStatus(message)
      setMessage?.(message)
    } catch (error) {
      const message =
        error?.message
        || "Impossible de copier la selection."

      setStatus(
        "Erreur : " + message
      )

      setMessage?.(
        "Erreur : " + message
      )
    }
  }

  function resolveLinkedObject(target) {
    const targetDn =
      typeof target === 'string'
        ? target
        : getObjectDn(target)

    if (!targetDn) {
      return (
        target &&
        typeof target === 'object'
          ? target
          : null
      )
    }

    return (
      adSnapshot.findByDnSync(targetDn) ||
      adDomainCatalog.findByDnSync(targetDn) ||
      (
        target &&
        typeof target === 'object'
          ? target
          : null
      )
    )
  }


  function openLinkedObject(target) {
    const linkedObject =
      resolveLinkedObject(target)

    if (!linkedObject) {
      const message =
        'Objet lié introuvable dans les données Active Directory.'

      setStatus(message)
      setMessage?.(message)
      return
    }

    selectObject(linkedObject)
    setPropertiesModal(linkedObject)
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


  async function loadDomainControllersView() {
    setLoading(true)
    setStatus(
      'Chargement des contrôleurs de domaine...'
    )

    try {
      let items = await adDomainCatalog.search({
        query: '',
        baseDn: DOMAIN_CONTROLLERS_DN,
        recursive: true,
        types: ['computer'],
        limit: 100,
      })

      const loadedFromCatalog =
        Array.isArray(items)

      if (!loadedFromCatalog) {
        const result = await runJob(
          'list_computers',
          {
            query: '',
            baseDn: DOMAIN_CONTROLLERS_DN,
            recursive: true,
            limit: 100
          }
        )

        items = extractExplorerItems(result)
      }

      setSelectedNode({
        name: 'Contrôleurs de domaine',
        type: 'domain-controllers-container',
        distinguished_name: DOMAIN_CONTROLLERS_DN,
        dn: DOMAIN_CONTROLLERS_DN,
        canonical_name: 'API.LOCAL/Domain Controllers'
      })

      setViewType('domain-controllers')
      setViewItems(items)
      setSelectedObject(null)
      setObjectMembers([])
      setMembersError('')

      setStatus(
        `${items.length} contrôleur(s) de domaine chargé(s)`
      )
    } catch (error) {
      setViewItems([])
      setSelectedObject(null)

      setStatus(
        error.message ||
        'Chargement des contrôleurs de domaine impossible.'
      )
    } finally {
      setLoading(false)
    }
  }

  async function loadContactsView() {
    setLoading(true)
    setStatus(
      'Chargement des contacts Active Directory...'
    )

    try {
      const items = await adSnapshot.search({
        query: '',
        baseDn: EITAS_DN,
        recursive: true,
        types: ['contact'],
        limit: 1000,
      })

      if (!Array.isArray(items)) {
        throw new Error(
          'Snapshot des contacts indisponible.'
        )
      }

      setSelectedNode({
        name: 'Contacts',
        type: 'contact-container',
        distinguished_name: EITAS_DN,
        dn: EITAS_DN,
        canonical_name: 'API.LOCAL/EITAS/Contacts'
      })

      setViewType('contacts')
      setViewItems(items)
      setSelectedObject(null)
      setObjectMembers([])
      setMembersError('')

      setStatus(
        `${items.length} contact(s) chargé(s) depuis le snapshot EITAS`
      )
    } catch (error) {
      setViewItems([])
      setSelectedObject(null)

      setStatus(
        error.message ||
        'Chargement des contacts Active Directory impossible.'
      )
    } finally {
      setLoading(false)
    }
  }

  function resolveUserUpdateTargetSync(target) {
    const targetDn =
      getObjectDn(target)

    if (!targetDn) {
      return target
    }

    const snapshotTarget =
      adSnapshot.findByDnSync(targetDn)

    const catalogTarget =
      adDomainCatalog.findByDnSync(targetDn)

    const availableTarget =
      snapshotTarget || catalogTarget

    if (!availableTarget) {
      return target
    }

    return mergeAdUserDetails(
      target,
      availableTarget
    )
  }


  async function resolveUserUpdateTarget(target) {
    const details =
      await runAdUserDetailsJob(target)

    if (!details) {
      throw new Error(
        'Les options avancées du compte utilisateur '
        + 'n’ont pas pu être chargées.'
      )
    }

    return mergeAdUserDetails(
      target,
      details
    )
  }


  async function openProperties(target) {
    setContextMenu(null)

    if (!target) {
      setStatus('Aucun objet sélectionné.')
      return
    }

    const requestId =
      propertiesDetailsRequestIdRef.current + 1

    propertiesDetailsRequestIdRef.current =
      requestId

    const targetDn = String(
      getObjectDn(target) || ''
    ).toLowerCase()

    const matchesTarget = candidate => {
      if (!candidate) {
        return false
      }

      const candidateDn = String(
        getObjectDn(candidate) || ''
      ).toLowerCase()

      if (targetDn) {
        return candidateDn === targetDn
      }

      return candidate === target
    }

    /*
     * Ouvre immédiatement avec les données déjà
     * disponibles dans le snapshot ou le catalogue.
     */
    setSelectedObject(target)
    setPropertiesModal(target)

    try {
      const details =
        await runAdUserDetailsJob(target)

      if (
        requestId !==
        propertiesDetailsRequestIdRef.current
      ) {
        return
      }

      if (!details) {
        return
      }

      const resolvedTarget =
        mergeAdUserDetails(target, details)

      /*
       * Enrichit uniquement l’objet encore affiché.
       * Une réponse ancienne ne peut donc pas
       * remplacer une autre fenêtre de propriétés.
       */
      setSelectedObject(previous =>
        matchesTarget(previous)
          ? resolvedTarget
          : previous
      )

      setPropertiesModal(previous =>
        matchesTarget(previous)
          ? resolvedTarget
          : previous
      )
    } catch (error) {
      if (
        requestId !==
        propertiesDetailsRequestIdRef.current
      ) {
        return
      }

      setStatus(
        error.message
        || 'Lecture détaillée utilisateur impossible.'
      )
    }
  }


  async function runGlobalAdSearch(event, queryOverride = null) {
    event?.preventDefault?.()

    const query = String(queryOverride ?? globalAdSearch).trim()

    if (!query) {
      setStatus('Recherche AD vide.')
      return
    }

    if (queryOverride !== null) {
      setGlobalAdSearch(query)
    }

    setGlobalAdSearchLoading(true)
    setStatus(`Recherche globale AD : ${query}...`)

    try {
      const baseDn = DOMAIN_DN

      const results = await runJob(
        'search_objects',
        {
          query,
          baseDn,
          recursive: true,
          limit: 1000
        }
      )

      const seen = new Set()

      const uniqueResults =
        extractExplorerItems(results)
          .filter(item => {
            const key = String(
              getObjectDn(item)
              || item?.sam_account_name
              || item?.name
              || ''
            )
              .trim()
              .toLowerCase()

            if (!key) {
              return true
            }

            if (seen.has(key)) {
              return false
            }

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
        `${uniqueResults.length} résultat(s) pour ${query}`
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
      const nextMode = data?.mode || 'Inconnu'

      setAdAgentMode(nextMode)
      return nextMode
    } catch (error) {
      console.warn(
        'Impossible de charger le mode agent',
        error
      )
      setAdAgentMode('Inconnu')
      return 'Inconnu'
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

  async function refreshAccountTarget(target) {
    const details =
      await runAdUserDetailsJob(target)

    if (!details) {
      return null
    }

    const targetDn = String(
      getObjectDn(target) || ''
    )
      .trim()
      .toLowerCase()

    const matchesTarget = candidate => {
      if (!candidate) {
        return false
      }

      const candidateDn = String(
        getObjectDn(candidate) || ''
      )
        .trim()
        .toLowerCase()

      if (targetDn) {
        return candidateDn === targetDn
      }

      return candidate === target
    }

    const mergeTarget = candidate =>
      matchesTarget(candidate)
        ? mergeAdUserDetails(candidate, details)
        : candidate

    setSelectedObject(mergeTarget)
    setPropertiesModal(mergeTarget)

    setViewItems(items =>
      items.map(mergeTarget)
    )

    return mergeAdUserDetails(
      target,
      details,
    )
  }


  async function setPrimaryGroupSimulation(group, subject) {
    const subjectDn = getObjectDn(subject)

    const groupDn =
      getObjectDn(group) ||
      String(
        group?.distinguished_name ||
        group?.dn ||
        ''
      ).trim()

    if (!subjectDn || !groupDn) {
      const message =
        'Impossible de préparer le groupe principal : DN introuvable.'

      setStatus(message)
      setMessage?.(message)
      return null
    }

    if (
      !isEitasManagedDn(subjectDn) ||
      !isEitasManagedDn(groupDn)
    ) {
      const message =
        'Action bloquée : le compte et le groupe cible doivent rester sous OU=EITAS.'

      setStatus(message)
      setMessage?.(message)
      return null
    }

    let currentMode = 'Inconnu'

    try {
      const modeData =
        await apiFetch('/api/agent/mode')

      currentMode =
        modeData?.mode || 'Inconnu'

      setAdAgentMode(currentMode)
    } catch (err) {
      const message =
        err?.message ||
        'Mode agent indisponible : changement de groupe principal bloqué.'

      setStatus(message)
      setMessage?.(message)
      return null
    }

    if (
      String(currentMode)
        .trim()
        .toLowerCase() !== 'simulation'
    ) {
      const message =
        'Le changement de groupe principal est disponible uniquement en mode Simulation.'

      setStatus(message)
      setMessage?.(message)
      return null
    }

    const groupLabel =
      group?.name ||
      group?.sam_account_name ||
      groupDn

    const subjectLabel =
      getObjectName(subject) ||
      subjectDn

    if (
      !window.confirm(
        `Simulation uniquement.\n\nDéfinir ${groupLabel} comme groupe principal de ${subjectLabel} ?\n\nAucune écriture Active Directory ne sera autorisée.`
      )
    ) {
      return null
    }

    setStatus(
      'Simulation du changement de groupe principal en cours...'
    )

    try {
      const job = await runAdAdminJob({
        action: 'set_primary_group',
        object_identity: subjectDn,
        group_identity: groupDn,
      })

      const output = job?.output || {}

      if (
        output.simulated !== true ||
        output.production_authorized !== false
      ) {
        throw new Error(
          'Résultat inattendu : la garantie Simulation n’est pas confirmée.'
        )
      }

      let refreshWarning = ''

      try {
        const subjectType =
          getObjectType(subject)

        if (
          subjectType === 'Ordinateur' ||
          subjectType ===
            'Contrôleur de domaine'
        ) {
          await loadComputersView()
        } else {
          await refreshAccountTarget(subject)
        }
      } catch {
        refreshWarning =
          ' Actualisation des propriétés impossible.'
      }

      const baseMessage =
        cleanAdAdminMessage(
          output.message ||
          job?.message ||
          'Simulation du changement de groupe principal validée.'
        )

      const message =
        `${baseMessage}${refreshWarning}`

      setStatus(message)
      setMessage?.(message)

      return job
    } catch (err) {
      const message =
        cleanAdAdminMessage(
          err?.message ||
          'Simulation du changement de groupe principal en erreur.'
        )

      setStatus(`Erreur : ${message}`)
      setMessage?.(message)

      return null
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


  useEffect(() => {
    if (
      !adSnapshot.snapshotRevision ||
      !adSnapshot.snapshotIsUsable
    ) {
      return
    }

    nodeContentCacheRef.current.clear()

    const snapshotOus =
      adSnapshot.getNavigationNodesSync()

    setTreeItems(snapshotOus)

    const selectedNodeDn =
      getObjectDn(selectedNode)

    if (
      !adSnapshot.canServeDn(
        selectedNodeDn
      ) ||
      viewType === 'computers' ||
        viewType === 'contacts' ||
        viewType === 'domain-controllers' ||
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
                className={viewType === 'contacts' ? 'active' : ''}
                onClick={loadContactsView}
              >
                Contacts
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
                            <button
                type="button"
                data-eitas-action="create-container-toolbar"
                disabled={
                  !isEitasManagedObject(selectedNode)
                }
                onClick={() =>
                  openCreateContainer(selectedNode)
                }
              >
                📦 Créer un conteneur
              </button>
              <button type="button" onClick={() => openCreateGroup(selectedNode)}>👥 Créer un groupe</button>
              <button
                type="button"
                data-eitas-action="create-contact-toolbar"
                disabled={
                  !isEitasManagedObject(selectedNode)
                }
                title={
                  isEitasManagedObject(selectedNode)
                    ? 'Créer un contact dans le périmètre EITAS'
                    : 'Sélectionne un objet du périmètre EITAS'
                }
                onClick={() =>
                  openCreateContact(selectedNode)
                }
              >
                📇 Créer un contact
              </button>
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
              <span>Cherche les utilisateurs, groupes et ordinateurs de API.LOCAL, ainsi que les contacts du périmètre EITAS. Les objets hors OU=EITAS sont en lecture seule.</span>
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
                    › 💻 Ordinateurs
                  </button>
                    <button
                      type="button"
                      className={`aduc-node system ${
                        viewType === 'contacts'
                          ? 'selected'
                          : ''
                      }`}
                      onClick={loadContactsView}
                    >
                      › 📇 Contacts
                    </button>
                  <button
                    type="button"
                    className={`aduc-node system ${viewType === 'domain-controllers' ? 'selected' : ''}`}
                    onClick={loadDomainControllersView}
                  >
                    › 🖥️ Contrôleurs de domaine
                  </button>

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

                    <div
                      className="aduc-saved-searches"
                    >
                      <button
                        type="button"
                        className="aduc-saved-searches-trigger"
                        title="Recherches enregistrées"
                        aria-label="Gérer les recherches enregistrées"
                        aria-expanded={savedSearchesOpen}
                        onClick={() => {
                          setFilterOptionsOpen(false)
                          setColumnOptionsOpen(false)
                          setSavedSearchError('')
                          setSavedSearchesOpen(
                            previous => !previous
                          )
                        }}
                      >
                        Recherches
                      </button>

                      {savedSearchesOpen && (
                        <div
                          className="aduc-saved-searches-menu"
                        >
                          <header
                            className="aduc-saved-searches-head"
                          >
                            <strong>
                              Recherches enregistrées
                            </strong>
                            <small>
                              Mémorise la recherche globale,
                              les filtres, les colonnes et le tri.
                            </small>
                          </header>

                          <div
                            className="aduc-saved-search-create"
                          >
                            <input
                              value={savedSearchName}
                              onChange={event => {
                                setSavedSearchName(
                                  event.target.value
                                )
                                setSavedSearchError('')
                              }}
                              placeholder="Nom de la recherche..."
                              maxLength={80}
                            />
                            <button
                              type="button"
                              onClick={
                                saveCurrentAdExplorerSearch
                              }
                            >
                              Enregistrer
                            </button>
                          </div>

                          {savedSearchError && (
                            <div
                              className="aduc-saved-search-error"
                            >
                              {savedSearchError}
                            </div>
                          )}

                          <div
                            className="aduc-saved-search-list"
                          >
                            {savedSearches.length === 0 ? (
                              <div
                                className="aduc-saved-search-empty"
                              >
                                Aucune recherche enregistrée.
                              </div>
                            ) : (
                              savedSearches.map(saved => (
                                <div
                                  key={saved.id}
                                  className="aduc-saved-search-item"
                                >
                                  <div>
                                    <strong>
                                      {saved.name}
                                    </strong>
                                    <span
                                      className="aduc-saved-search-summary"
                                    >
                                      {saved.query
                                        ? `Recherche : ${saved.query}`
                                        : 'Vue courante sans recherche globale'}
                                    </span>
                                  </div>

                                  <div
                                    className="aduc-saved-search-actions"
                                  >
                                    <button
                                      type="button"
                                      onClick={() =>
                                        loadAdExplorerSavedSearch(
                                          saved
                                        )
                                      }
                                    >
                                      Charger
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() =>
                                        replaceCurrentAdExplorerSearch(
                                          saved
                                        )
                                      }
                                    >
                                      Remplacer
                                    </button>
                                    <button
                                      type="button"
                                      className="danger"
                                      onClick={() =>
                                        deleteAdExplorerSavedSearch(
                                          saved
                                        )
                                      }
                                    >
                                      Supprimer
                                    </button>
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      )}
                    </div>

                    <div
                      className="aduc-filter-options"
                    >
                      <button
                        type="button"
                        className="aduc-filter-options-trigger"
                        title="Filtres avancés"
                        aria-label="Configurer les filtres avancés"
                        aria-expanded={
                          filterOptionsOpen
                        }
                        onClick={() => {
                          setColumnOptionsOpen(false)
                          setSavedSearchesOpen(false)
                          setFilterOptionsOpen(
                            previous =>
                              !previous
                          )
                        }}
                      >
                        <span>Filtres</span>
                        {advancedFilterCount > 0 && (
                          <strong>
                            {advancedFilterCount}
                          </strong>
                        )}
                      </button>

                      {filterOptionsOpen && (
                        <div
                          className={
                            "aduc-filter-options-menu"
                          }
                        >
                          <header
                            className={
                              "aduc-filter-options-head"
                            }
                          >
                            <div>
                              <strong>
                                Filtres avancés
                              </strong>
                              <small>
                                Les critères sont combinés
                                avec ET.
                              </small>
                            </div>

                            {advancedFilterCount > 0 && (
                              <button
                                type="button"
                                onClick={
                                  resetAdExplorerFilters
                                }
                              >
                                Effacer tout
                              </button>
                            )}
                          </header>

                          <div
                            className={
                              "aduc-filter-primary-grid"
                            }
                          >
                            <label>
                              <span>Type d’objet</span>
                              <select
                                value={
                                  advancedFilters.type
                                }
                                onChange={event =>
                                  updateAdExplorerFilterField(
                                    'type',
                                    event.target.value
                                  )
                                }
                              >
                                {AD_EXPLORER_TYPE_OPTIONS.map(
                                  option => (
                                    <option
                                      key={
                                        option.value
                                      }
                                      value={
                                        option.value
                                      }
                                    >
                                      {option.label}
                                    </option>
                                  )
                                )}
                              </select>
                            </label>

                            <label>
                              <span>État du compte</span>
                              <select
                                value={
                                  advancedFilters.enabled
                                }
                                onChange={event =>
                                  updateAdExplorerFilterField(
                                    'enabled',
                                    event.target.value
                                  )
                                }
                              >
                                <option value="all">
                                  Tous les états
                                </option>
                                <option value="enabled">
                                  Activé
                                </option>
                                <option value="disabled">
                                  Désactivé
                                </option>
                                <option value="unknown">
                                  Non applicable / inconnu
                                </option>
                              </select>
                            </label>
                          </div>

                          <div
                            className={
                              "aduc-filter-condition-list"
                            }
                          >
                            {advancedFilters.conditions
                              .map(condition => (
                                <div
                                  key={condition.id}
                                  className={
                                    "aduc-filter-condition"
                                  }
                                >
                                  <select
                                    aria-label={
                                      "Colonne du filtre"
                                    }
                                    value={
                                      condition.columnId
                                    }
                                    onChange={event =>
                                      updateAdExplorerFilterCondition(
                                        condition.id,
                                        'columnId',
                                        event.target.value
                                      )
                                    }
                                  >
                                    {AD_EXPLORER_COLUMNS.map(
                                      column => (
                                        <option
                                          key={
                                            column.id
                                          }
                                          value={
                                            column.id
                                          }
                                        >
                                          {column.label}
                                        </option>
                                      )
                                    )}
                                  </select>

                                  <select
                                    aria-label={
                                      "Opérateur du filtre"
                                    }
                                    value={
                                      condition.operator
                                    }
                                    onChange={event =>
                                      updateAdExplorerFilterCondition(
                                        condition.id,
                                        'operator',
                                        event.target.value
                                      )
                                    }
                                  >
                                    {AD_EXPLORER_FILTER_OPERATOR_OPTIONS
                                      .map(option => (
                                        <option
                                          key={
                                            option.value
                                          }
                                          value={
                                            option.value
                                          }
                                        >
                                          {option.label}
                                        </option>
                                      ))}
                                  </select>

                                  {![
                                    'present',
                                    'absent'
                                  ].includes(
                                    condition.operator
                                  ) && (
                                    <input
                                      aria-label={
                                        "Valeur du filtre"
                                      }
                                      value={
                                        condition.value
                                      }
                                      onChange={event =>
                                        updateAdExplorerFilterCondition(
                                          condition.id,
                                          'value',
                                          event.target.value
                                        )
                                      }
                                      placeholder="Valeur..."
                                    />
                                  )}

                                  <button
                                    type="button"
                                    className={
                                      "aduc-filter-remove"
                                    }
                                    title={
                                      "Supprimer ce critère"
                                    }
                                    aria-label={
                                      "Supprimer ce critère"
                                    }
                                    onClick={() =>
                                      removeAdExplorerFilterCondition(
                                        condition.id
                                      )
                                    }
                                  >
                                    ×
                                  </button>
                                </div>
                              ))}
                          </div>

                          <footer
                            className={
                              "aduc-filter-options-footer"
                            }
                          >
                            <button
                              type="button"
                              onClick={
                                addAdExplorerFilterCondition
                              }
                              disabled={
                                advancedFilters.conditions
                                  .length >= 8
                              }
                            >
                              + Ajouter un critère
                            </button>

                            <span>
                              {advancedFilterCount}
                              {' '}
                              filtre
                              {advancedFilterCount > 1
                                ? 's'
                                : ''}
                              {' '}
                              actif
                              {advancedFilterCount > 1
                                ? 's'
                                : ''}
                            </span>
                          </footer>
                        </div>
                      )}
                    </div>

                    <div
                      className="aduc-column-options"
                    >
                      <button
                        type="button"
                        className="aduc-column-options-trigger"
                        title="Options d’affichage"
                        aria-label="Choisir les colonnes affichées"
                        aria-expanded={
                          columnOptionsOpen
                        }
                        onClick={() => {
                          setFilterOptionsOpen(false)
                          setSavedSearchesOpen(false)
                          setColumnOptionsOpen(
                            previous =>
                              !previous
                          )
                        }}
                      >
                        <span aria-hidden="true">☷</span>
                        <span>Colonnes</span>
                      </button>

                      {columnOptionsOpen && (
                        <div
                          className={
                            "aduc-column-options-menu"
                          }
                        >
                          <div
                            className={
                              "aduc-column-options-title"
                            }
                          >
                            Colonnes affichées
                          </div>

                          {AD_EXPLORER_COLUMNS.map(
                            column => (
                              <label
                                key={column.id}
                                className={
                                  "aduc-column-option"
                                }
                              >
                                <input
                                  type="checkbox"
                                  checked={
                                    visibleColumnIds
                                      .includes(
                                        column.id
                                      )
                                  }
                                  disabled={
                                    Boolean(
                                      column.required
                                    )
                                  }
                                  onChange={() =>
                                    toggleAdExplorerColumn(
                                      column.id
                                    )
                                  }
                                />
                                <span>
                                  {column.label}
                                </span>
                              </label>
                            )
                          )}

                          <button
                            type="button"
                            className={
                              "aduc-column-reset"
                            }
                            onClick={
                              resetAdExplorerColumns
                            }
                          >
                            Réinitialiser
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div
                  className="aduc-table"
                  role="grid"
                  aria-multiselectable="true"
                  tabIndex={0}
                  onKeyDown={
                    handleAdExplorerSelectionKeyDown
                  }
                  title={
                    "Ctrl/Cmd + clic : ajouter ou retirer ; "
                    + "Maj + clic : selectionner une plage ; "
                    + "Ctrl/Cmd + A : tout selectionner ; "
                    + "Echap : vider la selection"
                  }
                >
                  {selectedObjectIds.length > 0 && (
                    <div
                      className="aduc-selection-actions"
                      role="toolbar"
                      aria-label="Actions sur la sélection"
                    >
                      <strong>
                        {selectedObjectIds.length}
                        {" "}
                        sélectionné(s)
                      </strong>

                      <button
                        type="button"
                        onClick={() =>
                          copyAdExplorerSelection(
                            "dn"
                          )
                        }
                      >
                        ⎙ Copier les DN
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          copyAdExplorerSelection(
                            "name"
                          )
                        }
                      >
                        ⎙ Copier les noms
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          copyAdExplorerSelection(
                            "csv"
                          )
                        }
                      >
                        ⇩ Copier CSV
                      </button>

                      {(
                        selectedObjectIds.length === 1
                        && isCopyableUserSource(
                          selectedObject
                        )
                      ) && (
                        <button
                          type="button"
                          onClick={() =>
                            openCopyUser(
                              selectedObject
                            )
                          }
                        >
                          👤 Copier utilisateur
                        </button>
                      )}

                      <button
                        type="button"
                        className="secondary"
                        onClick={
                          clearAdExplorerSelection
                        }
                      >
                        ✕ Désélectionner
                      </button>
                    </div>
                  )}

                  <div
                    className="aduc-table-row header"
                    style={{
                      gridTemplateColumns:
                        adExplorerGridTemplate
                    }}
                  >
                    {visibleColumns.map(column => (
                      <button
                        key={column.id}
                        type="button"
                        className={
                          "aduc-table-header-button"
                        }
                        onClick={() =>
                          toggleAdExplorerSort(
                            column.id
                          )
                        }
                        title={
                          `Trier par ${column.label}`
                        }
                        aria-sort={
                          viewSort.columnId ===
                          column.id
                            ? (
                                viewSort.direction ===
                                'desc'
                                  ? 'descending'
                                  : 'ascending'
                              )
                            : 'none'
                        }
                      >
                        {column.label}
                        {getAdExplorerSortIndicator(
                          column.id
                        )}
                      </button>
                    ))}
                  </div>

                  {loading ? (
                    <div className="aduc-empty">
                      Chargement depuis SRV-DC01...
                    </div>
                  ) : filteredViewItems.length === 0 ? (
                    <div className="aduc-empty">
                      Aucun objet dans cette vue.
                    </div>
                  ) : (
                    filteredViewItems.map(
                      (item, index) => (
                        <div
                          key={
                            item.distinguished_name
                            || item.sam_account_name
                            || index
                          }
                          role="row"
                          tabIndex={0}
                          aria-selected={
                            selectedObjectIds.includes(
                              getAdExplorerSelectionId(
                                item
                              )
                            )
                          }
                          className={
                            `aduc-table-row ${
                              selectedObjectIds.includes(
                                getAdExplorerSelectionId(
                                  item
                                )
                              )
                                ? "selected-object"
                                : ""
                            } ${
                              getAdExplorerSelectionId(
                                selectedObject
                              )
                              === getAdExplorerSelectionId(
                                item
                              )
                                ? "primary-selected-object"
                                : ""
                            }`
                          }
                          style={{
                            gridTemplateColumns:
                              adExplorerGridTemplate
                          }}
                          onClick={event =>
                            selectObject(
                              item,
                              event,
                              filteredViewItems
                            )
                          }
                          onDoubleClick={() => {
                            if (
                              isOuObject(item)
                              || isContainerObject(item)
                            ) {
                              loadNodeContent(
                                item,
                                getNodeKind(item)
                              )
                              return
                            }

                            openProperties(item)
                          }}
                          onContextMenu={event =>
                            openContextMenu(
                              event,
                              item,
                              'object'
                            )
                          }
                        >
                          {visibleColumns.map(
                            column => (
                              <span
                                key={column.id}
                                title={String(
                                  getAdExplorerColumnValue(
                                    item,
                                    column.id,
                                    {
                                      getObjectName,
                                      getObjectType,
                                      getObjectDescription:
                                        getGroupDescription,
                                    }
                                  ) || ''
                                )}
                              >
                                {column.id ===
                                'name' ? (
                                  <>
                                    <i>
                                      {getObjectType(
                                        item
                                      ).includes(
                                        'Groupe'
                                      )
                                        ? '👥'
                                        : getObjectType(
                                              item
                                            ).includes(
                                              'Utilisateur'
                                            )
                                          ? '👤'
                                          : [
                                                'Ordinateur',
                                                'Contrôleur de domaine'
                                              ].includes(
                                                getObjectType(
                                                  item
                                                )
                                              )
                                            ? '💻'
                                            : getObjectType(
                                                  item
                                                ) ===
                                                'Contact'
                                              ? '📇'
                                              : '📁'}
                                    </i>
                                    {getAdExplorerColumnValue(
                                      item,
                                      column.id,
                                      {
                                        getObjectName,
                                        getObjectType,
                                        getObjectDescription:
                                          getGroupDescription,
                                      }
                                    )}
                                  </>
                                ) : (
                                  getAdExplorerColumnValue(
                                    item,
                                    column.id,
                                    {
                                      getObjectName,
                                      getObjectType,
                                      getObjectDescription:
                                        getGroupDescription,
                                    }
                                  ) || '-'
                                )}
                              </span>
                            )
                          )}
                        </div>
                      )
                    )
                  )}
                </div>

                <footer className="aduc-list-footer">
                  <span>
                    {filteredViewItems.length} objet(s)
                  </span>
                  <span>
                    {selectedObjectIds.length}
                    {" "}
                    selectionne(s)
                  </span>
                  <span>
                    Affichage 1 - {filteredViewItems.length}
                    {" "}
                    sur {filteredViewItems.length}
                  </span>
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
                onOpenLinkedObject={openLinkedObject}
                onResolveLinkedObject={resolveLinkedObject}
                onClearManagedBy={target =>
                  objectUpdate.prepareClearManager(
                    target,
                    { openModal: true }
                  )
                }
                onCreateOu={target => openCreateOu(target)}
                onCreateContainer={target => openCreateContainer(target)}
                onCreateGroup={target => openCreateGroup(target)}
                onOpenMoveObject={target => openMoveObject(target)}
                onOpenUpdateObject={target => openUpdateObject(target)}
                onOpenRenameObject={target => openRenameObject(target)}
                onOpenDeleteObject={target => openDeleteObject(target)}
                onCopyUser={target => openCopyUser(target)}
                onPrepareAccountAction={prepareAccountAction}
                membersMode={membersMode}
                onMembersModeChange={(target, mode) =>
                  loadGroupMembers(target, {
                    recursive: mode === 'recursive',
                    forceJob: mode === 'recursive',
                  })
                }
                onLoadMembers={loadGroupMembers}
                onOpenAddMember={target => openAddMemberModal(target)}
                onRemoveMember={(group, member) => removeGroupMember(group, member)}
                onSetPrimaryGroup={
                  canManageActiveDirectory
                    ? setPrimaryGroupSimulation
                    : undefined
                }
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
        agentMode={adAgentMode}
        loadAgentMode={loadAdAgentMode}
        apiFetch={apiFetch}
        canManageActiveDirectory={canManageActiveDirectory}
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
          onOpenLinkedObject: openLinkedObject,
          onResolveLinkedObject: resolveLinkedObject,
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
          onCreateContainer: target => {
            setPropertiesModal(null)
            openCreateContainer(target)
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
          onCopyUser: target => {
            setPropertiesModal(null)
            openCopyUser(target)
          },
          onSetPrimaryGroup:
            canManageActiveDirectory
              ? setPrimaryGroupSimulation
              : undefined,
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
          membersMode,
          onMembersModeChange: (target, mode) =>
            loadGroupMembers(target, {
              recursive: mode === 'recursive',
              forceJob: mode === 'recursive',
            }),
          onLoadMembers: loadGroupMembers,
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
          openCreateContainer,
          openCreateGroup,
          openCreateContact,
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
