import PanelHeader from '../../components/PanelHeader.jsx'

export default function AdChecksPage({
  jobs,
  loadAdCheckJobs,
  openAdCheckJobFromHistory,
  copyAdCheckJobOutput,
  downloadAdCheckJobOutput
}) {
  const safeJobs = Array.isArray(jobs) ? jobs : []

  const stats = {
    total: safeJobs.length,
    completed: safeJobs.filter(job => job.status === 'completed').length,
    failed: safeJobs.filter(job => job.status === 'failed').length,
    running: safeJobs.filter(job => ['pending', 'processing'].includes(String(job.status || '').toLowerCase())).length,
    warnings: safeJobs.reduce((total, job) => total + Number(job.summary?.warnings || 0), 0)
  }

  function formatDate(value) {
    if (!value) return '-'

    const date = new Date(value)

    if (Number.isNaN(date.getTime())) {
      return value
    }

    return date.toLocaleString('fr-FR')
  }

  function statusLabel(status) {
    const value = String(status || '').toLowerCase()

    if (value === 'completed') return 'Terminé'
    if (value === 'failed') return 'Échec'
    if (value === 'processing') return 'En cours'
    if (value === 'pending') return 'En attente'

    return status || 'Inconnu'
  }

  return (
    <div className="ad-check-history-page">
      <section className="ad-check-history-kpis">
        <div>
          <span>Total</span>
          <strong>{stats.total}</strong>
        </div>

        <div>
          <span>Terminés</span>
          <strong>{stats.completed}</strong>
        </div>

        <div>
          <span>En cours</span>
          <strong>{stats.running}</strong>
        </div>

        <div>
          <span>Échecs</span>
          <strong>{stats.failed}</strong>
        </div>

        <div>
          <span>Warnings</span>
          <strong>{stats.warnings}</strong>
        </div>
      </section>

      <section className="panel">
        <PanelHeader
          title="Historique des contrôles AD"
          subtitle="Tous les contrôles Active Directory lancés depuis le portail."
          action={<button type="button" className="secondary" onClick={() => loadAdCheckJobs()}>Recharger</button>}
        />

        <div className="ad-check-history-list">
          {safeJobs.length === 0 && (
            <div className="empty-dashboard-state">
              <strong>Aucun contrôle AD</strong>
              <span>Lance un contrôle depuis la page Demandes pour alimenter l’historique.</span>
            </div>
          )}

          {safeJobs.map(job => {
            const summary = job.summary || {}
            const status = String(job.status || 'unknown').toLowerCase()

            return (
              <article className="ad-check-history-card" key={job.id}>
                <div className="ad-check-history-card-main">
                  <div>
                    <div className="ad-check-history-title">
                      <span className={`ad-check-history-dot ${status}`} />
                      <strong>{statusLabel(job.status)}</strong>
                    </div>

                    <p>{job.message || 'Contrôle AD'}</p>

                    <small>
                      {formatDate(job.created_at)}
                      {job.claimed_by ? ` · Agent ${job.claimed_by}` : ''}
                      {job.completed_at ? ` · Terminé ${formatDate(job.completed_at)}` : ''}
                    </small>
                  </div>

                  <code>{job.id}</code>
                </div>

                <div className="ad-check-history-summary">
                  <span>Contrôlées <strong>{summary.checked ?? job.selected_count ?? '-'}</strong></span>
                  <span>Trouvés <strong>{summary.found ?? '-'}</strong></span>
                  <span>Introuvables <strong>{summary.missing ?? '-'}</strong></span>
                  <span>OU OK <strong>{summary.ou_ok ?? '-'}</strong></span>
                  <span>Warnings <strong>{summary.warnings ?? '-'}</strong></span>
                </div>

                <div className="ad-check-history-actions">
                  <button type="button" onClick={() => openAdCheckJobFromHistory(job)}>
                    Ouvrir résultat
                  </button>

                  <button type="button" onClick={() => copyAdCheckJobOutput(job)}>
                    Copier
                  </button>

                  <button type="button" onClick={() => downloadAdCheckJobOutput(job)}>
                    Télécharger TXT
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      </section>
    </div>
  )
}
