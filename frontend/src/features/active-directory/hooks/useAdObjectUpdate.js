import {
  AD_LOGON_HOURS_CLEAR_VALUE,
  getLogonHoursSubmissionValue,
  normalizeLogonHoursHex,
} from '../utils/adLogonRestrictions'

import { useRef, useState } from 'react'

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
  resolveUserUpdateTarget,
  resolveUserUpdateTargetSync,
  invalidateUserDetailsCache,
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
  const [
    pendingUserAccountOptionFields,
    setPendingUserAccountOptionFields
  ] = useState([])
  const updatePreparationRequestIdRef = useRef(0)
  const updateDirtyFieldsRef = useRef(new Set())

  function getAdAttributeValue(item, ...names) {
      for (const name of names) {
        const value = item?.[name]

        if (value !== undefined && value !== null) {
          return String(value)
        }
      }

      return ''
    }

  function getAdDateInputValue(item, ...names) {
    const rawValue = getAdAttributeValue(
      item,
      ...names
    )

    if (!rawValue) return ''

    const parsed = new Date(rawValue)

    if (!Number.isNaN(parsed.getTime())) {
      const year = String(parsed.getFullYear())
      const month = String(
        parsed.getMonth() + 1
      ).padStart(2, '0')
      const day = String(
        parsed.getDate()
      ).padStart(2, '0')

      return `${year}-${month}-${day}`
    }

    const isoDateMatch = String(rawValue).match(
      /^(\d{4})-(\d{2})-(\d{2})/
    )

    return isoDateMatch
      ? `${isoDateMatch[1]}-${isoDateMatch[2]}-${isoDateMatch[3]}`
      : ''
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

  function hasAdBooleanAttributeValue(
    item,
    ...names
  ) {
    for (const name of names) {
      if (
        !Object.prototype.hasOwnProperty.call(
          item || {},
          name
        )
      ) {
        continue
      }

      const value = item?.[name]

      if (typeof value === 'boolean') {
        return true
      }

      const normalized =
        String(value)
          .trim()
          .toLowerCase()

      if (
        normalized === 'true'
        || normalized === 'false'
      ) {
        return true
      }
    }

    return false
  }


  function hasOwnAdAttribute(
    target,
    ...names
  ) {
    return names.some(name =>
      Object.prototype.hasOwnProperty.call(
        target || {},
        name
      )
    )
  }


  function getNullableAdBooleanAttributeValue(
    target,
    ...names
  ) {
    for (const name of names) {
      if (
        !Object.prototype.hasOwnProperty.call(
          target || {},
          name
        )
      ) {
        continue
      }

      const value = target?.[name]

      if (
        value === null
        || value === undefined
        || String(value).trim() === ''
      ) {
        return null
      }

      if (typeof value === 'boolean') {
        return value
      }

      const normalized = String(value)
        .trim()
        .toLowerCase()

      if (
        normalized === 'true'
        || normalized === '1'
      ) {
        return true
      }

      if (
        normalized === 'false'
        || normalized === '0'
      ) {
        return false
      }

      return null
    }

    return null
  }


  function getMsTsAllowLogonFormValue(target) {
    const value =
      getNullableAdBooleanAttributeValue(
        target,
        'msTSAllowLogon',
        'ms_ts_allow_logon'
      )

    if (value === true) return 'allow'
    if (value === false) return 'deny'

    return 'inherit'
  }


  function getMsTsAllowLogonSubmissionValue(
    value
  ) {
    if (value === 'allow') return true
    if (value === 'deny') return false

    return null
  }


  function hasAuthoritativeUserAccountOptions(
    target
  ) {
    return (
      hasAdBooleanAttributeValue(
        target,
        'passwordNeverExpires',
        'password_never_expires',
        'PasswordNeverExpires'
      )
      && hasAdBooleanAttributeValue(
        target,
        'cannotChangePassword',
        'cannot_change_password',
        'CannotChangePassword'
      )
      && hasAdBooleanAttributeValue(
        target,
        'smartcardLogonRequired',
        'smartcard_logon_required',
        'SmartcardLogonRequired'
      )
      && hasAdBooleanAttributeValue(
        target,
        'accountNotDelegated',
        'account_not_delegated',
        'AccountNotDelegated'
      )
    )
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

  const userAccountOptionDefinitions = [
    {
      field: 'passwordNeverExpires',
      aliases: [
        'passwordNeverExpires',
        'password_never_expires',
        'PasswordNeverExpires'
      ]
    },
    {
      field: 'cannotChangePassword',
      aliases: [
        'cannotChangePassword',
        'cannot_change_password',
        'CannotChangePassword'
      ]
    },
    {
      field: 'smartcardLogonRequired',
      aliases: [
        'smartcardLogonRequired',
        'smartcard_logon_required',
        'SmartcardLogonRequired'
      ]
    },
    {
      field: 'accountNotDelegated',
      aliases: [
        'accountNotDelegated',
        'account_not_delegated',
        'AccountNotDelegated'
      ]
    }
  ]

  const userRdsProfileDefinitions = [
    {
      field: 'msTSAllowLogon',
      aliases: [
        'msTSAllowLogon',
        'ms_ts_allow_logon'
      ],
      nullableBoolean: true
    },
    {
      field: 'msTSProfilePath',
      aliases: [
        'msTSProfilePath',
        'ms_ts_profile_path'
      ]
    },
    {
      field: 'msTSHomeDirectory',
      aliases: [
        'msTSHomeDirectory',
        'ms_ts_home_directory'
      ]
    },
    {
      field: 'msTSHomeDrive',
      aliases: [
        'msTSHomeDrive',
        'ms_ts_home_drive'
      ]
    },
    {
      field: 'msTSInitialProgram',
      aliases: [
        'msTSInitialProgram',
        'ms_ts_initial_program'
      ]
    },
    {
      field: 'msTSWorkDirectory',
      aliases: [
        'msTSWorkDirectory',
        'ms_ts_work_directory'
      ]
    }
  ]

  function getMissingUserAccountOptionFields(
    target
  ) {
    return userAccountOptionDefinitions
      .filter(definition =>
        !hasAdBooleanAttributeValue(
          target,
          ...definition.aliases
        )
      )
      .map(definition => definition.field)
  }

  function getUserAccountOptionPatch(target) {
    return Object.fromEntries(
      userAccountOptionDefinitions.map(
        definition => [
          definition.field,
          getAdBooleanAttributeValue(
            target,
            ...definition.aliases
          )
        ]
      )
    )
  }

  function hasAuthoritativeUserRdsProfile(
    target
  ) {
    return userRdsProfileDefinitions.every(
      definition =>
        hasOwnAdAttribute(
          target,
          ...definition.aliases
        )
    )
  }

  function getMissingUserRdsProfileFields(
    target
  ) {
    return userRdsProfileDefinitions
      .filter(definition =>
        !hasOwnAdAttribute(
          target,
          ...definition.aliases
        )
      )
      .map(definition => definition.field)
  }

  function getUserRdsProfilePatch(target) {
    return Object.fromEntries(
      userRdsProfileDefinitions.map(
        definition => [
          definition.field,
          definition.nullableBoolean
            ? getMsTsAllowLogonFormValue(target)
            : getAdAttributeValue(
                target,
                ...definition.aliases
              )
        ]
      )
    )
  }

  async function prepareUpdateObject(
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

    const preparationRequestId =
      updatePreparationRequestIdRef.current + 1

    updatePreparationRequestIdRef.current =
      preparationRequestId

    updateDirtyFieldsRef.current.clear()

    if (!dn) {
      setStatus('DN introuvable pour cet objet AD.')
      return false
    }

    if (
      isUpdateUserTarget(target)
      && (
        !hasAuthoritativeUserAccountOptions(
          target
        )
        || !hasAuthoritativeUserRdsProfile(
          target
        )
      )
      && typeof resolveUserUpdateTargetSync
        === 'function'
    ) {
      const synchronousTarget =
        resolveUserUpdateTargetSync(target)

      if (synchronousTarget) {
        target = synchronousTarget
      }
    }

    const pendingAccountFields =
      isUpdateUserTarget(target)
        ? [
            ...getMissingUserAccountOptionFields(
              target
            ),
            ...getMissingUserRdsProfileFields(
              target
            )
          ]
        : []

    const shouldLoadAccountOptions =
      pendingAccountFields.length > 0
      && typeof resolveUserUpdateTarget
        === 'function'

    setPendingUserAccountOptionFields(
      pendingAccountFields
    )



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
      userPrincipalName: getAdAttributeValue(
        target,
        'userPrincipalName',
        'user_principal_name',
        'upn'
      ),
      accountExpires: getAdDateInputValue(
        target,
        'accountExpires',
        'account_expires',
        'AccountExpirationDate'
      ),
      passwordNeverExpires:
        getAdBooleanAttributeValue(
          target,
          'passwordNeverExpires',
          'password_never_expires',
          'PasswordNeverExpires'
        ),
      cannotChangePassword:
        getAdBooleanAttributeValue(
          target,
          'cannotChangePassword',
          'cannot_change_password',
          'CannotChangePassword'
        ),
      smartcardLogonRequired:
        getAdBooleanAttributeValue(
          target,
          'smartcardLogonRequired',
          'smartcard_logon_required',
          'SmartcardLogonRequired'
        ),
      accountNotDelegated:
        getAdBooleanAttributeValue(
          target,
          'accountNotDelegated',
          'account_not_delegated',
          'AccountNotDelegated'
        ),
      userWorkstations: getAdAttributeValue(
        target,
        'userWorkstations',
        'user_workstations',
        'LogonWorkstations'
      ),
      logonHours: normalizeLogonHoursHex(
        getAdAttributeValue(
          target,
          'logonHours',
          'logon_hours'
        )
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
      msTSAllowLogon:
        getMsTsAllowLogonFormValue(target),
      msTSProfilePath: getAdAttributeValue(
        target,
        'msTSProfilePath',
        'ms_ts_profile_path'
      ),
      msTSHomeDirectory: getAdAttributeValue(
        target,
        'msTSHomeDirectory',
        'ms_ts_home_directory'
      ),
      msTSHomeDrive: getAdAttributeValue(
        target,
        'msTSHomeDrive',
        'ms_ts_home_drive'
      ),
      msTSInitialProgram: getAdAttributeValue(
        target,
        'msTSInitialProgram',
        'ms_ts_initial_program'
      ),
      msTSWorkDirectory: getAdAttributeValue(
        target,
        'msTSWorkDirectory',
        'ms_ts_work_directory'
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

    if (shouldLoadAccountOptions) {
      const expectedDn =
        String(dn).trim().toLowerCase()

      void resolveUserUpdateTarget(target)
        .then(resolvedTarget => {
          if (
            updatePreparationRequestIdRef.current
            !== preparationRequestId
          ) {
            return
          }

          const resolvedDn =
            String(
              getObjectDn(resolvedTarget) || ''
            )
              .trim()
              .toLowerCase()

          if (
            !resolvedTarget
            || resolvedDn !== expectedDn
            || !hasAuthoritativeUserAccountOptions(
              resolvedTarget
            )
            || !hasAuthoritativeUserRdsProfile(
              resolvedTarget
            )
          ) {
            throw new Error(
              'Active Directory n\u2019a pas retourne '
              + 'toutes les options avancees du compte.'
            )
          }

          const resolvedPatch = {
            ...getUserAccountOptionPatch(
              resolvedTarget
            ),
            ...getUserRdsProfilePatch(
              resolvedTarget
            )
          }

          setUpdateModal(current => {
            const currentDn =
              String(
                getObjectDn(current) || ''
              )
                .trim()
                .toLowerCase()

            if (currentDn !== expectedDn) {
              return current
            }

            return {
              ...current,
              ...resolvedTarget
            }
          })

          setUpdateOriginalForm(previous => ({
            ...previous,
            ...resolvedPatch
          }))

          setUpdateForm(previous => {
            const next = {
              ...previous
            }

            for (
              const [field, value]
              of Object.entries(resolvedPatch)
            ) {
              if (
                !updateDirtyFieldsRef.current.has(
                  field
                )
              ) {
                next[field] = value
              }
            }

            return next
          })

          setPendingUserAccountOptionFields([])
          setUpdateSaveError('')
        })
        .catch(error => {
          if (
            updatePreparationRequestIdRef.current
            !== preparationRequestId
          ) {
            return
          }

          setUpdateSaveError(
            error?.message
            || (
              'Certaines options du compte '
              + 'restent indisponibles.'
            )
          )
        })
    } else if (
      pendingAccountFields.length > 0
    ) {
      setUpdateSaveError(
        'Certaines options du compte '
        + 'restent indisponibles.'
      )
    }

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

    updateDirtyFieldsRef.current.add(name)

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
      const rawCurrentValue = value ?? ''
      const rawOriginalValue =
        originalForm?.[key] ?? ''

      const currentValue =
        key === 'logonHours'
          ? getLogonHoursSubmissionValue(
              rawCurrentValue
            )
          : key === 'msTSAllowLogon'
            ? getMsTsAllowLogonSubmissionValue(
                rawCurrentValue
              )
            : rawCurrentValue

      const originalValue =
        key === 'logonHours'
          ? getLogonHoursSubmissionValue(
              rawOriginalValue
            )
          : key === 'msTSAllowLogon'
            ? getMsTsAllowLogonSubmissionValue(
                rawOriginalValue
              )
            : rawOriginalValue

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
    updatePreparationRequestIdRef.current += 1
    updateDirtyFieldsRef.current.clear()
    setPendingUserAccountOptionFields([])
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

  async function prepareClearManager(
    target,
    { openModal = true } = {}
  ) {
    const prepared = await prepareUpdateObject(
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
        const savedForm = {
          ...updateForm,
          logonHours:
            getLogonHoursSubmissionValue(
              updateForm.logonHours
            ),
        }

        invalidateUserDetailsCache?.(
          updateModal
        )

        setUpdateForm(savedForm)
        setUpdateOriginalForm(savedForm)
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
    logonHoursClearValue:
      AD_LOGON_HOURS_CLEAR_VALUE,
    updateSaveNotice,
    updateSaveError,
    pendingUserAccountOptionFields,
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
