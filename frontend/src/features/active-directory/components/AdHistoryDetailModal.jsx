import {
  formatAdHistoryJson,
  copyText,
} from '../utils/adExplorerCore'

function AdHistoryDetailModal({
  job,
  activity,
  onClose,
}) {
  const {
    getAdActivityJobStatus,
    getAdActivityStatusLabel,
    copyAdHistoryDetailSummary,
    copyAdHistoryDetailJson,
    getAdActivityTargetDn,
    getAdActivityTargetLabel,
    getAdActivityActionLabel,
    getAdActivityDate,
    formatAdActivityDate,
    getAdActivityMessage,
    isAdActivityCritical,
    isAdActivitySimulation,
  } = activity

  if (!job) return null

  return (
    <div className="aduc-modal-backdrop" onClick={() => onClose()}>
              <section className="aduc-modal aduc-history-detail-modal" onClick={event => event.stopPropagation()}>
                <header>
                  <div>
                    <span>Historique AD Admin</span>
                    <h3>Détail de l’action</h3>
                  </div>

                  <button type="button" onClick={() => onClose()}>×</button>
                </header>

                <div className={`aduc-history-detail-summary-card ${getAdActivityJobStatus(job)}`}>
                  <div>
                    <span className="aduc-history-detail-action">
                      {getAdActivityActionLabel(job.action)}
                    </span>

                    <h4>{getAdActivityMessage(job)}</h4>

                    <p>
                      {job.claimed_by || job.created_by || '—'}
                      {' '}• {getAdActivityStatusLabel(job)}
                      {' '}• {formatAdActivityDate(getAdActivityDate(job))}
                    </p>
                  </div>

                  <div className="aduc-history-detail-badges">
                    <strong>{getAdActivityStatusLabel(job)}</strong>
                    {isAdActivitySimulation(job) && <em>Simulation</em>}
                    {isAdActivityCritical(job) && <em>Action critique</em>}
                  </div>
                </div>

                <div className="aduc-history-detail-actions">
                  <button type="button" onClick={() => copyAdHistoryDetailSummary(job)}>
                    Copier résumé
                  </button>

                  <button type="button" onClick={() => copyAdHistoryDetailJson(job)}>
                    Copier JSON job
                  </button>

                  {getAdActivityTargetDn(job) && (
                    <button type="button" onClick={() => copyText(getAdActivityTargetDn(job))}>
                      Copier DN cible
                    </button>
                  )}
                </div>

                <div className="aduc-history-detail-grid">
                  <div>
                    <span>Action</span>
                    <strong>{getAdActivityActionLabel(job.action)}</strong>
                  </div>

                  <div>
                    <span>Statut</span>
                    <strong>{getAdActivityStatusLabel(job)}</strong>
                  </div>

                  <div>
                    <span>Agent</span>
                    <strong>{job.claimed_by || '—'}</strong>
                  </div>

                  <div>
                    <span>Créé par</span>
                    <strong>{job.created_by || '—'}</strong>
                  </div>

                  <div>
                    <span>Création</span>
                    <strong>{formatAdActivityDate(job.created_at)}</strong>
                  </div>

                  <div>
                    <span>Dernière date</span>
                    <strong>{formatAdActivityDate(getAdActivityDate(job))}</strong>
                  </div>

                  {getAdActivityTargetLabel(job) && (
                    <div>
                      <span>Cible</span>
                      <strong>{getAdActivityTargetLabel(job)}</strong>
                    </div>
                  )}

                  {getAdActivityTargetDn(job) && (
                    <div className="aduc-history-detail-grid-wide">
                      <span>DN cible</span>
                      <code>{getAdActivityTargetDn(job)}</code>
                    </div>
                  )}
                </div>

                <div className="aduc-history-detail-message">
                  <div className="aduc-history-detail-message-head">
                    <span>Message</span>
                    <button type="button" onClick={() => copyText(getAdActivityMessage(job))}>
                      Copier
                    </button>
                  </div>

                  <strong>{getAdActivityMessage(job)}</strong>
                </div>

                <div className="aduc-history-detail-json">
                  <div className="aduc-history-detail-json-title">
                    <h4>Résultat agent</h4>
                    <button type="button" onClick={() => copyText(formatAdHistoryJson(job.result || job.output || {}))}>
                      Copier
                    </button>
                  </div>

                  <pre>{formatAdHistoryJson(job.result || job.output || {})}</pre>
                </div>

                <div className="aduc-history-detail-json">
                  <div className="aduc-history-detail-json-title">
                    <h4>Job complet</h4>
                    <button type="button" onClick={() => copyAdHistoryDetailJson(job)}>
                      Copier
                    </button>
                  </div>

                  <pre>{formatAdHistoryJson(job)}</pre>
                </div>

                <footer className="aduc-modal-actions">
                  <button type="button" onClick={() => onClose()}>Fermer</button>
                </footer>
              </section>
            </div>
  )
}

export default AdHistoryDetailModal
