import { useState } from 'react'

function useAdComputerCreation({
  adAgentMode,
  loadAdAgentMode,
  runAdAdminJob,
  loadComputersView,
  setMessage,
  cleanAdHistoryText,
  isComputerManagedDn,
  COMPUTERS_DN,
}) {
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

  return {
    createComputerModal,
    closeCreateComputerModal,
    createComputerLoading,
    submitCreateComputer,
    createComputerForm,
    updateCreateComputerField,
    createComputerConfirm,
    setCreateComputerConfirm,
    setCreateComputerError,
    createComputerError,
    getCreateComputerValidationError,
    openCreateComputerModal,
  }
}

export default useAdComputerCreation
