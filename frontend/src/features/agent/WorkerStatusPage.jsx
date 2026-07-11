import { useEffect, useMemo, useState } from 'react'

function formatDate(value) {
  if (!value) return 'Jamais'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return String(value)
  }

  return date.toLocaleString('fr-FR')
}

function formatAge(seconds) {
  if (seconds === null || seconds === undefined) return 'inconnu'

  const value = Number(seconds)

  if (Number.isNaN(value)) return 'inconnu'
  if (value < 60) return `${value}s`

  const minutes = Math.floor(value / 60)
  const rest = value % 60

  if (minutes < 60) return `${minutes}m ${rest}s`

  const hours = Math.floor(minutes / 60)
  const minuteRest = minutes % 60

  return `${hours}h ${minuteRest}m`
}

function getWorkerIcon(worker) {
  const role = worker?.role || worker?.worker_id || ''

  if (role.includes('admin')) return '🛠️'
  if (role.includes('read') || role.includes('lookup')) return '🔎'
  if (role.includes('check')) return '🧪'
  if (role.includes('lifecycle')) return '🔁'

  return '⚙️'
}

function getHealthLabel(worker) {
  if (worker?.healthy) return 'Sain'
  if (worker?.is_stale) return 'Silencieux'
  if (worker?.status === 'error') return 'Erreur'

  return 'À vérifier'
}

function getHealthClass(worker) {
  if (worker?.healthy) return 'healthy'
  if (worker?.is_stale) return 'stale'
  if (worker?.status === 'error') return 'error'

  return 'unknown'
}

function WorkerCard({ worker }) {
  const healthClass = getHealthClass(worker)

  return (
    <article className={`worker-card ${healthClass}`}>
      <div className="worker-card-header">
        <div>
          <span className="worker-icon">{getWorkerIcon(worker)}</span>
          <h3>{worker.worker_name || worker.worker_id}</h3>
          <p>{worker.worker_id}</p>
        </div>

        <span className={`worker-status-pill ${healthClass}`}>
          {getHealthLabel(worker)}
        </span>
      </div>

      <div className="worker-meta-grid">
        <div>
          <span>Agent</span>
          <strong>{worker.agent_name || '—'}</strong>
        </div>
        <div>
          <span>Rôle</span>
          <strong>{worker.role || '—'}</strong>
        </div>
        <div>
          <span>Statut</span>
          <strong>{worker.status || 'unknown'}</strong>
        </div>
        <div>
          <span>Mode</span>
          <strong>{worker.mode || '—'}</strong>
        </div>
        <div>
          <span>PID</span>
          <strong>{worker.pid || '—'}</strong>
        </div>
        <div>
          <span>Dernier heartbeat</span>
          <strong>{formatAge(worker.age_seconds)}</strong>
        </div>
      </div>

      <div className="worker-card-footer">
        <span>{worker.details?.script || 'script inconnu'}</span>
        <span>{formatDate(worker.last_seen_at)}</span>
      </div>
    </article>
  )
}

