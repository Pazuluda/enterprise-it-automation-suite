import { useState } from 'react'

import {
  getObjectDn,
  getObjectName,
  isEitasManagedObject,
} from '../utils/adExplorerCore'

function useAdAccountActions({
  setMessage,
  setStatus,
  setContextMenu,
  adAgentMode,
  viewType,
  runAdAdminJob,
  loadComputersView,
  getSelectedAccountEnabledState,
}) {
  const [accountActionModal, setAccountActionModal] = useState(null)
  const [accountActionPassword, setAccountActionPassword] = useState('')
  const [accountActionConfirm, setAccountActionConfirm] = useState('')
  const [accountActionLoading, setAccountActionLoading] = useState(false)

  function getAccountActionLabel(action) {
    const labels = {
      enable_account: 'Activer le compte',
      disable_account: 'Désactiver le compte',
      reset_password: 'Réinitialiser le mot de passe',
      unlock_account: 'Déverrouiller le compte'
    }

    return labels[action] || action
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

  return {
    accountActionModal,
    setAccountActionModal,
    accountActionPassword,
    setAccountActionPassword,
    accountActionConfirm,
    setAccountActionConfirm,
    accountActionLoading,
    setAccountActionLoading,
    getAccountActionLabel,
    prepareAccountAction,
    submitAccountAction,
  }
}

export default useAdAccountActions
