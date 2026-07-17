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
          className="aduc-modal aduc-create-user-modal"
          onClick={event =>
            event.stopPropagation()
          }
        >
          <header>
            <div>
              <span>Active Directory</span>
              <h3>Créer un utilisateur</h3>
            </div>

            <button
              type="button"
              onClick={closeCreateUserModal}
              disabled={createUserLoading}
              aria-label="Fermer"
            >
              ×
            </button>
          </header>

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
                {createUserLoading
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
