import {
  useEffect,
  useState,
} from 'react'

import {
  isEitasManagedDn,
  getObjectName,
  getObjectType,
  getObjectDn,
  isOuObject,
  formatAdValue,
  getObjectMetaRows,
  isGroupObject,
  formatAdHistoryAction,
  formatAdHistoryDate,
  formatAdHistoryStatus,
  formatAdHistoryMessage,
} from '../utils/adExplorerCore'

function ObjectDetailsPanel({ object, selectedNode, memberItems, membersLoading, membersError, historyItems, historyLoading, historyError, historyFilter, onHistoryFilterChange, onOpenHistoryJob, onLoadHistory, onCopyDn, onExplore, onCreateOu, onCreateGroup, onOpenMoveObject, onOpenUpdateObject, onOpenRenameObject, onOpenDeleteObject, onPrepareAccountAction, onLoadMembers, onOpenAddMember, onRemoveMember, onReloadObject, onOpenLinkedObject }) {
  const [activeDetailsTab, setActiveDetailsTab] = useState('general')
  const displayed = object || selectedNode
  const hasObject = Boolean(displayed)
  const rows = getObjectMetaRows(displayed)
  const dn = getObjectDn(displayed)
  const isManagedScope = isEitasManagedDn(dn)
  const type = getObjectType(displayed)
  const objectName = hasObject ? getObjectName(displayed) : 'Aucun objet sélectionné'
  const objectClass = String(
    displayed?.objectClass ||
    displayed?.object_class ||
    displayed?.type ||
    ''
  ).toLowerCase()

  const isComputerContainer =
    objectClass === 'computer-container'

  const isOu = isOuObject(displayed)
  const isGroup = isGroupObject(displayed)
  const isUser =
    type.includes('Utilisateur') ||
    objectClass === 'user'

  const isComputer =
    !isComputerContainer &&
    (
      type === 'Ordinateur' ||
      objectClass === 'computer'
    )
  const isContact = type === 'Contact' || objectClass === 'contact'
  const members = Array.isArray(memberItems) ? memberItems : []
  const history = Array.isArray(historyItems) ? historyItems : []

  function getHistoryStatus(job) {
    if (job?.status === 'failed' || job?.success === false) return 'failed'
    if (job?.status === 'processing') return 'processing'
    if (job?.status === 'pending') return 'pending'
    if (job?.status === 'completed' || job?.success === true) return 'completed'
    return job?.status || 'unknown'
  }

  function getHistoryCounter(filterValue) {
    return history.filter(job => {
      const status = getHistoryStatus(job)

      if (filterValue === 'all') return true
      if (filterValue === 'success') return status === 'completed'
      if (filterValue === 'running') return status === 'processing' || status === 'pending'
      if (filterValue === 'failed') return status === 'failed'
      if (filterValue === 'members') return ['add_group_member', 'remove_group_member'].includes(job.action)
      if (filterValue === 'create') return ['create_ou', 'create_group', 'create_user', 'create_computer'].includes(job.action)
      if (filterValue === 'delete') return job.action === 'delete_object'
      if (filterValue === 'edit') return ['update_object_properties', 'rename_object'].includes(job.action)
      if (filterValue === 'move') return job.action === 'move_object'

      return true
    }).length
  }

  const filteredHistory = history.filter(job => {
    const status = getHistoryStatus(job)

    if (historyFilter === 'all') return true
    if (historyFilter === 'success') return status === 'completed'
    if (historyFilter === 'running') return status === 'processing' || status === 'pending'
    if (historyFilter === 'failed') return status === 'failed'
    if (historyFilter === 'members') return ['add_group_member', 'remove_group_member'].includes(job.action)
    if (historyFilter === 'create') return ['create_ou', 'create_group', 'create_user', 'create_computer'].includes(job.action)
    if (historyFilter === 'delete') return job.action === 'delete_object'
    if (historyFilter === 'edit') return ['update_object_properties', 'rename_object'].includes(job.action)
    if (historyFilter === 'move') return job.action === 'move_object'
    return true
  })

  const historyFilterOptions = [
    ['all', 'Tout'],
    ['success', 'Succès'],
    ['running', 'En cours'],
    ['failed', 'Échecs'],
    ['create', 'Créations'],
    ['delete', 'Suppressions'],
    ['edit', 'Modifs'],
    ['move', 'Déplacements'],
    ['members', 'Membres']
  ].map(([value, label]) => ({
    value,
    label,
    count: getHistoryCounter(value)
  }))

  function pickAdField(names) {
    for (const name of names) {
      const value = displayed?.[name]
      if (value !== null && value !== undefined && String(value).trim() !== '') {
        return value
      }
    }

    return ''
  }

  function boolLabel(value) {
    if (value === true || String(value).toLowerCase() === 'true') return 'Oui'
    if (value === false || String(value).toLowerCase() === 'false') return 'Non'
    if (String(value).trim() === '1') return 'Oui'
    if (String(value).trim() === '0') return 'Non'
    return value || ''
  }

  function getAccountStatus() {
    const locked = pickAdField(['locked_out', 'lockedOut', 'LockedOut'])
    const enabled = pickAdField(['enabled', 'Enabled'])
    const disabled = pickAdField(['disabled', 'Disabled'])
    const passwordExpired = pickAdField(['password_expired', 'passwordExpired', 'PasswordExpired'])

    if (locked === true || String(locked).toLowerCase() === 'true') return 'Verrouillé'
    if (enabled === false || String(enabled).toLowerCase() === 'false') return 'Désactivé'
    if (disabled === true || String(disabled).toLowerCase() === 'true') return 'Désactivé'
    if (passwordExpired === true || String(passwordExpired).toLowerCase() === 'true') return 'MDP expiré'
    if (enabled === true || String(enabled).toLowerCase() === 'true') return 'Activé'

    return 'État inconnu'
  }

  function getAccountStatusClass() {
    const status = getAccountStatus().toLowerCase()

    if (status.includes('verrouillé')) return 'locked'
    if (status.includes('désactivé')) return 'disabled'
    if (status.includes('expiré')) return 'expired'
    if (status.includes('activé')) return 'enabled'

    return 'unknown'
  }
  function formatOptionalDateValue(value) {
    return value ? formatAdHistoryDate(value) : ''
  }


  const generalRows = rows.length ? rows.map(row => [row.label, row.value, row.long]) : [
    ['Nom', objectName],
    ['Type', type],
    ['Description', pickAdField(['description'])],
    ['Nom de compte SAM', pickAdField(['sam_account_name', 'samAccountName', 'sAMAccountName'])],
    ['UPN', pickAdField(['user_principal_name', 'userPrincipalName', 'upn'])]
  ]

  const accountRows = [
    ['État du compte', getAccountStatus()],
    ['Nom de compte SAM', pickAdField(['sam_account_name', 'samAccountName', 'sAMAccountName'])],
    ['UPN', pickAdField(['user_principal_name', 'userPrincipalName', 'upn'])],
    ['Activé', boolLabel(pickAdField(['enabled', 'Enabled']))],
    ['Verrouillé', boolLabel(pickAdField(['locked_out', 'lockedOut', 'LockedOut']))],
    ['Mot de passe expiré', boolLabel(pickAdField(['password_expired', 'passwordExpired', 'PasswordExpired']))],
    ['Mot de passe jamais expiré', boolLabel(pickAdField(['password_never_expires', 'passwordNeverExpires', 'PasswordNeverExpires']))],
    ['Ne peut pas changer MDP', boolLabel(pickAdField(['cannot_change_password', 'cannotChangePassword', 'CannotChangePassword']))],
    ['Dernier changement MDP', formatOptionalDateValue(pickAdField(['password_last_set', 'passwordLastSet', 'PasswordLastSet']))],
    ['Dernière connexion', formatAdHistoryDate(pickAdField(['last_logon_date', 'lastLogonDate', 'last_logon', 'lastLogon', 'lastLogonTimestamp', 'LastLogonDate']))],
    ['Dernière erreur MDP', pickAdField(['last_bad_password_attempt', 'lastBadPasswordAttempt', 'LastBadPasswordAttempt'])],
    ['Tentatives échouées', pickAdField(['bad_logon_count', 'badLogonCount', 'BadLogonCount'])],
    ['Expiration compte', pickAdField(['account_expires', 'accountExpires', 'AccountExpirationDate'])]
  ].filter(([, value]) => value !== '' && value !== null && value !== undefined)

  const objectRows = [
    ['DN', dn, true],
    ['Nom canonique', pickAdField(['canonical_name', 'canonicalName']), true],
    ['Classe d’objet', type],
    ['GUID de l’objet', pickAdField(['object_guid', 'objectGUID', 'guid'])],
    ['SID', pickAdField(['sid', 'objectSid'])],
    ['Créé le', formatAdHistoryDate(pickAdField(['created_at', 'whenCreated', 'created']))],
    ['Modifié le', formatAdHistoryDate(pickAdField(['updated_at', 'whenChanged', 'modified']))],
    ['Protection suppression accidentelle', boolLabel(pickAdField(['protected_from_accidental_deletion', 'protectedFromAccidentalDeletion']))]
  ].filter(([, value]) => value !== '' && value !== null && value !== undefined)

    const orgValue = names => pickAdField(names)

    const managerDn = orgValue([
      'manager',
      'manager_dn',
      'managerDn'
    ])

    const orgRows = [
      ['Titre / poste', orgValue(['title', 'job_title', 'poste'])],
      ['Service', orgValue(['department', 'service'])],
      ['Division', orgValue(['division', 'business_unit', 'businessUnit'])],
      ['Société', orgValue(['company'])],
      ['Bureau', orgValue(['office', 'physicalDeliveryOfficeName'])]
    ].filter(([, value]) => value !== '' && value !== null && value !== undefined)

    const hrRows = [
      [
        'Identifiant salarié',
        orgValue([
          'employee_id',
          'employeeID',
          'EmployeeID',
          'employee_number',
          'employeeNumber'
        ])
      ],
      ['Gestionnaire', managerDn, true]
    ].filter(([, value]) => value !== '' && value !== null && value !== undefined)

  const addressRows = [
    [
      'Adresse',
      orgValue([
        'street_address',
        'streetAddress',
      ]),
      true,
    ],
    [
      'Boîte postale',
      orgValue([
        'post_office_box',
        'postOfficeBox',
      ]),
    ],
    [
      'Ville',
      orgValue([
        'city',
        'l',
      ]),
    ],
    [
      'Région / département',
      orgValue([
        'state',
        'st',
      ]),
    ],
    [
      'Code postal',
      orgValue([
        'postal_code',
        'postalCode',
      ]),
    ],
    [
      'Pays',
      orgValue([
        'country',
        'co',
        'c',
      ]),
    ],
  ].filter(
    ([, value]) =>
      value !== '' &&
      value !== null &&
      value !== undefined
  )

  const phoneRows = [
    [
      'Téléphone professionnel',
      orgValue([
        'telephone_number',
        'telephoneNumber',
        'phone',
      ]),
    ],
    [
      'Mobile',
      orgValue([
        'mobile',
        'mobilePhone',
      ]),
    ],
    [
      'Télécopie',
      orgValue([
        'facsimile_telephone_number',
        'facsimileTelephoneNumber',
      ]),
    ],
    [
      'Pager',
      orgValue([
        'pager',
      ]),
    ],
    [
      'Téléphone IP',
      orgValue([
        'ip_phone',
        'ipPhone',
      ]),
    ],
    [
      'E-mail',
      orgValue([
        'mail',
        'email',
        'emailAddress',
      ]),
    ],
  ].filter(
    ([, value]) =>
      value !== '' &&
      value !== null &&
      value !== undefined
  )

  const computerEnabledValue = orgValue([
    'enabled',
    'Enabled'
  ])

  const computerEnabledText =
    computerEnabledValue === true ||
    String(computerEnabledValue || '')
      .toLowerCase() === 'true'
      ? 'Activé'
      : computerEnabledValue === false ||
          String(computerEnabledValue || '')
            .toLowerCase() === 'false'
        ? 'Désactivé'
        : ''

  const machineRows = [
    ['État du compte machine', computerEnabledText],
    [
      'Nom DNS',
      orgValue([
        'dns_host_name',
        'dnsHostName'
      ])
    ],
    [
      'Adresse IPv4',
      orgValue([
        'ipv4_address',
        'ipv4Address'
      ])
    ],
    [
      'Système d’exploitation',
      orgValue([
        'operating_system',
        'operatingSystem'
      ])
    ],
    [
      'Version du système',
      orgValue([
        'operating_system_version',
        'operatingSystemVersion'
      ])
    ],
    [
      'Service Pack',
      orgValue([
        'operating_system_service_pack',
        'operatingSystemServicePack'
      ])
    ],
    [
      'Dernière connexion',
      formatAdHistoryDate(
        orgValue([
          'last_logon_date',
          'last_logon',
          'lastLogonTimestamp',
          'lastLogonDate'
        ])
      )
    ],
    [
      'Mot de passe machine modifié',
      formatOptionalDateValue(
        orgValue([
          'password_last_set',
          'passwordLastSet'
        ])
      )
    ],
  ].filter(
    ([, value]) =>
      value !== '' &&
      value !== null &&
      value !== undefined
  )

  const locationRows = [
    [
      'Emplacement physique',
      orgValue([
        'location',
      ]),
    ],
    [
      'Bureau',
      orgValue([
        'office',
        'physicalDeliveryOfficeName',
      ]),
    ],
  ].filter(
    ([, value]) =>
      value !== '' &&
      value !== null &&
      value !== undefined
  )

  const managedByDn = orgValue([
    'managed_by',
    'managedBy',
  ])

  const tabs = [
    ['general', 'Général'],

    ...(isUser
      ? [
          ['account', 'Compte'],
          ['address', 'Adresse'],
          ['phones', 'Téléphones'],
          ['organization', 'Organisation'],
          ['membership', 'Membre de'],
        ]
      : []),

    ...(isGroup
      ? [
          ['members', 'Membres'],
          ['membership', 'Membre de'],
          ['managedBy', 'Géré par'],
        ]
      : []),

    ...(isComputer
      ? [
          ['account', 'Compte'],
          ['machine', 'Système'],
          ['location', 'Emplacement'],
          ['managedBy', 'Géré par'],
          ['membership', 'Membre de'],
        ]
      : []),

    ...(isContact ? [['address', 'Adresse'], ['phones', 'Téléphones'], ['organization', 'Organisation'], ['managedBy', 'Géré par']] : []),
    ...(isOu ? [['managedBy', 'Géré par']] : []),
    ['object', 'Objet'],
    ['history', 'Historique'],
  ]

  const displayedIdentity = [
    dn,
    objectName,
    type,
  ].join('|')

  useEffect(() => {
    setActiveDetailsTab('general')
  }, [displayedIdentity])

  function renderGrid(gridRows, emptyText = 'Aucune propriété disponible.') {
    const cleanRows = gridRows.filter(([, value]) => value !== '' && value !== null && value !== undefined)

    if (!cleanRows.length) {
      return <p className="aduc-details-empty-mini">{emptyText}</p>
    }

    return (
      <div className="aduc-aduc-grid">
        {cleanRows.map(([label, value, long]) => (
          <div className={long || String(label).toLowerCase().includes('dn') ? 'wide' : ''} key={label}>
            <span>{label}</span>
            {long || String(label).toLowerCase().includes('dn') ? (
              <code>{Array.isArray(value) ? value.join(', ') : formatAdValue(value)}</code>
            ) : (
              <strong>{Array.isArray(value) ? value.join(', ') : formatAdValue(value)}</strong>
            )}
          </div>
        ))}
      </div>
    )
  }

  function renderAccountTab() {
    return (
      <div className="aduc-tab-card aduc-account-tab">
        <div className="aduc-account-head">
          <div>
            <h4>Compte</h4>
            <span className={`aduc-account-status ${getAccountStatusClass()}`}>
              {getAccountStatus()}
            </span>
          </div>

          <div className="aduc-account-actions">
            <button type="button" disabled={!isManagedScope || isComputer} onClick={() => onPrepareAccountAction?.('toggle_enabled', displayed)}>
              {getAccountStatus().toLowerCase().includes('désactivé') ? 'Activer' : 'Désactiver'}
            </button>

            {isUser && (
              <>
                <button type="button" disabled={!isManagedScope || isComputer} onClick={() => onPrepareAccountAction?.('reset_password', displayed)}>
                  Réinitialiser MDP
                </button>

                <button type="button" disabled={!isManagedScope || isComputer} onClick={() => onPrepareAccountAction?.('unlock_account', displayed)}>
                  Déverrouiller
                </button>
              </>
            )}
          </div>
        </div>

        {renderGrid(accountRows, 'Aucune information de compte disponible.')}

        <div className="aduc-account-note">

          <p></p>
        </div>
      </div>
    )
  }
  function getGroupNameFromDn(groupDn) {
      const text = String(groupDn || '').trim()
      const firstPart = text.split(',')[0] || text
      return firstPart.replace(/^(CN|OU)=/i, '').replace(/\\,/g, ',') || text
    }

  function getGroupMemberships() {
      const raw = displayed?.member_of || displayed?.memberOf || displayed?.groups || []
      const values = Array.isArray(raw) ? raw : [raw]

      return values
        .filter(Boolean)
        .map((groupDn, index) => {
          if (typeof groupDn === 'object') {
            const dnValue = getObjectDn(groupDn)

            return {
              ...groupDn,
              type: groupDn.type || 'group',
              name: groupDn.name || getGroupNameFromDn(dnValue),
              distinguished_name: dnValue,
              dn: dnValue,
              key: dnValue || groupDn.name || `group-${index}`
            }
          }

          const dnValue = String(groupDn || '').trim()

          return {
            type: 'group',
            name: getGroupNameFromDn(dnValue),
            distinguished_name: dnValue,
            dn: dnValue,
            key: dnValue || `group-${index}`
          }
        })
        .filter(group => group.dn || group.name)
    }

  function renderMembershipsTab() {
      const groupMemberships =
        getGroupMemberships()

      const subjectLabel =
        isComputer
          ? 'ordinateur'
          : isGroup
            ? 'groupe'
            : 'utilisateur'

      return (
        <div className="aduc-members-card aduc-tab-card">
          <div className="aduc-members-head">
            <div>
              <h4>
                Groupes du {subjectLabel}
              </h4>

              <span>
                {groupMemberships.length}
                {' '}appartenance(s)
              </span>
            </div>

            <div className="aduc-members-buttons">
              <button
                type="button"
                onClick={() =>
                  onReloadObject?.(displayed)
                }
                title="Actualiser les appartenances"
              >
                ⟳
              </button>
            </div>
          </div>

          {groupMemberships.length === 0 ? (
            <p className="aduc-members-empty">
              Aucune appartenance de groupe
              remontée par Active Directory.
            </p>
          ) : (
            <div className="aduc-members-list">
              {groupMemberships.map(group => (
                <div
                  className="aduc-member-row aduc-user-group-row"
                  key={
                    group.key ||
                    group.dn ||
                    group.name
                  }
                >
                  <div className="aduc-member-main">
                    <strong>
                      {group.name ||
                        getGroupNameFromDn(
                          group.dn
                        )}
                    </strong>

                    <span>
                      {group.dn ||
                        group.distinguished_name ||
                        'DN non disponible'}
                    </span>
                  </div>

                  <div className="aduc-member-actions">
                    <button
                      type="button"
                      onClick={() =>
                        onOpenLinkedObject?.(
                          group.dn ||
                          group.distinguished_name
                        )
                      }
                    >
                      Ouvrir l’objet
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        onCopyDn?.(
                          group.dn ||
                          group.distinguished_name
                        )
                      }
                    >
                      Copier DN
                    </button>

                    {isManagedScope && (
                      <button
                        type="button"
                        className="danger"
                        onClick={() =>
                          onRemoveMember?.(
                            group,
                            displayed
                          )
                        }
                      >
                        Retirer
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

  function renderManagedByTab() {
      return (
        <div className="aduc-tab-card">
          <h4>Géré par</h4>

          {renderGrid(
            [
              [
                'Gestionnaire',
                managedByDn,
                true,
              ],
            ],
            'Aucun gestionnaire défini.'
          )}

          {managedByDn && (
            <div className="aduc-aduc-actionbar">
              <button
                type="button"
                onClick={() =>
                  onOpenLinkedObject?.(managedByDn)
                }
              >
                Ouvrir l’objet
              </button>

              <button
                type="button"
                onClick={() =>
                  onCopyDn?.(managedByDn)
                }
              >
                Copier le DN du gestionnaire
              </button>
            </div>
          )}
        </div>
      )
    }

  function renderGroupsTab() {
      return (
        <div className="aduc-members-card aduc-tab-card">
          <div className="aduc-members-head">
            <div>
              <h4>Membres du groupe</h4>
              <span>{membersLoading ? 'Chargement...' : `${members.length} membre(s)`}</span>
            </div>

            <div className="aduc-members-buttons">
              <button type="button" onClick={() => onOpenAddMember(displayed)} disabled={membersLoading} title="Ajouter un membre">＋</button>
              <button type="button" onClick={() => onLoadMembers(displayed)} disabled={membersLoading} title="Actualiser les membres">⟳</button>
            </div>
          </div>

          {membersError ? (
            <p className="aduc-members-error">{membersError}</p>
          ) : membersLoading ? (
            <p className="aduc-members-empty">Chargement des membres depuis SRV-DC01...</p>
          ) : members.length === 0 ? (
            <p className="aduc-members-empty">Aucun membre dans ce groupe.</p>
          ) : (
            <div className="aduc-members-list">
              {members.map(member => (
                <div className="aduc-member-row" key={getObjectDn(member) || member.name || member.sam_account_name}>
                  <div className="aduc-member-main">
                    <strong>{getObjectName(member)}</strong>
                    <span>{getObjectDn(member) || member.sam_account_name || member.user_principal_name || 'Identité non disponible'}</span>
                  </div>

                  <div className="aduc-member-actions">
                    <button
                      type="button"
                      onClick={() =>
                        onOpenLinkedObject?.(member)
                      }
                    >
                      Ouvrir l’objet
                    </button>

                    <button type="button" onClick={() => onCopyDn?.(getObjectDn(member))}>
                      Copier DN
                    </button>

                    <button type="button" className="danger" onClick={() => onRemoveMember?.(displayed, member)}>
                      Retirer
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

  function renderHistoryTab() {
    return (
      <div className="aduc-admin-history-card">
        <div className="aduc-admin-history-head">
          <div>
            <h4>Historique AD Admin</h4>
            <span>{historyLoading ? 'Chargement...' : `${filteredHistory.length}/${history.length} action(s)`}</span>
          </div>

          <button type="button" onClick={onLoadHistory} disabled={historyLoading}>⟳ Actualiser</button>
        </div>

        <div className="aduc-admin-history-filters">
          {historyFilterOptions.map(({ value, label, count }) => (
            <button type="button" key={value} className={historyFilter === value ? 'active' : ''} onClick={() => onHistoryFilterChange(value)}>
              <span>{label}</span>
              <small>{count}</small>
            </button>
          ))}
        </div>

        {historyError ? (
          <p className="aduc-admin-history-error">{historyError}</p>
        ) : filteredHistory.length === 0 ? (
          <p className="aduc-admin-history-empty">Aucune action ne correspond aux filtres actuels.</p>
        ) : (
          <div className="aduc-admin-history-list">
            {filteredHistory.slice(0, 8).map(job => (
              <button type="button" className={`aduc-admin-history-row ${getHistoryStatus(job)}`} key={job.id} onClick={() => onOpenHistoryJob(job)}>
                <span />
                <div>
                  <strong>{formatAdHistoryAction(job.action)}</strong>
                  <small>{job.agent_name || job.claimed_by || 'Agent non assigné'} • {formatAdHistoryStatus(job)}</small>
                  <em>{formatAdHistoryMessage(job)}</em>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <aside className="aduc-details-pane aduc-aduc-properties">
      <div className="aduc-details-header">
        <span className={`aduc-object-avatar ${isOu ? 'ou' : isGroup ? 'group' : isUser ? 'user' : isComputer ? 'computer' : ''}`}>
          {isOu ? '📁' : isGroup ? '👥' : isUser ? '👤' : isComputer ? '💻' : 'ⓘ'}
        </span>

        <div>
          <h3>{objectName}</h3>
          <p>{hasObject ? type : 'Clique un objet pour afficher ses propriétés.'}</p>
        </div>
      </div>

      {hasObject ? (
        <>
          <div className="aduc-aduc-actionbar">
            <button type="button" onClick={() => onCopyDn(displayed)} disabled={!dn}>Copier DN</button>
            {isOu && <button type="button" onClick={() => onExplore(displayed)}>Explorer cette OU</button>}

            {object && isManagedScope && (
              <>
                <button type="button" onClick={() => onOpenUpdateObject?.(displayed)}>Modifier</button>
                <button type="button" onClick={() => onOpenRenameObject?.(displayed)}>Renommer</button>
                <button type="button" onClick={() => onOpenMoveObject(displayed)}>Déplacer</button>
                <button type="button" className="danger" onClick={() => onOpenDeleteObject?.(displayed)}>Supprimer</button>
              </>
            )}

            {object && !isManagedScope && (
              <span className="aduc-readonly-scope-badge">
                Lecture seule — hors périmètre EITAS
              </span>
            )}
          </div>

          <div className="aduc-aduc-tabs">
            {tabs.map(([value, label]) => (
              <button type="button" key={value} className={activeDetailsTab === value ? 'active' : ''} onClick={() => setActiveDetailsTab(value)}>
                {label}
              </button>
            ))}
          </div>

          <div className="aduc-aduc-tab-panel">
            {activeDetailsTab === 'general' && (
              <div className="aduc-tab-card">
                <h4>Général</h4>
                {renderGrid(generalRows)}
              </div>
            )}

            {activeDetailsTab === 'account' &&
              renderAccountTab()}

            {activeDetailsTab === 'address' && (
              <div className="aduc-tab-card">
                <h4>Adresse</h4>

                {renderGrid(
                  addressRows,
                  'Aucune adresse disponible.'
                )}
              </div>
            )}

            {activeDetailsTab === 'phones' && (
              <div className="aduc-tab-card">
                <h4>Téléphones</h4>

                {renderGrid(
                  phoneRows,
                  'Aucune coordonnée téléphonique disponible.'
                )}
              </div>
            )}

            {activeDetailsTab === 'object' && (
              <div className="aduc-tab-card">
                <h4>Objet</h4>
                {renderGrid(objectRows)}
              </div>
            )}

              {activeDetailsTab === 'organization' && (
                <div className="aduc-tab-card">
                  <h4>Organisation</h4>
                  {renderGrid(
                    orgRows,
                    'Aucune information organisationnelle disponible.'
                  )}

                  <h4>Informations RH</h4>
                  {renderGrid(
                    hrRows,
                    'Aucune information RH disponible.'
                  )}

                  {managerDn && (
                    <div className="aduc-aduc-actionbar">
                      <button
                        type="button"
                        onClick={() => onCopyDn?.(managerDn)}
                      >
                        Copier le DN du gestionnaire
                      </button>
                    </div>
                  )}

                </div>
              )}

            {activeDetailsTab === 'machine' && (
              <div className="aduc-tab-card">
                <div className="aduc-machine-card-head">
                  <h4>Informations machine</h4>

                  {isManagedScope && (
                    <button
                      type="button"
                      onClick={() =>
                        onPrepareAccountAction?.(
                          'toggle_enabled',
                          displayed
                        )
                      }
                    >
                      {computerEnabledText === 'Activé'
                        ? 'Désactiver la machine'
                        : 'Activer la machine'}
                    </button>
                  )}
                </div>

                {renderGrid(
                  machineRows,
                  'Aucune information machine disponible.'
                )}
              </div>
            )}

            {activeDetailsTab === 'location' && (
              <div className="aduc-tab-card">
                <h4>Emplacement</h4>

                {renderGrid(
                  locationRows,
                  'Aucun emplacement disponible.'
                )}
              </div>
            )}

            {activeDetailsTab === 'members' &&
              renderGroupsTab()}

            {activeDetailsTab === 'membership' &&
              renderMembershipsTab()}

            {activeDetailsTab === 'managedBy' &&
              renderManagedByTab()}

            {activeDetailsTab === 'history' &&
              renderHistoryTab()}
          </div>

          {isOu &&
            isEitasManagedDn(
              getObjectDn(displayed)
            ) && (
              <div className="aduc-details-quick">
                <button type="button" onClick={() => onCreateOu(displayed)}>＋ OU ici</button>
                <button type="button" onClick={() => onCreateGroup(displayed)}>＋ Groupe ici</button>
              </div>
            )}
        </>
      ) : (
        <div className="aduc-details-empty">
          Sélectionne une OU, un utilisateur, un groupe, un ordinateur ou un contact dans la liste centrale.
        </div>
      )}
    </aside>
  )
}

export default ObjectDetailsPanel
