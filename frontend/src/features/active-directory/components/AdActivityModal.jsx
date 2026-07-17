function AdActivityModal({
  open,
  activity,
  loading,
  error,
  onClose,
  onRefresh,
  onSelectJob,
}) {
  const {
    adActivitySearch,
    setAdActivitySearch,
    adActivityScope,
    setAdActivityScope,
    adActivityShowSimulations,
    setAdActivityShowSimulations,
    adActivityTimeRange,
    setAdActivityTimeRange,
    adActivitySortOrder,
    setAdActivitySortOrder,
    getAdActivityFilteredJobs,
    copyAdActivitySummary,
    exportAdActivityJson,
    exportAdActivityCsv,
    resetAdActivityFilters,
    getAdActivityFilterSummary,
    getAdActivityStatCards,
    getAdActivityRecentJobs,
    getAdActivityCriticalJobs,
    getAdActivityJobStatus,
    getAdActivityActionLabel,
    getAdActivityStatusLabel,
    formatAdActivityDate,
    getAdActivityDate,
    getAdActivityMessage,
    getAdActivityTargetLabel,
    isAdActivitySimulation,
  } = activity

  if (!open) return null

  return (
    <div className="aduc-modal-backdrop" onClick={() => onClose()}>
              <section className="aduc-modal aduc-activity-center-modal" onClick={event => event.stopPropagation()}>
                <header>
                  <div>
                    <span>Centre d’activité Active Directory</span>
                    <h3>Activité AD Admin globale</h3>
                  </div>

                  <button type="button" onClick={() => onClose()}>×</button>
                </header>

                <div className="aduc-activity-actions">
                  <button type="button" onClick={onRefresh} disabled={loading}>
                    {loading ? 'Chargement...' : 'Actualiser l’activité'}
                  </button>
                </div>

                <div className="aduc-activity-tools">
                  <div className="aduc-activity-search">
                    <input
                      value={adActivitySearch}
                      onChange={event => setAdActivitySearch(event.target.value)}
                      placeholder="Rechercher action, objet, agent, message..."
                    />
                    <span>{getAdActivityFilteredJobs().length} résultat(s)</span>
                  </div>

                  <div className="aduc-activity-scope">
                    {[
                      ['all', 'Tout'],
                      ['critical', 'Critiques'],
                      ['failed', 'Échecs']
                    ].map(([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        className={adActivityScope === value ? 'active' : ''}
                        onClick={() => setAdActivityScope(value)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  <div className="aduc-activity-advanced">
                    <button
                      type="button"
                      className={adActivityShowSimulations ? 'active' : ''}
                      onClick={() => setAdActivityShowSimulations(value => !value)}
                    >
                      {adActivityShowSimulations ? 'Simulations visibles' : 'Simulations masquées'}
                    </button>

                    <select value={adActivityTimeRange} onChange={event => setAdActivityTimeRange(event.target.value)}>
                      <option value="all">Toute période</option>
                      <option value="24h">Dernières 24h</option>
                      <option value="7d">Derniers 7j</option>
                    </select>

                    <select value={adActivitySortOrder} onChange={event => setAdActivitySortOrder(event.target.value)}>
                      <option value="newest">Plus récent</option>
                      <option value="oldest">Plus ancien</option>
                    </select>
                  </div>

                  <div className="aduc-activity-export">
                    <button type="button" onClick={copyAdActivitySummary} disabled={getAdActivityFilteredJobs().length === 0}>
                      Copier synthèse
                    </button>
                    <button type="button" onClick={exportAdActivityJson} disabled={getAdActivityFilteredJobs().length === 0}>
                      Export JSON
                    </button>
                    <button type="button" onClick={exportAdActivityCsv} disabled={getAdActivityFilteredJobs().length === 0}>
                      Export CSV
                    </button>
                    <button type="button" className="neutral" onClick={resetAdActivityFilters}>
                      Réinitialiser
                    </button>
                  </div>
                </div>

                <div className="aduc-activity-filter-summary">
                  {getAdActivityFilterSummary()}
                </div>

                <div className="aduc-activity-kpis">
                  {getAdActivityStatCards().map(card => (
                    <article key={card.key} className={`aduc-activity-kpi ${card.key}`}>
                      <span>{card.label}</span>
                      <strong>{card.value}</strong>
                    </article>
                  ))}
                </div>

                {error && (
                  <div className="aduc-admin-history-error">
                    {error}
                  </div>
                )}

                <div className="aduc-activity-grid">
                  <section>
                    <h4>Dernières actions <span>{getAdActivityRecentJobs().length}</span></h4>

                    {getAdActivityRecentJobs().length === 0 ? (
                      <p className="aduc-admin-history-empty">Aucune action AD Admin récente.</p>
                    ) : (
                      <div className="aduc-activity-list">
                        {getAdActivityRecentJobs().map(job => (
                          <button
                            type="button"
                            key={job.id || job.job_id}
                            className={`aduc-activity-row ${getAdActivityJobStatus(job)}`}
                            onClick={() => onSelectJob(job)}
                          >
                            <span className="aduc-activity-dot" />

                            <div>
                              <strong>{getAdActivityActionLabel(job.action)}</strong>
                              <small>
                                {job.claimed_by || job.created_by || '—'} • {getAdActivityStatusLabel(job)} • {formatAdActivityDate(getAdActivityDate(job))}
                              </small>
                              <p>{getAdActivityMessage(job)}</p>
                              <div className="aduc-activity-tags">
                                {getAdActivityTargetLabel(job) && (
                                  <code className="aduc-activity-target">{getAdActivityTargetLabel(job)}</code>
                                )}

                                {isAdActivitySimulation(job) && (
                                  <em className="aduc-activity-simulation-badge">Simulation</em>
                                )}
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </section>

                  <section>
                    <h4>Actions sensibles / erreurs <span>{getAdActivityCriticalJobs().length}</span></h4>

                    {getAdActivityCriticalJobs().length === 0 ? (
                      <p className="aduc-admin-history-empty">Aucune action sensible ou erreur ne correspond aux filtres actuels.</p>
                    ) : (
                      <div className="aduc-activity-list">
                        {getAdActivityCriticalJobs().map(job => (
                          <button
                            type="button"
                            key={job.id || job.job_id}
                            className={`aduc-activity-row ${getAdActivityJobStatus(job)} critical`}
                            onClick={() => onSelectJob(job)}
                          >
                            <span className="aduc-activity-dot" />

                            <div>
                              <strong>{getAdActivityActionLabel(job.action)}</strong>
                              <small>
                                {job.claimed_by || job.created_by || '—'} • {getAdActivityStatusLabel(job)} • {formatAdActivityDate(getAdActivityDate(job))}
                              </small>
                              <p>{getAdActivityMessage(job)}</p>
                              <div className="aduc-activity-tags">
                                {getAdActivityTargetLabel(job) && (
                                  <code className="aduc-activity-target">{getAdActivityTargetLabel(job)}</code>
                                )}

                                {isAdActivitySimulation(job) && (
                                  <em className="aduc-activity-simulation-badge">Simulation</em>
                                )}
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </section>
                </div>

                <footer className="aduc-modal-actions">
                  <button type="button" onClick={() => onClose()}>Fermer</button>
                  <button type="button" onClick={onRefresh}>Actualiser</button>
                </footer>
              </section>
            </div>
  )
}

export default AdActivityModal
