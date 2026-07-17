function CreateComputerModal({
  creation,
}) {
  const {
    createComputerModal,
    closeCreateComputerModal,
    createComputerLoading,
    submitCreateComputer,
    getAdAgentModeLabel,
    isAdProductionMode,
    createComputerForm,
    updateCreateComputerField,
    computerOuOptions,
    getOuLabelFromDn,
    COMPUTERS_DN,
    createComputerConfirm,
    setCreateComputerConfirm,
    setCreateComputerError,
    createComputerError,
    adAgentModeLoading,
    getCreateComputerValidationError,
  } = creation

  if (!createComputerModal) return null

  return (
    <div
        className="aduc-modal-backdrop"
        onClick={closeCreateComputerModal}
      >
        <section
          className="aduc-modal aduc-create-computer-modal"
          onClick={event => event.stopPropagation()}
        >
          <header>
            <div>
              <span>Active Directory</span>
              <h3>Créer un ordinateur</h3>
            </div>

            <button
              type="button"
              onClick={closeCreateComputerModal}
              disabled={createComputerLoading}
            >
              ×
            </button>
          </header>

          <form
            className="aduc-create-computer-form"
            onSubmit={submitCreateComputer}
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
                  ? 'Le compte ordinateur sera réellement créé dans Active Directory.'
                  : 'Simulation active : aucun compte ordinateur réel ne sera créé.'}
              </p>
            </div>

            <div className="aduc-create-computer-grid">
              <label>
                <span>Nom de l’ordinateur</span>

                <input
                  type="text"
                  value={createComputerForm.name}
                  onChange={event =>
                    updateCreateComputerField(
                      'name',
                      event.target.value.toUpperCase()
                    )
                  }
                  maxLength="15"
                  placeholder="PC-EITAS-001"
                  autoFocus
                  disabled={createComputerLoading}
                />

                <small>
                  1 à 15 caractères : A-Z, chiffres et tirets.
                </small>
              </label>

              <label>
                <span>État initial du compte</span>

                <select
                  value={
                    createComputerForm.enabled
                      ? 'enabled'
                      : 'disabled'
                  }
                  onChange={event =>
                    updateCreateComputerField(
                      'enabled',
                      event.target.value === 'enabled'
                    )
                  }
                  disabled={createComputerLoading}
                >
                  <option value="disabled">
                    Désactivé — recommandé
                  </option>

                  <option value="enabled">
                    Activé
                  </option>
                </select>
              </label>

              <label className="wide">
                <span>OU de destination</span>

                <select
                  value={createComputerForm.target_ou_dn}
                  onChange={event =>
                    updateCreateComputerField(
                      'target_ou_dn',
                      event.target.value
                    )
                  }
                  disabled={createComputerLoading}
                >
                  {!computerOuOptions.some(
                    option =>
                      option.dn ===
                      createComputerForm.target_ou_dn
                  ) && (
                    <option
                      value={
                        createComputerForm.target_ou_dn
                      }
                    >
                      {getOuLabelFromDn(
                        createComputerForm.target_ou_dn
                      )} — personnalisée
                    </option>
                  )}

                  {computerOuOptions.map(option => (
                    <option
                      key={option.dn}
                      value={option.dn}
                    >
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <details className="wide aduc-create-user-advanced-dn">
                <summary>
                  DN personnalisé / avancé
                </summary>

                <input
                  type="text"
                  className="mono"
                  value={createComputerForm.target_ou_dn}
                  onChange={event =>
                    updateCreateComputerField(
                      'target_ou_dn',
                      event.target.value
                    )
                  }
                  placeholder={COMPUTERS_DN}
                  disabled={createComputerLoading}
                />
              </details>

              <label className="wide">
                <span>Description</span>

                <textarea
                  rows="3"
                  maxLength="1024"
                  value={createComputerForm.description}
                  onChange={event =>
                    updateCreateComputerField(
                      'description',
                      event.target.value
                    )
                  }
                  placeholder="Description du poste"
                  disabled={createComputerLoading}
                />
              </label>

              <label>
                <span>Emplacement physique</span>

                <input
                  type="text"
                  maxLength="128"
                  value={createComputerForm.location}
                  onChange={event =>
                    updateCreateComputerField(
                      'location',
                      event.target.value
                    )
                  }
                  placeholder="Ex : Salle informatique"
                  disabled={createComputerLoading}
                />
              </label>

              <div className="aduc-create-computer-summary">
                <span>Compte généré</span>
                <strong>
                  {createComputerForm.name
                    .trim()
                    .toUpperCase() || '—'}$
                </strong>
              </div>

              {isAdProductionMode() && (
                <label className="wide">
                  <span>Confirmation Production</span>

                  <input
                    type="text"
                    value={createComputerConfirm}
                    onChange={event => {
                      setCreateComputerConfirm(
                        event.target.value
                      )
                      setCreateComputerError('')
                    }}
                    placeholder="Tape PRODUCTION"
                    autoComplete="off"
                    disabled={createComputerLoading}
                  />

                  <small>
                    Cette confirmation est obligatoire
                    pour créer réellement le compte.
                  </small>
                </label>
              )}
            </div>

            {createComputerError && (
              <div className="aduc-member-submit-error">
                <strong>
                  Création impossible
                </strong>

                <span>{createComputerError}</span>
              </div>
            )}

            <footer className="aduc-modal-actions">
              <button
                type="button"
                onClick={closeCreateComputerModal}
                disabled={createComputerLoading}
              >
                Annuler
              </button>

              <button
                type="submit"
                className={
                  isAdProductionMode()
                    ? 'danger'
                    : ''
                }
                disabled={
                  createComputerLoading
                  || adAgentModeLoading
                  || Boolean(
                    getCreateComputerValidationError()
                  )
                  || (
                    isAdProductionMode()
                    && createComputerConfirm !== 'PRODUCTION'
                  )
                }
              >
                {createComputerLoading
                  ? 'Création...'
                  : adAgentModeLoading
                    ? 'Vérification du mode...'
                    : isAdProductionMode()
                      ? 'Créer en Production'
                      : 'Lancer la simulation'}
              </button>
            </footer>
          </form>
        </section>
      </div>
  )
}

export default CreateComputerModal
