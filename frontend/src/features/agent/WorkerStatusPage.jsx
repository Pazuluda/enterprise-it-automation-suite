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

export default function WorkerStatusPage({ apiFetch, setMessage }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastRefresh, setLastRefresh] = useState('')

  async function loadWorkerStatus(silent = false) {
    setLoading(true)
    setError('')

    try {
      const data = await apiFetch('/api/admin/worker-status')
      setStatus(data)
      setLastRefresh(new Date().toLocaleTimeString('fr-FR'))

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
    }, 10000)

    return () => window.clearInterval(timer)
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
    </section>
  )
}
