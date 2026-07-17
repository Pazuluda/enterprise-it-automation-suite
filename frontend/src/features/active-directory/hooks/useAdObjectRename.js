import { useState } from 'react'

import {
  cleanAdHistoryText,
  getObjectDn,
  getObjectName,
  isEitasManagedObject,
} from '../utils/adExplorerCore'

function useAdObjectRename({
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
}) {
  const [renameModal, setRenameModal] = useState(null)
  const [renameNewName, setRenameNewName] = useState('')

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

  return {
    renameModal,
    setRenameModal,
    renameNewName,
    setRenameNewName,
    submitRenameObject,
    openRenameObject,
  }
}

export default useAdObjectRename
