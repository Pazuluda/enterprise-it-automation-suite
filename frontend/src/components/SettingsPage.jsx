import PanelHeader from './PanelHeader.jsx'

function IdentityRow({ label, value }) {
  return (
    <div className="auth-identity-row">
      <span>{label}</span>
      <strong>{value || '—'}</strong>
    </div>
  )
}

export default function SettingsPage({
  authIdentity,
  apiStatus,
  testApi,
  refreshSession,
  reauthenticate,
  logout
}) {
  const roles = Array.isArray(authIdentity?.roles)
    ? authIdentity.roles
    : []

  return (
    <div className="page-stack auth-settings-page">
      <PanelHeader
        title="Session Keycloak"
        subtitle="Authentification OIDC avec Authorization Code et PKCE S256."
        action={(
          <button type="button" onClick={() => testApi(false)}>
            Tester l’API
          </button>
        )}
      />

      <section className="card auth-session-card">
        <div className="section-header">
          <div>
            <h2>Identité connectée</h2>
            <p>
              Les jetons restent uniquement en mémoire et ne sont pas
              enregistrés dans le navigateur.
            </p>
          </div>

          <span className="auth-session-state">
            Authentifié
          </span>
        </div>

        <div className="auth-identity-grid">
          <IdentityRow
            label="Nom"
            value={authIdentity?.displayName}
          />
          <IdentityRow
            label="Identifiant"
            value={authIdentity?.username}
          />
          <IdentityRow
            label="Adresse e-mail"
            value={authIdentity?.email}
          />
          <IdentityRow
            label="État API"
            value={apiStatus}
          />
        </div>

        <div className="auth-role-section">
          <span>Rôles Forteresse</span>

          <div className="auth-role-list">
            {roles.length > 0 ? (
              roles.map(role => (
                <strong key={role} className="auth-role-badge">
                  {role}
                </strong>
              ))
            ) : (
              <em>Aucun rôle métier attribué.</em>
            )}
          </div>
        </div>

        <div className="auth-actions">
          <button type="button" onClick={refreshSession}>
            Renouveler la session
          </button>

          <button
            type="button"
            className="auth-secondary-button"
            onClick={reauthenticate}
          >
            Se réauthentifier
          </button>

          <button
            type="button"
            className="auth-logout-button"
            onClick={logout}
          >
            Se déconnecter
          </button>
        </div>
      </section>

      <section className="card auth-security-card">
        <h2>Protection active</h2>

        <div className="auth-security-grid">
          <IdentityRow
            label="Fournisseur"
            value="Keycloak · realm eitas"
          />
          <IdentityRow
            label="Client"
            value="eitas-portal"
          />
          <IdentityRow
            label="Flux"
            value="Authorization Code"
          />
          <IdentityRow
            label="PKCE"
            value="S256"
          />
          <IdentityRow
            label="API"
            value="Bearer JWT RS256"
          />
          <IdentityRow
            label="Stockage des jetons"
            value="Mémoire uniquement"
          />
        </div>
      </section>
    </div>
  )
}
