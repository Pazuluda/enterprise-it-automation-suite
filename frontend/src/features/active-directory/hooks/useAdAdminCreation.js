import { useState } from 'react'

import {
  EITAS_DN,
  cleanAdHistoryText,
  getObjectDn,
  isEitasManagedDn,
  isEitasManagedObject,
} from '../utils/adExplorerCore'

function useAdAdminCreation({
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
}) {
  const [adminModal, setAdminModal] = useState(null)
  const [adminOuOptions, setAdminOuOptions] = useState([])
  const [adminOuLoading, setAdminOuLoading] = useState(false)
  const [adminForm, setAdminForm] = useState({
    name: '',
    description: '',
    sam_account_name: '',
    group_scope: 'Global',
    group_category: 'Security'
  })
  const [adminError, setAdminError] = useState('')

  function getAdminCreationOuDisplayLabel(dn) {
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

  function normalizeAdminCreationOptions(items) {
    const sourceItems = [
      {
        distinguished_name: EITAS_DN
      },
      ...(Array.isArray(items) ? items : [])
    ]

    return sortCreateUserOuOptions(
      dedupeCreateUserOuOptions(
        sourceItems
          .map(item => {
            const dn = String(
              getObjectDn(item)
              || item?.dn
              || item?.distinguished_name
              || ''
            ).trim()

            return {
              dn,
              label:
                getAdminCreationOuDisplayLabel(dn)
            }
          })
          .filter(option =>
            option.dn
            && isOuDn(option.dn)
            && isEitasManagedDn(option.dn)
          )
      )
    )
  }

  function getAdminCreationValidationError(
    form = adminForm,
    modal = adminModal
  ) {
    if (!modal) {
      return ''
    }

    const parentDn = String(
      form?.parent_dn || ''
    ).trim()

    const name = String(
      form?.name || ''
    ).trim()

    const forbiddenPattern =
      /[,+\=<>#;"\\]/

    if (!parentDn) {
      return 'Choisis une OU de destination.'
    }

    if (!isOuDn(parentDn)) {
      return (
        'La destination doit être le DN '
        + 'd’une unité d’organisation.'
      )
    }

    if (!isEitasManagedDn(parentDn)) {
      return (
        'Destination bloquée : la création '
        + 'doit rester sous OU=EITAS.'
      )
    }

    if (!name) {
      return 'Le nom est obligatoire.'
    }

    if (forbiddenPattern.test(name)) {
      return (
        'Le nom contient un caractère LDAP '
        + 'interdit.'
      )
    }

    if (modal.action === 'create_group') {
      const samAccountName = String(
        form?.sam_account_name || name
      ).trim()

      if (!samAccountName) {
        return 'Le SamAccountName est obligatoire.'
      }

      if (
        forbiddenPattern.test(samAccountName)
      ) {
        return (
          'Le SamAccountName contient un '
          + 'caractère LDAP interdit.'
        )
      }

      if (
        ![
          'Global',
          'Universal',
          'DomainLocal'
        ].includes(form?.group_scope)
      ) {
        return 'Le scope du groupe est invalide.'
      }

      if (
        ![
          'Security',
          'Distribution'
        ].includes(form?.group_category)
      ) {
        return 'Le type du groupe est invalide.'
      }
    }

    return ''
  }

  function getAdminCreationInlineError() {
    const explicitError = String(
      adminError || ''
    ).trim()

    if (explicitError) {
      return explicitError
    }

    const parentDn = String(
      adminForm?.parent_dn || ''
    ).trim()

    if (
      parentDn
      && (
        !isOuDn(parentDn)
        || !isEitasManagedDn(parentDn)
      )
    ) {
      return getAdminCreationValidationError()
    }

    const name = String(
      adminForm?.name || ''
    ).trim()

    const forbiddenPattern =
      /[,+\=<>#;"\\]/

    if (
      name
      && forbiddenPattern.test(name)
    ) {
      return getAdminCreationValidationError()
    }

    if (
      adminModal?.action === 'create_group'
    ) {
      const samAccountName = String(
        adminForm?.sam_account_name || ''
      ).trim()

      if (
        samAccountName
        && forbiddenPattern.test(
          samAccountName
        )
      ) {
        return getAdminCreationValidationError()
      }
    }

    return ''
  }

  function updateAdminFormField(field, value) {
    setAdminForm(current => ({
      ...current,
      [field]: value
    }))

    setAdminError('')
  }

  function closeAdminCreationModal() {
    if (adminLoading) {
      return
    }

    setAdminModal(null)
    setAdminOuOptions([])
    setAdminOuLoading(false)
    setAdminError('')
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

  async function loadAdminOuOptions(
    parentDn = ''
  ) {
    const searchBaseDn = EITAS_DN

    setAdminOuLoading(true)
    setAdminError('')

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
              'react-admin-create-ou-tree'
          })
        }
      )

      const jobId = created?.job?.id

      if (!jobId) {
        throw new Error(
          'Job list_ou_tree introuvable.'
        )
      }

      const completedJob =
        await waitForAdExplorerJob(jobId)

      const items =
        getCreateUserOuItemsFromJob(
          completedJob
        )

      let finalOptions =
        normalizeAdminCreationOptions(items)

      if (!finalOptions.length) {
        finalOptions =
          normalizeAdminCreationOptions(
            getFallbackCreateUserOuOptions(
              searchBaseDn
            )
          )
      }

      setAdminOuOptions(finalOptions)

      setAdminForm(current => {
        const currentDn = String(
          current.parent_dn || parentDn || ''
        ).trim()

        const currentExists =
          finalOptions.some(option =>
            option.dn.toUpperCase()
            === currentDn.toUpperCase()
          )

        if (
          currentDn
          && currentExists
          && isEitasManagedDn(currentDn)
        ) {
          return current
        }

        const preferred =
          getPreferredOuForAction(
            finalOptions,
            adminModal?.action,
            parentDn
          )

        return {
          ...current,
          parent_dn:
            preferred?.dn
            || parentDn
            || EITAS_DN
        }
      })
    } catch (error) {
      console.warn(
        'Impossible de charger l’arbre OU '
        + 'AD pour création OU/groupe',
        error
      )

      const fallbackOptions =
        normalizeAdminCreationOptions(
          getFallbackCreateUserOuOptions(
            searchBaseDn
          )
        )

      setAdminOuOptions(fallbackOptions)

      setAdminError(
        'Chargement complet des OU impossible. '
        + 'La liste locale ou le DN avancé '
        + 'restent disponibles.'
      )
    } finally {
      setAdminOuLoading(false)
    }
  }

  function openCreateOu(
    target = selectedNode
  ) {
    if (!isEitasManagedObject(target)) {
      const message =
        'Action bloquée : cet objet est hors '
        + 'du périmètre OU=EITAS et reste '
        + 'accessible uniquement en lecture.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

    loadAdAgentMode()

    const parentDn =
      getCreateAdminParentDn(target)

    if (
      !parentDn
      || !isEitasManagedDn(parentDn)
    ) {
      setMessage?.(
        'Sélectionne une OU EITAS de '
        + 'destination avant de créer une OU.'
      )
      return
    }

    setContextMenu(null)
    setAdminError('')
    setAdminOuOptions([])

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
      search_base_dn: EITAS_DN
    })

    window.setTimeout(
      () => loadAdminOuOptions(parentDn),
      0
    )
  }

  function openCreateGroup(
    target = selectedNode
  ) {
    if (!isEitasManagedObject(target)) {
      const message =
        'Action bloquée : cet objet est hors '
        + 'du périmètre OU=EITAS et reste '
        + 'accessible uniquement en lecture.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

    loadAdAgentMode()

    const parentDn =
      getCreateAdminParentDn(target)

    if (
      !parentDn
      || !isEitasManagedDn(parentDn)
    ) {
      setMessage?.(
        'Sélectionne une OU EITAS de '
        + 'destination avant de créer un groupe.'
      )
      return
    }

    setContextMenu(null)
    setAdminError('')
    setAdminOuOptions([])

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
      search_base_dn: EITAS_DN
    })

    window.setTimeout(
      () => loadAdminOuOptions(parentDn),
      0
    )
  }

  async function submitAdAdminJob(event) {
    event.preventDefault()

    if (!adminModal) {
      return
    }

    const validationError =
      getAdminCreationValidationError()

    if (validationError) {
      setAdminError(validationError)
      setStatus(validationError)
      return
    }

    const name = adminForm.name.trim()

    const description =
      adminForm.description.trim()

    const samAccountName = String(
      adminForm.sam_account_name || name
    ).trim()

    const parentDn = String(
      adminForm.parent_dn || ''
    ).trim()

    const actionLabel =
      adminModal.action === 'create_ou'
        ? 'La création de l’OU'
        : 'La création du groupe'

    const targetSummary =
      `${name} dans `
      + getAdminCreationOuDisplayLabel(
        parentDn
      )

    const confirmed =
      await confirmProductionAdAction(
        actionLabel,
        targetSummary
      )

    if (!confirmed) {
      return
    }

    setAdminLoading(true)
    setAdminError('')

    setStatus(
      adminModal.action === 'create_ou'
        ? 'Création de l’OU en cours...'
        : 'Création du groupe en cours...'
    )

    try {
      const payload = {
        action: adminModal.action,
        parent_dn: parentDn,
        name,
        description,
        created_by: 'react-admin'
      }

      if (
        adminModal.action === 'create_group'
      ) {
        payload.sam_account_name =
          samAccountName

        payload.group_scope =
          adminForm.group_scope

        payload.group_category =
          adminForm.group_category
      }

      const job = await runAdAdminJob(payload)

      const destinationLabel =
        getAdminCreationOuDisplayLabel(
          parentDn
        )

      const message = cleanAdHistoryText(
        adminModal.action === 'create_ou'
          ? `OU ${name} créée dans ${destinationLabel}.`
          : `Groupe ${name} créé dans ${destinationLabel}.`
      )

      setAdminModal(null)
      setAdminOuOptions([])
      setAdminError('')

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

      setAdminSuccess(message)
      setStatus(message)
      setMessage?.(message)
    } catch (error) {
      setAdminSuccess('')
      const message = cleanAdHistoryText(
        error?.message
        || 'Erreur pendant la création '
        + 'Active Directory.'
      )

      setAdminError(message)
      setStatus(message)
      setMessage?.(message)
    } finally {
      setAdminLoading(false)
    }
  }

  return {
    adminModal,
    setAdminModal,
    adminOuOptions,
    setAdminOuOptions,
    adminOuLoading,
    setAdminOuLoading,
    adminForm,
    setAdminForm,
    adminError,
    setAdminError,
    getAdminCreationOuDisplayLabel,
    normalizeAdminCreationOptions,
    getAdminCreationValidationError,
    getAdminCreationInlineError,
    updateAdminFormField,
    closeAdminCreationModal,
    getCreateAdminParentDn,
    loadAdminOuOptions,
    openCreateOu,
    openCreateGroup,
    submitAdAdminJob,
  }
}

export default useAdAdminCreation
