import { useEffect, useMemo, useState } from 'react'
import './App.css'

const STATUS_LABELS = {
  waiting_approval: 'À valider',
  pending: 'En attente agent',
  processing: 'En cours',
  completed: 'Terminée',
  failed: 'Échec',
  rejected: 'Rejetée'
}

const PAGES = {
  overview: {
    title: 'Vue générale',
    subtitle: 'Synthèse des demandes et de l’état de l’automatisation.'
  },
  requests: {
    title: 'Demandes onboarding',
    subtitle: 'Validation, suivi agent Windows et état de traitement.'
  },
  newRequest: {
    title: 'Nouvelle demande',
    subtitle: 'Créer une demande de compte avant validation.'
  },
  templates: {
    title: 'Templates',
    subtitle: 'Services, OU, groupes et postes disponibles.'
  },
  settings: {
    title: 'Paramètres',
    subtitle: 'Connexion API et configuration locale.'
  }
}

function normalizeText(value) {
  return value
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '-')
}

function App() {
  const [page, setPage] = useState('overview')
  const [apiKey, setApiKey] = useState(localStorage.getItem('eitas_api_key') || '')
  const [apiStatus, setApiStatus] = useState('Non testé')
  const [message, setMessage] = useState('')
  const [requests, setRequests] = useState([])
  const [templates, setTemplates] = useState({ departments: {} })
  const [selectedRequest, setSelectedRequest] = useState(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  const [form, setForm] = useState({
    first_name: 'Emma',
    last_name: 'Durand',
    department: '',
    job_title: '',
    manager: 'Admin Lab',
    start_date: '2026-07-20',
    manual_groups: 'GG_VPN_Users'
  })

  const departments = useMemo(() => Object.keys(templates.departments || {}), [templates])

  const roles = useMemo(() => {
    if (!form.department) return []
    return Object.keys(templates.departments?.[form.department]?.roles || {})
  }, [templates, form.department])

  const filteredRequests = useMemo(() => {
    return requests.filter(request => {
      const payload = request.ad_payload || {}
      const text = [
        payload.display_name,
        payload.username,
        payload.email,
        payload.department,
        payload.job_title,
        request.status
      ].filter(Boolean).join(' ').toLowerCase()

      const matchSearch = text.includes(search.toLowerCase())
      const matchStatus = statusFilter === 'all' || request.status === statusFilter

      return matchSearch && matchStatus
    })
  }, [requests, search, statusFilter])

  const stats = {
    total: requests.length,
    waiting: requests.filter(r => r.status === 'waiting_approval').length,
    pending: requests.filter(r => r.status === 'pending').length,
    processing: requests.filter(r => r.status === 'processing').length,
    completed: requests.filter(r => r.status === 'completed').length,
    failed: requests.filter(r => r.status === 'failed' || r.status === 'rejected').length
  }

  const preview = useMemo(() => {
    const first = normalizeText(form.first_name || '')
    const last = normalizeText(form.last_name || '')
    const username = first && last ? `${first[0]}.${last}` : ''
    const email = first && last ? `${first.replaceAll('-', '.')}.${last.replaceAll('-', '.')}@lab.local` : ''

    const departmentData = templates.departments?.[form.department] || {}
    const roleData = departmentData.roles?.[form.job_title] || {}

    const manualGroups = form.manual_groups
      .split('\n')
      .map(group => group.trim())
      .filter(Boolean)

    const groups = Array.from(new Set([
      ...(departmentData.default_groups || []),
      ...(roleData.groups || []),
      ...manualGroups
    ])).sort()

    return {
      displayName: `${form.first_name} ${form.last_name}`.trim(),
      username,
      email,
      ou: departmentData.default_ou || 'Aucune OU sélectionnée',
      groups
    }
  }, [form, templates])

  async function apiFetch(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
        ...(options.headers || {})
      }
    })

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(data?.detail || JSON.stringify(data, null, 2) || 'Erreur API')
    }

    return data
  }

  function saveConfig() {
    localStorage.setItem('eitas_api_key', apiKey)
    setMessage('Clé API enregistrée dans ce navigateur.')
  }

  async function testApi() {
    try {
      const data = await apiFetch('/api/agent/pending')
      setApiStatus(`Connecté · ${data.count} en attente agent`)
      setMessage('Connexion API opérationnelle.')
    } catch (error) {
      setApiStatus('Erreur API')
      setMessage(error.message)
    }
  }

  async function loadRequests() {
    try {
      const data = await apiFetch('/api/requests')
      setRequests(data)
      setMessage('Demandes rechargées.')
    } catch (error) {
      setMessage(error.message)
    }
  }

  async function loadTemplates() {
    try {
      const data = await apiFetch('/api/admin/templates')
      setTemplates(data)

      const departmentNames = Object.keys(data.departments || {})
      const firstDepartment = departmentNames[0] || ''

      setForm(current => {
        const validDepartment = departmentNames.includes(current.department)
          ? current.department
          : firstDepartment

        const roleNames = Object.keys(data.departments?.[validDepartment]?.roles || {})
        const validRole = roleNames.includes(current.job_title)
          ? current.job_title
          : roleNames[0] || ''

        return {
          ...current,
          department: validDepartment,
          job_title: validRole
        }
      })

      setMessage('Templates rechargés.')
    } catch (error) {
      setMessage(error.message)
    }
  }

  async function refreshAll() {
    await loadTemplates()
    await loadRequests()
    await testApi()
  }

  async function createRequest(event) {
    event.preventDefault()

    try {
      const payload = {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        department: form.department,
        job_title: form.job_title,
        manager: form.manager.trim(),
        start_date: form.start_date.trim(),
        manual_groups: form.manual_groups
          .split('\n')
          .map(group => group.trim())
          .filter(Boolean)
      }

      const result = await apiFetch('/api/onboarding/request', {
        method: 'POST',
        body: JSON.stringify(payload)
      })

      setMessage(`Demande créée : ${result.request.id}`)
      setPage('requests')
      await loadRequests()
    } catch (error) {
      setMessage(error.message)
    }
  }

  async function approveRequest(id) {
    try {
      await apiFetch(`/api/admin/requests/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({
          approved_by: 'react-admin',
          comment: 'Validation depuis le portail React'
        })
      })

      setMessage('Demande approuvée.')
      await loadRequests()
    } catch (error) {
      setMessage(error.message)
    }
  }

  async function rejectRequest(id) {
    try {
      await apiFetch(`/api/admin/requests/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({
          approved_by: 'react-admin',
          comment: 'Rejet depuis le portail React'
        })
      })

      setMessage('Demande rejetée.')
      await loadRequests()
    } catch (error) {
      setMessage(error.message)
    }
  }

  function updateForm(field, value) {
    setForm(current => {
      const next = { ...current, [field]: value }

      if (field === 'department') {
        const nextRoles = Object.keys(templates.departments?.[value]?.roles || {})
        next.job_title = nextRoles[0] || ''
      }

      return next
    })
  }

  useEffect(() => {
    if (apiKey) {
      loadTemplates()
      loadRequests()
    }
  }, [])

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">E</div>
          <div>
            <strong>EITAS</strong>
            <span>Admin Console</span>
          </div>
        </div>

        <nav className="nav">
          <button className={page === 'overview' ? 'active' : ''} onClick={() => setPage('overview')}>Vue générale</button>
          <button className={page === 'requests' ? 'active' : ''} onClick={() => setPage('requests')}>Demandes</button>
          <button className={page === 'newRequest' ? 'active' : ''} onClick={() => setPage('newRequest')}>Nouvelle demande</button>
          <button className={page === 'templates' ? 'active' : ''} onClick={() => setPage('templates')}>Templates</button>
          <button className={page === 'settings' ? 'active' : ''} onClick={() => setPage('settings')}>Paramètres</button>
        </nav>

        <div className="sidebar-card">
          <span>Environnement</span>
          <strong>Lab local</strong>
          <small>Agent Windows en simulation</small>
        </div>
      </aside>

      <div className="page">
        <header className="topbar">
          <div>
            <h1>{PAGES[page].title}</h1>
            <p>{PAGES[page].subtitle}</p>
          </div>

          <div className="topbar-actions">
            <span className={`api-badge ${apiStatus.startsWith('Connecté') ? 'online' : ''}`}>
              {apiStatus}
            </span>
            <button onClick={refreshAll}>Actualiser</button>
          </div>
        </header>

        <main className="main">
          {message && <div className="notice">{message}</div>}

          {page === 'overview' && (
            <OverviewPage
              stats={stats}
              requests={requests}
              setPage={setPage}
              setSelectedRequest={setSelectedRequest}
            />
          )}

          {page === 'requests' && (
            <RequestsPage
              requests={filteredRequests}
              search={search}
              setSearch={setSearch}
              statusFilter={statusFilter}
              setStatusFilter={setStatusFilter}
              loadRequests={loadRequests}
              approveRequest={approveRequest}
              rejectRequest={rejectRequest}
              setSelectedRequest={setSelectedRequest}
            />
          )}

          {page === 'newRequest' && (
            <NewRequestPage
              form={form}
              updateForm={updateForm}
              departments={departments}
              roles={roles}
              preview={preview}
              createRequest={createRequest}
            />
          )}

          {page === 'templates' && (
            <TemplatesPage
              departments={departments}
              templates={templates}
              loadTemplates={loadTemplates}
              apiFetch={apiFetch}
              setMessage={setMessage}
            />
          )}

          {page === 'settings' && (
            <SettingsPage
              apiKey={apiKey}
              setApiKey={setApiKey}
              apiStatus={apiStatus}
              saveConfig={saveConfig}
              testApi={testApi}
            />
          )}

          {selectedRequest && (
            <RequestDrawer
              request={selectedRequest}
              onClose={() => setSelectedRequest(null)}
            />
          )}
        </main>
      </div>
    </div>
  )
}

