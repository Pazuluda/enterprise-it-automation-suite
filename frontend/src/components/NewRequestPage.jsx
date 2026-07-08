import PanelHeader from './PanelHeader.jsx'
import { Field, PreviewRow } from './FormHelpers.jsx'

export default function NewRequestPage({ form, updateForm, departments, roles, preview, createRequest }) {
  return (
    <div className="content-grid">
      <section className="panel">
        <PanelHeader
          title="Formulaire onboarding"
          subtitle="Les données générées sont visibles dans l’aperçu."
        />

        <form className="form" onSubmit={createRequest}>
          <div className="form-grid">
            <Field label="Prénom">
              <input value={form.first_name} onChange={e => updateForm('first_name', e.target.value)} />
            </Field>

            <Field label="Nom">
              <input value={form.last_name} onChange={e => updateForm('last_name', e.target.value)} />
            </Field>

            <Field label="Service">
              <select value={form.department} onChange={e => updateForm('department', e.target.value)}>
                {departments.map(department => (
                  <option key={department} value={department}>{department}</option>
                ))}
              </select>
            </Field>

            <Field label="Poste">
              <select value={form.job_title} onChange={e => updateForm('job_title', e.target.value)}>
                {roles.map(role => (
                  <option key={role} value={role}>{role}</option>
                ))}
              </select>
            </Field>

            <Field label="Manager">
              <input value={form.manager} onChange={e => updateForm('manager', e.target.value)} />
            </Field>

            <Field label="Date d’arrivée">
              <input type="date" value={form.start_date} onChange={e => updateForm('start_date', e.target.value)} />
            </Field>
          </div>

          <Field label="Groupes manuels">
            <textarea value={form.manual_groups} onChange={e => updateForm('manual_groups', e.target.value)} />
          </Field>

          <div className="panel-footer">
            <button type="submit">Créer la demande</button>
          </div>
        </form>
      </section>

      <section className="panel preview-panel">
        <PanelHeader
          title="Aperçu du compte"
          subtitle="Résumé avant envoi en validation."
        />

        <div className="preview-card">
          <div className="avatar">{preview.displayName ? preview.displayName[0] : '?'}</div>

          <div>
            <strong>{preview.displayName || 'Utilisateur'}</strong>
            <span>{preview.email || 'email non généré'}</span>
          </div>
        </div>

        <div className="preview-list">
          <PreviewRow label="Login" value={preview.username || '-'} />
          <PreviewRow label="OU cible" value={preview.ou} />
          <PreviewRow label="Service" value={form.department || '-'} />
          <PreviewRow label="Poste" value={form.job_title || '-'} />
        </div>

        <div className="groups-box">
          <strong>Groupes prévus</strong>

          {preview.groups.length === 0 ? (
            <p>Aucun groupe calculé.</p>
          ) : (
            <ul>
              {preview.groups.map(group => (
                <li key={group}>{group}</li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  )
}
