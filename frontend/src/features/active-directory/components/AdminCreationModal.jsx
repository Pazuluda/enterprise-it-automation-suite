function AdminCreationModal({
  creation,
}) {
  const {
    loading,
    adminModal,
    adminForm,
    setAdminForm,
    adminLoading,
    setAdminError,
    adminOuOptions,
    adminOuLoading,
    adAgentModeLoading,
    getAdAgentModeLabel,
    isAdProductionMode,
    getAdminCreationOuDisplayLabel,
    getAdminCreationValidationError,
    getAdminCreationInlineError,
    updateAdminFormField,
    closeAdminCreationModal,
    submitAdAdminJob,
  } = creation

  if (!adminModal) return null

  return (
    <div
              className="aduc-modal-backdrop"
              onClick={closeAdminCreationModal}
            >
              <form
                className={
                  "aduc-modal "
                  + "aduc-admin-create-modal "
                  + "aduc-admin-create-modal-compact"
                }
                onSubmit={submitAdAdminJob}
                onClick={event =>
                  event.stopPropagation()
                }
              >
                <header>
                  <div>
                    <span>
                      Administration Active Directory
                    </span>

                    <h3>{adminModal.title}</h3>
                  </div>

                  <button
                    type="button"
                    onClick={closeAdminCreationModal}
                    disabled={adminLoading}
                  >
                    ×
                  </button>
                </header>

                <div
                  className={
                    `aduc-account-action-warning ${
                      isAdProductionMode()
                        ? 'production'
                        : 'simulation'
                    }`
                  }
                >
                  <strong>
                    {getAdAgentModeLabel()}
                  </strong>

                  <p>
                    {isAdProductionMode()
                      ? (
                        adminModal.action === 'create_ou'
                          ? 'L’OU sera réellement créée dans Active Directory.'
                          : 'Le groupe sera réellement créé dans Active Directory.'
                      )
                      : 'Simulation active : aucun objet réel ne sera créé.'}
                  </p>
                </div>

                <section
                  className="aduc-admin-create-section"
                >
                  <div
                    className={
                      "aduc-admin-create-section-head"
                    }
                  >
                    <div>
                      <span>Destination</span>

                      <strong>
                        {adminForm.parent_dn
                          ? getAdminCreationOuDisplayLabel(
                            adminForm.parent_dn
                          )
                          : 'Aucune OU sélectionnée'}
                      </strong>
                    </div>

                    <small>
                      {adminOuLoading
                        ? 'Chargement...'
                        : `${adminOuOptions.length} OU`}
                    </small>
                  </div>

                  <label className="aduc-admin-field">
                    <span>Emplacement de création</span>

                    <select
                      key={
                        adminOuOptions
                          .map(option => option.dn)
                          .join('|')
                        || 'admin-ou-loading'
                      }
                      value={
                        adminForm.parent_dn || ''
                      }
                      disabled={
                        adminOuLoading
                        || adminLoading
                      }
                      onChange={event =>
                        updateAdminFormField(
                          'parent_dn',
                          event.target.value
                        )
                      }
                    >
                      {!adminForm.parent_dn && (
                        <option value="" disabled>
                          Choisir une OU
                        </option>
                      )}

                      {adminOuLoading && (
                        <option
                          value={
                            adminForm.parent_dn || ''
                          }
                        >
                          Chargement des OU...
                        </option>
                      )}

                      {!adminOuLoading
                        && adminForm.parent_dn
                        && !adminOuOptions.some(
                          option =>
                            option.dn.toUpperCase()
                            === adminForm.parent_dn
                              .toUpperCase()
                        )
                        && (
                        <option
                          value={adminForm.parent_dn}
                        >
                          {getAdminCreationOuDisplayLabel(
                            adminForm.parent_dn
                          )} — personnalisée
                        </option>
                      )}

                      {!adminOuLoading
                        && adminOuOptions.map(
                          option => (
                            <option
                              key={option.dn}
                              value={option.dn}
                            >
                              {option.label}
                            </option>
                          )
                        )}
                    </select>
                  </label>

                  <details
                    className={
                      "aduc-create-user-advanced-dn "
                      + "aduc-admin-create-advanced"
                    }
                  >
                    <summary>
                      DN personnalisé / avancé
                    </summary>

                    <input
                      value={
                        adminForm.parent_dn || ''
                      }
                      onChange={event =>
                        updateAdminFormField(
                          'parent_dn',
                          event.target.value
                        )
                      }
                      placeholder={
                        "OU=Groups,OU=EITAS,"
                        + "DC=API,DC=LOCAL"
                      }
                      disabled={adminLoading}
                    />
                  </details>
                </section>

                <section
                  className="aduc-admin-create-section"
                >
                  <div
                    className={
                      "aduc-admin-create-section-head"
                    }
                  >
                    <div>
                      <span>Informations</span>

                      <strong>
                        {adminModal.action === 'create_ou'
                          ? 'Nouvelle unité d’organisation'
                          : 'Nouveau groupe Active Directory'}
                      </strong>
                    </div>
                  </div>

                  <div
                    className={
                      `aduc-admin-create-identity-grid ${
                        adminModal.action
                        === 'create_group'
                          ? 'two-columns'
                          : ''
                      }`
                    }
                  >
                    <label className="aduc-admin-field">
                      <span>
                        {adminModal.action === 'create_ou'
                          ? 'Nom de l’OU'
                          : 'Nom du groupe'}
                      </span>

                      <input
                        value={adminForm.name}
                        onChange={event => {
                          const value =
                            event.target.value

                          setAdminForm(current => ({
                            ...current,
                            name: value,
                            sam_account_name:
                              adminModal.action
                              === 'create_group'
                                ? value
                                : current
                                  .sam_account_name
                          }))

                          setAdminError('')
                        }}
                        placeholder={
                          adminModal.action === 'create_ou'
                            ? 'Finance'
                            : 'GG_Finance_RW'
                        }
                        autoFocus
                        disabled={adminLoading}
                      />
                    </label>

                    {adminModal.action
                      === 'create_group' && (
                      <label
                        className="aduc-admin-field"
                      >
                        <span>SamAccountName</span>

                        <input
                          value={
                            adminForm.sam_account_name
                          }
                          onChange={event =>
                            updateAdminFormField(
                              'sam_account_name',
                              event.target.value
                            )
                          }
                          placeholder="GG_Finance_RW"
                          disabled={adminLoading}
                        />
                      </label>
                    )}
                  </div>

                  {adminModal.action
                    === 'create_group' && (
                    <div
                      className={
                        "aduc-admin-create-options-grid"
                      }
                    >
                      <label
                        className="aduc-admin-field"
                      >
                        <span>Portée</span>

                        <select
                          value={
                            adminForm.group_scope
                          }
                          onChange={event =>
                            updateAdminFormField(
                              'group_scope',
                              event.target.value
                            )
                          }
                          disabled={adminLoading}
                        >
                          <option value="Global">
                            Globale
                          </option>

                          <option value="Universal">
                            Universelle
                          </option>

                          <option value="DomainLocal">
                            Domaine local
                          </option>
                        </select>
                      </label>

                      <label
                        className="aduc-admin-field"
                      >
                        <span>Catégorie</span>

                        <select
                          value={
                            adminForm.group_category
                          }
                          onChange={event =>
                            updateAdminFormField(
                              'group_category',
                              event.target.value
                            )
                          }
                          disabled={adminLoading}
                        >
                          <option value="Security">
                            Sécurité
                          </option>

                          <option value="Distribution">
                            Distribution
                          </option>
                        </select>
                      </label>
                    </div>
                  )}

                  <label className="aduc-admin-field">
                    <span>Description</span>

                    <textarea
                      value={adminForm.description}
                      onChange={event =>
                        updateAdminFormField(
                          'description',
                          event.target.value
                        )
                      }
                      placeholder="Description optionnelle"
                      disabled={adminLoading}
                    />
                  </label>
                </section>

                <div
                  className={
                    "aduc-admin-create-summary-compact"
                  }
                >
                  <div>
                    <span>Création prévue</span>

                    <strong>
                      {adminForm.name.trim()
                        || 'Nom à renseigner'}
                      {' → '}
                      {adminForm.parent_dn
                        ? getAdminCreationOuDisplayLabel(
                          adminForm.parent_dn
                        )
                        : 'OU non sélectionnée'}
                    </strong>
                  </div>

                  <code>
                    {adminForm.parent_dn
                      || 'DN non sélectionné'}
                  </code>
                </div>

                {getAdminCreationInlineError() && (
                  <div
                    className={
                      "aduc-admin-create-error-compact"
                    }
                  >
                    <strong>Attention :</strong>

                    <span>
                      {getAdminCreationInlineError()}
                    </span>
                  </div>
                )}

                <footer>
                  <button
                    type="button"
                    onClick={closeAdminCreationModal}
                    disabled={adminLoading}
                  >
                    Annuler
                  </button>

                  <button
                    type="submit"
                    disabled={
                      adminLoading
                      || adminOuLoading
                      || adAgentModeLoading
                      || Boolean(
                        getAdminCreationValidationError()
                      )
                    }
                  >
                    {adminLoading
                      ? 'Création en cours...'
                      : adminOuLoading
                        ? 'Chargement des OU...'
                        : adminModal.action
                          === 'create_ou'
                          ? 'Créer l’OU'
                          : 'Créer le groupe'}
                  </button>
                </footer>
              </form>
            </div>
  )
}

export default AdminCreationModal