function OverviewPage({ stats, requests, setPage, setSelectedRequest }) {
  const recent = requests.slice(-5).reverse()

  return (
    <>
      <section className="metrics">
        <Metric title="Total demandes" value={stats.total} tone="dark" />
        <Metric title="À valider" value={stats.waiting} tone="orange" />
        <Metric title="En attente agent" value={stats.pending} tone="blue" />
        <Metric title="Terminées" value={stats.completed} tone="green" />
        <Metric title="Échecs / rejets" value={stats.failed} tone="red" />
      </section>

      <div className="dashboard-grid">
        <section className="panel">
          <PanelHeader
            title="Demandes récentes"
            subtitle="Dernières demandes enregistrées."
            action={<button className="secondary" onClick={() => setPage('requests')}>Voir toutes</button>}
          />

          <div className="mini-list">
            {recent.length === 0 && <div className="empty-mini">Aucune demande récente.</div>}

            {recent.map(request => {
              const payload = request.ad_payload || {}

              return (
                <button className="mini-item" key={request.id} onClick={() => setSelectedRequest(request)}>
                  <div>
                    <strong>{payload.display_name || 'Utilisateur inconnu'}</strong>
                    <span>{payload.department || '-'} · {payload.job_title || '-'}</span>
                  </div>
                  <StatusBadge status={request.status} />
                </button>
              )
            })}
          </div>
        </section>

        <section className="panel">
          <PanelHeader
            title="Actions rapides"
            subtitle="Raccourcis de gestion."
          />

          <div className="quick-actions">
            <button onClick={() => setPage('newRequest')}>Créer une demande</button>
            <button className="secondary" onClick={() => setPage('requests')}>Gérer les validations</button>
            <button className="secondary" onClick={() => setPage('templates')}>Consulter les templates</button>
            <button className="secondary" onClick={() => setPage('settings')}>Configurer API</button>
          </div>
        </section>
      </div>
    </>
  )
}

