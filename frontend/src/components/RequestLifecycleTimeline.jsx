export default function RequestLifecycleTimeline({ request, details = {} }) {
  const result = request.agent_result || {}
  const status = String(request.status || '').toLowerCase()

  function formatDate(value) {
    if (!value) return '-'

    const date = new Date(value)

    if (Number.isNaN(date.getTime())) {
      return String(value)
    }

    return date.toLocaleString('fr-FR', {
      dateStyle: 'short',
      timeStyle: 'short'
    })
  }

  function display(value, fallback = '-') {
    if (value === true) return 'Oui'
    if (value === false) return 'Non'
    if (value === null || value === undefined || value === '') return fallback
    return String(value)
  }

  const isRejected = status === 'rejected'
  const isFailed = status === 'failed' || request.failed_at || result.success === false
  const isCompleted = status === 'completed' || request.completed_at
  const isProcessing = status === 'processing'
  const isWaitingApproval = status === 'waiting_approval'
  const isPendingAgent = ['approved', 'pending'].includes(status)

  const isApproved =
    request.approved_at ||
    ['approved', 'pending', 'processing', 'completed', 'failed'].includes(status)

  const hasAgentClaim =
    request.processing_at ||
    request.processing_by ||
    details.agent ||
    isProcessing ||
    isCompleted ||
    isFailed

  const agentName = request.processing_by || details.agent || 'Agent Windows'
  const agentMode = details.mode || result.mode
  const resultMessage = result.message || request.error || request.message

  const steps = [
    {
      label: 'Création',
      value: request.created_at,
      actor: request.created_by || 'Portail React',
      description: 'Demande enregistrée dans EITAS.',
      state: request.created_at ? 'done' : 'current'
    },
    {
      label: isRejected ? 'Rejet validation' : 'Validation',
      value: isRejected ? request.rejected_at : request.approved_at,
      actor: isRejected
        ? request.rejected_by || request.approved_by || 'Admin'
        : request.approved_by || 'Admin',
      description: isRejected
        ? 'La demande a été rejetée avant envoi agent.'
        : isApproved
          ? 'La demande est validée et peut partir vers l’agent.'
          : 'En attente d’approbation administrateur.',
      state: isRejected ? 'bad' : isApproved ? 'done' : isWaitingApproval ? 'current' : 'waiting'
    },
    {
      label: 'File agent',
      value: request.approved_at || request.updated_at,
      actor: 'API EITAS',
      description: isRejected
        ? 'Non envoyée à l’agent car rejetée.'
        : isApproved
          ? 'Demande disponible pour l’agent Windows.'
          : 'En attente de validation avant mise en file.',
      state: isRejected ? 'waiting' : hasAgentClaim ? 'done' : isPendingAgent ? 'current' : 'waiting'
    },
    {
      label: 'Prise en charge',
      value: request.processing_at,
      actor: agentName,
      description: hasAgentClaim
        ? 'La demande a été prise par un agent Windows.'
        : 'Aucun agent ne l’a encore prise en charge.',
      state: isRejected ? 'waiting' : hasAgentClaim ? 'done' : isPendingAgent ? 'current' : 'waiting'
    },
    {
      label: 'Exécution',
      value: request.processing_at || request.completed_at || request.failed_at,
      actor: agentName,
      description: agentMode
        ? `Mode agent : ${agentMode}`
        : isProcessing
          ? 'Traitement en cours côté Windows.'
          : 'En attente d’exécution agent.',
      state: isFailed ? 'bad' : isCompleted ? 'done' : isProcessing ? 'current' : 'waiting'
    },
    {
      label: isFailed ? 'Échec' : isRejected ? 'Rejetée' : isCompleted ? 'Terminée' : 'Fin de traitement',
      value: request.failed_at || request.rejected_at || request.completed_at,
      actor: isRejected ? request.rejected_by || 'Admin' : agentName,
      description: isFailed
        ? display(resultMessage, 'Le traitement agent a échoué.')
        : isRejected
          ? 'Workflow arrêté après rejet.'
          : isCompleted
            ? display(resultMessage, 'Traitement terminé avec succès.')
            : 'Pas encore terminé.',
      state: isFailed || isRejected ? 'bad' : isCompleted ? 'done' : 'waiting'
    }
  ]

  const progressDone = steps.filter(step => step.state === 'done').length
  const progressBad = steps.some(step => step.state === 'bad')

  return (
    <div className={`detail-section lifecycle-section ${progressBad ? 'has-error' : ''}`}>
      <div className="lifecycle-title-row">
        <div>
          <h4>Timeline de traitement</h4>
          <p>Suivi complet du cycle de vie de la demande.</p>
        </div>

        <span className={`lifecycle-progress-pill ${progressBad ? 'bad' : isCompleted ? 'done' : 'current'}`}>
          {progressBad ? 'Erreur / arrêt' : isCompleted ? 'Terminée' : `${progressDone}/${steps.length} étapes`}
        </span>
      </div>

      <div className="lifecycle-timeline">
        {steps.map((step, index) => (
          <div className={`lifecycle-step ${step.state}`} key={`${step.label}-${index}`}>
            <div className="lifecycle-dot">
              <span>{index + 1}</span>
            </div>

            <div className="lifecycle-card">
              <div className="lifecycle-card-header">
                <strong>{step.label}</strong>
                <em>{step.state === 'done' ? 'OK' : step.state === 'current' ? 'En cours' : step.state === 'bad' ? 'Erreur' : 'En attente'}</em>
              </div>

              <span>{formatDate(step.value)}</span>
              <p>{step.description}</p>

              <small>{display(step.actor)}</small>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
