import { useState } from 'react'

import {
  getObjectDn,
  getObjectName,
  isEitasManagedObject,
} from '../utils/adExplorerCore'

import {
  getAdAccountToggleAction,
} from '../utils/adAccountState'

import {
  buildAdPasswordResetPayload,
  createAdPasswordResetDraft,
} from '../utils/adPasswordReset'

function useAdAccountActions({
  setMessage,
  setStatus,
  setContextMenu,
  adAgentMode,
  loadAdAgentMode,
  viewType,
  runAdAdminJob,
  loadComputersView,
  refreshAccountTarget,
}) {
  const [accountActionModal, setAccountActionModal] = useState(null)
  const [
    passwordResetDraft,
    setPasswordResetDraft,
  ] = useState(() => createAdPasswordResetDraft())
  const [accountActionConfirm, setAccountActionConfirm] = useState('')
  const [accountActionLoading, setAccountActionLoading] = useState(false)
  const [
    accountActionModeLoading,
    setAccountActionModeLoading,
  ] = useState(false)

  function normalizeAccountActionMode(value) {
    const normalized = String(value || '')
      .trim()
      .toLowerCase()

    if (normalized === 'simulation') {
      return 'Simulation'
    }

    if (normalized === 'production') {
      return 'Production'
    }

    return null
  }

  async function resolveAccountActionMode() {
    setAccountActionModeLoading(true)

    try {
      const loadedMode =
        typeof loadAdAgentMode === 'function'
          ? await loadAdAgentMode()
          : adAgentMode

      return normalizeAccountActionMode(
        loadedMode
      )
    } catch {
      return null
    } finally {
      setAccountActionModeLoading(false)
    }
  }

  function updatePasswordResetDraft(name, value) {
    setPasswordResetDraft(previous => ({
      ...previous,
      [name]: value,
    }))
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

  async function prepareAccountAction(action, target) {
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

    const resolvedMode =
      await resolveAccountActionMode()

    if (!resolvedMode) {
      setMessage?.(
        'Mode agent indisponible : action de compte bloquée.'
      )
      return
    }

    let resolvedAction = action

    if (action === 'toggle_enabled') {
      resolvedAction =
        getAdAccountToggleAction(target)

      if (!resolvedAction) {
        setMessage?.(
          'État du compte inconnu : impossible de choisir automatiquement Activer/Désactiver.'
        )
        return
      }
    }

    setAccountActionModal({
      action: resolvedAction,
      target,
      targetName: getObjectName(target),
      targetDn,
      agentMode: resolvedMode,
    })

    setAccountActionConfirm('')
    setPasswordResetDraft(
      createAdPasswordResetDraft()
    )
  }

  async function submitAccountAction() {
    if (!accountActionModal) return

    const verifiedMode =
      await resolveAccountActionMode()

    if (!verifiedMode) {
      setMessage?.(
        'Mode agent indisponible : action de compte bloquée.'
      )
      return
    }

    if (
      verifiedMode
      !== accountActionModal.agentMode
    ) {
      setAccountActionModal(previous => ({
        ...previous,
        agentMode: verifiedMode,
      }))

      setAccountActionConfirm('')

      setMessage?.(
        `Le mode agent est maintenant ${verifiedMode}. Vérifie la modale puis relance l’action.`
      )
      return
    }

    if (
      verifiedMode === 'Production'
      && accountActionConfirm !== 'PRODUCTION'
    ) {
      setMessage?.(
        'Confirmation Production obligatoire : tape PRODUCTION.'
      )
      return
    }

    let passwordResetPayload = null

    if (
      accountActionModal.action
      === 'reset_password'
    ) {
      try {
        passwordResetPayload =
          buildAdPasswordResetPayload(
            passwordResetDraft
          )
      } catch (error) {
        setMessage?.(
          error?.message
          || 'Mot de passe temporaire invalide.'
        )
        return
      }
    }

    const payload = {
      action: accountActionModal.action,
      object_dn: accountActionModal.targetDn,
      created_by: 'react-admin'
    }

    if (passwordResetPayload) {
      Object.assign(
        payload,
        passwordResetPayload
      )
    }

    try {
      setAccountActionLoading(true)
      await runAdAdminJob(payload)

      let refreshWarning = ''

      try {
        if (viewType === 'computers') {
          await loadComputersView()
        } else if (
          typeof refreshAccountTarget === 'function'
        ) {
          await refreshAccountTarget(
            accountActionModal.target
          )
        }
      } catch (refreshError) {
        refreshWarning =
          refreshError?.message
          || 'Actualisation du compte impossible.'

        setStatus(
          `Action terminée, mais ${refreshWarning}`
        )
      }

      setAccountActionModal(null)
      setAccountActionConfirm('')
      setPasswordResetDraft(
        createAdPasswordResetDraft()
      )

      setMessage?.(
        refreshWarning
          ? `Action terminée, mais ${refreshWarning}`
          : `${getAccountActionLabel(
              accountActionModal.action
            )} terminée.`
      )
    } catch (err) {
      setMessage?.(err?.message || 'Erreur action Compte ADUC.')
    } finally {
      setAccountActionLoading(false)
    }
  }

  return {
    accountActionModal,
    setAccountActionModal,
    passwordResetDraft,
    updatePasswordResetDraft,
    accountActionConfirm,
    setAccountActionConfirm,
    accountActionLoading,
    setAccountActionLoading,
    accountActionModeLoading,
    getAccountActionLabel,
    prepareAccountAction,
    submitAccountAction,
  }
}

export default useAdAccountActions