function RequestsPage({
  requests,
  search,
  setSearch,
  statusFilter,
  setStatusFilter,
  loadRequests,
  approveRequest,
  rejectRequest,
  setSelectedRequest
}) {
  return (
    <section className="panel">
      <PanelHeader
        title="Liste des demandes"
        subtitle="Recherche, filtrage et validation."
        action={<button className="secondary" onClick={loadRequests}>Recharger</button>}
      />

      <div className="filters">
        <input
          value={search}
          onChange={event => setSearch(event.target.value)}
          placeholder="Rechercher un utilisateur, login, service..."
        />

        <select value={statusFilter} onChange={event => setStatusFilter(event.target.value)}>
          <option value="all">Tous les statuts</option>
          <option value="waiting_approval">À valider</option>
          <option value="pending">En attente agent</option>
          <option value="processing">En cours</option>
          <option value="completed">Terminée</option>
          <option value="failed">Échec</option>
          <option value="rejected">Rejetée</option>
        </select>
      </div>

      <RequestsTable
        requests={requests}
        approveRequest={approveRequest}
        rejectRequest={rejectRequest}
        setSelectedRequest={setSelectedRequest}
      />
    </section>
  )
}

function RequestsTable({ requests, approveRequest, rejectRequest, setSelectedRequest }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Utilisateur</th>
            <th>Login</th>
            <th>Email</th>
            <th>Service</th>
            <th>Poste</th>
            <th>Statut</th>
            <th>Actions</th>
          </tr>
        </thead>

        <tbody>
          {requests.length === 0 && (
            <tr>
              <td colSpan="7" className="empty">Aucune demande à afficher.</td>
            </tr>
          )}

          {requests.map(request => {
            const payload = request.ad_payload || {}

            return (
              <tr key={request.id}>
                <td>
                  <button className="link-button" onClick={() => setSelectedRequest(request)}>
                    {payload.display_name || 'Utilisateur inconnu'}
                  </button>
                </td>
                <td>{payload.username || '-'}</td>
                <td>{payload.email || '-'}</td>
                <td>{payload.department || '-'}</td>
                <td>{payload.job_title || '-'}</td>
                <td><StatusBadge status={request.status} /></td>
                <td>
                  {request.status === 'waiting_approval' ? (
                    <div className="row-actions">
                      <button className="success" onClick={() => approveRequest(request.id)}>Approuver</button>
                      <button className="danger" onClick={() => rejectRequest(request.id)}>Rejeter</button>
                    </div>
                  ) : (
                    <button className="secondary" onClick={() => setSelectedRequest(request)}>Détail</button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function NewRequestPage({ form, updateForm, departments, roles, preview, createRequest }) {
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

function TemplatesPage({ departments, templates, loadTemplates, apiFetch, setMessage }) {
  const [departmentName, setDepartmentName] = useState('Support')
  const [departmentOu, setDepartmentOu] = useState('OU=Users,OU=Support,DC=lab,DC=local')
  const [departmentGroups, setDepartmentGroups] = useState('GG_Support_Read\nGG_Printer_Support')

  const [roleDepartment, setRoleDepartment] = useState('')
  const [roleName, setRoleName] = useState('Technicien helpdesk')
  const [roleGroups, setRoleGroups] = useState('GG_Support_RW\nGG_RemoteSupport\nGG_M365_Standard')

  useEffect(() => {
    if (!roleDepartment && departments.length > 0) {
      setRoleDepartment(departments[0])
    }

    if (roleDepartment && departments.length > 0 && !departments.includes(roleDepartment)) {
      setRoleDepartment(departments[0])
    }
  }, [departments, roleDepartment])

  function linesToArray(value) {
    return value
      .split('\n')
      .map(line => line.trim())
      .filter(Boolean)
  }

  async function saveDepartment(event) {
    event.preventDefault()

    try {
      const payload = {
        name: departmentName.trim(),
        default_ou: departmentOu.trim(),
        default_groups: linesToArray(departmentGroups)
      }

      await apiFetch('/api/admin/templates/departments', {
        method: 'POST',
        body: JSON.stringify(payload)
      })

      setMessage(`Service ${payload.name} sauvegardé.`)
      await loadTemplates()
    } catch (error) {
      setMessage(error.message)
    }
  }

  async function deleteDepartment() {
    const name = departmentName.trim()

    if (!name) {
      setMessage('Nom du service vide.')
      return
    }

    if (!confirm(`Supprimer le service ${name} et tous ses postes ?`)) {
      return
    }

    try {
      await apiFetch(`/api/admin/templates/departments/${encodeURIComponent(name)}`, {
        method: 'DELETE'
      })

      setMessage(`Service ${name} supprimé.`)
      await loadTemplates()
    } catch (error) {
      setMessage(error.message)
    }
  }

  async function saveRole(event) {
    event.preventDefault()

    if (!roleDepartment) {
      setMessage('Aucun service sélectionné pour le poste.')
      return
    }

    try {
      const payload = {
        name: roleName.trim(),
        groups: linesToArray(roleGroups)
      }

      await apiFetch(`/api/admin/templates/departments/${encodeURIComponent(roleDepartment)}/roles`, {
        method: 'POST',
        body: JSON.stringify(payload)
      })

      setMessage(`Poste ${payload.name} sauvegardé dans ${roleDepartment}.`)
      await loadTemplates()
    } catch (error) {
      setMessage(error.message)
    }
  }

  async function deleteRole() {
    const role = roleName.trim()

    if (!roleDepartment || !role) {
      setMessage('Service ou poste vide.')
      return
    }

    if (!confirm(`Supprimer le poste ${role} dans ${roleDepartment} ?`)) {
      return
    }

    try {
      await apiFetch(`/api/admin/templates/departments/${encodeURIComponent(roleDepartment)}/roles/${encodeURIComponent(role)}`, {
        method: 'DELETE'
      })

      setMessage(`Poste ${role} supprimé.`)
      await loadTemplates()
    } catch (error) {
      setMessage(error.message)
    }
  }

  function loadDepartmentIntoForm(department) {
    const data = templates.departments[department]

    setDepartmentName(department)
    setDepartmentOu(data.default_ou || '')
    setDepartmentGroups((data.default_groups || []).join('\n'))
    setRoleDepartment(department)
  }

  function loadRoleIntoForm(department, role) {
    const data = templates.departments[department]
    const roleData = data.roles?.[role] || {}

    setRoleDepartment(department)
    setRoleName(role)
    setRoleGroups((roleData.groups || []).join('\n'))
  }

  return (
    <div className="templates-page">
      <div className="template-admin-grid">
        <section className="panel">
          <PanelHeader
            title="Créer / modifier un service"
            subtitle="Définis l’OU et les groupes par défaut."
          />

          <form className="form" onSubmit={saveDepartment}>
            <Field label="Nom du service">
              <input value={departmentName} onChange={e => setDepartmentName(e.target.value)} />
            </Field>

            <Field label="OU par défaut">
              <input value={departmentOu} onChange={e => setDepartmentOu(e.target.value)} />
            </Field>

            <Field label="Groupes par défaut">
              <textarea value={departmentGroups} onChange={e => setDepartmentGroups(e.target.value)} />
            </Field>

            <div className="panel-footer split-footer">
              <button type="button" className="danger" onClick={deleteDepartment}>Supprimer service</button>
              <button type="submit">Sauvegarder service</button>
            </div>
          </form>
        </section>

        <section className="panel">
          <PanelHeader
            title="Créer / modifier un poste"
            subtitle="Ajoute les groupes spécifiques au poste."
          />

          <form className="form" onSubmit={saveRole}>
            <Field label="Service">
              <select value={roleDepartment} onChange={e => setRoleDepartment(e.target.value)}>
                {departments.map(department => (
                  <option key={department} value={department}>{department}</option>
                ))}
              </select>
            </Field>

            <Field label="Nom du poste">
              <input value={roleName} onChange={e => setRoleName(e.target.value)} />
            </Field>

            <Field label="Groupes du poste">
              <textarea value={roleGroups} onChange={e => setRoleGroups(e.target.value)} />
            </Field>

            <div className="panel-footer split-footer">
              <button type="button" className="danger" onClick={deleteRole}>Supprimer poste</button>
              <button type="submit">Sauvegarder poste</button>
            </div>
          </form>
        </section>
      </div>

      <section className="panel">
        <PanelHeader
          title="Templates existants"
          subtitle="Clique sur un service ou un poste pour le charger dans le formulaire."
          action={<button className="secondary" onClick={loadTemplates}>Recharger</button>}
        />

        <div className="templates-grid">
          {departments.length === 0 && <div className="empty-mini">Aucun template chargé.</div>}

          {departments.map(department => {
            const data = templates.departments[department]
            const roles = Object.keys(data.roles || {})

            return (
              <div className="template-card" key={department}>
                <div className="template-card-header">
                  <button className="template-title-button" onClick={() => loadDepartmentIntoForm(department)}>
                    {department}
                  </button>
                  <span>{roles.length} poste(s)</span>
                </div>

                <p>{data.default_ou}</p>

                <div className="tag-list">
                  {(data.default_groups || []).map(group => (
                    <span key={group}>{group}</span>
                  ))}
                </div>

                <div className="role-list">
                  {roles.map(role => (
                    <button key={role} onClick={() => loadRoleIntoForm(department, role)}>
                      {role}
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}


function SettingsPage({ apiKey, setApiKey, apiStatus, saveConfig, testApi }) {
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

function RequestDrawer({ request, onClose }) {
  return (
    <div className="drawer-backdrop">
      <aside className="drawer">
        <div className="drawer-header">
          <div>
            <h2>Détail demande</h2>
            <p>{request.id}</p>
          </div>
          <button className="secondary" onClick={onClose}>Fermer</button>
        </div>

        <pre>{JSON.stringify(request, null, 2)}</pre>
      </aside>
    </div>
  )
}

function PanelHeader({ title, subtitle, action }) {
  return (
    <div className="panel-header">
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}

function Metric({ title, value, tone }) {
  return (
    <div className={`metric ${tone}`}>
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  )
}

function StatusBadge({ status }) {
  return (
    <span className={`status ${status}`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  )
}

function PreviewRow({ label, value }) {
  return (
    <div className="preview-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

export default App
