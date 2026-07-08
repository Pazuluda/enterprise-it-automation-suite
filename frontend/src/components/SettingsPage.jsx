import PanelHeader from './PanelHeader.jsx'
import { Field } from './FormHelpers.jsx'

export default function SettingsPage({ apiKey, setApiKey, apiStatus, saveConfig, testApi }) {
  return (
    <section className="panel settings-panel">
      <PanelHeader
        title="Connexion API"
        subtitle="La clé API est sauvegardée uniquement dans le navigateur."
      />

      <div className="settings-content">
        <Field label="Clé API">
          <input
            type="password"
            value={apiKey}
            onChange={event => setApiKey(event.target.value)}
            placeholder="Colle la clé API ici"
          />
        </Field>

        <div className="settings-actions">
          <button onClick={saveConfig}>Enregistrer</button>
          <button className="secondary" onClick={testApi}>Tester la connexion</button>
        </div>

        <div className="settings-state">
          <span>État actuel</span>
          <strong>{apiStatus}</strong>
        </div>
      </div>
    </section>
  )
}
