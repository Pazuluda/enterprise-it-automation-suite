import { useEffect, useState } from 'react'
import AuditDetails from './AuditDetails.jsx'

export default function AuditPage({ auditLogs, loadAuditLogs, auditFocusId = '', setAuditFocusId }) {
  const [auditSearch, setAuditSearch] = useState('')

  useEffect(() => {
    if (auditFocusId) {
      return
    }

    try {
      const stored = window.sessionStorage.getItem('eitasAuditFocusId') || ''

      if (stored && setAuditFocusId) {
        setAuditFocusId(stored)
      }
    } catch {
      // Non bloquant.
    }
  }, [auditFocusId, setAuditFocusId])

  const safeLogs = Array.isArray(auditLogs) ? auditLogs : []
  const activeFilter = String(auditFocusId || auditSearch || '').trim().toLowerCase()

  const filteredLogs = activeFilter
    ? safeLogs.filter(log => {
        const detailsText = JSON.stringify(log.details || {})
        const requestId = String(log.request_id || log.details?.request_id || '')

        const haystack = [
          log.created_at,
          log.timestamp,
          log.action,
          log.actor,
          requestId,
          log.message,
          detailsText
        ].join(' ').toLowerCase()

        return haystack.includes(activeFilter)
      })
    : safeLogs

  function formatAuditDate(value) {
    if (!value) return '-'

    let normalized = String(value)

    if (
      normalized.includes('T') &&
      !normalized.endsWith('Z') &&
      !/[+-]\d{2}:\d{2}$/.test(normalized)
    ) {
      normalized = `${normalized}Z`
    }

    const date = new Date(normalized)

    if (Number.isNaN(date.getTime())) {
      return String(value)
    }

    return date.toLocaleString('fr-FR', {
      dateStyle: 'short',
      timeStyle: 'medium',
      timeZone: 'Europe/Paris'
    })
  }

  function clearAuditFilter() {
    setAuditSearch('')

    if (setAuditFocusId) {
      setAuditFocusId('')
    }

    try {
      window.sessionStorage.removeItem('eitasAuditFocusId')
    } catch {
      // Non bloquant.
    }
  }

  function updateAuditSearch(value) {
    if (setAuditFocusId) {
      setAuditFocusId('')
    }

    try {
      window.sessionStorage.removeItem('eitasAuditFocusId')
    } catch {
      // Non bloquant.
    }

    setAuditSearch(value)
  }

  return (
    <section className="panel audit-panel">
      <div className="panel-header">
        <div>
          <h2>Journal d’audit</h2>
          <p>Dernières actions enregistrées par l’API.</p>
        </div>

        <button onClick={loadAuditLogs}>Recharger</button>
      </div>

      <div className="audit-toolbar">
        <input
          value={auditFocusId || auditSearch}
          onChange={event => updateAuditSearch(event.target.value)}
          placeholder="Rechercher par ID demande, action, acteur, message..."
        />

        {(auditFocusId || auditSearch) && (
          <button className="ghost-button" onClick={clearAuditFilter}>Effacer filtre</button>
        )}
      </div>

      {auditFocusId && (
        <div className="audit-focus-banner">
          <strong>Filtre actif :</strong>
          <span>{auditFocusId}</span>
        </div>
      )}

      <div className="audit-count-line">
        {filteredLogs.length} événement(s) affiché(s) sur {safeLogs.length}
      </div>

      <div className="audit-table-wrap">
        <table className="audit-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Action</th>
              <th>Acteur</th>
              <th>Demande</th>
              <th>Message</th>
              <th>Détails</th>
            </tr>
          </thead>

          <tbody>
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan="6" className="empty">Aucun log à afficher.</td>
              </tr>
            ) : (
              filteredLogs.map((log, index) => {
                const requestId = String(log.request_id || log.details?.request_id || '')
                const isFocused = activeFilter && requestId.toLowerCase().includes(activeFilter)

                return (
                  <tr key={`${log.created_at || log.timestamp || index}-${index}`} className={isFocused ? 'audit-row-focused' : ''}>
                    <td>{formatAuditDate(log.created_at || log.timestamp)}</td>
                    <td><span className="audit-action-badge">{log.action || '-'}</span></td>
                    <td>{log.actor || '-'}</td>
                    <td><code>{requestId || '-'}</code></td>
                    <td>{log.message || '-'}</td>
                    <td>
                      <AuditDetails details={log.details} />
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
