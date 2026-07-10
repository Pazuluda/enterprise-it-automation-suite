import { useState } from 'react'
import PanelHeader from '../../components/PanelHeader.jsx'

export default function AgentOperationsPage({ requests, agentStatus, agentConfig, loadAgentStatus, loadAgentConfig, updateAgentInterval, updateAgentPause, agentHistory, loadAgentHistory }) {
  const [copiedCommand, setCopiedCommand] = useState('')

  const agentRuns = (requests || [])
    .filter(request => request.agent_result || request.processing_by || request.completed_at)
    .sort((a, b) => {
      const dateA = new Date(a.completed_at || a.updated_at || a.created_at || 0).getTime()
      const dateB = new Date(b.completed_at || b.updated_at || b.created_at || 0).getTime()
      return dateB - dateA
    })

  const last = agentRuns[0]
  const result = last?.agent_result || {}
  const details = result.details || {}

  const pendingCount = (requests || []).filter(request => {
    return ['approved', 'pending', 'processing'].includes(request.status)
  }).length

  const failedCount = (requests || []).filter(request => {
    return ['failed', 'error'].includes(request.status)
  }).length

  const heartbeatOnline = agentStatus?.online === true
  const heartbeatSeen = agentStatus?.received_at
  const heartbeatSeconds = agentStatus?.seconds_since_seen

  const agentName = agentStatus?.agent_name || details.agent || last?.processing_by || 'SRV-DC01'
  const mode = agentStatus?.mode || details.mode || '-'
  const lastRun = heartbeatSeen || last?.completed_at || last?.updated_at || last?.created_at
  const lastMessage = agentStatus?.message || result.message || 'Aucun résultat agent récent.'
  const lastSuccess = heartbeatOnline || result.success !== false

  const powershellCommands = [
    {
      title: 'Voir la tâche planifiée',
      code: 'Get-ScheduledTaskInfo -TaskName "EITAS Employee Lifecycle Agent"'
    },
    {
      title: 'Lancer l’agent maintenant',
      code: 'Start-ScheduledTask -TaskName "EITAS Employee Lifecycle Agent"'
    },
    {
      title: 'Voir les logs du jour',
      code: 'Get-Content C:\\EnterpriseIT\\agent-windows\\logs\\agent-$(Get-Date -Format "yyyy-MM-dd").log -Tail 120'
    },
    {
      title: 'Passer en Simulation',
      code: '$Config = Get-Content C:\\EnterpriseIT\\agent-windows\\config.json -Raw | ConvertFrom-Json\n$Config.Mode = "Simulation"\n$Config | ConvertTo-Json -Depth 10 | Set-Content C:\\EnterpriseIT\\agent-windows\\config.json -Encoding UTF8'
    },
    {
      title: 'Passer en Production',
      code: '$Config = Get-Content C:\\EnterpriseIT\\agent-windows\\config.json -Raw | ConvertFrom-Json\n$Config.Mode = "Production"\n$Config | ConvertTo-Json -Depth 10 | Set-Content C:\\EnterpriseIT\\agent-windows\\config.json -Encoding UTF8'
    },
    {
      title: 'Désactiver temporairement l’agent automatique',
      code: 'Disable-ScheduledTask -TaskName "EITAS Employee Lifecycle Agent"'
    },
    {
      title: 'Réactiver l’agent automatique',
      code: 'Enable-ScheduledTask -TaskName "EITAS Employee Lifecycle Agent"'
    }
  ]


  async function copyAgentCommand(title, code) {
    const text = code

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
      }
      else {
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.setAttribute('readonly', '')
        textarea.style.position = 'fixed'
        textarea.style.top = '-9999px'
        textarea.style.left = '-9999px'

        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()

        const copied = document.execCommand('copy')
        document.body.removeChild(textarea)

        if (!copied) {
          throw new Error('fallback copy failed')
        }
      }

      setCopiedCommand(title)

      window.setTimeout(() => {
        setCopiedCommand('')
      }, 1800)
    }
    catch {
      window.prompt('Copie automatique bloquée. Copie la commande ici :', text)
    }
  }


  function getWindowsTaskStateLabel(state) {
    const labels = {
      Ready: 'Prête',
      Running: 'En cours',
      Disabled: 'Désactivée',
      Queued: 'En file d’attente',
      Unknown: 'Inconnue'
    }

    return labels[state] || state || '-'
  }

  function getWindowsTaskResultLabel(code) {
    const numericCode = Number(code)

    const labels = {
      0: 'Succès',
      267008: 'Prête',
      267009: 'En cours d’exécution',
      267010: 'Tâche désactivée',
      267011: 'Jamais lancée',
      267014: 'Déclencheurs désactivés'
    }

    if (code === null || code === undefined || code === '') {
      return '-'
    }

    return labels[numericCode] || `Code ${code}`
  }


  function getAgentHistoryActionLabel(action) {
    const labels = {
      agent_processing_paused: 'Pause activée',
      agent_processing_resumed: 'Traitement repris',
      agent_interval_updated: 'Fréquence modifiée'
    }

    return labels[action] || action || '-'
  }

  function getAgentHistoryActorLabel(actor) {
    const labels = {
      'react-admin': 'Portail admin',
      api: 'API',
      agent: 'Agent Windows'
    }

    return labels[actor] || actor || '-'
  }


  function buildAgentDiagnosticText() {
    const diagnostic = {
      generated_at: new Date().toISOString(),
      agent: {
        online: agentStatus?.online ?? null,
        agent_name: agentStatus?.agent_name || agentName,
        computer_name: agentStatus?.computer_name || '-',
        mode,
        script: agentStatus?.script || '-',
        received_at: agentStatus?.received_at || null,
        seconds_since_seen: agentStatus?.seconds_since_seen ?? null,
        message: agentStatus?.message || null
      },
      processing: {
        pause_processing: agentConfig?.pause_processing ?? agentStatus?.pause_processing ?? false,
        pending_count: pendingCount,
        failed_count: failedCount
      },
      schedule: {
        configured_interval_minutes: agentConfig?.interval_minutes || null,
        applied_interval_minutes: agentStatus?.schedule_interval_minutes || null,
        task_name: agentConfig?.task_name || agentStatus?.task?.task_name || 'EITAS Employee Lifecycle Agent'
      },
      windows_task: agentStatus?.task || null,
      paths: {
        wrapper: 'C:\\EnterpriseIT\\agent-windows\\Run-EitasAgent.ps1',
        script: 'C:\\EnterpriseIT\\agent-windows\\Invoke-EmployeeLifecycleAgent.ps1',
        config: 'C:\\EnterpriseIT\\agent-windows\\config.json',
        logs: 'C:\\EnterpriseIT\\agent-windows\\logs'
      },
      recent_agent_history: (agentHistory || []).slice(0, 5).map(log => ({
        timestamp: log.timestamp,
        action: log.action,
        actor: log.actor,
        message: log.message,
        details: log.details
      }))
    }

    return JSON.stringify(diagnostic, null, 2)
  }

  async function copyAgentDiagnostic() {
    const text = buildAgentDiagnosticText()

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
      }
      else {
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.setAttribute('readonly', '')
        textarea.style.position = 'fixed'
        textarea.style.top = '-9999px'
        textarea.style.left = '-9999px'

        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()

        const copied = document.execCommand('copy')
        document.body.removeChild(textarea)

        if (!copied) {
          throw new Error('fallback copy failed')
        }
      }

      setCopiedCommand('Diagnostic agent')

      window.setTimeout(() => {
        setCopiedCommand('')
      }, 1800)
    }
    catch {
      window.prompt('Copie automatique bloquée. Copie le diagnostic ici :', text)
    }
  }


  const configuredInterval = agentConfig?.interval_minutes || agentStatus?.schedule_interval_minutes || 2
  const appliedInterval = agentStatus?.schedule_interval_minutes || configuredInterval

  const compactAgentStatuses = [
    {
      label: 'Connexion',
      value: agentStatus?.online ? 'Connecté' : 'Hors ligne',
      state: agentStatus?.online ? 'ok' : 'error'
    },
    {
      label: 'Traitement',
      value: agentConfig?.pause_processing ? 'En pause' : 'Actif',
      state: agentConfig?.pause_processing ? 'warning' : 'ok'
    },
    {
      label: 'Fréquence config.',
      value: `${configuredInterval} min`,
      state: 'neutral'
    },
    {
      label: 'Fréquence appliquée',
      value: `${appliedInterval} min`,
      state: appliedInterval === configuredInterval ? 'ok' : 'warning'
    },
    {
      label: 'Tâche Windows',
      value: agentStatus?.task?.enabled ? 'Active' : 'Inactive',
      state: agentStatus?.task?.enabled ? 'ok' : 'error'
    },
    {
      label: 'Résultat',
      value: getWindowsTaskResultLabel(agentStatus?.task?.last_task_result),
      state: [0, 267008, 267009].includes(Number(agentStatus?.task?.last_task_result)) ? 'ok' : 'warning'
    }
  ]

  return (
    <div className="agent-ops-page" id="agent-page-top">
<div className="agent-layout-group" id="agent-etat-global">
        <div className="agent-section-heading">
          <span>État global</span>
          <strong>Synthèse immédiate de l’agent Windows.</strong>
        </div>

      <section className={`agent-ops-hero ${lastSuccess ? 'ok' : 'error'}`}>
        <div>
          <span>Exploitation agent</span>
          <h2>{lastSuccess ? 'Agent Windows opérationnel' : 'Dernier traitement en erreur'}</h2>
          <p>{lastMessage}</p>
        </div>

        <strong>{mode}</strong>
      </section>

      <section className="agent-compact-summary">
        {compactAgentStatuses.map(item => (
          <div className={`agent-compact-item ${item.state}`} key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </section>
      </div>

      <div className="agent-layout-group" id="agent-pilotage">
        <div className="agent-section-heading">
          <span>Pilotage</span>
          <strong>Actions et configuration appliquées par l’agent.</strong>
        </div>

      <section className={`agent-pause-card ${agentConfig?.pause_processing ? 'paused' : 'active'}`}>
        <div>
          <span>Traitement des demandes</span>
          <h3>{agentConfig?.pause_processing ? 'Agent en pause' : 'Traitement actif'}</h3>
          <p>
            {agentConfig?.pause_processing
              ? 'Le heartbeat continue, mais les demandes ne sont pas traitées.'
              : 'L’agent peut traiter les demandes validées.'}
          </p>
        </div>

        <button
          type="button"
          className={agentConfig?.pause_processing ? 'resume-agent-button' : 'pause-agent-button'}
          onClick={() => updateAgentPause(!agentConfig?.pause_processing)}
        >
          {agentConfig?.pause_processing ? 'Reprendre le traitement' : 'Mettre en pause'}
        </button>
      </section>

      <section className="panel agent-ops-section">
        <PanelHeader
          title="Configuration connue"
          subtitle="Chemins et éléments importants du serveur Windows."
          action={<button className="secondary" onClick={loadAgentStatus}>Recharger statut</button>}
        />

        <div className="agent-ops-config">
          <div>
            <span>Tâche planifiée</span>
            <strong>EITAS Employee Lifecycle Agent</strong>
          </div>

          <div>
            <span>Fréquence</span>
            <strong>
              Toutes les {agentConfig?.interval_minutes || 2} minute{(agentConfig?.interval_minutes || 2) > 1 ? 's' : ''}
            </strong>

            <div className="agent-frequency-control">
              <select
                value={agentConfig?.interval_minutes || 2}
                onChange={(event) => updateAgentInterval(Number(event.target.value))}
              >
                {(agentConfig?.allowed_intervals || [1, 2, 5, 10, 15, 30]).map(value => (
                  <option key={value} value={value}>
                    Toutes les {value} minute{value > 1 ? 's' : ''}
                  </option>
                ))}
              </select>

              <p>Appliquée automatiquement au prochain passage agent.</p>
            </div>
          </div>

          <div>
            <span>Wrapper logs</span>
            <strong>C:\EnterpriseIT\agent-windows\Run-EitasAgent.ps1</strong>
          </div>

          <div>
            <span>Script agent</span>
            <strong>C:\EnterpriseIT\agent-windows\Invoke-EmployeeLifecycleAgent.ps1</strong>
          </div>

          <div>
            <span>Config locale</span>
            <strong>C:\EnterpriseIT\agent-windows\config.json</strong>
          </div>

          <div>
            <span>Logs</span>
            <strong>C:\EnterpriseIT\agent-windows\logs</strong>
          </div>
        </div>
      </section>
      </div>

      <div className="agent-layout-group" id="agent-supervision">
        <div className="agent-section-heading">
          <span>Supervision technique</span>
          <strong>Heartbeat et état réel de la tâche planifiée Windows.</strong>
        </div>

      <section className={`agent-heartbeat-card ${agentStatus?.online ? 'online' : 'offline'}`}>
        <div>
          <span>Heartbeat agent</span>
          <h3>{agentStatus?.online ? 'Agent connecté' : 'Agent non connecté'}</h3>
          <p>{agentStatus?.message || 'Aucun heartbeat reçu.'}</p>
        </div>

        <div className="agent-heartbeat-details">
          <div>
            <span>Dernier signal</span>
            <strong>{agentStatus?.received_at ? new Date(agentStatus.received_at).toLocaleString('fr-FR') : '-'}</strong>
          </div>

          <div>
            <span>Vu il y a</span>
            <strong>{agentStatus?.seconds_since_seen != null ? `${agentStatus.seconds_since_seen}s` : '-'}</strong>
          </div>

          <div>
            <span>Mode</span>
            <strong>{agentStatus?.mode || '-'}</strong>
          </div>

          <div>
            <span>Script</span>
            <strong>{agentStatus?.script || '-'}</strong>
          </div>

          <div>
            <span>Fréquence appliquée</span>
            <strong>{agentStatus?.schedule_interval_minutes ? `Toutes les ${agentStatus.schedule_interval_minutes} min` : '-'}</strong>
          </div>

          <div>
            <span>Pause traitement</span>
            <strong>{agentStatus?.pause_processing ? 'Oui' : 'Non'}</strong>
          </div>
        </div>
      </section>

      <section className={`agent-task-status-card ${agentStatus?.task?.enabled ? 'enabled' : 'disabled'}`}>
        <div>
          <span>Tâche planifiée Windows</span>
          <h3>{agentStatus?.task?.enabled ? 'Tâche activée' : 'Tâche désactivée ou inconnue'}</h3>
          <p>{agentStatus?.task?.task_name || 'EITAS Employee Lifecycle Agent'}</p>
        </div>

        <div className="agent-task-status-details">
          <div>
            <span>État Windows</span>
            <strong>{getWindowsTaskStateLabel(agentStatus?.task?.state)}</strong>
          </div>

          <div>
            <span>Dernier lancement</span>
            <strong>{agentStatus?.task?.last_run_time ? new Date(agentStatus.task.last_run_time).toLocaleString('fr-FR') : '-'}</strong>
          </div>

          <div>
            <span>Prochain lancement</span>
            <strong>{agentStatus?.task?.next_run_time ? new Date(agentStatus.task.next_run_time).toLocaleString('fr-FR') : '-'}</strong>
          </div>

          <div>
            <span>Résultat Windows</span>
            <strong>{getWindowsTaskResultLabel(agentStatus?.task?.last_task_result)}</strong>
            {agentStatus?.task?.last_task_result != null && (
              <small className="agent-task-result-code">Code Windows : {agentStatus.task.last_task_result}</small>
            )}
          </div>

          <div>
            <span>Répétition</span>
            <strong>{agentStatus?.task?.repetition_interval || '-'}</strong>
          </div>

          <div>
            <span>Activée</span>
            <strong>{agentStatus?.task?.enabled === true ? 'Oui' : agentStatus?.task?.enabled === false ? 'Non' : '-'}</strong>
          </div>
        </div>
      </section>
      </div>

      <div className="agent-layout-group" id="agent-exploitation">
        <div className="agent-section-heading">
          <span>Exploitation</span>
          <strong>Historique et diagnostic de dépannage.</strong>
        </div>

      <section className="panel agent-history-section">
        <PanelHeader
          title="Historique exploitation agent"
          subtitle="Derniers changements de pause, reprise et fréquence."
          action={<button className="secondary" onClick={loadAgentHistory}>Recharger historique</button>}
        />

        <div className="agent-history-list">
          {(agentHistory || []).length === 0 && (
            <div className="agent-history-empty">
              Aucun événement d’exploitation agent récent.
            </div>
          )}

          {(agentHistory || []).map(log => (
            <div className="agent-history-row" key={`${log.timestamp}-${log.action}`}>
              <div>
                <span>{log.timestamp ? new Date(log.timestamp).toLocaleString('fr-FR') : '-'}</span>
                <strong>{log.message || log.action}</strong>
              </div>

              <div className="agent-history-meta">
                <small>{getAgentHistoryActionLabel(log.action)}</small>
                <small>{getAgentHistoryActorLabel(log.actor)}</small>
              </div>

              <div className="agent-history-details">
                {log.details?.interval_minutes && (
                  <span>Toutes les {log.details.interval_minutes} min</span>
                )}

                {log.details?.pause_processing !== undefined && (
                  <span>{log.details.pause_processing ? 'Pause active' : 'Traitement actif'}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel agent-diagnostic-section">
        <PanelHeader
          title="Diagnostic agent"
          subtitle="Bloc complet à copier pour dépannage ou documentation."
          action={
            <button className="secondary" onClick={copyAgentDiagnostic}>
              {copiedCommand === 'Diagnostic agent' ? 'Diagnostic copié' : 'Copier diagnostic'}
            </button>
          }
        />

        <details className="agent-diagnostic-details">
          <summary>Afficher le diagnostic brut</summary>
          <pre className="agent-diagnostic-preview">{buildAgentDiagnosticText()}</pre>
        </details>
      </section>
      </div>

      <div className="agent-layout-group" id="agent-powershell">
        <div className="agent-section-heading">
          <span>Référence PowerShell</span>
          <strong>Commandes utiles à lancer sur SRV-DC01.</strong>
        </div>

      <section className="panel agent-ops-section">
        <PanelHeader
          title="Commandes PowerShell utiles"
          subtitle="À lancer sur SRV-DC01 en PowerShell admin."
        />

        <details className="agent-commands-details">
          <summary>Afficher les commandes PowerShell</summary>

        <div className="agent-command-list">
          {powershellCommands.map(item => (
            <div className="agent-command-card" key={item.title}>
              <div className="agent-command-header">
                <strong>{item.title}</strong>

                <button
                  type="button"
                  className="copy-command-button"
                  onClick={() => copyAgentCommand(item.title, item.code)}
                >
                  {copiedCommand === item.title ? 'Copié' : 'Copier'}
                </button>
              </div>

              <pre>{item.code}</pre>
            </div>
          ))}
        </div>
        </details>
      </section>
      </div>

    </div>
  )
}
