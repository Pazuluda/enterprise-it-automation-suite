import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { TypeBadge, StatusBadge } from './components/Badges.jsx'
import PanelHeader from './components/PanelHeader.jsx'
import { Field, PreviewRow } from './components/FormHelpers.jsx'
import SmartRequestDrawer from './components/SmartRequestDrawer.jsx'
import AuditPage from './components/AuditPage.jsx'
import SettingsPage from './components/SettingsPage.jsx'
import NewRequestPage from './components/NewRequestPage.jsx'
import OffboardingPage from './components/OffboardingPage.jsx'

const STATUS_LABELS = {
  waiting_approval: 'À valider',
  pending: 'En attente agent',
  processing: 'En cours',
  completed: 'Terminée',
  failed: 'Échec',
  rejected: 'Rejetée'
}

const TYPE_LABELS = {
  onboarding: 'Création',
  offboarding: 'Départ',
  modification: 'Modification'
}

const TYPE_FILTERS = [
  { value: 'all', label: 'Tous les types' },
  { value: 'onboarding', label: 'Création' },
  { value: 'offboarding', label: 'Départ / offboarding' },
  { value: 'modification', label: 'Modification' }
]

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
  offboarding: {
    title: 'Offboarding',
    subtitle: 'Préparer le départ d’un collaborateur.'
  },
  modification: {
    title: 'Modification utilisateur',
    subtitle: 'Changer le service, le poste ou les groupes d’un collaborateur.'
  },
  templates: {
    title: 'Templates',
    subtitle: 'Services, OU, groupes et postes disponibles.'
  },
  audit: {
    title: 'Audit logs',
    subtitle: 'Historique des actions et traçabilité du portail.'
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

function splitListValue(value) {
  return String(value || '')
    .split(/[\n,;]/)
    .map(item => item.trim())
    .filter(Boolean)
}

const EITAS_DOMAIN_DN = 'DC=API,DC=LOCAL'
const EITAS_USERS_BASE_OU = `OU=Users,OU=EITAS,${EITAS_DOMAIN_DN}`

function normalizeOuName(value) {
  return String(value || '')
    .trim()
    .replace(/[,\+=<>#;"\\]/g, '')
    .replace(/\s+/g, ' ')
}


function normalizeGroupToken(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .replace(/[^A-Za-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
}

function buildServiceOu(serviceName) {
  const cleanName = normalizeOuName(serviceName)

  if (!cleanName) {
    return ''
  }

  return `OU=${cleanName},${EITAS_USERS_BASE_OU}`
}

function isLegacyOu(value) {
  const text = String(value || '').toLowerCase()

  return (
    text.includes('dc=lab,dc=local') ||
    text.includes('ou=users,ou=') ||
    !text.includes('ou=eitas')
  )
}



function App() {
  const [page, setPage] = useState('overview')
  const [apiKey, setApiKey] = useState(localStorage.getItem('eitas_api_key') || '')
  const [apiStatus, setApiStatus] = useState('Non testé')
  const [message, setMessage] = useState('')
  const [requests, setRequests] = useState([])
  const [templates, setTemplates] = useState({ departments: {} })
  const [auditLogs, setAuditLogs] = useState([])
  const [selectedRequest, setSelectedRequest] = useState(null)
  const [auditFocusId, setAuditFocusId] = useState('')

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')

  const [form, setForm] = useState({
    first_name: 'Emma',
    last_name: 'Durand',
    department: '',
    job_title: '',
    manager: 'Admin Lab',
    start_date: '2026-07-20',
    manual_groups: 'GG_VPN_Users'
  })

  const [offboardingForm, setOffboardingForm] = useState({
    username: '',
    display_name: '',
    department: '',
    manager: 'Admin Lab',
    end_date: '2026-07-31',
    disable_account: true,
    remove_groups: true,
    move_to_ou: 'OU=Disabled Users,OU=EITAS,DC=API,DC=LOCAL',
    convert_mailbox: false,
    forward_to: '',
    comment: 'Fin de contrat'
  })

  const [modificationForm, setModificationForm] = useState({
    username: '',
    display_name: '',
    current_department: '',
    current_job_title: '',
    new_department: '',
    new_job_title: '',
    manager: 'Admin Lab',
    effective_date: '2026-08-01',
    add_groups: 'GG_IT_Admin\nGG_Server_Admin',
    remove_groups: '',
    move_to_ou: '',
    comment: 'Changement utilisateur'
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
      const matchType = typeFilter === 'all' || request.type === typeFilter

      return matchSearch && matchStatus && matchType
    })
  }, [requests, search, statusFilter, typeFilter])

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
    const email = first && last ? `${first.replaceAll('-', '.')}.${last.replaceAll('-', '.')}@api.local` : ''

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

  async function loadAuditLogs() {
    try {
      const data = await apiFetch('/api/audit-logs?limit=100')
      const logs = Array.isArray(data)
        ? data
        : data.logs || data.audit_logs || data.events || []

      setAuditLogs(logs)
      setMessage('Audit logs rechargés.')
    } catch (error) {
      setMessage(error.message)
    }
  }

  async function refreshAll() {
    await loadTemplates()
    await loadRequests()
    await loadAuditLogs()
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

  async function retryRequest(id) {
    try {
      await apiFetch(`/api/admin/requests/${id}/retry`, {
        method: 'POST'
      })

      setMessage('Demande relancée. Elle est repassée en attente agent.')
      await loadRequests()
    } catch (error) {
      setMessage(error.message)
    }
  }

  async function createOffboardingRequest(event) {
    event.preventDefault()

    try {
      const payload = {
        username: offboardingForm.username.trim(),
        display_name: offboardingForm.display_name.trim(),
        department: offboardingForm.department.trim() || null,
        manager: offboardingForm.manager.trim() || null,
        end_date: offboardingForm.end_date.trim(),
        disable_account: offboardingForm.disable_account,
        remove_groups: offboardingForm.remove_groups,
        move_to_ou: offboardingForm.move_to_ou.trim() || null,
        convert_mailbox: offboardingForm.convert_mailbox,
        forward_to: offboardingForm.forward_to.trim() || null,
        comment: offboardingForm.comment.trim() || null
      }

      const result = await apiFetch('/api/offboarding/request', {
        method: 'POST',
        body: JSON.stringify(payload)
      })

      setMessage(`Demande offboarding créée : ${result.request.id}`)
      setPage('requests')
      await loadRequests()
    } catch (error) {
      setMessage(error.message)
    }
  }

  function updateOffboardingForm(field, value) {
    setOffboardingForm(current => ({
      ...current,
      [field]: value
    }))
  }

  function loadRequestIntoOffboarding(request) {
    const payload = request.ad_payload || {}

    setOffboardingForm(current => ({
      ...current,
      username: payload.username || '',
      display_name: payload.display_name || '',
      department: payload.department || '',
      manager: payload.manager || 'Admin Lab'
    }))

    setPage('offboarding')
    setMessage(`Utilisateur chargé pour offboarding : ${payload.display_name || payload.username}`)
  }

  async function createModificationRequest(event) {
    event.preventDefault()

    try {
      const payload = {
        username: modificationForm.username.trim(),
        display_name: modificationForm.display_name.trim(),
        current_department: modificationForm.current_department.trim() || null,
        current_job_title: modificationForm.current_job_title.trim() || null,
        new_department: modificationForm.new_department.trim() || null,
        new_job_title: modificationForm.new_job_title.trim() || null,
        manager: modificationForm.manager.trim() || null,
        effective_date: modificationForm.effective_date.trim(),
        add_groups: splitListValue(modificationForm.add_groups),
        remove_groups: splitListValue(modificationForm.remove_groups),
        reactivate_account: Boolean(modificationForm.reactivate_account),
        move_to_ou: modificationForm.move_to_ou.trim() || null,
        comment: modificationForm.comment.trim() || null
      }

      const result = await apiFetch('/api/modification/request', {
        method: 'POST',
        body: JSON.stringify(payload)
      })

      setMessage(`Demande modification créée : ${result.request.id}`)
      setPage('requests')
      await loadRequests()
    } catch (error) {
      setMessage(error.message)
    }
  }

  function updateModificationForm(field, value) {
    setModificationForm(current => ({
      ...current,
      [field]: value
    }))
  }

  function loadRequestIntoModification(request) {
    const payload = request.ad_payload || {}

    setModificationForm(current => ({
      ...current,
      username: payload.username || '',
      display_name: payload.display_name || '',
      current_department: payload.department || '',
      current_job_title: payload.job_title || '',
      new_department: payload.department || '',
      new_job_title: payload.job_title || '',
      manager: payload.manager || 'Admin Lab',
      move_to_ou: payload.ou || ''
    }))

    setPage('modification')
    setMessage(`Utilisateur chargé pour modification : ${payload.display_name || payload.username}`)
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
      loadAuditLogs()
    }
  }, [])

  function openAuditFromRequest(requestId) {
    const id = String(requestId || '').trim()

    setAuditFocusId(id)

    try {
      window.sessionStorage.setItem('eitasAuditFocusId', id)
    } catch {
      // Non bloquant.
    }

    setSelectedRequest(null)
    setPage('audit')
    setMessage(`Audit logs filtrés pour la demande : ${id}`)
  }

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
          <button className={page === 'offboarding' ? 'active' : ''} onClick={() => setPage('offboarding')}>Offboarding</button>
          <button className={page === 'modification' ? 'active' : ''} onClick={() => setPage('modification')}>Modification</button>
          <button className={page === 'templates' ? 'active' : ''} onClick={() => setPage('templates')}>Templates</button>
          <button className={page === 'audit' ? 'active' : ''} onClick={() => setPage('audit')}>Audit logs</button>
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
              typeFilter={typeFilter}
              setTypeFilter={setTypeFilter}
              loadRequests={loadRequests}
              approveRequest={approveRequest}
              rejectRequest={rejectRequest}
              retryRequest={retryRequest}
              setPage={setPage}
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

          {page === 'offboarding' && (
            <OffboardingPage
              requests={requests}
              form={offboardingForm}
              updateForm={updateOffboardingForm}
              createOffboardingRequest={createOffboardingRequest}
              loadRequestIntoOffboarding={loadRequestIntoOffboarding}
            />
          )}

          {page === 'modification' && (
            <ModificationPage
              requests={requests}
              form={modificationForm}
              updateForm={updateModificationForm}
              createModificationRequest={createModificationRequest}
              loadRequestIntoModification={loadRequestIntoModification}
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

          {page === 'audit' && (
            <AuditPage
              auditLogs={auditLogs}
              loadAuditLogs={loadAuditLogs}
              auditFocusId={auditFocusId}
              setAuditFocusId={setAuditFocusId}
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
            <SmartRequestDrawer
              request={selectedRequest}
              onClose={() => setSelectedRequest(null)}
              setPage={setPage}
              openAuditFromRequest={openAuditFromRequest}
            />
          )}
        </main>
      </div>
    </div>
  )
}


function AgentHealthCard({ requests }) {
  const completedWithAgent = (requests || [])
    .filter(request => request.agent_result || request.processing_by || request.completed_at)
    .sort((a, b) => {
      const dateA = new Date(a.completed_at || a.updated_at || a.created_at || 0).getTime()
      const dateB = new Date(b.completed_at || b.updated_at || b.created_at || 0).getTime()
      return dateB - dateA
    })

  const last = completedWithAgent[0]

  const pendingCount = (requests || []).filter(request => {
    return ['approved', 'pending', 'processing'].includes(request.status)
  }).length

  if (!last) {
    return (
      <section className="agent-health-card warning">
        <div className="agent-health-header">
          <div>
            <span>Agent automatique</span>
            <h3>Aucun passage détecté</h3>
          </div>
          <strong>Inconnu</strong>
        </div>

        <p>Aucune demande traitée par l’agent Windows pour le moment.</p>
      </section>
    )
  }

  const result = last.agent_result || {}
  const details = result.details || {}
  const success = result.success !== false
  const mode = details.mode || '-'
  const agent = details.agent || last.processing_by || '-'
  const completedAt = last.completed_at || last.updated_at || last.created_at
  const requestType = details.request_type || last.type || last.request_type || '-'

  return (
    <section className={`agent-health-card ${success ? 'ok' : 'error'}`}>
      <div className="agent-health-header">
        <div>
          <span>Agent automatique</span>
          <h3>{success ? 'Dernier passage OK' : 'Dernier passage en erreur'}</h3>
        </div>

        <strong>{mode}</strong>
      </div>

      <div className="agent-health-grid">
        <div>
          <span>Dernier agent</span>
          <strong>{agent}</strong>
        </div>

        <div>
          <span>Dernier passage</span>
          <strong>{completedAt ? new Date(completedAt).toLocaleString('fr-FR') : '-'}</strong>
        </div>

        <div>
          <span>Type traité</span>
          <strong>{requestType}</strong>
        </div>

        <div>
          <span>En attente agent</span>
          <strong>{pendingCount}</strong>
        </div>
      </div>

      <p>{result.message || 'Dernier résultat agent récupéré depuis les demandes.'}</p>
    </section>
  )
}


function OverviewPage({ requests, setPage }) {
  const safeRequests = Array.isArray(requests) ? requests : []

  const waitingApproval = safeRequests.filter(request => request.status === 'waiting_approval').length
  const pendingAgent = safeRequests.filter(request => request.status === 'pending' || request.status === 'processing').length
  const completed = safeRequests.filter(request => request.status === 'completed').length
  const issues = safeRequests.filter(request => request.status === 'failed' || request.status === 'rejected').length

  const recentRequests = [...safeRequests].slice(-5).reverse()

  return (
    <>
      <div className="stats-grid">
        <div className="stat-card total">
          <span>Total demandes</span>
          <strong>{safeRequests.length}</strong>
        </div>

        <div className="stat-card warning">
          <span>À valider</span>
          <strong>{waitingApproval}</strong>
        </div>

        <div className="stat-card pending">
          <span>En attente agent</span>
          <strong>{pendingAgent}</strong>
        </div>

        <div className="stat-card success">
          <span>Terminées</span>
          <strong>{completed}</strong>
        </div>

        <div className="stat-card danger">
          <span>Échecs / rejets</span>
          <strong>{issues}</strong>
        </div>
      </div>

      <div className="content-grid">
        <section className="panel">
                <AgentHealthCard requests={requests} />

<div className="panel-header">
            <div>
              <h2>Demandes récentes</h2>
              <p>Dernières demandes enregistrées.</p>
            </div>

            <button onClick={() => setPage('requests')}>Voir toutes</button>
          </div>

          <div className="recent-list">
            {recentRequests.length === 0 ? (
              <p className="empty">Aucune demande récente.</p>
            ) : (
              recentRequests.map(request => {
                const payload = request.ad_payload || request.payload || {}
                const type = request.type || 'onboarding'

                return (
                  <div className="recent-item" key={request.id}>
                    <div>
                      <strong>{payload.display_name || payload.username || 'Utilisateur inconnu'}</strong>
                      <span>{TYPE_LABELS[type] || type} · {payload.department || '-'} · {payload.job_title || '-'}</span>
                    </div>

                    <StatusBadge status={request.status} />
                  </div>
                )
              })
            )}
          </div>
        </section>

        <section className="panel quick-actions">
          <div className="panel-header">
            <div>
              <h2>Actions rapides</h2>
              <p>Raccourcis de gestion.</p>
            </div>
          </div>

          <div className="quick-action-list">
            <button onClick={() => setPage('newRequest')}>Créer une demande</button>
            <button onClick={() => setPage('requests')}>Gérer les validations</button>
            <button onClick={() => setPage('templates')}>Consulter les templates</button>
            <button onClick={() => setPage('settings')}>Configurer API</button>
          </div>
        </section>
      </div>

      <DashboardInsights requests={safeRequests} setPage={setPage} />
    </>
  )
}

function RequestsPage({
  requests,
  search,
  setSearch,
  statusFilter,
  setStatusFilter,
  typeFilter,
  setTypeFilter,
  loadRequests,
  approveRequest,
  rejectRequest,
  retryRequest,
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

        <select value={typeFilter} onChange={event => setTypeFilter(event.target.value)}>
          {TYPE_FILTERS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>

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
        retryRequest={retryRequest}
        setSelectedRequest={setSelectedRequest}
      />
    </section>
  )
}

function RequestsTable({ requests, approveRequest, rejectRequest, retryRequest, setSelectedRequest }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Utilisateur</th>
            <th>Type</th>
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
              <td colSpan="8" className="empty">Aucune demande à afficher.</td>
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
                <td><TypeBadge type={request.type} /></td>
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
                  ) : request.status === 'failed' || request.status === 'rejected' ? (
                    <div className="row-actions">
                      <button onClick={() => retryRequest(request.id)}>Relancer</button>
                      <button className="secondary" onClick={() => setSelectedRequest(request)}>Détail</button>
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

function ModificationPage({ requests, form, updateForm, createModificationRequest, loadRequestIntoModification }) {
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
              <input value={form.username} onChange={e => updateForm('username', e.target.value)} />
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


function TemplatesPage({ departments, templates, loadTemplates, apiFetch, setMessage }) {
  const [departmentName, setDepartmentName] = useState('Support')
  const [departmentOu, setDepartmentOu] = useState('OU=Support,OU=Users,OU=EITAS,DC=API,DC=LOCAL')
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
        default_ou: buildServiceOu(departmentName.trim()) || departmentOu.trim(),
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

  
  function autoFillServiceOu() {
    const generatedOu = buildServiceOu(departmentName)

    if (!generatedOu) {
      setMessage('Nom de service manquant pour générer l’OU.')
      return
    }

    setDepartmentOu(generatedOu)
    setMessage(`OU générée automatiquement : ${generatedOu}`)
  }


  function getRoleGroupSuggestions() {
    const serviceToken = normalizeGroupToken(roleDepartment)
    const departmentDefaults = templates?.departments?.[roleDepartment]?.default_groups || []

    const generated = serviceToken
      ? [
          `GG_${serviceToken}_Read`,
          `GG_${serviceToken}_RW`,
          `GG_${serviceToken}_Admin`,
          `GG_Printer_${serviceToken}`
        ]
      : []

    const common = [
      'GG_M365_Standard',
      'GG_VPN_Users',
      'GG_RemoteSupport',
      'GG_IT_Admins',
      'GG_Server_Admins'
    ]

    return Array.from(new Set([
      ...departmentDefaults,
      ...generated,
      ...common
    ].filter(Boolean)))
  }

  function addRoleGroup(group) {
    const cleanGroup = String(group || '').trim()

    if (!cleanGroup) {
      return
    }

    const currentGroups = linesToArray(roleGroups)

    if (currentGroups.includes(cleanGroup)) {
      setMessage(`Le groupe ${cleanGroup} est déjà présent.`)
      return
    }

    setRoleGroups([...currentGroups, cleanGroup].join('\n'))
    setMessage(`Groupe ajouté : ${cleanGroup}`)
  }

  function removeRoleGroup(group) {
    const cleanGroup = String(group || '').trim()
    const nextGroups = linesToArray(roleGroups).filter(item => item !== cleanGroup)

    setRoleGroups(nextGroups.join('\n'))
    setMessage(`Groupe retiré : ${cleanGroup}`)
  }

  function clearRoleGroups() {
    setRoleGroups('')
    setMessage('Groupes du poste vidés.')
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

              <div className="auto-ou-tools">
                <button
                  type="button"
                  className="secondary-small-button"
                  onClick={autoFillServiceOu}
                >
                  Regénérer l’OU
                </button>
                <span className="auto-ou-hint">
                  Générée depuis le nom du service.
                </span>
              </div>

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
              <div className="group-picker">
                <div className="group-picker-header">
                  <div>
                    <strong>Groupes sélectionnés</strong>
                    <span> Clique sur un groupe pour le retirer.</span>
                  </div>

                  <button type="button" className="secondary-small-button" onClick={clearRoleGroups}>
                    Vider
                  </button>
                </div>

                <div className="selected-group-list">
                  {linesToArray(roleGroups).length === 0 && (
                    <span className="empty-mini">Aucun groupe sélectionné.</span>
                  )}

                  {linesToArray(roleGroups).map(group => (
                    <button
                      key={group}
                      type="button"
                      className="selected-group-chip"
                      onClick={() => removeRoleGroup(group)}
                      title="Cliquer pour retirer"
                    >
                      {group}
                      <span>×</span>
                    </button>
                  ))}
                </div>

                <div className="group-picker-header">
                  <div>
                    <strong>Ajouter rapidement</strong>
                    <span> Groupes proposés selon le service.</span>
                  </div>
                </div>

                <div className="group-suggestion-grid">
                  {getRoleGroupSuggestions().map(group => (
                    <button
                      key={group}
                      type="button"
                      className="group-suggestion-button"
                      onClick={() => addRoleGroup(group)}
                    >
                      + {group}
                    </button>
                  ))}
                </div>

                <details className="advanced-groups-editor">
                  <summary>Options avancées : édition texte / copier-coller</summary>

                  <textarea
                    value={roleGroups}
                    onChange={e => setRoleGroups(e.target.value)}
                    placeholder={'Un groupe par ligne, exemple :\nGG_Marchand_Read\nGG_Marchand_RW'}
                  />
                </details>
              </div>
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



function formatDate(value) {
  if (!value) return '-'

  try {
    return new Date(value).toLocaleString('fr-FR')
  } catch {
    return value
  }
}


export default App

function DashboardInsights({ requests, setPage }) {
  const safeRequests = Array.isArray(requests) ? requests : []

  const byType = {
    onboarding: safeRequests.filter(request => (request.type || 'onboarding') === 'onboarding').length,
    offboarding: safeRequests.filter(request => request.type === 'offboarding').length,
    modification: safeRequests.filter(request => request.type === 'modification').length
  }

  const byStatus = {
    waiting_approval: safeRequests.filter(request => request.status === 'waiting_approval').length,
    pending: safeRequests.filter(request => request.status === 'pending').length,
    processing: safeRequests.filter(request => request.status === 'processing').length,
    completed: safeRequests.filter(request => request.status === 'completed').length,
    failed: safeRequests.filter(request => request.status === 'failed').length,
    rejected: safeRequests.filter(request => request.status === 'rejected').length
  }

  const total = safeRequests.length || 1
  const completedRate = Math.round((byStatus.completed / total) * 100)

  const latestIssues = safeRequests
    .filter(request => request.status === 'failed' || request.status === 'rejected')
    .slice(-5)
    .reverse()

  const latestAgentActions = safeRequests
    .filter(request => request.processing_by || request.agent_result)
    .slice(-5)
    .reverse()

  const pendingWork = safeRequests.filter(request => {
    return request.status === 'waiting_approval' || request.status === 'pending' || request.status === 'processing'
  })

  return (
    <div className="dashboard-plus">
      <section className="panel">
        <PanelHeader
          title="Répartition par type"
          subtitle="Vue rapide des workflows utilisés."
        />

        <div className="dashboard-bars">
          <DashboardBar label="Créations" value={byType.onboarding} total={total} type="onboarding" />
          <DashboardBar label="Départs" value={byType.offboarding} total={total} type="offboarding" />
          <DashboardBar label="Modifications" value={byType.modification} total={total} type="modification" />
        </div>
      </section>

      <section className="panel">
        <PanelHeader
          title="Santé du traitement"
          subtitle="État global des demandes."
        />

        <div className="health-card">
          <div>
            <strong>{completedRate}%</strong>
            <span>Demandes terminées</span>
          </div>

          <div className="health-meter">
            <span style={{ width: `${completedRate}%` }} />
          </div>
        </div>

        <div className="mini-status-grid">
          <MiniStatus label="À valider" value={byStatus.waiting_approval} />
          <MiniStatus label="En attente agent" value={byStatus.pending} />
          <MiniStatus label="En cours" value={byStatus.processing} />
          <MiniStatus label="Terminées" value={byStatus.completed} />
          <MiniStatus label="Échecs" value={byStatus.failed} />
          <MiniStatus label="Rejets" value={byStatus.rejected} />
        </div>
      </section>

      <section className="panel">
        <PanelHeader
          title="File de travail"
          subtitle="Ce qui demande encore une action."
        />

        {pendingWork.length === 0 ? (
          <div className="empty-dashboard-state">
            <strong>Aucune action en attente</strong>
            <span>Tout est traité pour le moment.</span>
          </div>
        ) : (
          <div className="compact-list">
            {pendingWork.slice(0, 6).map(request => {
              const payload = request.ad_payload || request.payload || {}

              return (
                <button key={request.id} className="compact-row" onClick={() => setPage('requests')}>
                  <span>
                    <strong>{payload.display_name || payload.username || 'Utilisateur'}</strong>
                    <small>{TYPE_LABELS[request.type || 'onboarding'] || request.type || 'Création'}</small>
                  </span>
                  <StatusBadge status={request.status} />
                </button>
              )
            })}
          </div>
        )}
      </section>

      <section className="panel">
        <PanelHeader
          title="Derniers problèmes"
          subtitle="Demandes rejetées ou en erreur."
        />

        {latestIssues.length === 0 ? (
          <div className="empty-dashboard-state">
            <strong>Aucun rejet ou échec récent</strong>
            <span>Le flux est propre.</span>
          </div>
        ) : (
          <div className="compact-list">
            {latestIssues.map(request => {
              const payload = request.ad_payload || request.payload || {}

              return (
                <button key={request.id} className="compact-row issue-row" onClick={() => setPage('requests')}>
                  <span>
                    <strong>{payload.display_name || payload.username || 'Utilisateur'}</strong>
                    <small>{request.agent_result?.message || request.rejection_comment || 'À consulter'}</small>
                  </span>
                  <StatusBadge status={request.status} />
                </button>
              )
            })}
          </div>
        )}
      </section>

      <section className="panel wide-panel">
        <PanelHeader
          title="Dernières actions agent"
          subtitle="Traitements récents côté Windows Server."
        />

        {latestAgentActions.length === 0 ? (
          <div className="empty-dashboard-state">
            <strong>Aucune action agent</strong>
            <span>L’agent n’a pas encore traité de demande récente.</span>
          </div>
        ) : (
          <div className="agent-action-list">
            {latestAgentActions.map(request => {
              const payload = request.ad_payload || request.payload || {}
              const result = request.agent_result || {}

              return (
                <div className="agent-action-row" key={request.id}>
                  <div>
                    <strong>{payload.display_name || payload.username || 'Utilisateur'}</strong>
                    <span>{TYPE_LABELS[request.type || 'onboarding'] || request.type || 'Création'} · {request.processing_by || result.details?.agent || 'agent inconnu'}</span>
                  </div>

                  <div>
                    <StatusBadge status={request.status} />
                    <small>{result.message || 'Traitement enregistré'}</small>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}

function DashboardBar({ label, value, total, type }) {
  const percent = total > 0 ? Math.round((value / total) * 100) : 0

  return (
    <div className="dashboard-bar">
      <div className="dashboard-bar-head">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>

      <div className={`dashboard-bar-track ${type}`}>
        <span style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

function MiniStatus({ label, value }) {
  return (
    <div className="mini-status">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  )
}


