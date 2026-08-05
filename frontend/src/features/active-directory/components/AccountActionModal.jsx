import {
  getAdPasswordResetInputType,
} from '../utils/adPasswordReset'

function AccountActionModal({
  account,
}) {
  const {
    accountActionModal,
    setAccountActionModal,
    accountActionLoading,
    accountActionModeLoading,
    getAccountActionLabel,
    adAgentMode,
    passwordResetDraft,
    updatePasswordResetDraft,
    accountActionConfirm,
    setAccountActionConfirm,
    submitAccountAction,
  } = account

  if (!accountActionModal) return null

  const effectiveAgentMode =
    accountActionModal.agentMode
    || adAgentMode
    || 'Inconnu'

  const isProductionMode =
    effectiveAgentMode === 'Production'

  const isSimulationMode =
    effectiveAgentMode === 'Simulation'

  const isKnownAgentMode =
    isProductionMode || isSimulationMode

  return (
    <div className="aduc-modal-backdrop" onClick={() => !accountActionLoading && setAccountActionModal(null)}>
        <section className="aduc-modal aduc-account-action-modal" onClick={event => event.stopPropagation()}>
          <header>
            <div>
              <span>Action Compte ADUC</span>
              <h3>{getAccountActionLabel(accountActionModal.action)}</h3>
            </div>

            <button type="button" onClick={() => setAccountActionModal(null)} disabled={accountActionLoading}>×</button>
          </header>

          <div
            className={[
              'aduc-account-action-warning',
              isProductionMode
                ? 'production'
                : isSimulationMode
                  ? 'simulation'
                  : 'unknown',
            ].join(' ')}
          >
            <strong>
              Mode agent : {effectiveAgentMode}
            </strong>

            <p>
              {isProductionMode
                ? 'Cette action modifiera réellement Active Directory.'
                : isSimulationMode
                  ? 'Simulation active : aucune modification réelle ne sera appliquée dans Active Directory.'
                  : 'Mode agent indisponible : cette action est bloquée par sécurité.'}
            </p>
          </div>

          <div className="aduc-account-action-target">
            <div>
              <span>Objet cible</span>
              <strong>{accountActionModal.targetName}</strong>
            </div>

            <div>
              <span>DN</span>
              <code>{accountActionModal.targetDn}</code>
            </div>
          </div>

          {accountActionModal.action === 'reset_password' && (
            <div className="aduc-password-reset-fields">
              <label className="aduc-account-action-field">
                <span>Mot de passe temporaire</span>

                <div className="aduc-password-input-row">
                  <input
                    type={getAdPasswordResetInputType(
                      passwordResetDraft.showPassword
                    )}
                    value={
                      passwordResetDraft.temporaryPassword
                    }
                    onChange={event =>
                      updatePasswordResetDraft(
                        'temporaryPassword',
                        event.target.value
                      )
                    }
                    placeholder="Mot de passe temporaire"
                    autoComplete="new-password"
                    disabled={accountActionLoading}
                  />

                  <button
                    type="button"
                    onClick={() =>
                      updatePasswordResetDraft(
                        'showPassword',
                        !passwordResetDraft.showPassword
                      )
                    }
                    aria-pressed={
                      passwordResetDraft.showPassword
                    }
                    disabled={accountActionLoading}
                  >
                    {passwordResetDraft.showPassword
                      ? 'Masquer'
                      : 'Afficher'}
                  </button>
                </div>

                <small>
                  Le mot de passe n’est pas conservé dans
                  les métadonnées d’audit.
                </small>
              </label>

              <div className="aduc-password-reset-options">
                <label>
                  <input
                    type="checkbox"
                    checked={
                      passwordResetDraft
                        .forceChangeAtLogon
                    }
                    onChange={event =>
                      updatePasswordResetDraft(
                        'forceChangeAtLogon',
                        event.target.checked
                      )
                    }
                    disabled={accountActionLoading}
                  />

                  <span>
                    Exiger le changement du mot de passe
                    à la prochaine ouverture de session
                  </span>
                </label>

                <label>
                  <input
                    type="checkbox"
                    checked={
                      passwordResetDraft
                        .unlockAfterReset
                    }
                    onChange={event =>
                      updatePasswordResetDraft(
                        'unlockAfterReset',
                        event.target.checked
                      )
                    }
                    disabled={accountActionLoading}
                  />

                  <span>
                    Déverrouiller le compte après la
                    réinitialisation
                  </span>
                </label>
              </div>
            </div>
          )}

          {isProductionMode && (
            <label className="aduc-account-action-field">
              <span>Confirmation Production</span>
              <input
                type="text"
                value={accountActionConfirm}
                onChange={event => setAccountActionConfirm(event.target.value)}
                placeholder="Tape PRODUCTION"
                disabled={accountActionLoading}
              />
            </label>
          )}

          <footer className="aduc-modal-actions">
            <button type="button" onClick={() => setAccountActionModal(null)} disabled={accountActionLoading}>
              Annuler
            </button>

            <button
              type="button"
              className={
                isProductionMode
                  ? 'danger'
                  : ''
              }
              onClick={submitAccountAction}
              disabled={
                accountActionLoading
                || accountActionModeLoading
                || !isKnownAgentMode
                || (
                  isProductionMode
                  && accountActionConfirm !== 'PRODUCTION'
                )
              }
            >
              {accountActionLoading
                ? 'Envoi...'
                : accountActionModeLoading
                  ? 'Vérification du mode...'
                  : !isKnownAgentMode
                    ? 'Mode agent indisponible'
                    : isProductionMode
                      ? 'Confirmer en Production'
                      : 'Lancer en Simulation'}
            </button>
          </footer>
        </section>
      </div>
  )
}

export default AccountActionModal
