import { useState } from 'react'

import {
  cleanAdHistoryText,
  getObjectDn,
  getObjectType,
  isOuObject,
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
  const [updateEditorOpen, setUpdateEditorOpen] = useState(false)
  const [updateForm, setUpdateForm] = useState({ description: '' })
  const [updateOriginalForm, setUpdateOriginalForm] = useState({ description: '' })
  const [managerSearchQuery, setManagerSearchQuery] = useState('')
  const [managerSearchResults, setManagerSearchResults] = useState([])
  const [managerSearchLoading, setManagerSearchLoading] = useState(false)
  const [managerSearchError, setManagerSearchError] = useState('')
  const [updateSaveNotice, setUpdateSaveNotice] = useState('')
  const [updateSaveError, setUpdateSaveError] = useState('')

  function getAdAttributeValue(item, ...names) {
      for (const name of names) {
        const value = item?.[name]

        if (value !== undefined && value !== null) {
          return String(value)
        }
      }

      return ''
    }

  function getAdBooleanAttributeValue(item, ...names) {
    for (const name of names) {
      const value = item?.[name]

      if (typeof value === 'boolean') return value
      if (String(value).toLowerCase() === 'true') return true
      if (String(value).toLowerCase() === 'false') return false
    }

    return false
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

  function isUpdateGroupTarget(target) {
    const objectClass = String(
      target?.objectClass
      || target?.object_class
      || target?.type
      || ''
    ).trim().toLowerCase()

    return objectClass === 'group'
      || getObjectType(target)
        .toLowerCase()
        .includes('groupe')
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

  function isUpdateContactTarget(target) {
    const objectClass = String(
      target?.objectClass
      || target?.object_class
      || target?.type
      || ''
    ).trim().toLowerCase()

    return objectClass === 'contact'
      || getObjectType(target) === 'Contact'
  }

  function isUpdateOrganizationalUnitTarget(target) {
    return isOuObject(target)
  }

  function prepareUpdateObject(
    target,
    { openModal = true } = {}
  ) {
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
      return false
    }

    const rawSamAccountName =
      getAdAttributeValue(
        target,
        'samAccountName',
        'sam_account_name',
        'sAMAccountName'
      )

    const form = {
      description: getAdAttributeValue(
        target,
        'description'
      ),
      location: getAdAttributeValue(
        target,
        'location'
      ),
      operatingSystem: getAdAttributeValue(
        target,
        'operatingSystem',
        'operating_system'
      ),
      operatingSystemVersion: getAdAttributeValue(
        target,
        'operatingSystemVersion',
        'operating_system_version'
      ),
      operatingSystemServicePack: getAdAttributeValue(
        target,
        'operatingSystemServicePack',
        'operating_system_service_pack'
      ),
      displayName: getAdAttributeValue(
        target,
        'displayName',
        'display_name',
        'display_name_value'
      ),
      givenName: getAdAttributeValue(
        target,
        'givenName',
        'given_name',
        'first_name'
      ),
      initials: getAdAttributeValue(
        target,
        'initials'
      ),
      sn: getAdAttributeValue(
        target,
        'sn',
        'surname',
        'last_name'
      ),
      mail: getAdAttributeValue(
        target,
        'mail',
        'email'
      ),
      wWWHomePage: getAdAttributeValue(
        target,
        'wWWHomePage',
        'www_home_page',
        'website'
      ),
      info: getAdAttributeValue(
        target,
        'info',
        'notes',
        'remarks'
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
      profilePath: getAdAttributeValue(
        target,
        'profilePath',
        'profile_path'
      ),
      scriptPath: getAdAttributeValue(
        target,
        'scriptPath',
        'script_path'
      ),
      homeDirectory: getAdAttributeValue(
        target,
        'homeDirectory',
        'home_directory'
      ),
      homeDrive: getAdAttributeValue(
        target,
        'homeDrive',
        'home_drive'
      ),
      samAccountName:
        isUpdateComputerTarget(target)
          ? rawSamAccountName.replace(/\$$/, '')
          : rawSamAccountName,
      groupScope: getAdAttributeValue(
        target,
        'groupScope',
        'group_scope'
      ),
      groupCategory: getAdAttributeValue(
        target,
        'groupCategory',
        'group_category'
      ),
      managedBy: getAdAttributeValue(
        target,
        'managedBy',
        'managed_by',
        'managed_by_dn',
        'managedByDn'
      ),
      telephoneNumber: getAdAttributeValue(
        target,
        'telephoneNumber',
        'telephone_number',
        'phone'
      ),
      homePhone: getAdAttributeValue(
        target,
        'homePhone',
        'home_phone'
      ),
      facsimileTelephoneNumber: getAdAttributeValue(
        target,
        'facsimileTelephoneNumber',
        'facsimile_telephone_number',
        'fax'
      ),
      pager: getAdAttributeValue(
        target,
        'pager'
      ),
      ipPhone: getAdAttributeValue(
        target,
        'ipPhone',
        'ip_phone'
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
      postOfficeBox: getAdAttributeValue(
        target,
        'postOfficeBox',
        'post_office_box'
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
      c: getAdAttributeValue(
        target,
        'c',
        'country_alpha2'
      ).toUpperCase(),
      co: getAdAttributeValue(
        target,
        'co',
        'country'
      ),
      countryCode: getAdAttributeValue(
        target,
        'countryCode',
        'country_numeric_code'
      ),
      protectedFromAccidentalDeletion: getAdBooleanAttributeValue(
        target,
        'protectedFromAccidentalDeletion',
        'protected_from_accidental_deletion'
      )
    }

    setUpdateSaveNotice('')
    setUpdateSaveError('')
    resetManagerPicker()
    setContextMenu(null)
    setUpdateModal(target)
    setUpdateForm(form)
    setUpdateOriginalForm(form)
    setUpdateEditorOpen(openModal)

    return true
  }

  function openUpdateObject(target) {
    return prepareUpdateObject(
      target,
      { openModal: true }
    )
  }

  function updateObjectFormField(name, value) {
    setUpdateSaveNotice('')
    setUpdateSaveError('')

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

  function getChangedUpdateProperties(
    form = updateForm,
    originalForm = updateOriginalForm
  ) {
    const properties = {}

    Object.entries(form || {}).forEach(([key, value]) => {
      const currentValue = value ?? ''
      const originalValue = originalForm?.[key] ?? ''

      if (
        String(currentValue) !==
        String(originalValue)
      ) {
        properties[key] = currentValue
      }
    })

    return properties
  }

  const hasUpdateChanges =
    Object.keys(
      getChangedUpdateProperties()
    ).length > 0

  function closeUpdateObject() {
    setUpdateSaveNotice('')
    setUpdateSaveError('')
    setUpdateEditorOpen(false)
    setUpdateModal(null)
    resetManagerPicker()
  }


  function getManagerCandidateDn(candidate) {
    return String(
      candidate?.distinguished_name ||
      candidate?.dn ||
      ''
    )
  }

  function getManagerPropertyName(
    target = updateModal
  ) {
    if (isUpdateUserTarget(target)) {
      return 'manager'
    }

    if (
      isUpdateGroupTarget(target) ||
      isUpdateComputerTarget(target) ||
      isUpdateOrganizationalUnitTarget(target)
    ) {
      return 'managedBy'
    }

    return 'manager'
  }

  function selectManagerCandidate(candidate) {
    const managerDn = getManagerCandidateDn(candidate)

    if (!managerDn) {
      setManagerSearchError(
        'Le nom distinctif de cet utilisateur est introuvable.'
      )
      return
    }

    const propertyName =
      getManagerPropertyName()

    updateObjectFormField(
      propertyName,
      managerDn
    )
    setManagerSearchQuery('')
    setManagerSearchResults([])
    setManagerSearchError('')
  }

  function prepareClearManager(
    target,
    { openModal = true } = {}
  ) {
    const prepared = prepareUpdateObject(
      target,
      { openModal }
    )

    if (!prepared) return false

    const propertyName =
      getManagerPropertyName(target)

    setUpdateForm(previous => ({
      ...previous,
      [propertyName]: '',
    }))

    resetManagerPicker()

    return true
  }


  function clearManagerSelection() {
    const propertyName =
      getManagerPropertyName()

    updateObjectFormField(
      propertyName,
      ''
    )
    resetManagerPicker()
  }

  async function searchManagerCandidates() {
    const query = managerSearchQuery.trim()

    setManagerSearchResults([])
    setManagerSearchError('')

    if (query.length < 2) {
      setManagerSearchError(
        'Tape au moins 2 caractères pour rechercher un gestionnaire.'
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
        'Recherche de gestionnaire impossible.'
      )
    } finally {
      setManagerSearchLoading(false)
    }
  }

  async function submitUpdateObject(
    event,
    { closeOnSuccess = true } = {}
  ) {
    event?.preventDefault?.()

    if (!updateModal) return false

    const objectDn = getObjectDn(updateModal)

    if (!objectDn) {
      setStatus('DN introuvable pour cet objet AD.')
      return
    }

    const properties =
      getChangedUpdateProperties()

    if (Object.keys(properties).length === 0) {
      setStatus('Aucune modification à enregistrer.')
      return false
    }

    setUpdateSaveNotice('')
    setUpdateSaveError('')
    setLoading(true)

    try {
      const job = await runAdAdminJob({
        action: 'update_object_properties',
        object_identity: objectDn,
        properties,
        created_by: 'react-admin'
      })

      const failed =
        String(job?.status || '').toLowerCase() === 'failed' ||
        job?.success === false

      if (failed) {
        const failureMessage = cleanAdHistoryText(
          job?.message ||
          job?.output?.error ||
          job?.error ||
          'La modification Active Directory a échoué.'
        )

        throw new Error(failureMessage)
      }

      const message = cleanAdHistoryText(job?.message || job?.output?.message || 'Propriétés objet AD modifiées')
      setStatus(message)

      setUpdateSaveNotice(
        message.toLowerCase().includes('simulation')
          ? 'Simulation réussie : Active Directory n’a pas été modifié.'
          : 'Propriétés enregistrées avec succès.'
      )
      if (closeOnSuccess) {
        closeUpdateObject()
      } else {
        setUpdateOriginalForm({
          ...updateForm
        })
        setUpdateEditorOpen(false)
      }

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

      return true
    } catch (err) {
      const errorMessage = cleanAdHistoryText(
        err?.message ||
        'Erreur pendant la modification AD.'
      )

      setUpdateSaveNotice('')
      setUpdateSaveError(errorMessage)
      setStatus(errorMessage)
      setMessage?.(errorMessage)

      try {
        await loadAdAdminHistory()
      } catch {
        // L’erreur principale doit rester visible.
      }

      return false
    } finally {
      setLoading(false)
    }
  }

  return {
    updateModal:
      updateEditorOpen
        ? updateModal
        : null,
    updateTarget: updateModal,
    updateEditorOpen,
    setUpdateModal,
    setUpdateEditorOpen,
    prepareUpdateObject,
    closeUpdateObject,
    submitUpdateObject,
    hasUpdateChanges,
    getChangedUpdateProperties,
    updateOriginalForm,
    updateSaveNotice,
    updateSaveError,
    isUpdateComputerTarget,
    isUpdateContactTarget,
    isUpdateOrganizationalUnitTarget,
    updateForm,
    updateObjectFormField,
    isUpdateUserTarget,
    isUpdateGroupTarget,
    clearManagerSelection,
    prepareClearManager,
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
