function toList(value) {
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

function getRequestType(request, details) {
  return details?.request_type || request?.type || request?.request_type || '-'
}

function getSuccess(result) {
  if (!result) return null
  return result.success !== false
}

function getDetails(result) {
  return result?.details || {}
}

function getTitle(request, result, details) {
  const type = getRequestType(request, details)
  const success = getSuccess(result)

  if (success === false) return 'Erreur agent'

  if (details?.simulated === true || details?.mode === 'Simulation') {
    return 'Simulation terminée'
  }

  if (type === 'onboarding') {
    if (details?.created === true) return 'Compte Active Directory créé'
    return 'Onboarding Active Directory terminé'
  }

  if (type === 'offboarding') {
    if (details?.disabled === true) return 'Compte Active Directory désactivé'
    return 'Offboarding Active Directory terminé'
  }

  if (type === 'modification') {
    if (details?.account_reactivated === true || details?.changed_fields?.enabled === true) {
      return 'Compte Active Directory réactivé'
    }

    return 'Modification Active Directory terminée'
  }

  return result?.message || 'Résultat agent reçu'
}

function getMainBadges(request, result, details) {
  const type = getRequestType(request, details)
  const badges = []

  if (details?.mode) badges.push({ label: details.mode, tone: details.mode === 'Production' ? 'prod' : 'sim' })
  if (type && type !== '-') badges.push({ label: type, tone: 'neutral' })

  if (details?.created === true) badges.push({ label: 'créé', tone: 'success' })
  if (details?.disabled === true) badges.push({ label: 'désactivé', tone: 'danger' })
  if (details?.account_reactivated === true || details?.changed_fields?.enabled === true) {
    badges.push({ label: 'réactivé', tone: 'success' })
  }

  if (details?.moved === true || details?.moved_to_ou) badges.push({ label: 'déplacé', tone: 'info' })

  return badges
}

function InfoRow({ label, value }) {
  if (value === undefined || value === null || value === '') return null

  return (
    <div className="agent-info-row">
      <span>{label}</span>
      <strong>{String(value)}</strong>
    </div>
  )
}

function ChipList({ title, items, tone }) {
  const list = toList(items)

  if (list.length === 0) return null

  return (
    <div className="agent-list-section">
      <h4>{title}</h4>
      <div className="agent-chip-list">
        {list.map(item => (
          <span key={item} className={`agent-chip ${tone || ''}`}>
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}

function ChangedFields({ fields }) {
  const entries = Object.entries(fields || {}).filter(([, value]) => {
    return value !== undefined && value !== null && value !== ''
  })

  if (entries.length === 0) return null

  return (
    <div className="agent-list-section">
      <h4>Champs modifiés</h4>

      <div className="agent-change-grid">
        {entries.map(([key, value]) => (
          <InfoRow key={key} label={key} value={value === true ? 'Oui' : value} />
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
        <div className="agent-result-top">
          <div>
            <span className="agent-eyebrow">Résultat agent</span>
            <h3>Aucun résultat agent</h3>
            <p>La demande n’a pas encore été traitée par l’agent Windows.</p>
          </div>

          <span className="agent-status waiting">En attente</span>
        </div>
      </section>
    )
  }

  const details = getDetails(result)
  const success = getSuccess(result)
  const title = getTitle(request, result, details)
  const badges = getMainBadges(request, result, details)

  const groupsAdded = details.groups_added || details.groups || []
  const groupsRemoved = details.groups_removed || []
  const finalOu = details.ou || details.target_ou || details.moved_to_ou || details.move_to_ou

  return (
    <section className={`agent-result-card ${success ? 'success' : 'error'}`}>
      <div className="agent-result-top">
        <div>
          <span className="agent-eyebrow">Résultat agent</span>
          <h3>{title}</h3>
          <p>{result.message || 'Résultat reçu depuis l’agent Windows.'}</p>
        </div>

        <span className={`agent-status ${success ? 'ok' : 'ko'}`}>
          {success ? 'Succès' : 'Erreur'}
        </span>
      </div>

      {badges.length > 0 && (
        <div className="agent-badge-line">
          {badges.map((badge, index) => (
            <span key={`${badge.label}-${index}`} className={`agent-badge ${badge.tone}`}>
              {badge.label}
            </span>
          ))}
        </div>
      )}

      <div className="agent-info-grid">
        <InfoRow label="Agent" value={details.agent} />
        <InfoRow label="Mode" value={details.mode} />
        <InfoRow label="Type traité" value={getRequestType(request, details)} />
        <InfoRow label="Login" value={details.username} />
        <InfoRow label="Utilisateur" value={details.display_name} />
        <InfoRow label="Email" value={details.email} />
        <InfoRow label="OU finale" value={finalOu} />
        <InfoRow label="Compte créé" value={details.created === true ? 'Oui' : null} />
        <InfoRow label="Compte désactivé" value={details.disabled === true ? 'Oui' : null} />
        <InfoRow label="Compte réactivé" value={(details.account_reactivated === true || details.changed_fields?.enabled === true) ? 'Oui' : null} />
        <InfoRow label="Déplacé" value={(details.moved === true || details.moved_to_ou) ? 'Oui' : null} />
        <InfoRow label="Mot de passe généré" value={details.password_generated === true ? 'Oui' : null} />
        <InfoRow label="Mot de passe stocké API" value={details.password_stored_in_api === false ? 'Non' : null} />
      </div>

      <ChangedFields fields={details.changed_fields} />

      <ChipList title="Groupes ajoutés" items={groupsAdded} tone="added" />
      <ChipList title="Groupes retirés" items={groupsRemoved} tone="removed" />

      {details.error && (
        <div className="agent-error-box">
          {details.error}
        </div>
      )}
    </section>
  )
}
