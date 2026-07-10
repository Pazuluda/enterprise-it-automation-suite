import { TypeBadge, StatusBadge } from './Badges.jsx'
import RequestLifecycleTimeline from './RequestLifecycleTimeline.jsx'
import CopyTextButton from './CopyTextButton.jsx'

export default function SmartRequestDrawer({
  request,
  auditLogs = [],
  onClose,
  approveRequest,
  rejectRequest,
  retryRequest,
  setPage,
  openAuditFromRequest
}) {
  const payload = request.ad_payload || request.payload || {}
  const result = request.agent_result || {}
  const details = result.details || {}
  const type = request.type || 'onboarding'
  const requestId = request.id || request.request_id || ''

  function display(value) {
    if (value === true) return 'Oui'
    if (value === false) return 'Non'
    if (value === null || value === undefined || value === '') return '-'
    return String(value)
  }

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

  function getAuditDate(log) {
    return log.timestamp || log.created_at || log.date || ''
  }

  function getAuditRequestId(log) {
    return log.request_id
      || log.details?.request_id
      || log.details?.id
      || log.details?.request?.id
      || ''
  }

  const auditActionLabels = {
    request_created: 'Demande créée',
    onboarding_request_created: 'Création demandée',
    offboarding_request_created: 'Départ demandé',
    modification_request_created: 'Modification demandée',
    request_approved: 'Demande approuvée',
    request_rejected: 'Demande rejetée',
    request_claimed: 'Prise par agent',
    request_completed: 'Traitement terminé',
    request_failed: 'Traitement échoué',
    request_retry: 'Demande relancée',
    request_retried: 'Demande relancée',
    requests_reset: 'Demandes réinitialisées',
    agent_heartbeat: 'Heartbeat agent',
    agent_config_updated: 'Configuration agent',
    agent_schedule_updated: 'Planification agent'
  }

  const relatedAuditLogs = (auditLogs || [])
    .filter(log => {
      if (!requestId) return false

      const directId = String(getAuditRequestId(log) || '').trim()

      if (directId === requestId) {
        return true
      }

      const text = JSON.stringify(log || {})

      return text.includes(requestId)
    })
    .sort((a, b) => {
      const dateA = new Date(getAuditDate(a) || 0).getTime()
      const dateB = new Date(getAuditDate(b) || 0).getTime()

      return dateA - dateB
    })

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

  function renderAuditLogSummary(log) {
    const details = log.details || {}
    const parts = []

    if (log.message) parts.push(log.message)
    if (details.status) parts.push(`Statut : ${details.status}`)
    if (details.agent) parts.push(`Agent : ${details.agent}`)
    if (details.mode) parts.push(`Mode : ${details.mode}`)
    if (details.error) parts.push(`Erreur : ${details.error}`)

    return parts.join(' · ') || 'Événement enregistré.'
  }

  function renderAuditEvents() {
    return (
      <div className="detail-section drawer-audit-section">
        <div className="drawer-audit-title-row">
          <div>
            <h4>Événements audit liés</h4>
            <p>Historique technique attaché à cette demande.</p>
          </div>

          <button type="button" className="audit-shortcut-button compact" onClick={goToAuditLogs}>
            Voir tout
          </button>
        </div>

        {relatedAuditLogs.length === 0 ? (
          <p className="muted">Aucun audit log lié trouvé dans les derniers logs chargés.</p>
        ) : (
          <div className="drawer-audit-list">
            {relatedAuditLogs.slice(-8).map((log, index) => (
              <div className="drawer-audit-item" key={`${log.action}-${getAuditDate(log)}-${index}`}>
                <div className="drawer-audit-dot" />

                <div className="drawer-audit-card">
                  <div className="drawer-audit-card-head">
                    <strong>{auditActionLabels[log.action] || log.action || 'Événement audit'}</strong>
                    <span>{formatDate(getAuditDate(log))}</span>
                  </div>

                  <p>{renderAuditLogSummary(log)}</p>
                  <small>{display(log.actor || log.user || log.source || 'Système')}</small>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  function renderResultValue(value) {
    if (value === true) return 'Oui'
    if (value === false) return 'Non'
    if (value === null || value === undefined || value === '') return '-'

    if (Array.isArray(value)) {
      if (value.length === 0) return '-'

      return (
        <ul className="agent-result-detail-list">
          {value.map(item => (
            <li key={String(item)}>{String(item)}</li>
          ))}
        </ul>
      )
    }

    if (typeof value === 'object') {
      return (
        <pre className="agent-result-detail-json">
          {JSON.stringify(value, null, 2)}
        </pre>
      )
    }

    return String(value)
  }

  function getResultDetailRows() {
    const rows = [
      ['Message', result.message],
      ['Mode', details.mode],
      ['Type traité', details.request_type],
      ['Agent', details.agent || request.processing_by],
      ['Utilisateur', details.username],
      ['Nom affiché', details.display_name],
      ['Email', details.email],
      ['OU cible', details.ou || details.target_ou || details.moved_to_ou || details.move_to_ou],
      ['Compte créé', details.created],
      ['Compte désactivé', details.disabled],
      ['Compte réactivé', details.account_reactivated],
      ['Mot de passe généré', details.password_generated],
      ['Mailbox traitée', details.mailbox_handled],
      ['Conversion mailbox demandée', details.mailbox_convert_requested],
      ['Redirection mail', details.forward_to],
      ['Groupes ajoutés', details.groups_added || details.groups || details.add_groups],
      ['Groupes retirés', details.groups_removed || details.remove_groups],
      ['Champs modifiés', details.changed_fields],
      ['Déplacement OU', details.moved],
      ['Simulation', details.simulated],
      ['Erreur', details.error || request.error]
    ]

    return rows.filter(([, value]) => {
      if (value === false) return true
      if (value === 0) return true
      if (Array.isArray(value)) return value.length > 0
      return value !== null && value !== undefined && value !== ''
    })
  }

  function renderAgentResultDetails() {
    const rows = getResultDetailRows()
    const success = result.success !== false && request.status !== 'failed' && !details.error

    return (
      <div className={`detail-section agent-result-detail-section ${success ? 'ok' : 'error'}`}>
        <div className="agent-result-detail-header">
          <div>
            <h4>Résultat agent détaillé</h4>
            <p>Résumé lisible du retour envoyé par l’agent Windows.</p>
          </div>

          <span className={success ? 'agent-result-pill ok' : 'agent-result-pill error'}>
            {success ? 'Succès' : 'Erreur'}
          </span>
        </div>

        {rows.length === 0 ? (
          <p className="muted">Aucun détail agent disponible.</p>
        ) : (
          <div className="agent-result-detail-grid">
            {rows.map(([label, value]) => (
              <div className="agent-result-detail-row" key={label}>
                <span>{label}</span>
                <strong>{renderResultValue(value)}</strong>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  function reportValue(value) {
    if (value === true) return 'Oui'
    if (value === false) return 'Non'
    if (value === null || value === undefined || value === '') return '-'

    if (Array.isArray(value)) {
      if (value.length === 0) return '-'
      return value.map(item => `  - ${String(item)}`).join('\n')
    }

    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2)
    }

    return String(value)
  }

  function reportLine(label, value) {
    const rendered = reportValue(value)

    if (rendered.includes('\n')) {
      return `${label} :\n${rendered}`
    }

    return `${label} : ${rendered}`
  }

  function buildRequestReportText() {
    const resultRows = getResultDetailRows()
    const auditRows = relatedAuditLogs.slice(-12)

    const lines = [
      '=== RAPPORT DEMANDE EITAS ===',
      '',
      reportLine('Titre', titleForType()),
      reportLine('ID demande', requestId),
      reportLine('Type', type),
      reportLine('Statut', request.status),
      '',
      '--- Identité ---',
      reportLine('Nom', payload.display_name),
      reportLine('Login', payload.username),
      reportLine('Email', payload.email),
      reportLine('Service', payload.department || payload.current_department || payload.new_department),
      reportLine('Poste', payload.job_title || payload.current_job_title || payload.new_job_title),
      reportLine('Manager', payload.manager),
      '',
      '--- Données demande ---',
      reportLine('Date arrivée', payload.start_date),
      reportLine('Date départ', payload.end_date),
      reportLine('Date effet', payload.effective_date),
      reportLine('OU cible', payload.ou || payload.move_to_ou),
      reportLine('Nouveau service', payload.new_department),
      reportLine('Nouveau poste', payload.new_job_title),
      reportLine('Groupes prévus', listValue(payload.groups)),
      reportLine('Groupes à ajouter', listValue(payload.add_groups)),
      reportLine('Groupes à retirer', listValue(payload.remove_groups)),
      reportLine('Commentaire', payload.comment),
      '',
      '--- Suivi ---',
      reportLine('Créée le', request.created_at),
      reportLine('Approuvée par', request.approved_by),
      reportLine('Approuvée le', request.approved_at),
      reportLine('Rejetée par', request.rejected_by),
      reportLine('Rejetée le', request.rejected_at),
      reportLine('Agent', request.processing_by || details.agent),
      reportLine('Traitement le', request.processing_at),
      reportLine('Terminée le', request.completed_at),
      reportLine('Échec le', request.failed_at),
      '',
      '--- Résultat agent ---'
    ]

    if (resultRows.length === 0) {
      lines.push('Aucun détail agent disponible.')
    } else {
      resultRows.forEach(([label, value]) => {
        lines.push(reportLine(label, value))
      })
    }

    lines.push('')
    lines.push('--- Audit logs liés ---')

    if (auditRows.length === 0) {
      lines.push('Aucun audit log lié chargé.')
    } else {
      auditRows.forEach(log => {
        const action = auditActionLabels[log.action] || log.action || 'Événement audit'
        const date = formatDate(getAuditDate(log))
        const actor = log.actor || log.user || log.source || 'Système'
        const summary = renderAuditLogSummary(log)

        lines.push(`- ${date} | ${action} | ${actor} | ${summary}`)
      })
    }

    lines.push('')
    lines.push('--- Rapport généré depuis EITAS React Admin ---')

    return lines.join('\n')
  }

  function sanitizeReportFileName(value) {
    return String(value || 'demande')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 80) || 'demande'
  }

  function downloadRequestReportText() {
    const content = buildRequestReportText()
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const employeeName = payload.display_name || payload.username || requestId || 'demande'
    const timestamp = new Date().toISOString().slice(0, 19).replaceAll(':', '-')

    link.href = url
    link.download = `eitas-rapport-${sanitizeReportFileName(employeeName)}-${timestamp}.txt`

    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  function escapePowerShellString(value) {
    return String(value || '')
      .replace(/'/g, "''")
  }

  function buildAdCheckPowerShellCommand() {
    const username = payload.username || details.username || ''
    const displayName = payload.display_name || details.display_name || username || 'Utilisateur'
    const expectedOu = payload.ou || payload.move_to_ou || details.ou || details.target_ou || details.moved_to_ou || details.move_to_ou || ''
    const requestType = type || details.request_type || 'onboarding'
    const expectedSimulation =
      details.simulated === true ||
      String(details.mode || '').toLowerCase().includes('simulation')

    const typeLabel = requestType === 'offboarding'
      ? 'Contrôle départ / offboarding'
      : requestType === 'modification'
        ? 'Contrôle modification utilisateur'
        : 'Contrôle création utilisateur'

    const lines = [
      '# ============================================================',
      `# EITAS - ${typeLabel}`,
      `# Demande : ${requestId}`,
      `# Utilisateur : ${displayName}`,
      '# À lancer sur SRV-DC01 en PowerShell administrateur',
      '# ============================================================',
      '',
      'Import-Module ActiveDirectory',
      '',
      `$Sam = '${escapePowerShellString(username)}'`,
      `$DisplayName = '${escapePowerShellString(displayName)}'`,
      `$ExpectedOu = '${escapePowerShellString(expectedOu)}'`,
      `$RequestType = '${escapePowerShellString(requestType)}'`,
      `$ExpectedSimulation = ${expectedSimulation ? '$true' : '$false'}`,
      '',
      '$Properties = @(',
      "  'DisplayName',",
      "  'Enabled',",
      "  'mail',",
      "  'Department',",
      "  'Title',",
      "  'Description',",
      "  'Manager',",
      "  'DistinguishedName',",
      "  'WhenCreated',",
      "  'WhenChanged',",
      "  'LastLogonDate'",
      ')',
      '',
      'Write-Host ""',
      'Write-Host "=== RECHERCHE UTILISATEUR AD ===" -ForegroundColor Cyan',
      'Write-Host "SamAccountName attendu : $Sam"',
      'Write-Host "Nom attendu            : $DisplayName"',
      '',
      '$User = $null',
      '$FoundBy = $null',
      '',
      'try {',
      '  $User = Get-ADUser -Identity $Sam -Properties $Properties -ErrorAction Stop',
      "  $FoundBy = 'Identity'",
      '} catch {',
      '  Write-Host "Introuvable par Identity, recherche alternative..." -ForegroundColor Yellow',
      '}',
      '',
      'if (-not $User) {',
      "  $FilterSam = $Sam -replace \"'\", \"''\"",
      "  $FilterName = $DisplayName -replace \"'\", \"''\"",
      `  $Filter = "SamAccountName -eq '$FilterSam' -or UserPrincipalName -like '$FilterSam*' -or DisplayName -eq '$FilterName' -or Name -eq '$FilterName'"`,
      '  $User = Get-ADUser -Filter $Filter -Properties $Properties | Select-Object -First 1',
      "  if ($User) { $FoundBy = 'Filter' }",
      '}',
      '',
      'if (-not $User) {',
      '  Write-Host ""',
      '  Write-Host "UTILISATEUR AD INTROUVABLE" -ForegroundColor Red',
      '  Write-Host "Aucun objet AD trouve pour : $Sam / $DisplayName" -ForegroundColor Red',
      '',
      '  if ($ExpectedSimulation) {',
      '    Write-Host ""',
      '    Write-Host "INFO : cette demande etait en Simulation." -ForegroundColor Yellow',
      '    Write-Host "Donc aucun changement AD reel nest attendu pour cette demande." -ForegroundColor Yellow',
      '  }',
      '',
      '  Write-Host ""',
      '  Write-Host "Ca peut aussi arriver si le compte a ete supprime, renomme, ou si la demande est historique." -ForegroundColor DarkYellow',
      '} else {',
      '  Write-Host ""',
      '  Write-Host "=== UTILISATEUR AD ===" -ForegroundColor Cyan',
      '  Write-Host "Trouve via : $FoundBy" -ForegroundColor Green',
      '  $User | Select-Object SamAccountName,DisplayName,Enabled,mail,Department,Title,Description,DistinguishedName,WhenCreated,WhenChanged,LastLogonDate | Format-List',
      '',
      '  Write-Host ""',
      '  Write-Host "=== GROUPES AD ===" -ForegroundColor Cyan',
      '  Get-ADPrincipalGroupMembership -Identity $User.DistinguishedName | Select-Object Name | Sort-Object Name | Format-Table -AutoSize',
      '',
      '  Write-Host ""',
      '  Write-Host "=== CONTROLE OU ===" -ForegroundColor Cyan',
      '  Write-Host "OU attendue : $ExpectedOu"',
      '  Write-Host "DN actuel   : $($User.DistinguishedName)"',
      '',
      '  if ($ExpectedOu -and $User.DistinguishedName -like "*,$ExpectedOu") {',
      '    Write-Host "OK : utilisateur dans OU attendue" -ForegroundColor Green',
      '  } elseif ($ExpectedOu) {',
      '    Write-Host "ATTENTION : utilisateur pas dans OU attendue" -ForegroundColor Yellow',
      '  } else {',
      '    Write-Host "Aucune OU attendue fournie par la demande" -ForegroundColor DarkYellow',
      '  }',
      '',
      '  Write-Host ""',
      '  Write-Host "=== CONTROLE ETAT COMPTE ===" -ForegroundColor Cyan',
      '  if ($RequestType -eq "offboarding") {',
      '    if ($User.Enabled -eq $false) {',
      '      Write-Host "OK : compte desactive" -ForegroundColor Green',
      '    } else {',
      '      Write-Host "ATTENTION : compte encore actif" -ForegroundColor Red',
      '    }',
      '  } elseif ($RequestType -eq "onboarding") {',
      '    if ($User.Enabled -eq $true) {',
      '      Write-Host "OK : compte actif" -ForegroundColor Green',
      '    } else {',
      '      Write-Host "ATTENTION : compte cree mais desactive" -ForegroundColor Yellow',
      '    }',
      '  } else {',
      '    Write-Host "Etat actuel Enabled : $($User.Enabled)"',
      '  }',
      ''
    ]

    if (requestType === 'modification') {
      lines.push(
        '  Write-Host ""',
        '  Write-Host "=== CONTROLE MODIFICATION ===" -ForegroundColor Cyan',
        '  Write-Host "Departement actuel : $($User.Department)"',
        '  Write-Host "Titre actuel       : $($User.Title)"',
        '  Write-Host "Description        : $($User.Description)"',
        ''
      )
    }

    lines.push(
      '}',
      '',
      'Write-Host ""',
      'Write-Host "=== FIN CONTROLE EITAS ===" -ForegroundColor Cyan'
    )

    return lines.join('\n')
  }

  function downloadAdCheckPowerShellFile() {
    const content = buildAdCheckPowerShellCommand()
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const employeeName = payload.display_name || payload.username || details.display_name || details.username || requestId || 'demande'
    const timestamp = new Date().toISOString().slice(0, 19).replaceAll(':', '-')

    link.href = url
    link.download = `eitas-controle-ad-${sanitizeReportFileName(employeeName)}-${timestamp}.ps1`

    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  function goToAuditLogs() {
    if (typeof openAuditFromRequest === 'function') {
      openAuditFromRequest(requestId)
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
            <p>{payload.display_name || payload.username || requestId}</p>
          </div>

          <div className="drawer-header-actions">
            <CopyTextButton text={buildRequestReportText()} label="Copier rapport" copiedLabel="Rapport copié" />
            <button type="button" className="download-report-button" onClick={downloadRequestReportText}>
              Télécharger rapport
            </button>
            <CopyTextButton text={buildAdCheckPowerShellCommand()} label="Copier contrôle AD" copiedLabel="Contrôle AD copié" />
            <button type="button" className="download-ad-check-button" onClick={downloadAdCheckPowerShellFile}>
              Télécharger contrôle AD
            </button>
            <CopyTextButton text={requestId} label="Copier ID" copiedLabel="ID copié" />
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

        {renderAuditEvents()}

        <div className="detail-section">
          <h4>Suivi de traitement</h4>

          <div className="detail-grid">
            <SmartDetailRow label="ID demande" value={requestId} wide />
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

        {renderAgentResultDetails()}

        <div className="drawer-actions">
          {request.status === 'waiting_approval' && (
            <>
              <button onClick={() => approveRequest?.(requestId)}>Approuver</button>
              <button className="danger-button" onClick={() => rejectRequest?.(requestId)}>Rejeter</button>
            </>
          )}

          {(request.status === 'failed' || request.status === 'rejected') && (
            <button onClick={() => retryRequest?.(requestId)}>Relancer</button>
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
