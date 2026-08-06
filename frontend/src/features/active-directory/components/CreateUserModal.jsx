function CreateUserModal({
  creation,
}) {
  const {
    createUserModal,
    closeCreateUserModal,
    createUserLoading,
    submitCreateUser,
    getAdAgentModeLabel,
    isAdProductionMode,
    createUserForm,
    updateCreateUserField,
    createUserOuLoading,
    createUserOuOptions,
    getAdminCreationOuDisplayLabel,
    createUserConfirm,
    setCreateUserConfirm,
    setCreateUserError,
    createUserError,
  } = creation

  if (!createUserModal) return null

  return (
    <div
        className="aduc-modal-backdrop"
        data-eitas-modal="create-user"
        onClick={closeCreateUserModal}
      >
        <section
          className={
            `aduc-modal aduc-create-user-modal${
              createUserModal.copy_source
                ? ' is-copy-mode'
                : ''
            }`
          }
          aria-busy={Boolean(
            createUserModal.copy_preparing
          )}
          onClick={event =>
            event.stopPropagation()
          }
        >
          <header>
            <div>
              <span>Active Directory</span>
              <h3>
                {createUserModal.copy_source
                  ? 'Copier un utilisateur'
                  : 'Créer un utilisateur'}
              </h3>
            </div>

            <button
              type="button"
              onClick={closeCreateUserModal}
              disabled={
                createUserLoading
                && !createUserModal.copy_preparing
              }
              aria-label="Fermer"
            >
              ×
            </button>
          </header>

          {createUserModal.copy_preparing && (
            <div
              className="aduc-copy-user-preparing"
              role="status"
              aria-live="polite"
            >
              <span
                className="aduc-copy-user-spinner"
                aria-hidden="true"
              />

              <div>
                <strong>
                  Chargement du profil complet
                </strong>

                <p>
                  La fenêtre est disponible pendant
                  la récupération des attributs AD.
                </p>
              </div>
            </div>
          )}

          {createUserModal.copy_source && (
            <div
              className="aduc-account-action-warning simulation"
              data-eitas-copy-source="true"
            >
              <strong>
                Copie contrôlée
              </strong>

              <p>
                Profil chargé depuis
                {' '}
                <b>
                  {createUserModal.copy_source.display_name
                    || createUserModal.copy_source.sam_account_name
                    || 'l’utilisateur sélectionné'}
                </b>
                . Les groupes, mots de passe et identifiants
                techniques ne sont jamais copiés.
              </p>
            </div>
          )}

          <form
            className="aduc-create-user-form"
            onSubmit={submitCreateUser}
          >
            <div
              className={`aduc-account-action-warning ${
                isAdProductionMode()
                  ? 'production'
                  : 'simulation'
              }`}
            >
              <strong>
                {getAdAgentModeLabel()}
              </strong>

              <p>
                {isAdProductionMode()
                  ? 'Le compte utilisateur sera réellement créé dans Active Directory.'
                  : 'Simulation active : aucun compte utilisateur réel ne sera créé.'}
              </p>
            </div>

            <div className="aduc-create-user-grid">
              <label>
                <span>Prénom</span>

                <input
                  type="text"
                  data-eitas-create-user-field="first_name"
                  value={createUserForm.first_name}
                  onChange={event =>
                    updateCreateUserField(
                      'first_name',
                      event.target.value
                    )
                  }
                  autoFocus
                  autoComplete="off"
                  disabled={createUserLoading}
                />
              </label>

              <label>
                <span>Nom</span>

                <input
                  type="text"
                  data-eitas-create-user-field="last_name"
                  value={createUserForm.last_name}
                  onChange={event =>
                    updateCreateUserField(
                      'last_name',
                      event.target.value
                    )
                  }
                  autoComplete="off"
                  disabled={createUserLoading}
                />
              </label>

              <label>
                <span>Identifiant AD</span>

                <input
                  type="text"
                  value={
                    createUserForm.sam_account_name
                  }
                  onChange={event =>
                    updateCreateUserField(
                      'sam_account_name',
                      event.target.value.toLowerCase()
                    )
                  }
                  maxLength="20"
                  placeholder="prenom.nom"
                  autoComplete="off"
                  disabled={createUserLoading}
                />

                <small>
                  Maximum 20 caractères, sans espace
                  ni accent.
                </small>
              </label>

              <label>
                <span>UPN de connexion</span>

                <input
                  type="text"
                  value={
                    createUserForm.user_principal_name
                  }
                  onChange={event =>
                    updateCreateUserField(
                      'user_principal_name',
                      event.target.value
                    )
                  }
                  placeholder="prenom.nom@API.LOCAL"
                  autoComplete="off"
                  disabled={createUserLoading}
                />
              </label>

              <label className="wide">
                <span>OU de destination</span>

                <select
                  value={
                    createUserForm.target_ou_dn
                  }
                  onChange={event =>
                    updateCreateUserField(
                      'target_ou_dn',
                      event.target.value
                    )
                  }
                  disabled={
                    createUserLoading
                    || createUserOuLoading
                  }
                >
                  {createUserOuOptions.map(option => (
                    <option
                      key={option.dn}
                      value={option.dn}
                    >
                      {option.label}
                    </option>
                  ))}
                </select>

                <small>
                  Seules les OU situées sous
                  OU=EITAS sont proposées.
                </small>
              </label>

              <label className="wide">
                <span>
                  Mot de passe temporaire
                </span>

                <input
                  type="password"
                  value={
                    createUserForm.temporary_password
                  }
                  onChange={event =>
                    updateCreateUserField(
                      'temporary_password',
                      event.target.value
                    )
                  }
                  placeholder="Minimum 12 caractères"
                  autoComplete="new-password"
                  disabled={createUserLoading}
                />

                <small>
                  Majuscule, minuscule, chiffre et
                  caractère spécial obligatoires.
                </small>
              </label>

              <label className="wide">
                <span>Description</span>

                <textarea
                  value={createUserForm.description}
                  onChange={event =>
                    updateCreateUserField(
                      'description',
                      event.target.value
                    )
                  }
                  rows="3"
                  placeholder="Fonction, service ou motif de création"
                  disabled={createUserLoading}
                />
              </label>

              <details
                className="wide"
                data-eitas-copy-profile="true"
                open={Boolean(
                  createUserModal.copy_source
                )}
              >
                <summary>
                  Profil utilisateur optionnel
                </summary>

                <div className="aduc-create-user-grid">
                  <label>
                    <span>Fonction</span>

                    <input
                      type="text"
                      value={createUserForm.title}
                      onChange={event =>
                        updateCreateUserField(
                          'title',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Service</span>

                    <input
                      type="text"
                      value={createUserForm.department}
                      onChange={event =>
                        updateCreateUserField(
                          'department',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Division</span>

                    <input
                      type="text"
                      value={createUserForm.division}
                      onChange={event =>
                        updateCreateUserField(
                          'division',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Société</span>

                    <input
                      type="text"
                      value={createUserForm.company}
                      onChange={event =>
                        updateCreateUserField(
                          'company',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Bureau</span>

                    <input
                      type="text"
                      value={createUserForm.office}
                      onChange={event =>
                        updateCreateUserField(
                          'office',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Téléphone professionnel</span>

                    <input
                      type="text"
                      value={
                        createUserForm.telephone_number
                      }
                      onChange={event =>
                        updateCreateUserField(
                          'telephone_number',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Téléphone mobile</span>

                    <input
                      type="text"
                      value={createUserForm.mobile}
                      onChange={event =>
                        updateCreateUserField(
                          'mobile',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Code postal</span>

                    <input
                      type="text"
                      value={createUserForm.postal_code}
                      onChange={event =>
                        updateCreateUserField(
                          'postal_code',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Ville</span>

                    <input
                      type="text"
                      value={createUserForm.city}
                      onChange={event =>
                        updateCreateUserField(
                          'city',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label>
                    <span>Région / État</span>

                    <input
                      type="text"
                      value={createUserForm.state}
                      onChange={event =>
                        updateCreateUserField(
                          'state',
                          event.target.value
                        )
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label className="wide">
                    <span>Adresse</span>

                    <textarea
                      value={createUserForm.street_address}
                      onChange={event =>
                        updateCreateUserField(
                          'street_address',
                          event.target.value
                        )
                      }
                      rows="2"
                      autoComplete="off"
                      disabled={createUserLoading}
                    />
                  </label>

                  <label className="wide">
                    <span>Gestionnaire — DN LDAP</span>

                    <input
                      type="text"
                      value={createUserForm.manager}
                      onChange={event =>
                        updateCreateUserField(
                          'manager',
                          event.target.value
                        )
                      }
                      placeholder={
                        'CN=Responsable,'
                        + 'OU=Users,OU=EITAS,'
                        + 'DC=API,DC=LOCAL'
                      }
                      autoComplete="off"
                      disabled={createUserLoading}
                    />

                    <small>
                      Le gestionnaire doit être renseigné
                      sous la forme d’un DN LDAP complet.
                    </small>
                  </label>
                </div>
              </details>
            </div>

            <div className="aduc-create-user-options">
              <label className="aduc-create-user-toggle">
                <input
                  type="checkbox"
                  checked={createUserForm.enabled}
                  onChange={event =>
                    updateCreateUserField(
                      'enabled',
                      event.target.checked
                    )
                  }
                  disabled={createUserLoading}
                />

                <span>
                  Activer immédiatement le compte
                </span>
              </label>

              <label className="aduc-create-user-toggle">
                <input
                  type="checkbox"
                  checked={
                    createUserForm
                      .force_change_at_logon
                  }
                  onChange={event =>
                    updateCreateUserField(
                      'force_change_at_logon',
                      event.target.checked
                    )
                  }
                  disabled={createUserLoading}
                />

                <span>
                  Exiger le changement du mot de
                  passe à la première connexion
                </span>
              </label>
            </div>

            <div className="aduc-create-user-summary">
              <span>Compte préparé</span>

              <strong>
                {createUserForm.user_principal_name
                  || 'UPN en attente'}
              </strong>

              <small>
                {getAdminCreationOuDisplayLabel(
                  createUserForm.target_ou_dn
                )}
              </small>
            </div>

            {isAdProductionMode() && (
              <label className="aduc-create-user-production">
                <span>
                  Confirmation Production
                </span>

                <input
                  type="text"
                  value={createUserConfirm}
                  onChange={event => {
                    setCreateUserConfirm(
                      event.target.value
                    )
                    setCreateUserError('')
                  }}
                  placeholder="Tape PRODUCTION"
                  autoComplete="off"
                  disabled={createUserLoading}
                />

                <small>
                  La saisie exacte est obligatoire
                  avant toute création réelle.
                </small>
              </label>
            )}

            {createUserError && (
              <div
                className="aduc-create-user-error"
                role="alert"
              >
                {createUserError}
              </div>
            )}

            <footer>
              <button
                type="button"
                onClick={closeCreateUserModal}
                disabled={createUserLoading}
              >
                Annuler
              </button>

              <button
                type="submit"
                disabled={
                  createUserLoading
                  || createUserOuLoading
                }
              >
                {createUserModal.copy_preparing
                  ? 'Chargement du profil...'
                  : createUserLoading
                    ? 'Création en cours...'
                    : createUserOuLoading
                    ? 'Chargement des OU...'
                    : isAdProductionMode()
                      ? 'Créer dans Active Directory'
                      : 'Lancer la simulation'}
              </button>
            </footer>
          </form>
        </section>
      </div>
  )
}

export default CreateUserModal
