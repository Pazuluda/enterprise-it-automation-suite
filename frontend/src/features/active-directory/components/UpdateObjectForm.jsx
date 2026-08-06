import {
  getObjectDn,
  getObjectName,
  getObjectType,
} from '../utils/adExplorerCore'
import {
  COUNTRIES_FR,
  getCountryByAlpha2,
} from '../utils/countriesFr'
import {
  AD_LOGON_HOURS_CLEAR_VALUE,
  AD_LOGON_DAY_LABELS,
  AD_LOGON_HOURS_PER_DAY,
  countAllowedLocalLogonHours,
  createAllAllowedLogonHoursHex,
  createAllDeniedLogonHoursHex,
  formatLogonHoursOffset,
  isLocalLogonHourAllowed,
  normalizeLogonHoursHex,
  toggleLocalLogonHour,
} from '../utils/adLogonRestrictions'

function UpdateObjectForm({
  update,
  target = null,
  showTargetSummary = true,
  showActions = true,
  onSubmit = null,
  onCancel = null,
}) {
  const {
    updateModal,
    loading,
    closeUpdateObject,
    submitUpdateObject,
    hasUpdateChanges,
    isUpdateComputerTarget,
    isUpdateContactTarget,
    isUpdateOrganizationalUnitTarget,
    updateForm,
    updateOriginalForm,
    updateObjectFormField,
    isUpdateUserTarget,
    isUpdateGroupTarget,
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
    getMemberCandidateTitle,
    getMemberCandidateSubtitle,
  } = update

  const currentTarget =
    target || updateModal

  const postOfficeBoxValueCount = Number(
    currentTarget?.post_office_box_count
    ?? currentTarget?.postOfficeBoxCount
    ?? 0
  )

  const hasMultiplePostOfficeBoxes =
    postOfficeBoxValueCount > 1

  const logonHoursUtcOffsetMinutes = Number(
    currentTarget?.logon_hours_utc_offset_minutes
    ?? currentTarget?.logonHoursUtcOffsetMinutes
    ?? 0
  )

  const handleSubmit =
    onSubmit || submitUpdateObject

  const handleCancel =
    onCancel || closeUpdateObject

  if (!currentTarget) return null

  return (
<form onSubmit={handleSubmit}>
  {showTargetSummary && (
<div className="aduc-update-object-target">
    <div>
      <span>Objet cible</span>
      <strong>{getObjectName(currentTarget)}</strong>
    </div>

    <div>
      <span>Type</span>
      <strong>{getObjectType(currentTarget)}</strong>
    </div>

    <div className="wide">
      <span>DN</span>
      <code>{getObjectDn(currentTarget)}</code>
    </div>
  </div>
)}

<p className="aduc-update-object-help">
    Seuls les champs modifiés seront envoyés au worker.
    Vider un champ supprimera l’attribut correspondant
    dans Active Directory.
  </p>

  <div className="aduc-update-object-sections">
    <section>
      <h4>Informations générales</h4>

      <div className="aduc-update-object-grid">
          {!isUpdateGroupTarget(currentTarget) &&
            !isUpdateComputerTarget(currentTarget) && (
            <label>
              <span>Nom d’affichage</span>
              <input
                type="text"
                value={updateForm.displayName || ''}
                onChange={event => updateObjectFormField(
                  'displayName',
                  event.target.value
                )}
                disabled={loading}
              />
            </label>
          )}

        {isUpdateComputerTarget(currentTarget) && (
          <label className="wide">
            <span>
              Nom de l’ordinateur
              {' '}
              (antérieur à Windows 2000)
            </span>

            <input
              type="text"
              value={updateForm.samAccountName || ''}
              maxLength={255}
              onChange={event =>
                updateObjectFormField(
                  'samAccountName',
                  event.target.value
                )
              }
              disabled={loading}
            />

            <small>
              Le suffixe $ est ajouté automatiquement
              par EITAS lors de l’enregistrement.
            </small>
          </label>
        )}

        <label className="wide">
          <span>Description</span>
          <textarea
            rows="3"
            value={updateForm.description || ''}
            onChange={event => updateObjectFormField(
              'description',
              event.target.value
            )}
            disabled={loading}
          />
        </label>
      </div>
    </section>

    {isUpdateComputerTarget(currentTarget) && (
      <>
        <section>
          <h4>Système d’exploitation</h4>

          <div className="aduc-update-object-grid">
            {[
              [
                'operatingSystem',
                'Nom',
              ],
              [
                'operatingSystemVersion',
                'Version',
              ],
              [
                'operatingSystemServicePack',
                'Service Pack',
              ],
            ].map(([name, label]) => (
              <label key={name}>
                <span>{label}</span>

                <input
                  type="text"
                  value={updateForm[name] || ''}
                  onChange={event =>
                    updateObjectFormField(
                      name,
                      event.target.value
                    )
                  }
                  disabled={loading}
                />
              </label>
            ))}
          </div>
        </section>

        <section>
          <h4>Emplacement</h4>

          <div className="aduc-update-object-grid">
            <label className="wide">
              <span>Emplacement</span>

              <input
                type="text"
                value={updateForm.location || ''}
                onChange={event =>
                  updateObjectFormField(
                    'location',
                    event.target.value
                  )
                }
                placeholder="Ex : Salle informatique"
                disabled={loading}
              />
            </label>
          </div>
        </section>
      </>
    )}

    {isUpdateUserTarget(currentTarget) && (
      <>
        {[
          {
            title: 'Identité',
            fields: [
              ['givenName', 'Prénom'],
              ['sn', 'Nom']
            ]
          },
          {
            title: 'Profil avancé',
            fields: [
              [
                'personalTitle',
                'Titre de civilité'
              ],
              [
                'initials',
                'Initiales'
              ],
              [
                'preferredLanguage',
                'Langue préférée'
              ],
              [
                'info',
                'Remarques',
                true
              ]
            ]
          },

          {
            title: 'Profil Unix / POSIX',
            fields: [
              [
                'uidNumber',
                'Identifiant utilisateur Unix (UID)'
              ],
              [
                'gidNumber',
                'Identifiant de groupe Unix (GID)'
              ],
              [
                'unixHomeDirectory',
                'Répertoire personnel Unix',
                true
              ],
              [
                'loginShell',
                'Shell de connexion',
                true
              ],
              [
                'gecos',
                'Informations GECOS',
                true
              ]
            ]
          },
          {
            title: 'Organisation',
            fields: [
              ['title', 'Titre / poste'],
              ['department', 'Service'],
              ['division', 'Division'],
              ['company', 'Société'],
              [
                'physicalDeliveryOfficeName',
                'Bureau'
              ]
            ]
          },
          {
            title: 'Informations RH',
            fields: [
              ['employeeID', 'Identifiant salarié'],
              [
                'employeeNumber',
                'Numéro employé'
              ],
              [
                'manager',
                'Gestionnaire — Nom distinctif',
                true
              ]
            ]
          },
          {
            title: 'Coordonnées',
            fields: [
              ['mail', 'E-mail'],
              [
                'telephoneNumber',
                'Téléphone'
              ],
              ['mobile', 'Mobile'],
              [
                'streetAddress',
                'Adresse',
                true
              ],
              ['postalCode', 'Code postal'],
              ['l', 'Ville'],
              [
                'st',
                'Région / département'
              ],
              ['co', 'Pays']
            ]
          },
          {
            title: 'Compte',
            fields: [
              [
                'userPrincipalName',
                'Nom d’ouverture de session utilisateur',
                true
              ],
              [
                'accountExpires',
                'Le compte expire le'
              ],
              [
                'passwordNeverExpires',
                'Le mot de passe n’expire jamais'
              ],
              [
                'cannotChangePassword',
                'L’utilisateur ne peut pas changer le mot de passe'
              ],
              [
                'smartcardLogonRequired',
                'Carte à puce obligatoire'
              ],
              [
                'accountNotDelegated',
                'Compte sensible et non délégable'
              ],
              [
                'userWorkstations',
                'Stations de travail autorisées',
                true
              ],
              [
                'logonHours',
                'Horaires d’accès',
                true
              ]
            ]
          },
          {
            title: 'Profil',
            fields: [
              [
                'profilePath',
                'Chemin du profil',
                true
              ],
              [
                'scriptPath',
                'Script d’ouverture de session',
                true
              ],
              [
                'homeDirectory',
                'Dossier de base',
                true
              ],
              [
                'homeDrive',
                'Lecteur de connexion'
              ]
            ]
          },
          {
            title: 'Services Bureau à distance',
            fields: [
              [
                'msTSAllowLogon',
                'Autorisation de connexion RDS',
                true
              ],
              [
                'msTSProfilePath',
                'Chemin du profil RDS',
                true
              ],
              [
                'msTSHomeDirectory',
                'Dossier de base RDS',
                true
              ],
              [
                'msTSHomeDrive',
                'Lecteur de connexion RDS'
              ],
              [
                'msTSInitialProgram',
                'Programme initial',
                true
              ],
              [
                'msTSWorkDirectory',
                'Dossier de démarrage',
                true
              ]
            ]
          }
        ].map(section => (
          <section key={section.title}>
            <h4>{section.title}</h4>

            <div className="aduc-update-object-grid">
              {section.fields.map(
                ([name, label, wide]) => {
                  if (
                    name === 'cannotChangePassword'
                    || name === 'accountNotDelegated'
                  ) {
                    return null
                  }

                  if (
                    name === 'smartcardLogonRequired'
                  ) {
                    return (
                      <fieldset
                        key="securityAccountOptions"
                        className="aduc-account-options-group"
                      >
                        <legend>
                          Options de sécurité du compte
                        </legend>

                        <div className="aduc-account-options-list">
                          <label className="aduc-account-option-row">
                            <input
                              type="checkbox"
                              checked={
                                updateForm.smartcardLogonRequired
                                === true
                              }
                              onChange={event =>
                                updateObjectFormField(
                                  'smartcardLogonRequired',
                                  event.target.checked
                                )
                              }
                              disabled={
                                loading
                                || update
                                  ?.pendingUserAccountOptionFields
                                  ?.includes('smartcardLogonRequired')
                              }
                            />

                            <span className="aduc-account-option-copy">
                              <strong>
                                Exiger une carte à puce
                              </strong>

                              <small>
                                L’utilisateur devra utiliser une
                                carte à puce pour ouvrir sa session.
                              </small>
                            </span>
                          </label>

                          <label className="aduc-account-option-row">
                            <input
                              type="checkbox"
                              checked={
                                updateForm.accountNotDelegated
                                === true
                              }
                              onChange={event =>
                                updateObjectFormField(
                                  'accountNotDelegated',
                                  event.target.checked
                                )
                              }
                              disabled={
                                loading
                                || update
                                  ?.pendingUserAccountOptionFields
                                  ?.includes('accountNotDelegated')
                              }
                            />

                            <span className="aduc-account-option-copy">
                              <strong>
                                Compte sensible et non délégable
                              </strong>

                              <small>
                                Empêche la délégation du
                                contexte d’authentification de ce
                                compte utilisateur.
                              </small>
                            </span>
                          </label>
                        </div>
                      </fieldset>
                    )
                  }

                  if (
                    name === 'passwordNeverExpires'
                  ) {
                    return (
                      <fieldset
                        key="passwordAccountOptions"
                        className="aduc-account-options-group"
                      >
                        <legend>
                          Options du mot de passe
                        </legend>

                        <div className="aduc-account-options-list">
                          <label className="aduc-account-option-row">
                            <input
                              type="checkbox"
                              checked={
                                updateForm.passwordNeverExpires
                                === true
                              }
                              onChange={event =>
                                updateObjectFormField(
                                  'passwordNeverExpires',
                                  event.target.checked
                                )
                              }
                              disabled={
                                loading
                                || update
                                  ?.pendingUserAccountOptionFields
                                  ?.includes('passwordNeverExpires')
                              }
                            />

                            <span className="aduc-account-option-copy">
                              <strong>
                                Le mot de passe n’expire jamais
                              </strong>

                              <small>
                                Désactive l’expiration automatique
                                du mot de passe de cet utilisateur.
                              </small>
                            </span>
                          </label>

                          <label className="aduc-account-option-row">
                            <input
                              type="checkbox"
                              checked={
                                updateForm.cannotChangePassword
                                === true
                              }
                              onChange={event =>
                                updateObjectFormField(
                                  'cannotChangePassword',
                                  event.target.checked
                                )
                              }
                              disabled={
                                loading
                                || update
                                  ?.pendingUserAccountOptionFields
                                  ?.includes('cannotChangePassword')
                              }
                            />

                            <span className="aduc-account-option-copy">
                              <strong>
                                L’utilisateur ne peut pas changer
                                le mot de passe
                              </strong>

                              <small>
                                Seul un administrateur autorisé
                                pourra gérer ce mot de passe.
                              </small>
                            </span>
                          </label>
                        </div>
                      </fieldset>
                    )
                  }

                  if (name === 'msTSAllowLogon') {
                    return (
                      <fieldset
                        key={name}
                        className="
                          wide
                          aduc-account-options-group
                        "
                      >
                        <legend>{label}</legend>

                        <label>
                          <span>
                            Comportement de la connexion
                          </span>

                          <select
                            value={
                              updateForm.msTSAllowLogon
                              || 'inherit'
                            }
                            onChange={event =>
                              updateObjectFormField(
                                'msTSAllowLogon',
                                event.target.value
                              )
                            }
                            disabled={
                              loading
                              || update
                                ?.pendingUserAccountOptionFields
                                ?.includes('msTSAllowLogon')
                            }
                          >
                            <option value="inherit">
                              Non configuré
                            </option>

                            <option value="allow">
                              Autoriser la connexion RDS
                            </option>

                            <option value="deny">
                              Refuser la connexion RDS
                            </option>
                          </select>

                          <small>
                            « Non configuré » efface la valeur
                            explicite et restaure l’état absent
                            dans Active Directory.
                          </small>
                        </label>
                      </fieldset>
                    )
                  }

                  if (name === 'logonHours') {
                    const clearRequested =
                      updateForm.logonHours ===
                      AD_LOGON_HOURS_CLEAR_VALUE

                    const normalizedHours =
                      clearRequested
                        ? ''
                        : normalizeLogonHoursHex(
                            updateForm.logonHours
                          )

                    const customHours =
                      Boolean(normalizedHours)

                    const allowedHourCount =
                      countAllowedLocalLogonHours(
                        normalizedHours
                      )

                    return (
                      <fieldset
                        key={name}
                        className="
                          wide
                          aduc-logon-hours-field
                        "
                        disabled={loading}
                      >
                        <legend>{label}</legend>

                        <div className="aduc-logon-hours-summary">
                          <strong>
                            {clearRequested
                              ? 'La restriction sera supprimée à l’enregistrement'
                              : customHours
                                ? `${allowedHourCount} créneau(x) autorisé(s)`
                                : 'Tous les horaires sont autorisés'}
                          </strong>

                          <span>
                            Décalage standard du contrôleur :
                            {' '}
                            {formatLogonHoursOffset(
                              logonHoursUtcOffsetMinutes
                            )}
                          </span>
                        </div>

                        <div className="aduc-logon-hours-controls">
                          {clearRequested ? (
                            <button
                              type="button"
                              onClick={() =>
                                updateObjectFormField(
                                  'logonHours',
                                  updateOriginalForm
                                    ?.logonHours || ''
                                )
                              }
                              disabled={loading}
                            >
                              Annuler la suppression
                            </button>
                          ) : !customHours ? (
                            <button
                              type="button"
                              onClick={() =>
                                updateObjectFormField(
                                  'logonHours',
                                  createAllAllowedLogonHoursHex()
                                )
                              }
                              disabled={loading}
                            >
                              Définir des horaires personnalisés
                            </button>
                          ) : (
                            <>
                              <button
                                type="button"
                                onClick={() =>
                                  updateObjectFormField(
                                    'logonHours',
                                    createAllAllowedLogonHoursHex()
                                  )
                                }
                                disabled={loading}
                              >
                                Tout autoriser
                              </button>

                              <button
                                type="button"
                                onClick={() =>
                                  updateObjectFormField(
                                    'logonHours',
                                    createAllDeniedLogonHoursHex()
                                  )
                                }
                                disabled={loading}
                              >
                                Tout refuser
                              </button>

                              <button
                                type="button"
                                onClick={() =>
                                  updateObjectFormField(
                                    'logonHours',
                                    AD_LOGON_HOURS_CLEAR_VALUE
                                  )
                                }
                                disabled={loading}
                              >
                                Supprimer la restriction
                              </button>
                            </>
                          )}
                        </div>

                        {customHours && !clearRequested && (
                          <div className="aduc-logon-hours-scroll">
                            <div className="aduc-logon-hours-header">
                              <span>Jour</span>

                              {Array.from(
                                {
                                  length:
                                    AD_LOGON_HOURS_PER_DAY
                                },
                                (_, hour) => (
                                  <span key={hour}>
                                    {hour % 2 === 0
                                      ? hour
                                      : ''}
                                  </span>
                                )
                              )}
                            </div>

                            {AD_LOGON_DAY_LABELS.map(
                              (dayLabel, dayIndex) => (
                                <div
                                  className="aduc-logon-hours-row"
                                  key={dayLabel}
                                >
                                  <strong>{dayLabel}</strong>

                                  {Array.from(
                                    {
                                      length:
                                        AD_LOGON_HOURS_PER_DAY
                                    },
                                    (_, hour) => {
                                      const localHourIndex =
                                        (
                                          dayIndex *
                                          AD_LOGON_HOURS_PER_DAY
                                        ) + hour

                                      const allowed =
                                        isLocalLogonHourAllowed(
                                          normalizedHours,
                                          localHourIndex,
                                          logonHoursUtcOffsetMinutes
                                        )

                                      const endHour =
                                        (
                                          hour + 1
                                        ) % 24

                                      return (
                                        <button
                                          key={hour}
                                          type="button"
                                          className={
                                            allowed
                                              ? 'allowed'
                                              : 'denied'
                                          }
                                          aria-pressed={allowed}
                                          aria-label={
                                            `${dayLabel}, ` +
                                            `${String(hour).padStart(2, '0')}:00` +
                                            ` à ` +
                                            `${String(endHour).padStart(2, '0')}:00, ` +
                                            (
                                              allowed
                                                ? 'autorisé'
                                                : 'refusé'
                                            )
                                          }
                                          title={
                                            allowed
                                              ? 'Ouverture de session autorisée'
                                              : 'Ouverture de session refusée'
                                          }
                                          onClick={() =>
                                            updateObjectFormField(
                                              'logonHours',
                                              toggleLocalLogonHour(
                                                normalizedHours,
                                                localHourIndex,
                                                logonHoursUtcOffsetMinutes
                                              )
                                            )
                                          }
                                          disabled={loading}
                                        />
                                      )
                                    }
                                  )}
                                </div>
                              )
                            )}
                          </div>
                        )}

                        <small>
                          Les 168 créneaux sont enregistrés dans
                          l’attribut AD logonHours de 21 octets.
                          Un champ sans restriction autorise tous
                          les horaires.
                        </small>
                      </fieldset>
                    )
                  }

                  if (name === 'manager') {
                    return (
                      <label
                        key={name}
                        className="wide aduc-manager-field"
                      >
                        <span>{label}</span>

                        <div className="aduc-manager-current-row">
                          <input
                            className="mono"
                            value={updateForm.manager || ''}
                            placeholder="Aucun gestionnaire défini"
                            readOnly
                            disabled={loading}
                          />

                          <button
                            type="button"
                            className="aduc-manager-clear-button"
                            onClick={clearManagerSelection}
                            disabled={
                              loading ||
                              !updateForm.manager
                            }
                          >
                            Retirer
                          </button>
                        </div>

                        <div className="aduc-member-picker-row">
                          <input
                            value={managerSearchQuery}
                            onChange={event => {
                              setManagerSearchQuery(
                                event.target.value
                              )
                              setManagerSearchResults([])
                              setManagerSearchError('')
                            }}
                            onKeyDown={event => {
                              if (event.key === 'Enter') {
                                event.preventDefault()
                                searchManagerCandidates()
                              }
                            }}
                            placeholder="Nom, identifiant ou e-mail du gestionnaire..."
                            disabled={
                              loading ||
                              managerSearchLoading
                            }
                          />

                          <button
                            type="button"
                            className="aduc-member-search-button"
                            onClick={searchManagerCandidates}
                            disabled={
                              loading ||
                              managerSearchLoading ||
                              managerSearchQuery.trim().length < 2
                            }
                          >
                            {managerSearchLoading
                              ? 'Recherche...'
                              : 'Rechercher'}
                          </button>
                        </div>

                        {managerSearchError && (
                          <div className="aduc-member-search-error">
                            {managerSearchError}
                          </div>
                        )}

                        {managerSearchResults.length > 0 && (
                          <div className="aduc-member-search-results aduc-manager-search-results">
                            {managerSearchResults.map(
                              candidate => {
                                const candidateDn =
                                  getManagerCandidateDn(candidate)

                                return (
                                  <button
                                    type="button"
                                    key={candidateDn}
                                    data-kind-label="Gestionnaire possible"
                                    onClick={() =>
                                      selectManagerCandidate(
                                        candidate
                                      )
                                    }
                                  >
                                    <strong>
                                      {getMemberCandidateTitle(
                                        candidate
                                      )}
                                    </strong>

                                    <small>
                                      {getMemberCandidateSubtitle(
                                        candidate
                                      )}
                                    </small>
                                  </button>
                                )
                              }
                            )}
                          </div>
                        )}

                        <small>
                          Recherche dans le domaine API.LOCAL.
                          L’utilisateur en cours de modification
                          est automatiquement exclu. Seuls
                          les comptes actifs sont proposés.
                        </small>
                      </label>
                    )
                  }

                  if (
                    name === 'uidNumber'
                    || name === 'gidNumber'
                  ) {
                    return (
                      <label key={name}>
                        <span>{label}</span>

                        <input
                          type="number"
                          step="1"
                          min={-2147483648}
                          max={2147483647}
                          value={updateForm[name] ?? ''}
                          onChange={event =>
                            updateObjectFormField(
                              name,
                              event.target.value
                            )
                          }
                          disabled={
                            loading
                            || update
                              ?.pendingUserAccountOptionFields
                              ?.includes(name)
                          }
                        />

                        <small>
                          Entier Active Directory Integer32.
                        </small>
                      </label>
                    )
                  }

                  if (name === 'gecos') {
                    return (
                      <label
                        key={name}
                        className="wide"
                      >
                        <span>{label}</span>

                        <textarea
                          rows="3"
                          maxLength={10240}
                          value={updateForm.gecos || ''}
                          onChange={event =>
                            updateObjectFormField(
                              'gecos',
                              event.target.value
                            )
                          }
                          disabled={
                            loading
                            || update
                              ?.pendingUserAccountOptionFields
                              ?.includes('gecos')
                          }
                        />

                        <small>
                          Champ descriptif Unix limite a
                          10 240 caracteres.
                        </small>
                      </label>
                    )
                  }

                  if (name === 'info') {
                    return (
                      <label
                        key={name}
                        className="wide"
                      >
                        <span>{label}</span>

                        <textarea
                          rows="4"
                          maxLength={1024}
                          value={updateForm.info || ''}
                          onChange={event =>
                            updateObjectFormField(
                              'info',
                              event.target.value
                            )
                          }
                          disabled={
                            loading
                            || update
                              ?.pendingUserAccountOptionFields
                              ?.includes('info')
                          }
                        />

                        <small>
                          Remarque interne Active Directory,
                          limitée à 1 024 caractères.
                        </small>
                      </label>
                    )
                  }

                  return (
                    <label
                      key={name}
                      className={wide ? 'wide' : ''}
                    >
                      <span>{label}</span>

                      <input
                        type={
                          name === 'mail'
                            ? 'email'
                            : name === 'accountExpires'
                              ? 'date'
                              : 'text'
                        }
                        value={updateForm[name] || ''}
                        maxLength={
                          name === 'homeDrive'
                          || name === 'msTSHomeDrive'
                            ? 2
                            : name.startsWith('msTS')
                              ? 32767
                              : name === 'userWorkstations'
                                ? 1024
                                : name === 'userPrincipalName'
                                  ? 1024
                                  : name === 'personalTitle'
                                    ? 64
                                    : name === 'initials'
                                      ? 6
                                      : name === 'preferredLanguage'
                                        ? 32767
                                        : name === 'unixHomeDirectory'
                                          ? 2048
                                          : name === 'loginShell'
                                            ? 1024
                                            : name === 'gecos'
                                              ? 10240
                                              : name === 'info'
                                          ? 1024
                                          : undefined
                        }
                        pattern={
                          name === 'homeDrive'
                          || name === 'msTSHomeDrive'
                            ? '[A-Za-z]:'
                            : undefined
                        }
                        placeholder={
                          name === 'homeDrive'
                            ? 'Ex : H:'
                            : name === 'msTSHomeDrive'
                              ? 'Ex : R:'
                              : name === 'msTSProfilePath'
                                ? 'Ex : \\\\SRV-RDS\\Profils\\%username%'
                                : name === 'msTSHomeDirectory'
                                  ? 'Ex : \\\\SRV-RDS\\Utilisateurs\\%username%'
                                  : name === 'msTSInitialProgram'
                                    ? 'Ex : C:\\Applications\\app.exe'
                                    : name === 'msTSWorkDirectory'
                                      ? 'Ex : C:\\Applications'
                                      : name === 'userWorkstations'
                                        ? 'Ex : SRV-DC01,PC-COMPTA-01'
                                        : name === 'userPrincipalName'
                                          ? 'Ex : prenom.nom@API.LOCAL'
                                          : undefined
                        }
                        title={
                          name === 'homeDrive'
                            ? 'Une lettre suivie de deux-points, par exemple H:'
                            : name === 'msTSHomeDrive'
                              ? 'Une lettre suivie de deux-points, par exemple R:'
                              : name === 'msTSProfilePath'
                                ? 'Chemin réseau du profil utilisé pour les sessions RDS'
                                : name === 'msTSHomeDirectory'
                                  ? 'Dossier de base utilisé pendant les sessions RDS'
                                  : name === 'msTSInitialProgram'
                                    ? 'Programme lancé automatiquement à la connexion RDS'
                                    : name === 'msTSWorkDirectory'
                                      ? 'Dossier de travail du programme initial'
                                      : name === 'userWorkstations'
                                        ? 'Noms NetBIOS séparés par des virgules. Champ vide : tous les ordinateurs.'
                                        : name === 'userPrincipalName'
                                          ? 'Nom d’ouverture de session complet avec suffixe UPN'
                                          : name === 'accountExpires'
                                            ? 'Champ vide : le compte n’expire jamais'
                                            : undefined
                        }
                        onChange={event =>
                          updateObjectFormField(
                            name,
                            name === 'homeDrive'
                            || name === 'msTSHomeDrive'
                            || name === 'userWorkstations'
                              ? event.target.value.toUpperCase()
                              : event.target.value
                          )
                        }
                        disabled={
                          loading
                          || update
                            ?.pendingUserAccountOptionFields
                            ?.includes(name)
                        }
                      />

                      {name === 'userWorkstations' && (
                        <small>
                          Noms NetBIOS séparés par des virgules.
                          Laisser vide pour autoriser la connexion
                          depuis tous les ordinateurs.
                        </small>
                      )}

                      {name === 'userPrincipalName' && (
                        <small>
                          Suffixe UPN disponible : @API.LOCAL.
                        </small>
                      )}

                      {name === 'accountExpires' && (
                        <small>
                          Laisser vide pour que le compte
                          n’expire jamais.
                        </small>
                      )}
                    </label>
                  )
                }
              )}
            </div>
          </section>
        ))}
      </>
    )}
    {isUpdateContactTarget(currentTarget) && (
      <>
        <section>
          <h4>Identité du contact</h4>

          <div className="aduc-update-object-grid">
            {[
              ['givenName', 'Prénom'],
              ['initials', 'Initiales', 6],
              ['sn', 'Nom'],
            ].map(([name, label, maxLength]) => (
              <label key={name}>
                <span>{label}</span>

                <input
                  type="text"
                  maxLength={maxLength || undefined}
                  value={updateForm[name] || ''}
                  onChange={event =>
                    updateObjectFormField(
                      name,
                      event.target.value
                    )
                  }
                  disabled={loading}
                />
              </label>
            ))}
          </div>
        </section>

        <section>
          <h4>Coordonnées générales</h4>

          <div className="aduc-update-object-grid">
            {[
              [
                'physicalDeliveryOfficeName',
                'Bureau',
                128,
                false,
                'text',
              ],
              [
                'telephoneNumber',
                'Numéro de téléphone',
                64,
                false,
                'text',
              ],
              [
                'mail',
                'Adresse de messagerie',
                256,
                true,
                'email',
              ],
              [
                'wWWHomePage',
                'Page Web',
                2048,
                true,
                'text',
              ],
            ].map(([
              name,
              label,
              maxLength,
              wide,
              inputType,
            ]) => (
              <label
                key={name}
                className={wide ? 'wide' : ''}
              >
                <span>{label}</span>

                <input
                  type={inputType}
                  maxLength={maxLength}
                  value={updateForm[name] || ''}
                  onChange={event =>
                    updateObjectFormField(
                      name,
                      event.target.value
                    )
                  }
                  disabled={loading}
                />
              </label>
            ))}
          </div>
        </section>

        <section>
          <h4>Adresse</h4>

          <div className="aduc-update-object-grid">
            {[
              [
                'streetAddress',
                'Adresse',
                true,
              ],
              [
                'postalCode',
                'Code postal',
                false,
              ],
              [
                'l',
                'Ville',
                false,
              ],
              [
                'st',
                'Département ou région',
                false,
              ],
            ].map(([name, label, wide]) => (
              <label
                key={name}
                className={wide ? 'wide' : ''}
              >
                <span>{label}</span>

                <input
                  type="text"
                  value={updateForm[name] || ''}
                  onChange={event =>
                    updateObjectFormField(
                      name,
                      event.target.value
                    )
                  }
                  disabled={loading}
                />
              </label>
            ))}

            <label>
              <span>Boîte postale</span>

              <input
                type="text"
                maxLength={40}
                value={
                  updateForm.postOfficeBox || ''
                }
                onChange={event =>
                  updateObjectFormField(
                    'postOfficeBox',
                    event.target.value
                  )
                }
                disabled={
                  loading ||
                  hasMultiplePostOfficeBoxes
                }
              />

              {hasMultiplePostOfficeBoxes && (
                <small>
                  Cet objet contient
                  {' '}
                  {postOfficeBoxValueCount}
                  {' '}
                  valeurs. Leur modification sera
                  disponible dans l’éditeur LDAP C2.
                </small>
              )}
            </label>

            <label>
              <span>Pays/région</span>

              <select
                value={updateForm.c || ''}
                onChange={event => {
                  const country =
                    getCountryByAlpha2(
                      event.target.value
                    )

                  updateObjectFormField(
                    'c',
                    country?.alpha2 || ''
                  )

                  updateObjectFormField(
                    'co',
                    country?.name || ''
                  )

                  updateObjectFormField(
                    'countryCode',
                    country
                      ? String(country.numeric)
                      : ''
                  )
                }}
                disabled={loading}
              >
                <option value="">
                  Aucun pays défini
                </option>

                {COUNTRIES_FR.map(country => (
                  <option
                    key={country.alpha2}
                    value={country.alpha2}
                  >
                    {country.name}
                    {' — '}
                    {country.alpha2}
                  </option>
                ))}
              </select>

              <small>
                Attributs AD :
                {' '}
                {updateForm.c || '—'}
                {' / '}
                {updateForm.co || '—'}
                {' / '}
                {updateForm.countryCode || '—'}
              </small>
            </label>
          </div>
        </section>

        <section>
          <h4>Téléphones</h4>

          <div className="aduc-update-object-grid">
            {[
              [
                'homePhone',
                'Domicile',
              ],
              [
                'pager',
                'Radiomessagerie',
              ],
              [
                'mobile',
                'Tél. mobile',
              ],
              [
                'facsimileTelephoneNumber',
                'Télécopie',
              ],
              [
                'ipPhone',
                'Téléphone IP',
              ],
            ].map(([name, label]) => (
              <label key={name}>
                <span>{label}</span>

                <input
                  type="text"
                  maxLength={64}
                  value={updateForm[name] || ''}
                  onChange={event =>
                    updateObjectFormField(
                      name,
                      event.target.value
                    )
                  }
                  disabled={loading}
                />
              </label>
            ))}

            <label className="wide">
              <span>Remarques</span>

              <textarea
                rows="4"
                maxLength={1024}
                value={updateForm.info || ''}
                onChange={event =>
                  updateObjectFormField(
                    'info',
                    event.target.value
                  )
                }
                disabled={loading}
              />
            </label>
          </div>
        </section>

        <section>
          <h4>Organisation</h4>

          <div className="aduc-update-object-grid">
            {[
              [
                'title',
                'Fonction',
              ],
              [
                'department',
                'Service',
              ],
              [
                'company',
                'Société',
              ],
            ].map(([name, label]) => (
              <label key={name}>
                <span>{label}</span>

                <input
                  type="text"
                  value={updateForm[name] || ''}
                  onChange={event =>
                    updateObjectFormField(
                      name,
                      event.target.value
                    )
                  }
                  disabled={loading}
                />
              </label>
            ))}

            <label className="wide aduc-manager-field">
              <span>
                Gestionnaire — Nom distinctif
              </span>

              <div className="aduc-manager-current-row">
                <input
                  className="mono"
                  value={updateForm.manager || ''}
                  placeholder="Aucun gestionnaire défini"
                  readOnly
                  disabled={loading}
                />

                <button
                  type="button"
                  className="aduc-manager-clear-button"
                  onClick={clearManagerSelection}
                  disabled={
                    loading ||
                    !updateForm.manager
                  }
                >
                  Retirer
                </button>
              </div>

              <div className="aduc-member-picker-row">
                <input
                  value={managerSearchQuery}
                  onChange={event => {
                    setManagerSearchQuery(
                      event.target.value
                    )
                    setManagerSearchResults([])
                    setManagerSearchError('')
                  }}
                  onKeyDown={event => {
                    if (event.key === 'Enter') {
                      event.preventDefault()
                      searchManagerCandidates()
                    }
                  }}
                  placeholder={
                    'Nom, identifiant ou e-mail ' +
                    'du gestionnaire...'
                  }
                  disabled={
                    loading ||
                    managerSearchLoading
                  }
                />

                <button
                  type="button"
                  className="aduc-member-search-button"
                  onClick={searchManagerCandidates}
                  disabled={
                    loading ||
                    managerSearchLoading ||
                    managerSearchQuery.trim().length < 2
                  }
                >
                  {managerSearchLoading
                    ? 'Recherche...'
                    : 'Rechercher'}
                </button>
              </div>

              {managerSearchError && (
                <div className="aduc-member-search-error">
                  {managerSearchError}
                </div>
              )}

              {managerSearchResults.length > 0 && (
                <div className={
                  'aduc-member-search-results ' +
                  'aduc-manager-search-results'
                }>
                  {managerSearchResults.map(
                    candidate => {
                      const candidateDn =
                        getManagerCandidateDn(
                          candidate
                        )

                      return (
                        <button
                          type="button"
                          key={candidateDn}
                          data-kind-label={
                            'Gestionnaire possible'
                          }
                          onClick={() =>
                            selectManagerCandidate(
                              candidate
                            )
                          }
                        >
                          <strong>
                            {getMemberCandidateTitle(
                              candidate
                            )}
                          </strong>

                          <span>
                            {getMemberCandidateSubtitle(
                              candidate
                            )}
                          </span>
                        </button>
                      )
                    }
                  )}
                </div>
              )}
            </label>
          </div>
        </section>
      </>
    )}

    {isUpdateContactTarget(currentTarget) && (
      <section>
        <h4>Objet</h4>

        <div className="aduc-update-object-grid">
          <label className="wide aduc-ou-protection-field">
            <span>
              <input
                type="checkbox"
                checked={Boolean(
                  updateForm.protectedFromAccidentalDeletion
                )}
                onChange={event => updateObjectFormField(
                  'protectedFromAccidentalDeletion',
                  event.target.checked
                )}
                disabled={loading}
              />

              Protéger contre la suppression accidentelle
            </span>
          </label>
        </div>
      </section>
    )}

    {isUpdateOrganizationalUnitTarget(currentTarget) && (
      <section>
        <h4>Adresse de l’unité d’organisation</h4>

        <div className="aduc-update-object-grid">
          {[
            ["streetAddress", "Adresse", true],
            ["postalCode", "Code postal"],
            ["l", "Ville"],
            ["st", "Région / département"],
            ["co", "Pays"]
          ].map(([name, label, wide]) => (
            <label
              key={name}
              className={wide ? "wide" : ""}
            >
              <span>{label}</span>
              <input
                type="text"
                value={updateForm[name] || ""}
                onChange={event =>
                  updateObjectFormField(name, event.target.value)
                }
                disabled={loading}
              />
            </label>
          ))}
        </div>
      </section>
    )}

    {(
      isUpdateGroupTarget(currentTarget) ||
      isUpdateComputerTarget(currentTarget) ||
      isUpdateOrganizationalUnitTarget(currentTarget)
    ) && (
      <section>
        <h4>
          {isUpdateGroupTarget(currentTarget)
            ? 'Paramètres du groupe'
            : isUpdateComputerTarget(currentTarget)
              ? 'Géré par et objet'
              : 'Gestion de l’objet'}
        </h4>

        <div className="aduc-update-object-grid">
          {isUpdateGroupTarget(currentTarget) && (
            <>
              <label className="wide">
                <span>
                  Nom de groupe (antérieur à Windows 2000)
                </span>
                <input
                  type="text"
                  value={updateForm.samAccountName || ''}
                  maxLength={256}
                  onChange={event =>
                    updateObjectFormField(
                      'samAccountName',
                      event.target.value
                    )
                  }
                  disabled={loading}
                />
                <small>
                  Modifie uniquement le nom de compte SAM.
                  Le nom CN du groupe reste inchangé.
                </small>
              </label>

              <label className="wide">
                <span>Adresse de messagerie</span>
                <input
                  type="email"
                  value={updateForm.mail || ''}
                  onChange={event =>
                    updateObjectFormField(
                      'mail',
                      event.target.value
                    )
                  }
                  disabled={loading}
                />
              </label>

              <label>
                <span>Portée du groupe</span>

            <select
              value={updateForm.groupScope || ''}
              onChange={event => updateObjectFormField(
                'groupScope',
                event.target.value
              )}
              disabled={loading}
            >
              <option value="" disabled>
                Sélectionner une portée
              </option>
              <option value="Global">Globale</option>
              <option value="Universal">Universelle</option>
              <option value="DomainLocal">
                Domaine local
              </option>
            </select>
          </label>

          <label>
            <span>Catégorie du groupe</span>

            <select
              value={updateForm.groupCategory || ''}
              onChange={event => updateObjectFormField(
                'groupCategory',
                event.target.value
              )}
              disabled={loading}
            >
              <option value="" disabled>
                Sélectionner une catégorie
              </option>
              <option value="Security">Sécurité</option>
              <option value="Distribution">
                Distribution
              </option>
            </select>
              </label>

              <label className="wide">
                <span>Remarques</span>
                <textarea
                  rows="4"
                  value={updateForm.info || ''}
                  onChange={event =>
                    updateObjectFormField(
                      'info',
                      event.target.value
                    )
                  }
                  disabled={loading}
                />
              </label>
            </>
          )}

            {(
              isUpdateOrganizationalUnitTarget(currentTarget) ||
              isUpdateComputerTarget(currentTarget)
            ) && (
              <label className="wide aduc-ou-protection-field">
                <span>
                  <input
                    type="checkbox"
                    checked={Boolean(
                      updateForm.protectedFromAccidentalDeletion
                    )}
                    onChange={event => updateObjectFormField(
                      'protectedFromAccidentalDeletion',
                      event.target.checked
                    )}
                    disabled={loading}
                  />
                  Protéger contre la suppression accidentelle
                </span>
              </label>
            )}

          <label className="wide aduc-manager-field">
            <span>Gestionnaire — Nom distinctif</span>

            <div className="aduc-manager-current-row">
              <input
                className="mono"
                value={updateForm.managedBy || ''}
                placeholder="Aucun gestionnaire défini"
                readOnly
                disabled={loading}
              />

              <button
                type="button"
                className="aduc-manager-clear-button"
                onClick={clearManagerSelection}
                disabled={
                  loading ||
                  !updateForm.managedBy
                }
              >
                Retirer
              </button>
            </div>

            <div className="aduc-member-picker-row">
              <input
                value={managerSearchQuery}
                onChange={event => {
                  setManagerSearchQuery(
                    event.target.value
                  )
                  setManagerSearchResults([])
                  setManagerSearchError('')
                }}
                onKeyDown={event => {
                  if (event.key === 'Enter') {
                    event.preventDefault()
                    searchManagerCandidates()
                  }
                }}
                placeholder="Nom, identifiant ou e-mail du gestionnaire..."
                disabled={
                  loading ||
                  managerSearchLoading
                }
              />

              <button
                type="button"
                className="aduc-member-search-button"
                onClick={searchManagerCandidates}
                disabled={
                  loading ||
                  managerSearchLoading ||
                  managerSearchQuery.trim().length < 2
                }
              >
                {managerSearchLoading
                  ? 'Recherche...'
                  : 'Rechercher'}
              </button>
            </div>

            {managerSearchError && (
              <div className="aduc-member-search-error">
                {managerSearchError}
              </div>
            )}

            {managerSearchResults.length > 0 && (
              <div className="aduc-member-search-results aduc-manager-search-results">
                {managerSearchResults.map(
                  candidate => {
                    const candidateDn =
                      getManagerCandidateDn(candidate)

                    return (
                      <button
                        type="button"
                        key={candidateDn}
                        data-kind-label="Gestionnaire possible"
                        onClick={() =>
                          selectManagerCandidate(
                            candidate
                          )
                        }
                      >
                        <strong>
                          {getMemberCandidateTitle(
                            candidate
                          )}
                        </strong>

                        <small>
                          {getMemberCandidateSubtitle(
                            candidate
                          )}
                        </small>
                      </button>
                    )
                  }
                )}
              </div>
            )}

            <small>
              Recherche des utilisateurs actifs dans
              le domaine API.LOCAL.
            </small>
          </label>
        </div>
      </section>
    )}
  </div>

  {showActions && (
<footer className="aduc-modal-actions">
    <button
      type="button"
      onClick={() => handleCancel()}
      disabled={loading}
    >
      Annuler
    </button>

    <button
      type="submit"
      disabled={
        loading ||
        !hasUpdateChanges
      }
    >
      {loading
        ? 'Enregistrement...'
        : hasUpdateChanges
          ? 'Enregistrer les modifications'
          : 'Aucune modification'}
    </button>
  </footer>
)}
</form>
  )
}

export default UpdateObjectForm
