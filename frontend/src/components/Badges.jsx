const TYPE_LABELS = {
  onboarding: 'Création',
  offboarding: 'Départ',
  modification: 'Modification'
}

const STATUS_LABELS = {
  waiting_approval: 'À valider',
  pending: 'En attente agent',
  processing: 'En cours',
  completed: 'Terminée',
  failed: 'Échec',
  rejected: 'Rejetée'
}

export function TypeBadge({ type }) {
  const safeType = type || 'onboarding'

  return (
    <span className={`type-badge ${safeType}`}>
      {TYPE_LABELS[safeType] || safeType}
    </span>
  )
}

export function StatusBadge({ status }) {
  return (
    <span className={`status-badge ${status || 'unknown'}`}>
      {STATUS_LABELS[status] || status || 'Inconnu'}
    </span>
  )
}
