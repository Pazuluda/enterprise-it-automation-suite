import { useState } from 'react'

import {
  EITAS_DN,
  cleanAdHistoryText,
  getObjectDn,
  getObjectName,
  isEitasManagedDn,
  isEitasManagedObject,
  splitLdapDn,
} from '../utils/adExplorerCore'
import {
  dedupeCreateUserOuOptions,
  getCreateUserOuItemsFromJob,
} from '../utils/adCreationOptions'

function useAdObjectMove({
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
}) {
  const [moveModal, setMoveModal] = useState(null)
  const [moveTargetDn, setMoveTargetDn] = useState('')
  const [moveOuOptions, setMoveOuOptions] = useState([])
  const [moveOuLoading, setMoveOuLoading] = useState(false)
  const [moveOuError, setMoveOuError] = useState('')

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

  return {
    moveModal,
    closeMoveModal,
    submitMoveObject,
    getMoveCurrentParentDn,
    moveOuOptions,
    moveTargetDn,
    setMoveTargetDn,
    setMoveOuError,
    moveOuLoading,
    getMoveOuDisplayLabel,
    moveOuError,
    getMoveValidationError,
    openMoveObject,
  }
}

export default useAdObjectMove
