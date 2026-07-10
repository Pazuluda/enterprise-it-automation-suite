export default function AgentModePage({ agentModeControl, loadAgentMode, updateAgentMode }) {
  const mode = agentModeControl.mode || 'Simulation'
  const isProduction = mode === 'Production'

  return (
    <div className="agent-mode-page">
      <section className={`agent-mode-hero ${isProduction ? 'production' : 'simulation'}`}>
        <div>
          <span>Mode actuel</span>
          <strong>{mode}</strong>
          <p>
            {isProduction
              ? 'Les prochaines demandes traitées par l’agent modifieront réellement Active Directory.'
              : 'Les prochaines demandes seront simulées : aucun changement réel dans Active Directory.'}
          </p>
        </div>

        <button type="button" onClick={() => loadAgentMode()} disabled={agentModeControl.loading}>
          Actualiser
        </button>
      </section>

      {agentModeControl.error && (
        <div className="agent-mode-error">
          {agentModeControl.error}
        </div>
      )}

      <section className="agent-mode-grid">
        <article className={`agent-mode-card ${mode === 'Simulation' ? 'selected' : ''}`}>
          <div>
            <span>Mode sécurisé</span>
            <strong>Simulation</strong>
            <p>Teste les workflows sans modifier les comptes AD.</p>
          </div>

          <button
            type="button"
            onClick={() => updateAgentMode('Simulation')}
            disabled={agentModeControl.loading || mode === 'Simulation'}
          >
            Activer Simulation
          </button>
        </article>

        <article className={`agent-mode-card danger ${mode === 'Production' ? 'selected' : ''}`}>
          <div>
            <span>Mode réel</span>
            <strong>Production</strong>
            <p>Applique réellement les créations, modifications, réactivations et offboardings AD.</p>
          </div>

          <button
            type="button"
            onClick={() => updateAgentMode('Production')}
            disabled={agentModeControl.loading || mode === 'Production'}
          >
            Activer Production
          </button>
        </article>
      </section>

      <section className="agent-mode-note">
        <strong>Important</strong>
        <p>
          Le changement est pris en compte au prochain passage de l’agent Windows. Le worker recherche AD live reste en lookup-only et ne traite pas les demandes classiques.
        </p>
      </section>
    </div>
  )
}
