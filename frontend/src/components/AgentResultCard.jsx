function normalizeList(value) {
  if (!value) return []

  if (Array.isArray(value)) {
    return value.filter(Boolean)
  }

  if (typeof value === 'string') {
    return value
      .split(/[\n,;]+/)
      .map(item => item.trim())
      .filter(Boolean)
  }

  return []
}

function boolLabel(value) {
  return value ? 'Oui' : 'Non'
}

function getChangedFieldRows(changedFields = {}) {
  return Object.entries(changedFields || {}).filter(([, value]) => value !== undefined && value !== null && value !== '')
}

function ResultRow({ label, value }) {
  if (value === undefined || value === null || value === '') return null

  return (
    <div className="agent-result-row">
      <span>{label}</span>
      <strong>{String(value)}</strong>
    </div>
  )
}

function ResultList({ title, items, mode }) {
  const list = normalizeList(items)

  if (list.length === 0) return null

  return (
    <div className="agent-result-list-block">
      <strong>{title}</strong>
      <div className="agent-result-chip-list">
        {list.map(item => (
          <span key={item} className={`agent-result-chip ${mode || ''}`}>
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function AgentResultCard({ request }) {
  const result = request?.agent_result

  if (!result) {
    return (
      <section className="agent-result-card pending">
        <div className="agent-result-header">
          <div>
            <span className="agent-result-eyebrow">Résultat agent</span>
            <h3>Aucun résultat agent pour le moment</h3>
          </div>
          <span className="agent-result-status waiting">En attente</span>
        </div>
      </section>
    )
  }

  const details = result.details || {}
  const success = result.success !== false
  const requestType = details.request_type || request?.type || request?.request_type || 'unknown'

  const created = details.created === true
  const disabled = details.disabled === true
  const reactivated = details.account_reactivated === true || details.changed_fields?.enabled === true
  const moved = details.moved === true || Boolean(details.moved_to_ou)

  const groupsAdded = details.groups_added || details.groups || []
  const groupsRemoved = details.groups_removed || []
  const changedFields = getChangedFieldRows(details.changed_fields)

  let title = 'Résultat agent reçu'

  if (requestType === 'onboarding' && created) {
    title = 'Compte Active Directory créé'
  }

  if (requestType === 'offboarding' && disabled) {
    title = 'Compte Active Directory désactivé'
  }

  if (requestType === 'modification' && reactivated) {
    title = 'Compte Active Directory réactivé'
  } else if (requestType === 'modification') {
    title = 'Compte Active Directory modifié'
  }

  return (
    <section className={`agent-result-card ${success ? 'success' : 'error'}`}>
      <div className="agent-result-header">
        <div>
          <span className="agent-result-eyebrow">Résultat agent</span>
          <h3>{title}</h3>
          <p>{result.message || 'Résultat reçu depuis l’agent Windows.'}</p>
        </div>

        <span className={`agent-result-status ${success ? 'ok' : 'ko'}`}>
          {success ? 'Succès' : 'Erreur'}
        </span>
      </div>

      <div className="agent-result-grid">
        <ResultRow label="Agent" value={details.agent} />
        <ResultRow label="Mode" value={details.mode} />
        <ResultRow label="Login" value={details.username} />
        <ResultRow label="Utilisateur" value={details.display_name} />
        <ResultRow label="Email" value={details.email} />
        <ResultRow label="OU" value={details.ou || details.target_ou || details.moved_to_ou} />
        <ResultRow label="Compte créé" value={created ? 'Oui' : null} />
        <ResultRow label="Compte désactivé" value={disabled ? 'Oui' : null} />
        <ResultRow label="Compte réactivé" value={reactivated ? 'Oui' : null} />
        <ResultRow label="Déplacé" value={moved ? 'Oui' : null} />
        <ResultRow label="Mot de passe généré" value={details.password_generated ? boolLabel(details.password_generated) : null} />
        <ResultRow label="Mot de passe stocké API" value={details.password_stored_in_api === false ? 'Non' : null} />
      </div>

      {changedFields.length > 0 && (
        <div className="agent-result-list-block">
          <strong>Champs modifiés</strong>
          <div className="agent-result-change-list">
            {changedFields.map(([key, value]) => (
              <div key={key} className="agent-result-row compact">
                <span>{key}</span>
                <strong>{String(value)}</strong>
              </div>
            ))}
          </div>
        </div>
      )}

      <ResultList title="Groupes ajoutés" items={groupsAdded} mode="added" />
      <ResultList title="Groupes retirés" items={groupsRemoved} mode="removed" />

      {details.error && (
        <div className="agent-result-error">
          {details.error}
        </div>
      )}
    </section>
  )
}
