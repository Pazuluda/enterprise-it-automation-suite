import { useState } from 'react'

import {
  getObjectDn,
  isEitasManagedObject,
} from '../utils/adExplorerCore'

function useAdObjectDeletion({
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
}) {
  const [deleteModal, setDeleteModal] = useState(null)
  const [deleteConfirmDn, setDeleteConfirmDn] = useState('')
  const [deleteError, setDeleteError] = useState('')

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

  return {
    deleteModal,
    setDeleteModal,
    deleteConfirmDn,
    setDeleteConfirmDn,
    deleteError,
    setDeleteError,
    openDeleteObject,
    submitDeleteObject,
  }
}

export default useAdObjectDeletion
