function AccountActionModal({
  account,
}) {
  const {
    accountActionModal,
    setAccountActionModal,
    accountActionLoading,
    getAccountActionLabel,
    adAgentMode,
    accountActionPassword,
    setAccountActionPassword,
    accountActionConfirm,
    setAccountActionConfirm,
    submitAccountAction,
  } = account

  if (!accountActionModal) return null

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

          <div className={`aduc-account-action-warning ${adAgentMode === 'Production' ? 'production' : 'simulation'}`}>
            <strong>Mode agent : {adAgentMode}</strong>
            <p>
              {adAgentMode === 'Production'
                ? 'Cette action modifiera réellement Active Directory.'
                : 'Simulation active : aucune modification réelle ne sera appliquée dans Active Directory.'}
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
            <label className="aduc-account-action-field">
              <span>Mot de passe temporaire</span>
              <input
                type="text"
                value={accountActionPassword}
                onChange={event => setAccountActionPassword(event.target.value)}
                placeholder="Mot de passe temporaire"
                disabled={accountActionLoading}
              />
              <small>Le changement au prochain logon et le déverrouillage après reset seront demandés.</small>
            </label>
          )}

          {adAgentMode === 'Production' && (
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
              className={adAgentMode === 'Production' ? 'danger' : ''}
              onClick={submitAccountAction}
              disabled={accountActionLoading || (adAgentMode === 'Production' && accountActionConfirm !== 'PRODUCTION')}
            >
              {accountActionLoading ? 'Envoi...' : adAgentMode === 'Production' ? 'Confirmer en Production' : 'Lancer en Simulation'}
            </button>
          </footer>
        </section>
      </div>
  )
}

export default AccountActionModal
