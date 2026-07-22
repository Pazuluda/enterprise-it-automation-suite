import {
  getObjectDn,
  getObjectName,
  getObjectType,
} from '../utils/adExplorerCore'

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
    updateForm,
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
        {!isUpdateComputerTarget(currentTarget) && (
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
          <label>
            <span>Emplacement</span>
            <input
              type="text"
              value={updateForm.location || ''}
              onChange={event => updateObjectFormField(
                'location',
                event.target.value
              )}
              placeholder="Ex : Salle informatique"
              disabled={loading}
            />
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

    {isUpdateUserTarget(currentTarget) && (
      <>
        {[
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
              ['employeeID', 'Employee ID'],
              [
                'employeeNumber',
                'Numéro employé'
              ],
              [
                'manager',
                'Manager — Distinguished Name',
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
          }
        ].map(section => (
          <section key={section.title}>
            <h4>{section.title}</h4>

            <div className="aduc-update-object-grid">
              {section.fields.map(
                ([name, label, wide]) => {
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
                            placeholder="Aucun manager défini"
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
                            placeholder="Nom, identifiant ou e-mail du manager..."
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
                                    data-kind-label="Manager possible"
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
                            : 'text'
                        }
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
                  )
                }
              )}
            </div>
          </section>
        ))}
      </>
    )}
    {isUpdateGroupTarget(currentTarget) && (
      <section>
        <h4>Paramètres du groupe</h4>

        <div className="aduc-update-object-grid">
          <label>
            <span>Étendue du groupe</span>

            <select
              value={updateForm.groupScope || ''}
              onChange={event => updateObjectFormField(
                'groupScope',
                event.target.value
              )}
              disabled={loading}
            >
              <option value="" disabled>
                Sélectionner une étendue
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
          <label className="wide aduc-manager-field">
            <span>Géré par — Distinguished Name</span>

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