function WorkerEventsTimeline({ events }) {
  const safeEvents = Array.isArray(events) ? events : []

  return (
    <section className="worker-events-panel">
      <div className="worker-events-header">
        <div>
          <h2>Historique workers</h2>
          <p>Derniers changements d’état détectés par les heartbeats.</p>
        </div>

        <span>{safeEvents.length} événement(s)</span>
      </div>

      {safeEvents.length === 0 ? (
        <p className="worker-events-empty">Aucun événement worker enregistré pour le moment.</p>
      ) : (
        <div className="worker-events-list">
          {safeEvents.map(event => {
            const state = event.current_state || 'unknown'

            return (
              <article className={`worker-event-item ${state}`} key={event.id || `${event.worker_id}-${event.created_at}`}>
                <div className="worker-event-dot" />

                <div className="worker-event-body">
                  <div className="worker-event-title">
                    <strong>{event.worker_name || event.worker_id || 'Worker inconnu'}</strong>
                    <span>{formatDate(event.created_at)}</span>
                  </div>

                  <p>
                    {event.message || `${event.previous_state_label || event.previous_state} → ${event.current_state_label || event.current_state}`}
                  </p>

                  <small>
                    {event.previous_state_label || event.previous_state || 'Inconnu'} → {event.current_state_label || event.current_state || 'Inconnu'}
                    {event.mode ? ` · ${event.mode}` : ''}
                    {event.agent_name ? ` · ${event.agent_name}` : ''}
                  </small>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default function WorkerStatusPage({ apiFetch, setMessage }) {
  const [status, setStatus] = useState(null)
  const [workerEvents, setWorkerEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastRefresh, setLastRefresh] = useState('')

  async function loadWorkerEvents(silent = false) {
    try {
      const data = await apiFetch('/api/admin/worker-events?limit=30')
      setWorkerEvents(Array.isArray(data?.events) ? data.events : [])
    }
    catch (err) {
      setWorkerEvents([])

      if (!silent && setMessage) {
        setMessage(err?.message || 'Impossible de charger l’historique workers.')
      }
    }
  }

  async function loadWorkerStatus(silent = false) {
    setLoading(true)
    setError('')

    try {
      const data = await apiFetch('/api/admin/worker-status')
      setStatus(data)
      setLastRefresh(new Date().toLocaleTimeString('fr-FR'))

      await loadWorkerEvents(true)

      if (!silent && setMessage) {
        setMessage('Santé workers rechargée.')
      }
    }
    catch (err) {
      const message = err?.message || 'Erreur chargement santé workers'
      setError(message)

      if (setMessage) {
        setMessage(`Erreur santé workers : ${message}`)
      }
    }
    finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadWorkerStatus(true)
  }, [])

  useEffect(() => {
    if (!autoRefresh) return undefined

    const timer = window.setInterval(() => {
      loadWorkerStatus(true)
    }, 5000)

    function refreshOnFocus() {
      loadWorkerStatus(true)
    }

    function refreshOnVisibility() {
      if (document.visibilityState === 'visible') {
        loadWorkerStatus(true)
      }
    }

    window.addEventListener('focus', refreshOnFocus)
    document.addEventListener('visibilitychange', refreshOnVisibility)

    return () => {
      window.clearInterval(timer)
      window.removeEventListener('focus', refreshOnFocus)
      document.removeEventListener('visibilitychange', refreshOnVisibility)
    }
  }, [autoRefresh])

  const workers = useMemo(() => {
    return Array.isArray(status?.workers) ? status.workers : []
  }, [status])

  const summary = status?.summary || {
    total: 0,
    healthy: 0,
    stale: 0,
    errors: 0,
  }

  return (
    <section className="page-section worker-status-page">
      <div className="page-header split">
        <div>
          <p className="eyebrow">Supervision</p>
          <h1>Santé workers</h1>
          <p>
            Suivi en direct des workers Windows séparés : lifecycle, AD Admin,
            AD Lookup/Explorer et AD Check.
          </p>
        </div>

        <div className="worker-actions">
          <button
            type="button"
            className="secondary"
            onClick={() => setAutoRefresh(value => !value)}
          >
            Auto-refresh : {autoRefresh ? 'ON' : 'OFF'}
          </button>

          <button type="button" onClick={() => loadWorkerStatus(false)} disabled={loading}>
            {loading ? 'Chargement...' : 'Recharger'}
          </button>
        </div>
      </div>

      <div className="worker-summary-grid">
        <div className="worker-summary-card">
          <span>Total</span>
          <strong>{summary.total}</strong>
        </div>
        <div className="worker-summary-card healthy">
          <span>Sains</span>
          <strong>{summary.healthy}</strong>
        </div>
        <div className="worker-summary-card stale">
          <span>Silencieux</span>
          <strong>{summary.stale}</strong>
        </div>
        <div className="worker-summary-card error">
          <span>Erreurs</span>
          <strong>{summary.errors}</strong>
        </div>
      </div>

      <div className="worker-toolbar-note">
        <span>Dernière actualisation : {lastRefresh || '—'}</span>
        <span>Source API : /api/admin/worker-status</span>
      </div>

      {error && (
        <div className="alert error">
          {error}
        </div>
      )}

      {workers.length === 0 && !loading ? (
        <div className="empty-state">
          Aucun worker remonté pour le moment.
        </div>
      ) : (
        <div className="worker-grid">
          {workers.map(worker => (
            <WorkerCard key={worker.worker_id} worker={worker} />
          ))}
        </div>
      )}

      <WorkerEventsTimeline events={workerEvents} />
    </section>
  )
}
