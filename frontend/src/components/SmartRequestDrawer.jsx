import { TypeBadge, StatusBadge } from './Badges.jsx'
import RequestLifecycleTimeline from './RequestLifecycleTimeline.jsx'
import CopyTextButton from './CopyTextButton.jsx'

export default function SmartRequestDrawer({ request, onClose, approveRequest, rejectRequest, retryRequest, setPage, openAuditFromRequest }) {
  const payload = request.ad_payload || request.payload || {}
  const result = request.agent_result || {}
  const details = result.details || {}
  const type = request.type || 'onboarding'

  function display(value) {
    if (value === true) return 'Oui'
    if (value === false) return 'Non'
    if (value === null || value === undefined || value === '') return '-'
    return String(value)
  }

  function listValue(value) {
    if (!value) return []

    if (Array.isArray(value)) {
      return value.filter(Boolean)
    }

    return String(value)
      .split(/[\n,;]/)
      .map(item => item.trim())
      .filter(Boolean)
  }

  function titleForType() {
    if (type === 'offboarding') return 'Détail départ utilisateur'
    if (type === 'modification') return 'Détail modification utilisateur'
    return 'Détail création utilisateur'
  }

  function renderGroups(title, groups, prefix = '') {
    const items = listValue(groups)

    return (
      <div className="detail-section">
        <h4>{title}</h4>

        {items.length === 0 ? (
          <p className="muted">Aucun groupe.</p>
        ) : (
          <ul className="detail-list">
            {items.map(group => (
              <li key={group}>{prefix}{group}</li>
            ))}
          </ul>
        )}
      </div>
    )
  }

  function renderIdentity() {
    return (
      <div className="detail-section">
        <h4>Identité</h4>

        <div className="detail-grid">
          <SmartDetailRow label="Nom" value={payload.display_name} />
          <SmartDetailRow label="Login" value={payload.username} />
          <SmartDetailRow label="Email" value={payload.email} />
          <SmartDetailRow label="Service" value={payload.department} />
          <SmartDetailRow label="Poste" value={payload.job_title} />
          <SmartDetailRow label="Manager" value={payload.manager} />
        </div>
      </div>
    )
  }

  function renderOnboarding() {
    return (
      <>
        {renderIdentity()}

        <div className="detail-section">
          <h4>Création compte</h4>

          <div className="detail-grid">
            <SmartDetailRow label="Prénom" value={payload.first_name} />
            <SmartDetailRow label="Nom" value={payload.last_name} />
            <SmartDetailRow label="Date arrivée" value={payload.start_date} />
            <SmartDetailRow label="OU cible" value={payload.ou} />
          </div>
        </div>

        {renderGroups('Groupes prévus', payload.groups)}
      </>
    )
  }

  function renderOffboarding() {
    return (
      <>
        {renderIdentity()}

        <div className="detail-section danger-section">
          <h4>Actions départ</h4>

          <div className="detail-grid">
            <SmartDetailRow label="Date de départ" value={payload.end_date} />
            <SmartDetailRow label="Désactiver compte" value={payload.disable_account} />
            <SmartDetailRow label="Retirer groupes" value={payload.remove_groups} />
            <SmartDetailRow label="OU cible" value={payload.move_to_ou} />
            <SmartDetailRow label="Convertir mailbox" value={payload.convert_mailbox} />
            <SmartDetailRow label="Redirection mail" value={payload.forward_to} />
            <SmartDetailRow label="Commentaire" value={payload.comment} wide />
          </div>
        </div>
      </>
    )
  }

  function renderModification() {
    return (
      <>
        <div className="detail-section warning-section">
          <h4>Utilisateur modifié</h4>

          <div className="detail-grid">
            <SmartDetailRow label="Nom" value={payload.display_name} />
            <SmartDetailRow label="Login" value={payload.username} />
            <SmartDetailRow label="Manager" value={payload.manager} />
            <SmartDetailRow label="Date d’effet" value={payload.effective_date} />
          </div>
        </div>

        <div className="detail-section">
          <h4>Changements demandés</h4>

          <div className="detail-grid">
            <SmartDetailRow label="Service actuel" value={payload.current_department} />
            <SmartDetailRow label="Nouveau service" value={payload.new_department} />
            <SmartDetailRow label="Poste actuel" value={payload.current_job_title} />
            <SmartDetailRow label="Nouveau poste" value={payload.new_job_title} />
            <SmartDetailRow label="OU cible" value={payload.move_to_ou} />
            <SmartDetailRow label="Commentaire" value={payload.comment} wide />
          </div>
        </div>

        {renderGroups('Groupes à ajouter', payload.add_groups, '+ ')}
        {renderGroups('Groupes à retirer', payload.remove_groups, '- ')}
      </>
    )
  }

  function goToAuditLogs() {
    if (typeof openAuditFromRequest === 'function') {
      openAuditFromRequest(request.id)
      return
    }

    onClose()
  }

  function renderTypeContent() {
    if (type === 'offboarding') return renderOffboarding()
    if (type === 'modification') return renderModification()
    return renderOnboarding()
  }

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="request-drawer" onClick={event => event.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <h3>{titleForType()}</h3>
            <p>{payload.display_name || payload.username || request.id}</p>
          </div>

          <div className="drawer-header-actions">
            <CopyTextButton text={request.id} label="Copier ID" copiedLabel="ID copié" />
            <button type="button" className="audit-shortcut-button" onClick={goToAuditLogs}>Voir audit</button>
            <button className="ghost-button" onClick={onClose}>Fermer</button>
          </div>
        </div>

        <div className="drawer-badges">
          <TypeBadge type={type} />
          <StatusBadge status={request.status} />
        </div>

        {renderTypeContent()}

        <RequestLifecycleTimeline request={request} details={details} />

        <div className="detail-section">
          <h4>Suivi de traitement</h4>

          <div className="detail-grid">
            <SmartDetailRow label="ID demande" value={request.id} wide />
            <SmartDetailRow label="Créée le" value={request.created_at} />
            <SmartDetailRow label="Approuvée par" value={request.approved_by} />
            <SmartDetailRow label="Approuvée le" value={request.approved_at} />
            <SmartDetailRow label="Rejetée par" value={request.rejected_by} />
            <SmartDetailRow label="Rejetée le" value={request.rejected_at} />
            <SmartDetailRow label="Agent" value={request.processing_by || details.agent} />
            <SmartDetailRow label="Traitement le" value={request.processing_at} />
            <SmartDetailRow label="Terminée le" value={request.completed_at} />
            <SmartDetailRow label="Échec le" value={request.failed_at} />
          </div>
        </div>

        <div className="detail-section">
          <h4>Résultat agent</h4>

          <div className="agent-result-box">
            <strong>{display(result.message)}</strong>
            <p>Mode : {display(details.mode)}</p>
            <p>Type traité : {display(details.request_type)}</p>
          </div>
        </div>

        <div className="drawer-actions">
          {request.status === 'waiting_approval' && (
            <>
              <button onClick={() => approveRequest(request.id)}>Approuver</button>
              <button className="danger-button" onClick={() => rejectRequest(request.id)}>Rejeter</button>
            </>
          )}

          {(request.status === 'failed' || request.status === 'rejected') && (
            <button onClick={() => retryRequest(request.id)}>Relancer</button>
          )}

          <button className="ghost-button" onClick={onClose}>Fermer</button>
        </div>
      </aside>
    </div>
  )
}

function SmartDetailRow({ label, value, wide = false }) {
  function display(value) {
    if (value === true) return 'Oui'
    if (value === false) return 'Non'
    if (value === null || value === undefined || value === '') return '-'
    return String(value)
  }

  return (
    <div className={wide ? 'detail-row wide' : 'detail-row'}>
      <span>{label}</span>
      <strong>{display(value)}</strong>
    </div>
  )
}
