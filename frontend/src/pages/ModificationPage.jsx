import { Field, PreviewRow } from '../components/FormHelpers.jsx'
import PanelHeader from '../components/PanelHeader.jsx'


function splitListValue(value) {
  if (!value) return []

  return String(value)
    .split(/[\n,;]+/)
    .map(item => item.trim())
    .filter(Boolean)
}


export default function ModificationPage({ requests, form, updateForm, createModificationRequest, loadRequestIntoModification, runAdLookup, adLookupRunning }) {
  const onboardingRequests = requests.filter(request => request.type === 'onboarding' && request.status === 'completed')
  const addGroups = splitListValue(form.add_groups)
  const removeGroups = splitListValue(form.remove_groups)

  return (
    <div className="content-grid">
      <section className="panel">
        <PanelHeader
          title="Créer une demande modification"
          subtitle="Changement de service, poste, OU ou groupes AD."
        />

        <form className="form" onSubmit={createModificationRequest}>
          <Field label="Utilisateur existant">
            <select
              value=""
              onChange={event => {
                const selected = requests.find(request => request.id === event.target.value)
                if (selected) {
                  loadRequestIntoModification(selected)
                }
              }}
            >
              <option value="">Sélectionner depuis les onboardings terminés...</option>
              {onboardingRequests.map(request => {
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
              <div className="ad-lookup-inline">
                <input value={form.username} onChange={e => updateForm('username', e.target.value)} />
                <button type="button" className="ad-lookup-button" onClick={runAdLookup} disabled={adLookupRunning}>
                  {adLookupRunning ? 'Recherche...' : 'Rechercher dans AD'}
                </button>
              </div>
            </Field>

            <Field label="Nom affiché">
              <input value={form.display_name} onChange={e => updateForm('display_name', e.target.value)} />
            </Field>

            <Field label="Service actuel">
              <input value={form.current_department} onChange={e => updateForm('current_department', e.target.value)} />
            </Field>

            <Field label="Poste actuel">
              <input value={form.current_job_title} onChange={e => updateForm('current_job_title', e.target.value)} />
            </Field>

            <Field label="Nouveau service">
              <input value={form.new_department} onChange={e => updateForm('new_department', e.target.value)} />
            </Field>

            <Field label="Nouveau poste">
              <input value={form.new_job_title} onChange={e => updateForm('new_job_title', e.target.value)} />
            </Field>

            <Field label="Manager">
              <input value={form.manager} onChange={e => updateForm('manager', e.target.value)} />
            </Field>

            <Field label="Date d’effet">
              <input type="date" value={form.effective_date} onChange={e => updateForm('effective_date', e.target.value)} />
            </Field>
          </div>

          <Field label="OU cible">
            <input value={form.move_to_ou} onChange={e => updateForm('move_to_ou', e.target.value)} placeholder="optionnel" />
          </Field>

          <div className="form-grid">
            <Field label="Compte AD">
              <label className="checkbox-line">
                <input
                  type="checkbox"
                  checked={Boolean(form.reactivate_account)}
                  onChange={e => updateForm('reactivate_account', e.target.checked)}
                />
                <span>Réactiver le compte si l’utilisateur est désactivé</span>
              </label>
            </Field>

            <Field label="Groupes à ajouter">
              <textarea value={form.add_groups} onChange={e => updateForm('add_groups', e.target.value)} />
            </Field>

            <Field label="Groupes à retirer">
              <textarea value={form.remove_groups} onChange={e => updateForm('remove_groups', e.target.value)} />
            </Field>
          </div>

          <Field label="Commentaire">
            <textarea value={form.comment} onChange={e => updateForm('comment', e.target.value)} />
          </Field>

          <div className="panel-footer">
            <button type="submit">Créer demande modification</button>
          </div>
        </form>
      </section>

      <section className="panel preview-panel">
        <PanelHeader
          title="Aperçu modification"
          subtitle="Ce que l’agent Windows simulera après validation."
        />

        <div className="preview-card modification-preview">
          <div className="avatar modification-avatar">M</div>

          <div>
            <strong>{form.display_name || 'Utilisateur'}</strong>
            <span>{form.username || 'login non défini'}</span>
          </div>
        </div>

        <div className="preview-list">
          <PreviewRow label="Service actuel" value={form.current_department || '-'} />
          <PreviewRow label="Nouveau service" value={form.new_department || '-'} />
          <PreviewRow label="Poste actuel" value={form.current_job_title || '-'} />
          <PreviewRow label="Nouveau poste" value={form.new_job_title || '-'} />
          <PreviewRow label="Date effet" value={form.effective_date || '-'} />
          <PreviewRow label="OU cible" value={form.move_to_ou || '-'} />
          <PreviewRow label="Réactivation compte" value={form.reactivate_account ? 'Oui' : 'Non'} />
        </div>

        <div className="groups-box">
          <strong>Groupes à ajouter</strong>
          {addGroups.length === 0 ? (
            <p>Aucun groupe à ajouter.</p>
          ) : (
            <ul>
              {addGroups.map(group => <li key={group}>+ {group}</li>)}
            </ul>
          )}
        </div>

        <div className="groups-box">
          <strong>Groupes à retirer</strong>
          {removeGroups.length === 0 ? (
            <p>Aucun groupe à retirer.</p>
          ) : (
            <ul>
              {removeGroups.map(group => <li key={group}>- {group}</li>)}
            </ul>
          )}
        </div>
      </section>
    </div>
  )
}
