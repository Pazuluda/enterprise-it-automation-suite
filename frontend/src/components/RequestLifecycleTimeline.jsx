export default function RequestLifecycleTimeline({ request, details = {} }) {
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

  const approvedOrRejected = request.status === 'rejected'
    ? {
        label: 'Rejetée',
        value: request.rejected_at,
        actor: request.rejected_by,
        state: 'bad'
      }
    : {
        label: 'Approuvée',
        value: request.approved_at,
        actor: request.approved_by,
        state: request.approved_at ? 'done' : 'waiting'
      }

  const finalStep = request.status === 'failed'
    ? {
        label: 'Échec',
        value: request.failed_at,
        actor: details.agent || request.processing_by,
        state: 'bad'
      }
    : {
        label: 'Terminée',
        value: request.completed_at,
        actor: details.agent || request.processing_by,
        state: request.completed_at ? 'done' : 'waiting'
      }

  const steps = [
    {
      label: 'Créée',
      value: request.created_at,
      actor: 'Portail React',
      state: request.created_at ? 'done' : 'waiting'
    },
    approvedOrRejected,
    {
      label: 'Agent',
      value: request.processing_at,
      actor: request.processing_by || details.agent,
      state: request.processing_at ? 'done' : 'waiting'
    },
    finalStep
  ]

  return (
    <div className="detail-section lifecycle-section">
      <h4>Timeline de traitement</h4>

      <div className="lifecycle-timeline">
        {steps.map((step, index) => (
          <div className={`lifecycle-step ${step.state}`} key={`${step.label}-${index}`}>
            <div className="lifecycle-dot">
              <span>{index + 1}</span>
            </div>

            <div className="lifecycle-card">
              <strong>{step.label}</strong>
              <span>{formatDate(step.value)}</span>
              <p>{step.actor || '-'}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
