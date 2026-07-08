import PanelHeader from './PanelHeader.jsx'
import { Field, PreviewRow } from './FormHelpers.jsx'

export default function OffboardingPage({ requests, form, updateForm, createOffboardingRequest, loadRequestIntoOffboarding }) {
  const onboardingUsers = requests
    .filter(request => request.type === 'onboarding' && request.status === 'completed')
    .map(request => request.ad_payload || {})
    .filter(payload => payload.username)

  return (
    <div className="content-grid">
      <section className="panel">
        <PanelHeader
          title="Créer une demande offboarding"
          subtitle="Prépare la désactivation et le nettoyage d’un compte utilisateur."
        />

        <form className="form" onSubmit={createOffboardingRequest}>
          <Field label="Utilisateur existant">
            <select
              value=""
              onChange={event => {
                const selected = requests.find(request => request.id === event.target.value)
                if (selected) {
                  loadRequestIntoOffboarding(selected)
                }
              }}
            >
              <option value="">Sélectionner depuis les onboardings terminés...</option>
              {requests
                .filter(request => request.type === 'onboarding' && request.status === 'completed')
                .map(request => {
                  const payload = request.ad_payload || {}
                  return (
                    <option key={request.id} value={request.id}>
                      {payload.display_name} · {payload.username}
                    </option>
                  )
                })}
            </select>
          </Field>

          <div className="form-grid">
            <Field label="Login">
              <input value={form.username} onChange={e => updateForm('username', e.target.value)} />
            </Field>

            <Field label="Nom affiché">
              <input value={form.display_name} onChange={e => updateForm('display_name', e.target.value)} />
            </Field>

            <Field label="Service">
              <input value={form.department} onChange={e => updateForm('department', e.target.value)} />
            </Field>

            <Field label="Manager">
              <input value={form.manager} onChange={e => updateForm('manager', e.target.value)} />
            </Field>

            <Field label="Date de départ">
              <input type="date" value={form.end_date} onChange={e => updateForm('end_date', e.target.value)} />
            </Field>

            <Field label="OU cible">
              <input value={form.move_to_ou} onChange={e => updateForm('move_to_ou', e.target.value)} />
            </Field>
          </div>

          <div className="option-grid">
            <label className="check-option">
              <input
                type="checkbox"
                checked={form.disable_account}
                onChange={e => updateForm('disable_account', e.target.checked)}
              />
              <span>Désactiver le compte</span>
            </label>

            <label className="check-option">
              <input
                type="checkbox"
                checked={form.remove_groups}
                onChange={e => updateForm('remove_groups', e.target.checked)}
              />
              <span>Retirer les groupes</span>
            </label>

            <label className="check-option">
              <input
                type="checkbox"
                checked={form.convert_mailbox}
                onChange={e => updateForm('convert_mailbox', e.target.checked)}
              />
              <span>Convertir la mailbox</span>
            </label>
          </div>

          <Field label="Redirection mail vers">
            <input value={form.forward_to} onChange={e => updateForm('forward_to', e.target.value)} placeholder="optionnel" />
          </Field>

          <Field label="Commentaire">
            <textarea value={form.comment} onChange={e => updateForm('comment', e.target.value)} />
          </Field>

          <div className="panel-footer">
            <button type="submit">Créer demande offboarding</button>
          </div>
        </form>
      </section>

      <section className="panel preview-panel">
        <PanelHeader
          title="Aperçu offboarding"
          subtitle="Actions prévues pour l’agent Windows."
        />

        <div className="preview-card offboarding-preview">
          <div className="avatar danger-avatar">D</div>

          <div>
            <strong>{form.display_name || 'Utilisateur'}</strong>
            <span>{form.username || 'login non défini'}</span>
          </div>
        </div>

        <div className="preview-list">
          <PreviewRow label="Service" value={form.department || '-'} />
          <PreviewRow label="Fin prévue" value={form.end_date || '-'} />
          <PreviewRow label="OU cible" value={form.move_to_ou || '-'} />
          <PreviewRow label="Manager" value={form.manager || '-'} />
        </div>

        <div className="groups-box">
          <strong>Actions prévues</strong>
          <ul>
            <li>{form.disable_account ? 'Désactivation du compte' : 'Compte non désactivé'}</li>
            <li>{form.remove_groups ? 'Retrait des groupes' : 'Groupes conservés'}</li>
            <li>{form.convert_mailbox ? 'Conversion mailbox demandée' : 'Pas de conversion mailbox'}</li>
            <li>{form.forward_to ? `Redirection vers ${form.forward_to}` : 'Pas de redirection mail'}</li>
          </ul>
        </div>

        <div className="groups-box">
          <strong>Utilisateurs disponibles</strong>
          {onboardingUsers.length === 0 ? (
            <p>Aucun onboarding terminé chargé.</p>
          ) : (
            <ul>
              {onboardingUsers.slice(0, 8).map(user => (
                <li key={user.username}>{user.display_name} · {user.username}</li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  )
}
