import { useState } from 'react'

import {
  cleanAdHistoryText,
  getObjectDn,
  getObjectType,
  isEitasManagedObject,
} from '../utils/adExplorerCore'

function useAdObjectUpdate({
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
  getMemberCandidateTitle,
}) {
  const [updateModal, setUpdateModal] = useState(null)
  const [updateForm, setUpdateForm] = useState({ description: '' })
  const [updateOriginalForm, setUpdateOriginalForm] = useState({ description: '' })
  const [managerSearchQuery, setManagerSearchQuery] = useState('')
  const [managerSearchResults, setManagerSearchResults] = useState([])
  const [managerSearchLoading, setManagerSearchLoading] = useState(false)
  const [managerSearchError, setManagerSearchError] = useState('')

  function getAdAttributeValue(item, ...names) {
      for (const name of names) {
        const value = item?.[name]

        if (value !== undefined && value !== null) {
          return String(value)
        }
      }

      return ''
    }

  function isUpdateUserTarget(target) {
    const objectClass = String(
      target?.objectClass
      || target?.object_class
      || target?.type
      || ''
    ).toLowerCase()

    return objectClass.includes('user')
      || getObjectType(target)
        .toLowerCase()
        .includes('utilisateur')
  }

  function isUpdateComputerTarget(target) {
    const objectClass = String(
      target?.objectClass
      || target?.object_class
      || target?.type
      || ''
    ).trim().toLowerCase()

    return objectClass === 'computer'
      || getObjectType(target) === 'Ordinateur'
  }

  function openUpdateObject(target) {
    if (!isEitasManagedObject(target)) {
      const message =
        'Action bloquée : cet objet est hors du périmètre OU=EITAS et reste accessible uniquement en lecture.'

      setStatus(message)
      setMessage?.(message)
      setContextMenu(null)
      return
    }

    if (!target) {
      setStatus('Aucun objet sélectionné pour la modification.')
      return
    }

    const dn = getObjectDn(target)

    if (!dn) {
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    const form = {
      description: getAdAttributeValue(
        target,
        'description'
      ),
      location: getAdAttributeValue(
        target,
        'location'
      ),
      displayName: getAdAttributeValue(
        target,
        'displayName',
        'display_name',
        'display_name_value'
      ),
      mail: getAdAttributeValue(
        target,
        'mail',
        'email'
      ),
      title: getAdAttributeValue(
        target,
        'title',
        'job_title'
      ),
      department: getAdAttributeValue(
        target,
        'department',
        'service'
      ),
      division: getAdAttributeValue(
        target,
        'division',
        'business_unit',
        'businessUnit'
      ),
      company: getAdAttributeValue(
        target,
        'company'
      ),
      physicalDeliveryOfficeName: getAdAttributeValue(
        target,
        'physicalDeliveryOfficeName',
        'office'
      ),
      employeeID: getAdAttributeValue(
        target,
        'employeeID',
        'employee_id',
        'EmployeeID'
      ),
      employeeNumber: getAdAttributeValue(
        target,
        'employeeNumber',
        'employee_number'
      ),
      manager: getAdAttributeValue(
        target,
        'manager',
        'manager_dn',
        'managerDn'
      ),
      telephoneNumber: getAdAttributeValue(
        target,
        'telephoneNumber',
        'telephone_number',
        'phone'
      ),
      mobile: getAdAttributeValue(
        target,
        'mobile',
        'mobilePhone'
      ),
      streetAddress: getAdAttributeValue(
        target,
        'streetAddress',
        'street_address'
      ),
      postalCode: getAdAttributeValue(
        target,
        'postalCode',
        'postal_code'
      ),
      l: getAdAttributeValue(
        target,
        'l',
        'city'
      ),
      st: getAdAttributeValue(
        target,
        'st',
        'state'
      ),
      co: getAdAttributeValue(
        target,
        'co',
        'country'
      )
    }

    resetManagerPicker()
    setContextMenu(null)
    setUpdateModal(target)
    setUpdateForm(form)
    setUpdateOriginalForm(form)
  }

  function updateObjectFormField(name, value) {
    setUpdateForm(previous => ({
      ...previous,
      [name]: value
    }))
  }

  function resetManagerPicker() {
    setManagerSearchQuery('')
    setManagerSearchResults([])
    setManagerSearchLoading(false)
    setManagerSearchError('')
  }

  function getManagerCandidateDn(candidate) {
    return String(
      candidate?.distinguished_name ||
      candidate?.dn ||
      ''
    )
  }

  function selectManagerCandidate(candidate) {
    const managerDn = getManagerCandidateDn(candidate)

    if (!managerDn) {
      setManagerSearchError(
        'Le Distinguished Name de cet utilisateur est introuvable.'
      )
      return
    }

    updateObjectFormField('manager', managerDn)
    setManagerSearchQuery('')
    setManagerSearchResults([])
    setManagerSearchError('')
  }

  function clearManagerSelection() {
    updateObjectFormField('manager', '')
    resetManagerPicker()
  }

  async function searchManagerCandidates() {
    const query = managerSearchQuery.trim()

    setManagerSearchResults([])
    setManagerSearchError('')

    if (query.length < 2) {
      setManagerSearchError(
        'Tape au moins 2 caractères pour rechercher un manager.'
      )
      return
    }

    setManagerSearchLoading(true)

    try {
      let users =
        await adDomainCatalog?.search?.({
          query,
          baseDn: 'DC=API,DC=LOCAL',
          types: ['user'],
          limit: 50,
          recursive: true,
        })

      if (!Array.isArray(users)) {
        users = await runJob(
          'search_users',
          {
            query,
            baseDn: 'DC=API,DC=LOCAL',
            limit: 50,
            recursive: true
          }
        )
      }

      const currentDn = String(
        getObjectDn(updateModal) || ''
      ).toLowerCase()

      const currentSam = String(
        updateModal?.sam_account_name ||
        updateModal?.samAccountName ||
        ''
      ).toLowerCase()

      const results = users
        .filter(candidate => {
          const candidateDn =
            getManagerCandidateDn(candidate)

          if (!candidateDn) return false

          const enabledValue =
            candidate?.enabled ??
            candidate?.Enabled

          const isDisabled =
            enabledValue === false ||
            enabledValue === 0 ||
            String(enabledValue || '')
              .trim()
              .toLowerCase() === 'false'

          if (isDisabled) return false

          const candidateSam = String(
            candidate?.sam_account_name ||
            candidate?.samAccountName ||
            ''
          ).toLowerCase()

          const isCurrentObject =
            candidateDn.toLowerCase() === currentDn ||
            (
              currentSam &&
              candidateSam &&
              candidateSam === currentSam
            )

          return !isCurrentObject
        })
        .sort((first, second) =>
          getMemberCandidateTitle(first).localeCompare(
            getMemberCandidateTitle(second),
            'fr',
            {
              sensitivity: 'base',
            }
          )
        )

      setManagerSearchResults(results)

      if (!results.length) {
        setManagerSearchError(
          'Aucun autre utilisateur Active Directory actif trouvé.'
        )
      }
    } catch (error) {
      setManagerSearchResults([])
      setManagerSearchError(
        error.message ||
        'Recherche de manager impossible.'
      )
    } finally {
      setManagerSearchLoading(false)
    }
  }

  async function submitUpdateObject(event) {
    event.preventDefault()

    if (!updateModal) return

    const objectDn = getObjectDn(updateModal)

    if (!objectDn) {
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    const properties = {}

    Object.entries(updateForm).forEach(([key, value]) => {
      const currentValue = value || ''
      const originalValue = updateOriginalForm?.[key] || ''

      if (currentValue !== originalValue) {
        properties[key] = currentValue
      }
    })

    if (Object.keys(properties).length === 0) {
      setStatus('Aucune modification à enregistrer.')
      return
    }

    setLoading(true)

    try {
      const job = await runAdAdminJob({
        action: 'update_object_properties',
        object_identity: objectDn,
        properties,
        created_by: 'react-admin'
      })

      const message = cleanAdHistoryText(job?.message || job?.output?.message || 'Propriétés objet AD modifiées')
      setStatus(message)
      setUpdateModal(null)
      resetManagerPicker()

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
      setStatus(err.message || 'Erreur pendant la modification AD.')
    } finally {
      setLoading(false)
    }
  }

  return {
    updateModal,
    setUpdateModal,
    submitUpdateObject,
    isUpdateComputerTarget,
    updateForm,
    updateObjectFormField,
    isUpdateUserTarget,
    clearManagerSelection,
    managerSearchQuery,
    setManagerSearchQuery,
    setManagerSearchResults,
    setManagerSearchError,
    managerSearchLoading,
    searchManagerCandidates,
    managerSearchError,
    managerSearchResults,
    getManagerCandidateDn,
    selectManagerCandidate,
    openUpdateObject,
  }
}

export default useAdObjectUpdate
