import { useState } from 'react'

import {
  EITAS_DN,
  cleanAdHistoryText,
  getObjectDn,
  getOuLabelFromDn,
  isEitasManagedDn,
  isEitasManagedObject,
  splitLdapDn,
} from '../utils/adExplorerCore'
import {
  getCreateUserOuItemsFromJob,
} from '../utils/adCreationOptions'

function useAdUserCreation({
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
}) {
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

  function normalizeCreateUserPart(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '.')
      .replace(/^\.+|\.+$/g, '')
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

  return {
    createUserModal,
    closeCreateUserModal,
    createUserLoading,
    submitCreateUser,
    createUserForm,
    updateCreateUserField,
    createUserOuLoading,
    createUserOuOptions,
    createUserConfirm,
    setCreateUserConfirm,
    setCreateUserError,
    createUserError,
    openCreateUser,
  }
}

export default useAdUserCreation
