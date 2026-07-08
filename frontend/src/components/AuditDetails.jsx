export default function AuditDetails({ details }) {
  const safeDetails = details && typeof details === 'object' ? details : {}

  const labels = {
    request_id: 'ID demande',
    request_type: 'Type demande',
    mode: 'Mode',
    agent: 'Agent',
    username: 'Login',
    display_name: 'Utilisateur',
    email: 'Email',
    department: 'Service',
    job_title: 'Poste',
    current_department: 'Service actuel',
    current_job_title: 'Poste actuel',
    new_department: 'Nouveau service',
    new_job_title: 'Nouveau poste',
    effective_date: 'Date effet',
    end_date: 'Date départ',
    disable_account: 'Désactiver compte',
    remove_groups: 'Retirer groupes',
    convert_mailbox: 'Convertir mailbox',
    forward_to: 'Redirection mail',
    move_to_ou: 'OU cible',
    ou: 'OU cible',
    groups: 'Groupes',
    add_groups: 'Groupes à ajouter',
    remove_groups_list: 'Groupes à retirer',
    success: 'Succès',
    message: 'Message'
  }

  const entries = Object.entries(safeDetails).filter(([, value]) => {
    if (value === null || value === undefined || value === '') return false
    if (Array.isArray(value) && value.length === 0) return false
    return true
  })

  function formatKey(key) {
    return labels[key] || key.replaceAll('_', ' ')
  }

  function formatValue(value) {
    if (value === true) return 'Oui'
    if (value === false) return 'Non'
    if (typeof value === 'string' || typeof value === 'number') return String(value)

    return JSON.stringify(value, null, 2)
  }

  function renderValue(value) {
    if (Array.isArray(value)) {
      return (
        <ul className="audit-details-list">
          {value.map(item => (
            <li key={String(item)}>{String(item)}</li>
          ))}
        </ul>
      )
    }

    if (value && typeof value === 'object') {
      return <pre>{JSON.stringify(value, null, 2)}</pre>
    }

    return <strong>{formatValue(value)}</strong>
  }

  return (
    <details className="audit-details">
      <summary>Détails</summary>

      {entries.length === 0 ? (
        <p className="muted">Aucun détail.</p>
      ) : (
        <div className="audit-details-grid">
          {entries.map(([key, value]) => (
            <div className="audit-details-row" key={key}>
              <span>{formatKey(key)}</span>
              {renderValue(value)}
            </div>
          ))}
        </div>
      )}
    </details>
  )
}
