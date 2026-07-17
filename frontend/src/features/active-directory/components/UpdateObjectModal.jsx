import {
  getObjectDn,
  getObjectName,
  getObjectType,
} from '../utils/adExplorerCore'

function UpdateObjectModal({
  update,
}) {
  const {
    updateModal,
    loading,
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
    getMemberCandidateTitle,
    getMemberCandidateSubtitle,
  } = update

  if (!updateModal) return null

  return (
    <div
        className="aduc-modal-backdrop"
        onClick={() => !loading && setUpdateModal(null)}
      >
        <section
          className="aduc-modal aduc-update-object-modal"
          onClick={event => event.stopPropagation()}
        >
          <header>
            <div>
              <span>Active Directory</span>
              <h3>Modifier les propriétés</h3>
            </div>

            <button
              type="button"
              onClick={() => setUpdateModal(null)}
              disabled={loading}
            >
              ×
            </button>
          </header>

          <form onSubmit={submitUpdateObject}>
            <div className="aduc-update-object-target">
              <div>
                <span>Objet cible</span>
                <strong>{getObjectName(updateModal)}</strong>
              </div>

              <div>
                <span>Type</span>
                <strong>{getObjectType(updateModal)}</strong>
              </div>

              <div className="wide">
                <span>DN</span>
                <code>{getObjectDn(updateModal)}</code>
              </div>
            </div>

            <p className="aduc-update-object-help">
              Seuls les champs modifiés seront envoyés au worker.
              Vider un champ supprimera l’attribut correspondant
              dans Active Directory.
            </p>

            <div className="aduc-update-object-sections">
              <section>
                <h4>Informations générales</h4>

                <div className="aduc-update-object-grid">
                  {!isUpdateComputerTarget(updateModal) && (
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

                  {isUpdateComputerTarget(updateModal) && (
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

              {isUpdateUserTarget(updateModal) && (
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
            </div>

            <footer className="aduc-modal-actions">
              <button
                type="button"
                onClick={() => setUpdateModal(null)}
                disabled={loading}
              >
                Annuler
              </button>

              <button
                type="submit"
                disabled={loading}
              >
                {loading
                  ? 'Enregistrement...'
                  : 'Enregistrer les modifications'}
              </button>
            </footer>
          </form>
        </section>
      </div>
  )
}

export default UpdateObjectModal
