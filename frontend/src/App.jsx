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
import AgentModePage from './pages/AgentModePage.jsx'
import AdChecksPage from './pages/AdChecksPage.jsx'
import ModificationPage from './pages/ModificationPage.jsx'

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
  csvImport: {
    title: 'Import CSV',
    subtitle: 'Créer plusieurs demandes onboarding depuis un fichier CSV.'
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
  agentOps: {

    title: 'Exploitation agent',

    subtitle: 'Supervision et commandes utiles côté Windows Server.'

  },

  adChecks: {
    title: 'Contrôles AD',
    subtitle: 'Historique des contrôles Active Directory lancés depuis le portail.'
  },

  agentMode: {
    title: 'Mode agent',
    subtitle: 'Choisir si l’agent Windows travaille en simulation ou en production.'
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





function CsvImportPage({ apiFetch, loadRequests, setMessage, templates, requests = [] }) {
  const [csvText, setCsvText] = useState('')
  const [headers, setHeaders] = useState([])
  const [csvRecords, setCsvRecords] = useState([])
  const [columnMapping, setColumnMapping] = useState({})
  const [rows, setRows] = useState([])
  const [importing, setImporting] = useState(false)
  const [approvingImported, setApprovingImported] = useState(false)
  const [report, setReport] = useState(null)
  const [parseError, setParseError] = useState('')

  function buildCsvDuplicateKey(row) {
    return [
      row.first_name,
      row.last_name,
      row.department
    ]
      .map(value => normalizeKey(value))
      .filter(Boolean)
      .join('|')
  }

  function buildRequestDuplicateKey(request) {
    const firstName = request.first_name || request.employee?.first_name || request.payload?.first_name || ''
    const lastName = request.last_name || request.employee?.last_name || request.payload?.last_name || ''

    const displayName = request.display_name
      || request.full_name
      || request.name
      || request.employee?.display_name
      || request.payload?.display_name
      || [firstName, lastName].filter(Boolean).join(' ')

    const parts = String(displayName || '')
      .trim()
      .split(/\s+/)

    const guessedFirstName = firstName || parts[0] || ''
    const guessedLastName = lastName || parts.slice(1).join(' ') || ''

    const department = request.department
      || request.service
      || request.employee?.department
      || request.payload?.department
      || ''

    return [
      guessedFirstName,
      guessedLastName,
      department
    ]
      .map(value => normalizeKey(value))
      .filter(Boolean)
      .join('|')
  }

  const existingRequestKeys = new Set(
    requests
      .map(buildRequestDuplicateKey)
      .filter(Boolean)
  )

  const csvKeyCounts = rows.reduce((acc, row) => {
    const key = buildCsvDuplicateKey(row)

    if (key) {
      acc[key] = (acc[key] || 0) + 1
    }

    return acc
  }, {})

  const rowsWithDuplicateState = rows.map(row => {
    const key = buildCsvDuplicateKey(row)
    const duplicateErrors = []

    if (key && csvKeyCounts[key] > 1) {
      duplicateErrors.push('Doublon dans le CSV')
    }

    if (key && existingRequestKeys.has(key)) {
      duplicateErrors.push('Déjà présent dans les demandes')
    }

    return {
      ...row,
      duplicateErrors,
      allErrors: [
        ...(row.errors || []),
        ...duplicateErrors
      ]
    }
  })

  const validRows = rowsWithDuplicateState.filter(row => row.allErrors.length === 0)
  const invalidRows = rowsWithDuplicateState.filter(row => row.allErrors.length > 0)

  const departmentTemplates = templates?.departments || {}

  const departmentOptions = Object.keys(departmentTemplates)
    .sort((a, b) => a.localeCompare(b, 'fr'))

  function findDepartmentTemplate(departmentName) {
    const wanted = normalizeKey(departmentName)

    if (!wanted) return null

    const exact = departmentTemplates[departmentName]
    if (exact) return exact

    const matchingName = Object.keys(departmentTemplates)
      .find(name => normalizeKey(name) === wanted)

    return matchingName ? departmentTemplates[matchingName] : null
  }

  function normalizeGroups(value) {
    if (Array.isArray(value)) {
      return value.map(group => String(group || '').trim()).filter(Boolean)
    }

    return String(value || '')
      .split(/[,;|\n]/)
      .map(group => group.trim())
      .filter(Boolean)
  }

  function getGroupFields(source) {
    if (!source || typeof source !== 'object') return []

    return [
      source.default_groups,
      source.groups,
      source.ad_groups,
      source.manual_groups,
      source.security_groups
    ].flatMap(normalizeGroups)
  }

  function getDepartmentJobs(departmentName) {
    const department = findDepartmentTemplate(departmentName)

    if (!department) return []

    const sources = [
      department.jobs,
      department.job_titles,
      department.positions,
      department.postes,
      department.roles
    ].filter(Boolean)

    const jobs = []

    for (const source of sources) {
      if (Array.isArray(source)) {
        for (const item of source) {
          if (typeof item === 'string') {
            jobs.push(item)
          } else if (item && typeof item === 'object') {
            jobs.push(item.name || item.title || item.job_title || item.poste || item.position || '')
          }
        }
      } else if (source && typeof source === 'object') {
        jobs.push(...Object.keys(source))
      }
    }

    return Array.from(new Set(jobs.map(job => String(job || '').trim()).filter(Boolean)))
      .sort((a, b) => a.localeCompare(b, 'fr'))
  }

  function findJobTemplate(departmentName, jobTitle) {
    const department = findDepartmentTemplate(departmentName)
    const wanted = normalizeKey(jobTitle)

    if (!department || !wanted) return null

    const sources = [
      department.jobs,
      department.job_titles,
      department.positions,
      department.postes,
      department.roles
    ].filter(Boolean)

    for (const source of sources) {
      if (Array.isArray(source)) {
        const match = source.find(item => {
          if (typeof item === 'string') return normalizeKey(item) === wanted

          if (item && typeof item === 'object') {
            return normalizeKey(item.name || item.title || item.job_title || item.poste || item.position) === wanted
          }

          return false
        })

        if (match && typeof match === 'object') return match
      }

      if (source && typeof source === 'object') {
        const key = Object.keys(source).find(name => normalizeKey(name) === wanted)
        if (key) return source[key]
      }
    }

    return null
  }

  function getTemplateGroups(departmentName, jobTitle = '') {
    const department = findDepartmentTemplate(departmentName)
    const job = findJobTemplate(departmentName, jobTitle)

    const groups = [
      ...getGroupFields(department),
      ...getGroupFields(job)
    ]

    return Array.from(new Set(groups)).join('\n')
  }


  const aliases = {
    first_name: ['prenom', 'prénom', 'first_name', 'firstname', 'given_name', 'givenname', 'first', 'forename'],
    last_name: ['nom', 'last_name', 'lastname', 'surname', 'family_name', 'familyname', 'last', 'name'],
    department: ['service', 'departement', 'département', 'department', 'equipe', 'équipe', 'team', 'business_unit', 'bu'],
    job_title: ['poste', 'fonction', 'job_title', 'jobtitle', 'position', 'role', 'rôle', 'metier', 'métier'],
    manager: ['manager', 'responsable', 'manager_name', 'managername', 'superieur', 'supérieur', 'n1'],
    start_date: ['date_debut', 'date début', 'date_arrivee', 'date arrivée', 'start_date', 'startdate', 'arrival_date', 'date'],
    manual_groups: ['groupes', 'groupes_ad', 'ad_groups', 'groups', 'manual_groups', 'groupes manuels', 'security_groups', 'gg']
  }

  function normalizeKey(value) {
    return String(value || '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]/g, '')
  }

  function parseCsvLine(line, delimiter) {
    const values = []
    let current = ''
    let inQuotes = false

    for (let i = 0; i < line.length; i += 1) {
      const char = line[i]
      const next = line[i + 1]

      if (char === '"' && inQuotes && next === '"') {
        current += '"'
        i += 1
        continue
      }

      if (char === '"') {
        inQuotes = !inQuotes
        continue
      }

      if (char === delimiter && !inQuotes) {
        values.push(current.trim())
        current = ''
        continue
      }

      current += char
    }

    values.push(current.trim())
    return values
  }

  function detectDelimiter(firstLine) {
    const candidates = [';', ',', '\t']
    return candidates
      .map(delimiter => ({
        delimiter,
        count: firstLine.split(delimiter).length
      }))
      .sort((a, b) => b.count - a.count)[0].delimiter
  }

  function getValue(record, field) {
    const wanted = new Set(aliases[field].map(normalizeKey))

    for (const [key, value] of Object.entries(record)) {
      if (wanted.has(normalizeKey(key))) {
        return value
      }
    }

    return ''
  }

  function splitGroups(value) {
    return String(value || '')
      .split(/[,|;]/)
      .map(group => group.trim())
      .filter(Boolean)
      .join('\n')
  }

  const csvMappingFields = [
    { key: 'first_name', label: 'Prénom', required: true },
    { key: 'last_name', label: 'Nom', required: true },
    { key: 'department', label: 'Service', required: true },
    { key: 'job_title', label: 'Poste', required: true },
    { key: 'manager', label: 'Manager', required: false },
    { key: 'start_date', label: 'Date début', required: false },
    { key: 'manual_groups', label: 'Groupes AD', required: false }
  ]

  function guessColumnMapping(csvHeaders) {
    const mapping = {}

    for (const field of csvMappingFields) {
      const wanted = new Set((aliases[field.key] || []).map(normalizeKey))
      const exact = csvHeaders.find(header => wanted.has(normalizeKey(header)))

      mapping[field.key] = exact || ''
    }

    return mapping
  }

  function getMappedValue(record, field, mapping) {
    const mappedColumn = mapping[field]

    if (mappedColumn && Object.prototype.hasOwnProperty.call(record, mappedColumn)) {
      return record[mappedColumn]
    }

    return getValue(record, field)
  }

  function buildRowsFromRecords(records, mapping) {
    return records.map(({ line, record }, index) => {
      const row = {
        id: `csv-${Date.now()}-${index}`,
        line,
        first_name: getMappedValue(record, 'first_name', mapping),
        last_name: getMappedValue(record, 'last_name', mapping),
        department: getMappedValue(record, 'department', mapping),
        job_title: getMappedValue(record, 'job_title', mapping),
        manager: getMappedValue(record, 'manager', mapping),
        start_date: getMappedValue(record, 'start_date', mapping),
        manual_groups: splitGroups(getMappedValue(record, 'manual_groups', mapping)),
        raw: record,
        errors: [],
        warning: ''
      }

      const groupsFromTemplate = getTemplateGroups(row.department, row.job_title)

      if (groupsFromTemplate) {
        row.manual_groups = groupsFromTemplate
      }

      row.errors = validateRow(row)
      return row
    })
  }

  function updateColumnMapping(field, value) {
    setColumnMapping(current => ({
      ...current,
      [field]: value
    }))
  }

  function applyColumnMapping() {
    if (csvRecords.length === 0) {
      setMessage('Aucune ligne CSV à remapper.')
      return
    }

    const remappedRows = buildRowsFromRecords(csvRecords, columnMapping)

    setRows(remappedRows)
    setReport(null)
    setMessage('Mapping CSV appliqué.')
  }

  function validateRow(row) {
    const errors = []

    if (!row.first_name.trim()) errors.push('Prénom manquant')
    if (!row.last_name.trim()) errors.push('Nom manquant')
    if (!row.department.trim()) errors.push('Service manquant')
    if (!row.job_title.trim()) errors.push('Poste manquant')

    return errors
  }

  function parseCsvImport() {
    setParseError('')
    setReport(null)

    const cleanText = csvText.trim()

    if (!cleanText) {
      setParseError('Colle un CSV ou sélectionne un fichier avant analyse.')
      setRows([])
      return
    }

    const lines = cleanText
      .split(/\r?\n/)
      .map(line => line.trim())
      .filter(Boolean)

    if (lines.length < 2) {
      setParseError('Le CSV doit contenir une ligne d’en-têtes et au moins une ligne employé.')
      setRows([])
      return
    }

    const delimiter = detectDelimiter(lines[0])
    const csvHeaders = parseCsvLine(lines[0], delimiter)

    const parsedRecords = lines.slice(1).map((line, index) => {
      const values = parseCsvLine(line, delimiter)
      const record = {}

      csvHeaders.forEach((header, headerIndex) => {
        record[header] = values[headerIndex] || ''
      })

      return {
        line: index + 2,
        record
      }
    })

    const guessedMapping = guessColumnMapping(csvHeaders)
    const parsedRows = buildRowsFromRecords(parsedRecords, guessedMapping)

    setHeaders(csvHeaders)
    setCsvRecords(parsedRecords)
    setColumnMapping(guessedMapping)
    setRows(parsedRows)
    setMessage(`${parsedRows.length} ligne(s) CSV analysée(s).`)
  }

  function updateRow(index, field, value) {
    setRows(currentRows => currentRows.map((row, rowIndex) => {
      if (rowIndex !== index) return row

      const updated = {
        ...row,
        [field]: value,
        warning: ''
      }

      if (field === 'department') {
        const jobs = getDepartmentJobs(value)
        const currentJobStillValid = jobs.some(job => normalizeKey(job) === normalizeKey(updated.job_title))

        if (jobs.length > 0 && !currentJobStillValid) {
          updated.job_title = jobs[0]
        }

        const groupsFromTemplate = getTemplateGroups(value, updated.job_title)

        updated.manual_groups = groupsFromTemplate || ''
        updated.warning = groupsFromTemplate
          ? ''
          : 'Aucun groupe trouvé pour ce service/poste'
      }

      if (field === 'job_title') {
        const groupsFromTemplate = getTemplateGroups(updated.department, value)

        updated.manual_groups = groupsFromTemplate || ''
        updated.warning = groupsFromTemplate
          ? ''
          : 'Aucun groupe trouvé pour ce service/poste'
      }

      updated.errors = validateRow(updated)
      return updated
    }))
  }

  function removeRow(index) {
    setRows(currentRows => currentRows.filter((_, rowIndex) => rowIndex !== index))
  }

  function findRequestIdDeep(source) {
    if (!source || typeof source !== 'object') {
      return ''
    }

    for (const key of ['id', 'request_id']) {
      const value = source[key]

      if (typeof value === 'string' && value.trim()) {
        return value
      }
    }

    for (const value of Object.values(source)) {
      if (value && typeof value === 'object') {
        const found = findRequestIdDeep(value)

        if (found) {
          return found
        }
      }
    }

    return ''
  }

  function normalizeImportedName(value) {
    return String(value || '')
      .trim()
      .split(/\s+/)
      .map(part => normalizeKey(part))
      .filter(Boolean)
  }

  function requestMatchesImportedResult(request, result) {
    const status = request.status || ''

    if (status === 'rejected') {
      return false
    }

    const requestKey = buildRequestDuplicateKey(request)

    if (result.rowKey && requestKey === result.rowKey) {
      return true
    }

    const requestText = normalizeKey(JSON.stringify(request))
    const nameParts = normalizeImportedName(result.name)

    return nameParts.length > 0 && nameParts.every(part => requestText.includes(part))
  }

  async function resolveImportedResultIds(results) {
    let latestRequests = requests

    try {
      const data = await apiFetch('/api/requests')
      latestRequests = Array.isArray(data)
        ? data
        : data.requests || data.items || data.data || []
    } catch {
      latestRequests = requests
    }

    return results.map(result => {
      if (!result.ok || result.id) {
        return result
      }

      const matchingRequest = latestRequests.find(request => requestMatchesImportedResult(request, result))
      const resolvedId = findRequestIdDeep(matchingRequest)

      return {
        ...result,
        id: resolvedId || ''
      }
    })
  }

  async function importValidRows() {
    if (validRows.length === 0) {
      setMessage('Aucune ligne valide à importer.')
      return
    }

    setImporting(true)
    setReport(null)

    const results = []

    for (const row of validRows) {
      const payload = {
        first_name: row.first_name.trim(),
        last_name: row.last_name.trim(),
        department: row.department.trim(),
        job_title: row.job_title.trim(),
        manager: row.manager.trim(),
        start_date: row.start_date.trim(),
        manual_groups: row.manual_groups
          .split('\n')
          .map(group => group.trim())
          .filter(Boolean)
      }

      try {
        const created = await apiFetch('/api/onboarding/request', {
          method: 'POST',
          body: JSON.stringify(payload)
        })

        results.push({
          ok: true,
          name: `${row.first_name} ${row.last_name}`,
          id: findRequestIdDeep(created),
          rowKey: buildCsvDuplicateKey(row),
          department: row.department
        })
      } catch (error) {
        results.push({
          ok: false,
          name: `${row.first_name} ${row.last_name}`,
          error: error.message,
          rowKey: buildCsvDuplicateKey(row),
          department: row.department
        })
      }
    }

    const resolvedResults = await resolveImportedResultIds(results)
    const successCount = resolvedResults.filter(result => result.ok).length
    const failedCount = resolvedResults.length - successCount

    setReport({
      successCount,
      failedCount,
      results: resolvedResults
    })

    await loadRequests(true)
    setMessage(`${successCount} demande(s) importée(s), ${failedCount} erreur(s).`)
    setImporting(false)
  }

  function downloadCsvTemplate() {
    const escapeCsv = (value) => {
      const text = String(value ?? '')
      return `"${text.replaceAll('"', '""')}"`
    }

    const headers = [
      'prenom',
      'nom',
      'service',
      'poste',
      'manager',
      'date_debut',
      'groupes'
    ]

    const templateRows = []

    for (const departmentName of departmentOptions) {
      const jobs = getDepartmentJobs(departmentName)

      if (jobs.length === 0) {
        templateRows.push([
          'Prenom',
          'Nom',
          departmentName,
          '',
          'Manager',
          '2026-07-20',
          getTemplateGroups(departmentName, '')
            .split('\n')
            .filter(Boolean)
            .join(',')
        ])

        continue
      }

      for (const jobTitle of jobs) {
        templateRows.push([
          'Prenom',
          'Nom',
          departmentName,
          jobTitle,
          'Manager',
          '2026-07-20',
          getTemplateGroups(departmentName, jobTitle)
            .split('\n')
            .filter(Boolean)
            .join(',')
        ])
      }
    }

    if (templateRows.length === 0) {
      templateRows.push([
        'Jean',
        'Dupont',
        'Support',
        'Technicien helpdesk',
        'Nina Moreau',
        '2026-07-20',
        'GG_M365_Standard,GG_VPN_Users'
      ])
    }

    const csv = '\ufeff' + [
      headers.map(escapeCsv).join(';'),
      ...templateRows.map(row => row.map(escapeCsv).join(';'))
    ].join('\r\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const timestamp = new Date().toISOString().slice(0, 10)

    link.href = url
    link.download = `modele-import-onboarding-${timestamp}.csv`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)

    setMessage('Modèle CSV téléchargé.')
  }

  async function approveImportedRequests() {
    if (!report?.results?.length) {
      setMessage('Aucune demande importée à approuver.')
      return
    }

    const resolvedResults = await resolveImportedResultIds(report.results)

    setReport(current => ({
      ...current,
      results: resolvedResults
    }))

    const importedRequests = resolvedResults.filter(result => result.ok && result.id)

    if (importedRequests.length === 0) {
      setMessage('Aucune demande créée avec ID disponible.')
      return
    }

    const confirmed = window.confirm(
      `Approuver ${importedRequests.length} demande(s) importée(s) ? Elles passeront en attente agent Windows.`
    )

    if (!confirmed) {
      return
    }

    setApprovingImported(true)

    const approvalResults = []

    for (const item of importedRequests) {
      try {
        await apiFetch(`/api/admin/requests/${item.id}/approve`, {
          method: 'POST',
          body: JSON.stringify({
            approved_by: 'react-admin'
          })
        })

        approvalResults.push({
          ...item,
          approved: true
        })
      } catch (error) {
        approvalResults.push({
          ...item,
          approved: false,
          error: error.message
        })
      }
    }

    const approvedCount = approvalResults.filter(result => result.approved).length
    const failedCount = approvalResults.length - approvedCount

    setReport(current => ({
      ...current,
      results: resolvedResults,
      approvalResults,
      approvedCount,
      approvalFailedCount: failedCount
    }))

    await loadRequests(true)
    setMessage(`${approvedCount} demande(s) approuvée(s), ${failedCount} erreur(s).`)
    setApprovingImported(false)
  }

  async function readCsvFile(event) {
    const file = event.target.files?.[0]

    if (!file) return

    const text = await file.text()
    setCsvText(text)
    setRows([])
    setCsvRecords([])
    setHeaders([])
    setColumnMapping({})
    setReport(null)
    setParseError('')
  }

  return (
    <div className="csv-import-page">
      <section className="card csv-import-intro">
        <div>
          <h2>Import CSV onboarding en masse</h2>
          <p>
            Importe plusieurs collaborateurs, vérifie les lignes, modifie les groupes si besoin,
            puis crée les demandes onboarding dans le workflow normal.
          </p>
        </div>

        <div className="csv-import-format">
          <strong>Colonnes reconnues</strong>
          <span>prenom / nom / service / poste / manager / date_debut / groupes</span>
        </div>
      </section>

      <section className="card csv-import-panel">
        <div className="section-header">
          <div>
            <h2>Source CSV</h2>
            <p>Colle le contenu CSV ou sélectionne un fichier.</p>
          </div>

          <div className="csv-source-actions">
            <button
              type="button"
              className="csv-template-button"
              onClick={downloadCsvTemplate}
            >
              Télécharger modèle CSV
            </button>

            <label className="csv-file-button">
              Choisir un CSV
              <input type="file" accept=".csv,text/csv" onChange={readCsvFile} />
            </label>
          </div>
        </div>

        <textarea
          className="csv-import-textarea"
          value={csvText}
          onChange={(event) => setCsvText(event.target.value)}
          placeholder={`prenom;nom;service;poste;manager;date_debut;groupes
Lucas;Martin;Comptabilité;Assistant comptable;Marie Dupont;2026-07-15;GG_Compta_Read,GG_M365_Standard
Emma;Durand;Support;Technicien helpdesk;Nina Moreau;2026-07-16;GG_M365_Standard`}
        />

        {parseError && <div className="csv-import-error">{parseError}</div>}

        {headers.length > 0 && (
          <div className="csv-mapping-panel">
            <div className="csv-mapping-header">
              <div>
                <strong>Mapping des colonnes CSV</strong>
                <span>Associe chaque champ attendu à une colonne de ton fichier.</span>
              </div>

              <button type="button" onClick={applyColumnMapping}>
                Appliquer mapping
              </button>
            </div>

            <div className="csv-mapping-grid">
              {csvMappingFields.map(field => (
                <label key={field.key} className={field.required ? 'required' : ''}>
                  <span>{field.label}{field.required ? ' *' : ''}</span>

                  <select
                    value={columnMapping[field.key] || ''}
                    onChange={(event) => updateColumnMapping(field.key, event.target.value)}
                  >
                    <option value="">Auto / non défini</option>
                    {headers.map(header => (
                      <option key={`${field.key}-${header}`} value={header}>
                        {header}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="csv-import-actions">
          <button type="button" onClick={parseCsvImport}>
            Analyser CSV
          </button>

          {rows.length > 0 && (
            <button
              type="button"
              className="csv-import-create-button"
              disabled={importing || validRows.length === 0}
              onClick={importValidRows}
            >
              {importing ? 'Import en cours...' : `Créer ${validRows.length} demande(s)`}
            </button>
          )}
        </div>
      </section>

      {rows.length > 0 && (
        <section className="card csv-import-preview">
          <div className="section-header">
            <div>
              <h2>Prévisualisation avant import</h2>
              <p>
                {validRows.length} ligne(s) valide(s), {invalidRows.length} ligne(s) à corriger.
                Les doublons CSV ou déjà présents sont bloqués avant import.
              </p>
            </div>

            <div className="csv-import-badges">
              <span>{rows.length} ligne(s)</span>
              <span>{headers.length} colonne(s)</span>
            </div>
          </div>

          <div className="csv-import-table-wrapper">
            <table className="csv-import-table">
              <thead>
                <tr>
                  <th>Ligne</th>
                  <th>Prénom</th>
                  <th>Nom</th>
                  <th>Service</th>
                  <th>Poste</th>
                  <th>Manager</th>
                  <th>Date début</th>
                  <th>Groupes AD</th>
                  <th>État</th>
                  <th></th>
                </tr>
              </thead>

              <tbody>
                {rowsWithDuplicateState.map((row, index) => (
                  <tr key={row.id} className={row.allErrors.length ? 'csv-row-invalid' : ''}>
                    <td>{row.line}</td>
                    <td>
                      <input value={row.first_name} onChange={(event) => updateRow(index, 'first_name', event.target.value)} />
                    </td>
                    <td>
                      <input value={row.last_name} onChange={(event) => updateRow(index, 'last_name', event.target.value)} />
                    </td>
                    <td>
                      <select
                        className="csv-service-select"
                        value={row.department}
                        onChange={(event) => updateRow(index, 'department', event.target.value)}
                      >
                        {!departmentOptions.includes(row.department) && row.department && (
                          <option value={row.department}>{row.department} — CSV</option>
                        )}

                        <option value="">Choisir un service</option>

                        {departmentOptions.map(departmentName => (
                          <option key={departmentName} value={departmentName}>
                            {departmentName}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <select
                        className="csv-job-select"
                        value={row.job_title}
                        onChange={(event) => updateRow(index, 'job_title', event.target.value)}
                      >
                        {!getDepartmentJobs(row.department).some(job => normalizeKey(job) === normalizeKey(row.job_title)) && row.job_title && (
                          <option value={row.job_title}>{row.job_title} — CSV</option>
                        )}

                        <option value="">Choisir un poste</option>

                        {getDepartmentJobs(row.department).map(jobTitle => (
                          <option key={jobTitle} value={jobTitle}>
                            {jobTitle}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input value={row.manager} onChange={(event) => updateRow(index, 'manager', event.target.value)} />
                    </td>
                    <td>
                      <input value={row.start_date} onChange={(event) => updateRow(index, 'start_date', event.target.value)} />
                    </td>
                    <td>
                      <textarea value={row.manual_groups} onChange={(event) => updateRow(index, 'manual_groups', event.target.value)} />
                    </td>
                    <td>
                      {row.allErrors.length === 0 && !row.warning ? (
                        <span className="csv-status-ok">Valide</span>
                      ) : row.allErrors.length > 0 ? (
                        <span className="csv-status-error">{row.allErrors.join(', ')}</span>
                      ) : row.warning ? (
                        <span className="csv-status-warning">{row.warning}</span>
                      ) : (
                        <span className="csv-status-ok">Valide</span>
                      )}
                    </td>
                    <td>
                      <button type="button" className="csv-remove-row-button" onClick={() => removeRow(index)}>
                        Retirer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {report && (
        <section className="card csv-import-report">
          <div className="csv-report-header">
            <div>
              <h2>Rapport d’import</h2>
              <p>{report.successCount} demande(s) créée(s), {report.failedCount} erreur(s).</p>
              {typeof report.approvedCount === 'number' && (
                <p>{report.approvedCount} demande(s) approuvée(s), {report.approvalFailedCount || 0} erreur(s) d’approbation.</p>
              )}
            </div>

            {report.successCount > 0 && (
              <button
                type="button"
                className="csv-bulk-approve-button"
                disabled={approvingImported || report.approvedCount === report.successCount}
                onClick={approveImportedRequests}
              >
                {approvingImported ? 'Approbation...' : report.approvedCount === report.successCount ? 'Demandes approuvées' : 'Approuver les demandes importées'}
              </button>
            )}
          </div>

          <div className="csv-report-list">
            {report.results.map((result, index) => (
              <div key={`${result.name}-${index}`} className={result.ok ? 'csv-report-ok' : 'csv-report-error'}>
                <strong>{result.name}</strong>
                <span>
                  {result.ok ? `Créée ${result.id ? `(${result.id})` : ''}` : result.error}
                  {report.approvalResults?.find(item => item.id === result.id)?.approved && ' · Approuvée'}
                  {report.approvalResults?.find(item => item.id === result.id && item.approved === false)?.error && (
                    ` · Erreur approbation : ${report.approvalResults.find(item => item.id === result.id)?.error}`
                  )}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}


function BackToTopButton({ page }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const main = document.querySelector('.main')

    function updateVisibility() {
      const scrollTop = main ? main.scrollTop : window.scrollY
      setVisible(scrollTop > 240)
    }

    updateVisibility()

    if (main) {
      main.addEventListener('scroll', updateVisibility, { passive: true })
      return () => main.removeEventListener('scroll', updateVisibility)
    }

    window.addEventListener('scroll', updateVisibility, { passive: true })
    return () => window.removeEventListener('scroll', updateVisibility)
  }, [page])

  function scrollToTop() {
    const main = document.querySelector('.main')

    if (main) {
      main.scrollTo({ top: 0, behavior: 'smooth' })
      return
    }

    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <button
      type="button"
      className={`back-to-top-button ${visible ? 'visible' : 'hidden'} ${page === 'overview' ? 'overview' : 'with-live-badge'}`}
      onClick={scrollToTop}
      title="Remonter en haut"
      aria-label="Remonter en haut"
    >
      ↑
    </button>
  )
}

function App() {
  const [page, setPage] = useState(() => {
    const savedPage = localStorage.getItem('eitas_last_page')
    return savedPage && PAGES[savedPage] ? savedPage : 'overview'
  })
  const [apiKey, setApiKey] = useState(localStorage.getItem('eitas_api_key') || '')
  const [apiStatus, setApiStatus] = useState('Non testé')
  const [message, setMessage] = useState('')
  const [requests, setRequests] = useState([])
  const [agentStatus, setAgentStatus] = useState(null)
  const [agentConfig, setAgentConfig] = useState(null)
  const [agentHistory, setAgentHistory] = useState([])
  const [liveRefreshEnabled, setLiveRefreshEnabled] = useState(() => {
    return localStorage.getItem('eitas_live_refresh_enabled') !== 'false'
  })
  const [lastLiveRefreshAt, setLastLiveRefreshAt] = useState(null)
  const [templates, setTemplates] = useState({ departments: {} })
  const [auditLogs, setAuditLogs] = useState([])
  const [auditPage, setAuditPage] = useState(() => {
    const savedPage = Number(localStorage.getItem('eitas_audit_page') || '1')
    return Number.isFinite(savedPage) && savedPage > 0 ? savedPage : 1
  })
  const [auditPageSize, setAuditPageSize] = useState(() => {
    const savedSize = Number(localStorage.getItem('eitas_audit_page_size') || '50')
    return [20, 50, 100].includes(savedSize) ? savedSize : 50
  })
  const [auditSearch, setAuditSearch] = useState(() => localStorage.getItem('eitas_audit_search') || '')
  const [auditActionFilter, setAuditActionFilter] = useState(() => localStorage.getItem('eitas_audit_action_filter') || 'all')
  const [selectedRequest, setSelectedRequest] = useState(null)
  const [auditFocusId, setAuditFocusId] = useState('')

  const [search, setSearch] = useState(() => localStorage.getItem('eitas_requests_search') || '')
  const [statusFilter, setStatusFilter] = useState(() => localStorage.getItem('eitas_requests_status_filter') || 'all')
  const [typeFilter, setTypeFilter] = useState(() => localStorage.getItem('eitas_requests_type_filter') || 'all')
  const [requestPage, setRequestPage] = useState(() => {
    const savedPage = Number(localStorage.getItem('eitas_requests_page') || '1')
    return Number.isFinite(savedPage) && savedPage > 0 ? savedPage : 1
  })
  const [requestPageSize, setRequestPageSize] = useState(() => {
    const savedSize = Number(localStorage.getItem('eitas_requests_page_size') || '20')
    return [10, 20, 50].includes(savedSize) ? savedSize : 20
  })
  const [selectedRequestIds, setSelectedRequestIds] = useState([])
  const [adCheckTerminal, setAdCheckTerminal] = useState({
    open: false,
    jobId: '',
    status: '',
    message: '',
    output: '',
    summary: null,
    loading: false,
    error: ''
  })

  const [adCheckJobs, setAdCheckJobs] = useState([])
  const [agentModeControl, setAgentModeControl] = useState({
    mode: 'Simulation',
    loading: false,
    error: ''
  })
  const [adLookupPanel, setAdLookupPanel] = useState({
    open: false,
    jobId: '',
    target: '',
    query: '',
    status: '',
    message: '',
    output: '',
    result: null,
    loading: false,
    error: ''
  })

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

  const requestTotalPages = Math.max(1, Math.ceil(filteredRequests.length / requestPageSize))
  const requestPageStart = (requestPage - 1) * requestPageSize
  const paginatedRequests = filteredRequests.slice(requestPageStart, requestPageStart + requestPageSize)

  useEffect(() => {
    const maxPage = Math.max(1, Math.ceil(filteredRequests.length / requestPageSize))

    if (requestPage > maxPage) {
      setRequestPage(maxPage)
    }
  }, [filteredRequests.length, requestPage, requestPageSize])

  useEffect(() => {
    setSelectedRequestIds(currentIds =>
      currentIds.filter(id =>
        filteredRequests.some(request => findRequestIdForBulkAction(request) === id)
      )
    )
  }, [filteredRequests])


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

  useEffect(() => {
    const portalGlobalLiveRefresh = window.setInterval(() => {
      if (!liveRefreshEnabled) {
        return
      }

      testApi(true)
      loadRequests(true)
      loadAgentStatus()
      loadAgentConfig()

      if (page === 'audit' || page === 'agentOps' || page === 'adChecks') {
        loadAuditLogs(true)
        loadAgentHistory()
      }

      if (page === 'adChecks') {
        loadAdCheckJobs(true)
      loadAgentMode(true)
      }

      if (page === 'templates' || page === 'newRequest' || page === 'offboarding' || page === 'modification') {
        loadTemplates(true)
      }

      setLastLiveRefreshAt(new Date())
    }, 5000)

    return () => {
      window.clearInterval(portalGlobalLiveRefresh)
    }
  }, [apiKey, page, liveRefreshEnabled])

  useEffect(() => {
    if (!message) {
      return
    }

    const persistentKeywords = [
      'invalide',
      'erreur',
      'Erreur',
      'impossible',
      'Impossible',
      'manquante',
      'refusée',
      'échoué',
      'échec'
    ]

    const shouldPersist = persistentKeywords.some(keyword => message.includes(keyword))

    if (shouldPersist) {
      return
    }

    const messageAutoClearTimer = window.setTimeout(() => {
      setMessage('')
    }, 3500)

    return () => {
      window.clearTimeout(messageAutoClearTimer)
    }
  }, [message])

  useEffect(() => {
    localStorage.setItem('eitas_live_refresh_enabled', liveRefreshEnabled ? 'true' : 'false')
  }, [liveRefreshEnabled])

  useEffect(() => {
    localStorage.setItem('eitas_last_page', page)
  }, [page])


  useEffect(() => {
    localStorage.setItem('eitas_requests_search', search)
  }, [search])

  useEffect(() => {
    localStorage.setItem('eitas_requests_status_filter', statusFilter)
  }, [statusFilter])

  useEffect(() => {
    localStorage.setItem('eitas_requests_type_filter', typeFilter)
  }, [typeFilter])

  useEffect(() => {
    localStorage.setItem('eitas_requests_page', String(requestPage))
  }, [requestPage])

  useEffect(() => {
    localStorage.setItem('eitas_requests_page_size', String(requestPageSize))
    setRequestPage(1)
  }, [requestPageSize])

  useEffect(() => {
    localStorage.setItem('eitas_audit_page', String(auditPage))
  }, [auditPage])

  useEffect(() => {
    localStorage.setItem('eitas_audit_page_size', String(auditPageSize))
    setAuditPage(1)
  }, [auditPageSize])

  useEffect(() => {
    localStorage.setItem('eitas_audit_search', auditSearch)
  }, [auditSearch])

  useEffect(() => {
    localStorage.setItem('eitas_audit_action_filter', auditActionFilter)
  }, [auditActionFilter])

  useEffect(() => {
    setAuditPage(1)
  }, [auditSearch, auditActionFilter])

  useEffect(() => {
    setRequestPage(1)
  }, [search, statusFilter, typeFilter])


  function saveConfig() {
    localStorage.setItem('eitas_api_key', apiKey)
    setMessage('Clé API enregistrée dans ce navigateur.')
  }

  async function testApi(silent = false) {
    try {
      const data = await apiFetch('/api/agent/pending')
      setApiStatus(`Connecté · ${data.count} en attente agent`)
      if (!silent) setMessage('Connexion API opérationnelle.')
    } catch (error) {
      setApiStatus('Erreur API')
      if (!silent) setMessage(error.message)
    }
  }

  async function loadRequests(silent = false) {
    try {
      const data = await apiFetch('/api/requests')
      setRequests(data)
      if (!silent) setMessage('Demandes rechargées.')
    } catch (error) {
      if (!silent) setMessage(error.message)
    }
  }

  async function loadAgentStatus() {
    try {
      const data = await apiFetch('/api/agent/status')
      setAgentStatus(data)
    }
    catch {
      setAgentStatus(null)
    }
  }

  async function loadAgentConfig() {
    try {
      const data = await apiFetch('/api/agent/config')
      setAgentConfig(data)
    }
    catch {
      setAgentConfig(null)
    }
  }

  async function loadAgentHistory() {
    try {
      const data = await apiFetch('/api/audit-logs?limit=200')

      const logs = Array.isArray(data)
        ? data
        : Array.isArray(data?.logs)
          ? data.logs
          : Array.isArray(data?.items)
            ? data.items
            : Array.isArray(data?.audit_logs)
              ? data.audit_logs
              : []

      const agentActions = [
        'agent_processing_paused',
        'agent_processing_resumed',
        'agent_interval_updated'
      ]

      const filteredLogs = logs
        .filter(log => agentActions.includes(log.action))
        .sort((a, b) => new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime())
        .slice(0, 12)

      setAgentHistory(filteredLogs)
    }
    catch (error) {
      console.error('Erreur chargement historique agent', error)
      setAgentHistory([])
    }
  }


  async function updateAgentInterval(intervalMinutes) {
    try {
      const data = await apiFetch('/api/agent/config', {
        method: 'POST',
        body: JSON.stringify({
          interval_minutes: intervalMinutes
        })
      })

      setAgentConfig(data.config)
      setMessage(`Fréquence agent enregistrée : toutes les ${intervalMinutes} minute(s). Elle sera appliquée au prochain passage agent.`)
      await loadAgentHistory()
    }
    catch (error) {
      setMessage(error.message)
    }
  }

  async function updateAgentPause(pauseProcessing) {
    try {
      const intervalMinutes = agentConfig?.interval_minutes || 2

      const data = await apiFetch('/api/agent/config', {
        method: 'POST',
        body: JSON.stringify({
          interval_minutes: intervalMinutes,
          pause_processing: pauseProcessing
        })
      })

      setAgentConfig(data.config)
      setMessage(pauseProcessing ? 'Traitement agent mis en pause.' : 'Traitement agent repris.')
      await loadAgentStatus()
      await loadAgentHistory()
    }
    catch (error) {
      setMessage(error.message)
    }
  }




  async function loadTemplates(silent = false) {
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

      if (!silent) setMessage('Templates rechargés.')
    } catch (error) {
      if (!silent) setMessage(error.message)
    }
  }

  async function loadAgentMode(silent = false) {
    try {
      const data = await apiFetch('/api/agent/mode')

      setAgentModeControl({
        mode: data.mode || 'Simulation',
        loading: false,
        error: ''
      })

      if (!silent) {
        setMessage(`Mode agent actuel : ${data.mode || 'Simulation'}`)
      }
    } catch (error) {
      setAgentModeControl(current => ({
        ...current,
        loading: false,
        error: error.message
      }))

      if (!silent) {
        setMessage(error.message)
      }
    }
  }

  async function updateAgentMode(nextMode) {
    setAgentModeControl(current => ({
      ...current,
      loading: true,
      error: ''
    }))

    try {
      const data = await apiFetch('/api/admin/agent/mode', {
        method: 'POST',
        body: JSON.stringify({
          mode: nextMode,
          updated_by: 'react-admin'
        })
      })

      setAgentModeControl({
        mode: data.mode || nextMode,
        loading: false,
        error: ''
      })

      setMessage(`Mode agent défini sur ${data.mode || nextMode}. Prochain passage agent : nouveau mode appliqué.`)

      if (typeof loadAgentStatus === 'function') {
        loadAgentStatus()
      }
    } catch (error) {
      setAgentModeControl(current => ({
        ...current,
        loading: false,
        error: error.message
      }))

      setMessage(error.message)
    }
  }

  async function loadAdCheckJobs(silent = false) {
    try {
      const data = await apiFetch('/api/ad-check/jobs?limit=300')
      const jobs = Array.isArray(data)
        ? data
        : data.jobs || data.items || []

      setAdCheckJobs(jobs)

      if (!silent) {
        setMessage('Contrôles AD rechargés.')
      }
    } catch (error) {
      if (!silent) setMessage(error.message)
    }
  }

  async function loadAuditLogs(silent = false) {
    try {
      const data = await apiFetch('/api/audit-logs?limit=5000')
      const logs = Array.isArray(data)
        ? data
        : data.logs || data.audit_logs || data.events || []

      setAuditLogs(logs)
      if (!silent) setMessage('Audit logs rechargés.')
    } catch (error) {
      if (!silent) setMessage(error.message)
    }
  }

  const auditActionLabels = {
    request_created: 'Demande créée',
    offboarding_request_created: 'Départ créé',
    modification_request_created: 'Modification créée',
    request_approved: 'Demande approuvée',
    request_rejected: 'Demande rejetée',
    request_claimed: 'Prise par agent',
    request_completed: 'Demande terminée',
    request_failed: 'Demande échouée',
    request_retried: 'Demande relancée',
    template_department_upserted: 'Template modifié',
    agent_processing_paused: 'Agent en pause',
    agent_processing_resumed: 'Agent repris',
    agent_interval_updated: 'Fréquence agent modifiée',
    requests_reset: 'Demandes réinitialisées'
  }

  const auditActionOptions = Array.from(
    new Set(auditLogs.map(log => log.action).filter(Boolean))
  ).sort()

  const filteredAuditLogs = auditLogs.filter((log) => {
    const searchValue = auditSearch.trim().toLowerCase()
    const actionMatches = auditActionFilter === 'all' || log.action === auditActionFilter

    if (!actionMatches) {
      return false
    }

    if (!searchValue) {
      return true
    }

    const actorValue = String(log.actor || log.user || log.source || '').toLowerCase()

    // Si tu tapes exactement api/admin/agent, on filtre vraiment sur l'acteur.
    // Ça évite les faux résultats venant des détails techniques.
    if (['api', 'admin', 'agent', 'react-admin'].includes(searchValue)) {
      return actorValue === searchValue
    }

    // Recherche uniquement dans les colonnes visibles, pas dans le JSON details.
    const haystack = [
      log.timestamp,
      log.created_at,
      log.date,
      log.action,
      auditActionLabels[log.action],
      log.actor,
      log.user,
      log.source,
      log.request_id,
      log.id,
      log.message
    ].join(' ').toLowerCase()

    return haystack.includes(searchValue)
  })

  const auditTotalPages = Math.max(1, Math.ceil(filteredAuditLogs.length / auditPageSize))
  const auditPageStart = (auditPage - 1) * auditPageSize
  const paginatedAuditLogs = filteredAuditLogs.slice(auditPageStart, auditPageStart + auditPageSize)

  useEffect(() => {
    const maxPage = Math.max(1, Math.ceil(filteredAuditLogs.length / auditPageSize))

    if (auditPage > maxPage) {
      setAuditPage(maxPage)
    }
  }, [filteredAuditLogs.length, auditPage, auditPageSize])

  function exportAuditLogsCsv() {
    const escapeCsv = (value) => {
      const text = String(value ?? '')
      return `"${text.replaceAll('"', '""')}"`
    }

    const formatAuditDate = (value) => {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return date.toLocaleString('fr-FR')
    }

    const actionLabels = {
      request_created: 'Demande créée',
      request_approved: 'Demande approuvée',
      request_rejected: 'Demande rejetée',
      request_claimed: 'Demande prise par agent',
      request_completed: 'Demande terminée',
      request_failed: 'Demande échouée',
      request_retried: 'Demande relancée',
      agent_processing_paused: 'Agent mis en pause',
      agent_processing_resumed: 'Agent repris',
      agent_interval_updated: 'Fréquence agent modifiée',
      requests_reset: 'Demandes réinitialisées'
    }

    const headers = [
      'Date',
      'Action',
      'Acteur',
      'Demande',
      'Message',
      'Details'
    ]

    const rows = filteredAuditLogs.map((log) => {
      const details = log.details && typeof log.details === 'object'
        ? JSON.stringify(log.details)
        : (log.details || '')

      return [
        formatAuditDate(log.timestamp || log.created_at || log.date),
        actionLabels[log.action] || log.action || '',
        log.actor || log.user || log.source || '',
        log.request_id || log.id || '',
        log.message || '',
        details
      ]
    })

    const csv = '\ufeff' + [
      headers.map(escapeCsv).join(';'),
      ...rows.map(row => row.map(escapeCsv).join(';'))
    ].join('\r\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const timestamp = new Date().toISOString().slice(0, 19).replaceAll(':', '-')

    link.href = url
    link.download = `eitas-audit-logs-${timestamp}.csv`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)

    setMessage(`${filteredAuditLogs.length} audit log(s) exporté(s).`)
  }

  function exportFilteredRequestsCsv(sourceRequests = null) {
    const requestsToExport = Array.isArray(sourceRequests) ? sourceRequests : filteredRequests

    const escapeCsv = (value) => {
      const text = String(value ?? '')
      return `"${text.replaceAll('"', '""')}"`
    }

    const normalizeKey = (value) => String(value || '')
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '')

    const findDeepValue = (source, keys) => {
      const wanted = new Set(keys.map(normalizeKey))
      const queue = [source]
      const seen = new Set()

      while (queue.length > 0) {
        const current = queue.shift()

        if (!current || typeof current !== 'object') continue
        if (seen.has(current)) continue
        seen.add(current)

        for (const [key, value] of Object.entries(current)) {
          if (wanted.has(normalizeKey(key)) && value !== null && value !== undefined && value !== '') {
            if (typeof value !== 'object') return value
          }

          if (value && typeof value === 'object') {
            queue.push(value)
          }
        }
      }

      return ''
    }

    const pick = (request, paths, deepKeys = []) => {
      for (const path of paths) {
        const value = path.split('.').reduce((current, key) => current?.[key], request)

        if (value !== null && value !== undefined && value !== '') {
          return value
        }
      }

      return findDeepValue(request, deepKeys.length ? deepKeys : paths.map(path => path.split('.').pop()))
    }

    const typeLabels = {
      onboarding: 'Création',
      offboarding: 'Départ',
      modification: 'Modification'
    }

    const statusLabels = {
      waiting_approval: 'En attente validation',
      approved: 'Validée',
      pending: 'En attente agent',
      processing: 'En traitement',
      completed: 'Terminée',
      failed: 'Échouée',
      rejected: 'Rejetée'
    }

    const headers = [
      'Utilisateur',
      'Type',
      'Login',
      'Email',
      'Service',
      'Poste',
      'Statut',
      'Agent',
      'Message'
    ]

    const rows = requestsToExport.map((request) => {
      const requestType = pick(request, ['type', 'request_type'], ['type', 'request_type'])
      const firstName = pick(request, ['first_name', 'employee.first_name', 'payload.first_name', 'data.first_name'], ['first_name', 'firstname', 'given_name', 'prenom'])
      const lastName = pick(request, ['last_name', 'employee.last_name', 'payload.last_name', 'data.last_name'], ['last_name', 'lastname', 'surname', 'nom'])

      const user = pick(
        request,
        ['display_name', 'full_name', 'name', 'employee.display_name', 'payload.display_name', 'data.display_name'],
        ['display_name', 'fullname', 'full_name', 'displayname', 'name']
      ) || [firstName, lastName].filter(Boolean).join(' ')

      const login = pick(
        request,
        ['login', 'username', 'sam_account_name', 'employee.login', 'payload.login', 'data.login'],
        ['login', 'username', 'sam_account_name', 'samaccountname']
      )

      const email = pick(
        request,
        ['email', 'mail', 'employee.email', 'payload.email', 'data.email'],
        ['email', 'mail', 'user_principal_name', 'upn']
      )

      const department = pick(
        request,
        ['department', 'service', 'employee.department', 'payload.department', 'data.department'],
        ['department', 'service']
      )

      const jobTitle = pick(
        request,
        ['job_title', 'poste', 'position', 'employee.job_title', 'payload.job_title', 'data.job_title'],
        ['job_title', 'jobtitle', 'poste', 'position']
      )

      const status = pick(request, ['status'], ['status'])
      const agent = pick(
        request,
        ['processing_by', 'agent_name', 'completed_by', 'agent.computer_name'],
        ['processing_by', 'agent_name', 'computer_name', 'completed_by']
      )

      const message = request.agent_result?.message
        || request.result?.message
        || pick(request, ['message'], ['message'])

      return [
        user,
        typeLabels[requestType] || requestType || '',
        login,
        email,
        department,
        jobTitle,
        statusLabels[status] || status || '',
        agent,
        message
      ]
    })

    const csv = '\ufeff' + [
      headers.map(escapeCsv).join(';'),
      ...rows.map(row => row.map(escapeCsv).join(';'))
    ].join('\r\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const timestamp = new Date().toISOString().slice(0, 19).replaceAll(':', '-')

    link.href = url
    link.download = `eitas-demandes-${timestamp}.csv`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)

    setMessage(`${requestsToExport.length} demande(s) exportée(s).`)
  }

  function findRequestIdForBulkAction(source) {
    if (!source || typeof source !== 'object') {
      return ''
    }

    for (const key of ['id', 'request_id']) {
      const value = source[key]

      if (typeof value === 'string' && value.trim()) {
        return value
      }
    }

    for (const value of Object.values(source)) {
      if (value && typeof value === 'object') {
        const found = findRequestIdForBulkAction(value)

        if (found) {
          return found
        }
      }
    }

    return ''
  }

  const selectedRequests = filteredRequests.filter(request => {
    const requestId = findRequestIdForBulkAction(request)
    return requestId && selectedRequestIds.includes(requestId)
  })

  const selectedApprovableRequests = selectedRequests.filter(request => {
    const status = String(request.status || '').toLowerCase()
    return ['waiting_approval', 'a_valider', 'à valider', 'to_approve'].includes(status)
  })

  const selectedRetryableRequests = selectedRequests.filter(request => {
    const status = String(request.status || '').toLowerCase()
    return ['failed', 'rejected', 'échouée', 'echouee', 'rejetée', 'rejetee'].includes(status)
  })

  function clearRequestSelection() {
    setSelectedRequestIds([])
  }

  function exportSelectedRequestsCsv() {
    if (selectedRequests.length === 0) {
      setMessage('Aucune demande sélectionnée à exporter.')
      return
    }

    exportFilteredRequestsCsv(selectedRequests)
  }

  function sanitizeBulkAdCheckFileName(value) {
    return String(value || 'selection')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 80) || 'selection'
  }

  function escapePowerShellSingleQuotedValue(value) {
    return String(value ?? '').replaceAll("'", "''")
  }

  function getBulkAdCheckItem(request) {
    const payload = request.ad_payload || {}
    const result = request.agent_result || request.result || {}
    const details = result.details || result.data || {}
    const requestId = findRequestIdForBulkAction(request)

    const username = payload.username || payload.sam_account_name || payload.sam || details.username || details.sam_account_name || ''
    const displayName = payload.display_name || payload.full_name || payload.name || details.display_name || details.full_name || ''
    const expectedOu = payload.target_ou || payload.ou || payload.ou_path || payload.organizational_unit || details.target_ou || details.ou || details.ou_path || ''
    const type = request.type || request.request_type || payload.type || details.type || ''
    const status = request.status || ''

    const modeText = [
      result.mode,
      details.mode,
      payload.mode,
      request.mode
    ].filter(Boolean).join(' ').toLowerCase()

    const simulated = Boolean(
      details.simulated === true ||
      details.simulation === true ||
      payload.simulated === true ||
      payload.simulation === true ||
      modeText.includes('simulation')
    )

    return {
      id: requestId,
      type,
      status,
      username,
      displayName,
      expectedOu,
      simulated
    }
  }

  function buildBulkAdCheckPowerShellScript(sourceRequests) {
    const items = sourceRequests.map(getBulkAdCheckItem)

    const psItems = items.map(item => {
      return `  @{
    Id = '${escapePowerShellSingleQuotedValue(item.id)}'
    Type = '${escapePowerShellSingleQuotedValue(item.type)}'
    Status = '${escapePowerShellSingleQuotedValue(item.status)}'
    Sam = '${escapePowerShellSingleQuotedValue(item.username)}'
    DisplayName = '${escapePowerShellSingleQuotedValue(item.displayName)}'
    ExpectedOu = '${escapePowerShellSingleQuotedValue(item.expectedOu)}'
    Simulated = ${item.simulated ? '$true' : '$false'}
  }`
    }).join(",\n")

    return `# EITAS - Controle AD en masse
# Genere depuis le portail React
# Date : ${new Date().toISOString()}

Import-Module ActiveDirectory -ErrorAction Stop

$Requests = @(
${psItems}
)

$Properties = @(
  'SamAccountName',
  'DisplayName',
  'Enabled',
  'mail',
  'Department',
  'Title',
  'Description',
  'DistinguishedName',
  'WhenCreated',
  'WhenChanged',
  'LastLogonDate'
)

function Escape-AdFilterValue {
  param([string]$Value)

  if ($null -eq $Value) {
    return ''
  }

  return $Value -replace "'", "''"
}

$FoundCount = 0
$MissingCount = 0
$OkOuCount = 0
$WarningCount = 0
$Index = 0

Write-Host ""
Write-Host "============================================================"
Write-Host "EITAS - CONTROLE AD EN MASSE"
Write-Host "Demandes a controler : $($Requests.Count)"
Write-Host "============================================================"

foreach ($Item in $Requests) {
  $Index += 1
  $User = $null
  $FoundVia = ''

  Write-Host ""
  Write-Host "------------------------------------------------------------"
  Write-Host ("DEMANDE {0}/{1}" -f $Index, $Requests.Count)
  Write-Host "------------------------------------------------------------"
  Write-Host "ID demande        : $($Item.Id)"
  Write-Host "Type              : $($Item.Type)"
  Write-Host "Statut portail    : $($Item.Status)"
  Write-Host "SamAccountName    : $($Item.Sam)"
  Write-Host "Nom attendu       : $($Item.DisplayName)"
  Write-Host "OU attendue       : $($Item.ExpectedOu)"
  Write-Host "Simulation        : $($Item.Simulated)"

  if ([string]::IsNullOrWhiteSpace($Item.Sam) -and [string]::IsNullOrWhiteSpace($Item.DisplayName)) {
    Write-Host "DONNEES INSUFFISANTES : aucun login ni nom pour rechercher l'utilisateur." -ForegroundColor Yellow
    $MissingCount += 1
    continue
  }

  if (-not [string]::IsNullOrWhiteSpace($Item.Sam)) {
    try {
      $User = Get-ADUser -Identity $Item.Sam -Properties $Properties -ErrorAction Stop
      $FoundVia = 'Identity'
    } catch {
      Write-Host "Introuvable par Identity, recherche alternative..."
    }
  }

  if (-not $User) {
    $Conditions = @()

    if (-not [string]::IsNullOrWhiteSpace($Item.Sam)) {
      $FilterSam = Escape-AdFilterValue $Item.Sam
      $Conditions += "SamAccountName -eq '$FilterSam'"
      $Conditions += "UserPrincipalName -like '$FilterSam@*'"
    }

    if (-not [string]::IsNullOrWhiteSpace($Item.DisplayName)) {
      $FilterName = Escape-AdFilterValue $Item.DisplayName
      $Conditions += "DisplayName -eq '$FilterName'"
      $Conditions += "Name -eq '$FilterName'"
    }

    if ($Conditions.Count -gt 0) {
      $Filter = $Conditions -join ' -or '

      try {
        $User = Get-ADUser -Filter $Filter -Properties $Properties | Select-Object -First 1

        if ($User) {
          $FoundVia = 'Recherche alternative'
        }
      } catch {
        Write-Host "Recherche alternative impossible : $($_.Exception.Message)" -ForegroundColor Yellow
      }
    }
  }

  if (-not $User) {
    Write-Host ""
    Write-Host "UTILISATEUR AD INTROUVABLE" -ForegroundColor Yellow
    Write-Host "Aucun objet AD trouve pour : $($Item.Sam) / $($Item.DisplayName)"

    if ($Item.Simulated) {
      Write-Host "INFO : cette demande etait en Simulation." -ForegroundColor Cyan
      Write-Host "Donc aucun changement AD reel nest attendu pour cette demande." -ForegroundColor Cyan
    } else {
      Write-Host "Attention : demande non detectee comme Simulation. Verifier si compte supprime, renomme ou historique." -ForegroundColor Yellow
    }

    $MissingCount += 1
    continue
  }

  $FoundCount += 1

  Write-Host ""
  Write-Host "UTILISATEUR AD TROUVE" -ForegroundColor Green
  Write-Host "Trouve via : $FoundVia"

  $User | Select-Object SamAccountName, DisplayName, Enabled, mail, Department, Title, Description, DistinguishedName, WhenCreated, WhenChanged, LastLogonDate | Format-List

  Write-Host "GROUPES AD"
  try {
    Get-ADPrincipalGroupMembership -Identity $User.SamAccountName |
      Sort-Object Name |
      Select-Object Name |
      Format-Table -AutoSize
  } catch {
    Write-Host "Impossible de lire les groupes : $($_.Exception.Message)" -ForegroundColor Yellow
    $WarningCount += 1
  }

  if (-not [string]::IsNullOrWhiteSpace($Item.ExpectedOu)) {
    Write-Host "CONTROLE OU"
    Write-Host "OU attendue : $($Item.ExpectedOu)"
    Write-Host "DN actuel   : $($User.DistinguishedName)"

    if ($User.DistinguishedName -like "*,$($Item.ExpectedOu)") {
      Write-Host "OK : utilisateur dans OU attendue" -ForegroundColor Green
      $OkOuCount += 1
    } else {
      Write-Host "WARNING : utilisateur hors OU attendue" -ForegroundColor Yellow
      $WarningCount += 1
    }
  } else {
    Write-Host "CONTROLE OU : aucune OU attendue dans la demande."
  }

  Write-Host "CONTROLE ETAT COMPTE"
  Write-Host "Enabled actuel : $($User.Enabled)"

  if ($Item.Type -eq 'offboarding') {
    if (-not $User.Enabled) {
      Write-Host "OK : compte desactive pour offboarding" -ForegroundColor Green
    } else {
      Write-Host "WARNING : compte encore actif pour offboarding" -ForegroundColor Yellow
      $WarningCount += 1
    }
  }

  if ($Item.Type -eq 'onboarding' -or $Item.Type -eq 'modification') {
    if ($User.Enabled) {
      Write-Host "OK : compte actif" -ForegroundColor Green
    } else {
      Write-Host "WARNING : compte desactive" -ForegroundColor Yellow
      $WarningCount += 1
    }
  }
}

Write-Host ""
Write-Host "============================================================"
Write-Host "RESUME CONTROLE AD EN MASSE"
Write-Host "Demandes controlees       : $($Requests.Count)"
Write-Host "Utilisateurs trouves      : $FoundCount"
Write-Host "Utilisateurs introuvables : $MissingCount"
Write-Host "OU OK                     : $OkOuCount"
Write-Host "Warnings                  : $WarningCount"
Write-Host "============================================================"
`
  }

  function downloadSelectedAdCheckPowerShellFile() {
    if (selectedRequests.length === 0) {
      setMessage('Aucune demande sélectionnée pour le contrôle AD.')
      return
    }

    const script = buildBulkAdCheckPowerShellScript(selectedRequests)
    const blob = new Blob([script], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const timestamp = new Date().toISOString().slice(0, 19).replaceAll(':', '-')

    link.href = url
    link.download = `eitas-controle-ad-selection-${sanitizeBulkAdCheckFileName(String(selectedRequests.length))}-${timestamp}.ps1`

    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)

    setMessage(`${selectedRequests.length} demande(s) exportée(s) en contrôle AD PowerShell.`)
  }

  function closeAdLookupPanel() {
    setAdLookupPanel({
      open: false,
      jobId: '',
      target: '',
      query: '',
      status: '',
      message: '',
      output: '',
      result: null,
      loading: false,
      error: ''
    })
  }

  function applyAdLookupResultToForm(result, target) {
    if (!result || !result.found) {
      return
    }

    if (target === 'offboarding') {
      setOffboardingForm(current => ({
        ...current,
        username: result.username || result.sam_account_name || current.username,
        display_name: result.display_name || result.name || current.display_name,
        department: result.department || current.department,
        comment: current.comment || `Compte trouvé dans AD : ${result.distinguished_name || result.ou || ''}`.trim()
      }))

      setPage('offboarding')
      closeAdLookupPanel()
      setMessage(`Données AD appliquées à l’offboarding : ${result.username || result.sam_account_name}`)
      return
    }

    if (target === 'modification') {
      setModificationForm(current => ({
        ...current,
        username: result.username || result.sam_account_name || current.username,
        display_name: result.display_name || result.name || current.display_name,
        current_department: result.department || current.current_department,
        current_job_title: result.title || current.current_job_title,
        comment: current.comment || `Données récupérées depuis Active Directory`
      }))

      setPage('modification')
      closeAdLookupPanel()
      setMessage(`Données AD appliquées à la modification : ${result.username || result.sam_account_name}`)
    }
  }

  async function refreshAdLookupJob(jobId, target = '') {
    const job = await apiFetch(`/api/ad-lookup/jobs/${jobId}`)
    const result = job.result || null

    setAdLookupPanel(current => ({
      ...current,
      open: true,
      jobId: job.id,
      target: target || current.target,
      query: job.query || current.query,
      status: job.status || '',
      message: job.message || '',
      output: job.output || current.output || '',
      result,
      loading: ['pending', 'processing'].includes(String(job.status || '').toLowerCase()),
      error: ''
    }))

    return job
  }

  async function pollAdLookupJob(jobId, target) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const job = await refreshAdLookupJob(jobId, target)
      const status = String(job.status || '').toLowerCase()

      if (status === 'completed' || status === 'failed') {
        if (job.result?.found) {
          applyAdLookupResultToForm(job.result, target)
        }

        return job
      }

      await new Promise(resolve => setTimeout(resolve, 2000))
    }

    setAdLookupPanel(current => ({
      ...current,
      loading: false,
      error: 'Timeout : la recherche AD est toujours en attente. Tu peux rafraîchir plus tard.'
    }))

    return null
  }

  async function runAdLookupForForm(target) {
    const sourceForm = target === 'offboarding' ? offboardingForm : modificationForm
    const query = String(sourceForm.username || '').trim()

    if (!query) {
      setMessage('Renseigne un login avant de lancer la recherche AD.')
      return
    }

    setAdLookupPanel({
      open: true,
      jobId: '',
      target,
      query,
      status: 'creating',
      message: 'Création du job recherche AD...',
      output: `Recherche Active Directory demandée pour : ${query}\nEn attente de l’agent Windows...`,
      result: null,
      loading: true,
      error: ''
    })

    try {
      const response = await apiFetch('/api/ad-lookup/jobs', {
        method: 'POST',
        body: JSON.stringify({
          query,
          created_by: 'react-admin'
        })
      })

      const job = response.job || response

      setAdLookupPanel(current => ({
        ...current,
        jobId: job.id,
        status: job.status || 'pending',
        message: job.message || 'Recherche AD en attente agent',
        output: `Job recherche AD créé : ${job.id}\nQuery : ${query}\n\nEn attente de l’agent Windows...`,
        loading: true,
        error: ''
      }))

      setMessage(`Recherche AD lancée pour ${query}.`)

      await pollAdLookupJob(job.id, target)
    } catch (error) {
      setAdLookupPanel(current => ({
        ...current,
        loading: false,
        error: error.message || 'Erreur recherche AD',
        output: `${current.output || ''}\n\nERREUR : ${error.message || 'Erreur recherche AD'}`
      }))

      setMessage(`Erreur recherche AD : ${error.message || 'inconnue'}`)
    }
  }

  function closeAdCheckTerminal() {
    setAdCheckTerminal({
      open: false,
      jobId: '',
      status: '',
      message: '',
      output: '',
      summary: null,
      loading: false,
      error: ''
    })
  }

  function copyAdCheckTerminalOutput() {
    const text = adCheckTerminal.output || ''
    if (!text) {
      setMessage('Aucun résultat contrôle AD à copier.')
      return
    }

    navigator.clipboard.writeText(text)
    setMessage('Contrôle Active Directory copié.')
  }

  function downloadAdCheckTerminalOutput() {
    const text = adCheckTerminal.output || ''
    if (!text) {
      setMessage('Aucun résultat contrôle AD à télécharger.')
      return
    }

    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const timestamp = new Date().toISOString().slice(0, 19).replaceAll(':', '-')

    link.href = url
    link.download = `eitas-controle-ad-resultat-${adCheckTerminal.jobId || 'job'}-${timestamp}.txt`

    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)

    setMessage('Contrôle Active Directory téléchargé.')
  }

  async function refreshAdCheckJob(jobId) {
    const job = await apiFetch(`/api/ad-check/jobs/${jobId}`)

    setAdCheckTerminal(current => ({
      ...current,
      open: true,
      jobId: job.id,
      status: job.status || '',
      message: job.message || '',
      output: job.output || current.output || '',
      summary: job.summary || null,
      loading: ['pending', 'processing'].includes(String(job.status || '').toLowerCase()),
      error: ''
    }))

    return job
  }

  async function openAdCheckJobFromHistory(job) {
    const jobId = job?.id

    if (!jobId) {
      setMessage('Job contrôle AD introuvable.')
      return
    }

    setAdCheckTerminal({
      open: true,
      jobId,
      status: job.status || '',
      message: job.message || 'Chargement du contrôle AD...',
      output: job.output || 'Chargement du résultat...',
      summary: job.summary || null,
      loading: ['pending', 'processing'].includes(String(job.status || '').toLowerCase()),
      error: ''
    })

    try {
      await refreshAdCheckJob(jobId)
    } catch (error) {
      setAdCheckTerminal(current => ({
        ...current,
        loading: false,
        error: error.message || 'Erreur chargement contrôle AD'
      }))
    }
  }

  function copyAdCheckJobOutput(job) {
    const text = job?.output || ''

    if (!text) {
      setMessage('Aucun résultat à copier pour ce contrôle AD.')
      return
    }

    navigator.clipboard.writeText(text)
    setMessage('Résultat contrôle AD copié.')
  }

  function downloadAdCheckJobOutput(job) {
    const text = job?.output || ''

    if (!text) {
      setMessage('Aucun résultat à télécharger pour ce contrôle AD.')
      return
    }

    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const timestamp = new Date().toISOString().slice(0, 19).replaceAll(':', '-')

    link.href = url
    link.download = `eitas-controle-ad-resultat-${job.id || 'job'}-${timestamp}.txt`

    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)

    setMessage('Résultat contrôle AD téléchargé.')
  }

  async function pollAdCheckJob(jobId) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const job = await refreshAdCheckJob(jobId)
      const status = String(job.status || '').toLowerCase()

      if (status === 'completed' || status === 'failed') {
        return job
      }

      await new Promise(resolve => setTimeout(resolve, 2000))
    }

    setAdCheckTerminal(current => ({
      ...current,
      loading: false,
      error: 'Timeout : le contrôle AD est toujours en attente. Tu peux relancer le rafraîchissement plus tard.'
    }))

    return null
  }

  async function runSelectedAdCheckJob() {
    if (selectedRequests.length === 0) {
      setMessage('Aucune demande sélectionnée pour le contrôle AD.')
      return
    }

    const requestIds = selectedRequests
      .map(request => findRequestIdForBulkAction(request))
      .filter(Boolean)

    if (requestIds.length === 0) {
      setMessage('Aucun ID de demande valide dans la sélection.')
      return
    }

    setAdCheckTerminal({
      open: true,
      jobId: '',
      status: 'creating',
      message: 'Création du job contrôle AD...',
      output: 'Création du job contrôle AD...\nEn attente de prise en charge par l’agent Windows...',
      summary: null,
      loading: true,
      error: ''
    })

    try {
      const response = await apiFetch('/api/ad-check/jobs', {
        method: 'POST',
        body: JSON.stringify({
          created_by: 'react-admin',
          request_ids: requestIds
        })
      })

      const job = response.job || response

      setAdCheckTerminal(current => ({
        ...current,
        jobId: job.id,
        status: job.status || 'pending',
        message: job.message || 'Contrôle AD en attente agent',
        output: `Job contrôle AD créé : ${job.id}\nDemandes sélectionnées : ${requestIds.length}\n\nEn attente de l’agent Windows...`,
        summary: job.summary || null,
        loading: true,
        error: ''
      }))

      setMessage(`Contrôle AD lancé pour ${requestIds.length} demande(s).`)

      await pollAdCheckJob(job.id)
      await loadAdCheckJobs(true)
    } catch (error) {
      setAdCheckTerminal(current => ({
        ...current,
        loading: false,
        error: error.message || 'Erreur création contrôle AD',
        output: `${current.output || ''}\n\nERREUR : ${error.message || 'Erreur création contrôle AD'}`
      }))
      setMessage(`Erreur contrôle AD : ${error.message || 'inconnue'}`)
    }
  }

  async function approveSelectedRequests() {
    if (selectedApprovableRequests.length === 0) {
      setMessage('Aucune demande sélectionnée à approuver.')
      return
    }

    const confirmed = window.confirm(
      `Approuver ${selectedApprovableRequests.length} demande(s) sélectionnée(s) ?`
    )

    if (!confirmed) {
      return
    }

    let approvedCount = 0
    let failedCount = 0
    const processedIds = []

    for (const request of selectedApprovableRequests) {
      const requestId = findRequestIdForBulkAction(request)

      if (!requestId) {
        failedCount += 1
        continue
      }

      try {
        await apiFetch(`/api/admin/requests/${requestId}/approve`, {
          method: 'POST',
          body: JSON.stringify({
            approved_by: 'react-admin'
          })
        })

        approvedCount += 1
        processedIds.push(requestId)
      } catch {
        failedCount += 1
      }
    }

    setSelectedRequestIds(current => current.filter(id => !processedIds.includes(id)))

    await loadRequests(true)
    await loadAuditLogs(true)

    setMessage(`${approvedCount} demande(s) sélectionnée(s) approuvée(s), ${failedCount} erreur(s).`)
  }

  async function retrySelectedRequests() {
    if (selectedRetryableRequests.length === 0) {
      setMessage('Aucune demande sélectionnée à relancer.')
      return
    }

    const confirmed = window.confirm(
      `Relancer ${selectedRetryableRequests.length} demande(s) sélectionnée(s) ?`
    )

    if (!confirmed) {
      return
    }

    let retriedCount = 0
    let failedCount = 0
    const processedIds = []

    for (const request of selectedRetryableRequests) {
      const requestId = findRequestIdForBulkAction(request)

      if (!requestId) {
        failedCount += 1
        continue
      }

      try {
        await apiFetch(`/api/admin/requests/${requestId}/retry`, {
          method: 'POST'
        })

        retriedCount += 1
        processedIds.push(requestId)
      } catch {
        failedCount += 1
      }
    }

    setSelectedRequestIds(current => current.filter(id => !processedIds.includes(id)))

    await loadRequests(true)
    await loadAuditLogs(true)

    setMessage(`${retriedCount} demande(s) sélectionnée(s) relancée(s), ${failedCount} erreur(s).`)
  }

  const approvableFilteredRequests = filteredRequests.filter(request => {
    const status = String(request.status || '').toLowerCase()
    return ['waiting_approval', 'a_valider', 'à valider', 'to_approve'].includes(status)
  })

  async function approveFilteredRequests() {
    if (approvableFilteredRequests.length === 0) {
      setMessage('Aucune demande filtrée à approuver.')
      return
    }

    const confirmed = window.confirm(
      `Approuver ${approvableFilteredRequests.length} demande(s) filtrée(s) ? Elles passeront en attente agent Windows.`
    )

    if (!confirmed) {
      return
    }

    let approvedCount = 0
    let failedCount = 0

    for (const request of approvableFilteredRequests) {
      const requestId = findRequestIdForBulkAction(request)

      if (!requestId) {
        failedCount += 1
        continue
      }

      try {
        await apiFetch(`/api/admin/requests/${requestId}/approve`, {
          method: 'POST',
          body: JSON.stringify({
            approved_by: 'react-admin'
          })
        })

        approvedCount += 1
      } catch {
        failedCount += 1
      }
    }

    await loadRequests(true)
    await loadAuditLogs(true)

    setMessage(`${approvedCount} demande(s) approuvée(s), ${failedCount} erreur(s).`)
  }

  const retryableFilteredRequests = filteredRequests.filter(request => {
    const status = String(request.status || '').toLowerCase()
    return ['failed', 'rejected', 'échouée', 'echouee', 'rejetée', 'rejetee'].includes(status)
  })

  async function retryFilteredRequests() {
    if (retryableFilteredRequests.length === 0) {
      setMessage('Aucune demande filtrée à relancer.')
      return
    }

    const confirmed = window.confirm(
      `Relancer ${retryableFilteredRequests.length} demande(s) filtrée(s) ? Elles repartiront dans le workflow agent.`
    )

    if (!confirmed) {
      return
    }

    let retriedCount = 0
    let failedCount = 0

    for (const request of retryableFilteredRequests) {
      const requestId = findRequestIdForBulkAction(request)

      if (!requestId) {
        failedCount += 1
        continue
      }

      try {
        await apiFetch(`/api/admin/requests/${requestId}/retry`, {
          method: 'POST'
        })

        retriedCount += 1
      } catch {
        failedCount += 1
      }
    }

    await loadRequests(true)
    await loadAuditLogs(true)

    setMessage(`${retriedCount} demande(s) relancée(s), ${failedCount} erreur(s).`)
  }

  async function refreshAll() {
    await loadTemplates()
    await loadRequests()
    loadAgentStatus()
    await loadAuditLogs()
    await loadAdCheckJobs(true)
    await testApi()
  }

  function buildOnboardingFormDuplicateKey(source) {
    return [
      source.first_name,
      source.last_name,
      source.department
    ]
      .map(value => normalizeText(String(value || '')))
      .filter(Boolean)
      .join('|')
  }

  function buildExistingOnboardingDuplicateKey(request) {
    const requestType = request.type || request.request_type || 'onboarding'

    if (requestType !== 'onboarding') {
      return ''
    }

    const firstName =
      request.first_name ||
      request.employee?.first_name ||
      request.payload?.first_name ||
      request.data?.first_name ||
      ''

    const lastName =
      request.last_name ||
      request.employee?.last_name ||
      request.payload?.last_name ||
      request.data?.last_name ||
      ''

    const displayName =
      request.display_name ||
      request.full_name ||
      request.name ||
      request.employee?.display_name ||
      request.payload?.display_name ||
      request.data?.display_name ||
      [firstName, lastName].filter(Boolean).join(' ')

    const parts = String(displayName || '').trim().split(/\s+/)

    const guessedFirstName = firstName || parts[0] || ''
    const guessedLastName = lastName || parts.slice(1).join(' ') || ''

    const department =
      request.department ||
      request.service ||
      request.employee?.department ||
      request.payload?.department ||
      request.data?.department ||
      ''

    return [
      guessedFirstName,
      guessedLastName,
      department
    ]
      .map(value => normalizeText(String(value || '')))
      .filter(Boolean)
      .join('|')
  }

  function getOnboardingDuplicateRequest(source) {
    const wantedFirstName = normalizeText(String(source.first_name || ''))
    const wantedLastName = normalizeText(String(source.last_name || ''))
    const wantedDepartment = normalizeText(String(source.department || ''))

    if (!wantedFirstName || !wantedLastName || !wantedDepartment) {
      return null
    }

    return requests.find(request => {
      const status = request.status || ''

      // Une demande rejetée peut être relancée, donc on ne bloque pas dessus.
      if (status === 'rejected') {
        return false
      }

      const typeText = normalizeText(String(
        request.type ||
        request.request_type ||
        request.kind ||
        request.category ||
        ''
      ))

      // On ne bloque que les créations / onboarding.
      // Si le type est inconnu, on accepte quand même la recherche car les anciennes demandes
      // peuvent ne pas avoir toutes les mêmes clés.
      const looksLikeNonOnboarding =
        typeText.includes('offboarding') ||
        typeText.includes('depart') ||
        typeText.includes('modification')

      if (looksLikeNonOnboarding) {
        return false
      }

      const requestText = normalizeText(JSON.stringify(request))

      return (
        requestText.includes(wantedFirstName) &&
        requestText.includes(wantedLastName) &&
        requestText.includes(wantedDepartment)
      )
    }) || null
  }

  function getRequestDisplayName(request) {
    return request.display_name
      || request.full_name
      || request.name
      || [request.first_name, request.last_name].filter(Boolean).join(' ')
      || request.username
      || request.login
      || 'Utilisateur'
  }

  function getStatusLabel(status) {
    const labels = {
      waiting_approval: 'En attente validation',
      approved: 'Validée',
      pending: 'En attente agent',
      processing: 'En traitement',
      completed: 'Terminée',
      failed: 'Échouée',
      rejected: 'Rejetée'
    }

    return labels[status] || status || 'Statut inconnu'
  }

  async function createRequest(event) {
    event.preventDefault()

    const duplicateRequest = getOnboardingDuplicateRequest(form)

    if (duplicateRequest) {
      setMessage(
        `Doublon détecté : ${getRequestDisplayName(duplicateRequest)} existe déjà en statut ${getStatusLabel(duplicateRequest.status)}.`
      )
      return
    }

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
      loadAdCheckJobs(true)
    }
  }, [])

  async function openAuditFromRequest(requestId) {
    const id = String(requestId || '').trim()

    setAuditFocusId(id)

    try {
      window.sessionStorage.setItem('eitasAuditFocusId', id)
    } catch {
      // Non bloquant.
    }

    setSelectedRequest(null)
    await loadAuditLogs(true)
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
<button className={page === 'csvImport' ? 'active' : ''} onClick={() => setPage('csvImport')}>Import CSV</button>
          <button className={page === 'offboarding' ? 'active' : ''} onClick={() => setPage('offboarding')}>Offboarding</button>
          <button className={page === 'modification' ? 'active' : ''} onClick={() => setPage('modification')}>Modification</button>
          <button className={page === 'templates' ? 'active' : ''} onClick={() => setPage('templates')}>Templates</button>
          <button className={page === 'audit' ? 'active' : ''} onClick={() => setPage('audit')}>Audit logs</button>
          <button className={page === 'agentOps' ? 'active' : ''} onClick={() => setPage('agentOps')}>Exploitation agent</button>

            <button

              type="button"

              className={page === 'agentMode' ? 'active' : ''}

              onClick={() => {

                setPage('agentMode')

                loadAgentMode(true)

              }}

            >

              Mode agent

            </button>

            <button

              type="button"

              className={page === 'adChecks' ? 'active' : ''}

              onClick={() => setPage('adChecks')}

            >

              Contrôles AD

            </button>
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
            {page === 'overview' && (
              <span className={`api-badge ${apiStatus.startsWith('Connecté') ? 'online' : ''}`}>
                {apiStatus}
              </span>
            )}
            <button
            type="button"
            className={`live-refresh-pill ${['overview', 'dashboard'].includes(page) ? 'visible' : 'hidden'} ${liveRefreshEnabled ? 'active' : 'paused'}`}
            onClick={() => setLiveRefreshEnabled(current => !current)}
            title="Activer ou mettre en pause le rafraîchissement automatique de l’interface"
          >
            {liveRefreshEnabled ? 'Temps réel actif' : 'Temps réel en pause'}
            {lastLiveRefreshAt && (
              <small>Dernière synchro {lastLiveRefreshAt.toLocaleTimeString('fr-FR')}</small>
            )}
          </button>

          {page === 'requests' && (
            <span className={`request-filter-summary ${(search || typeFilter !== 'all' || statusFilter !== 'all') ? 'active' : ''}`}>
              {filteredRequests.length} / {requests.length} demandes
            </span>
          )}

          {page === 'requests' && approvableFilteredRequests.length > 0 && (
            <button
              type="button"
              className="bulk-approve-filtered-button"
              onClick={approveFilteredRequests}
            >
              Approuver les résultats
            </button>
          )}

          {page === 'requests' && retryableFilteredRequests.length > 0 && (
            <button
              type="button"
              className="bulk-retry-filtered-button"
              onClick={retryFilteredRequests}
            >
              Relancer les résultats
            </button>
          )}

          {page === 'requests' && filteredRequests.length > 0 && (
            <button
              type="button"
              className="export-requests-button"
              onClick={exportFilteredRequestsCsv}
            >
              Export CSV
            </button>
          )}

          {page === 'requests' && requests.length > 0 && (
            <select
              className="request-page-size-select"
              value={requestPageSize}
              onChange={(event) => setRequestPageSize(Number(event.target.value))}
              title="Nombre de demandes affichées par page"
            >
              <option value={10}>10 / page</option>
              <option value={20}>20 / page</option>
              <option value={50}>50 / page</option>
            </select>
          )}

          {page === 'requests' && filteredRequests.length > requestPageSize && (
            <div className="request-pagination-controls">
              <button
                type="button"
                disabled={requestPage <= 1}
                onClick={() => setRequestPage(current => Math.max(1, current - 1))}
              >‹</button>

              <span>{requestPage} / {requestTotalPages}</span>

              <button
                type="button"
                disabled={requestPage >= requestTotalPages}
                onClick={() => setRequestPage(current => Math.min(requestTotalPages, current + 1))}
              >›</button>
            </div>
          )}

          {page === 'requests' && (search || typeFilter !== 'all' || statusFilter !== 'all') && (
            <button
              type="button"
              className="reset-filters-button"
              onClick={() => {
                setSearch('')
                setTypeFilter('all')
                setStatusFilter('all')
                setRequestPage(1)
              }}
            >
              Réinitialiser filtres
            </button>
          )}

          {page === 'audit' && auditLogs.length > 0 && (
            <span className={`audit-filter-summary ${(auditSearch || auditActionFilter !== 'all') ? 'active' : ''}`}>
              {filteredAuditLogs.length} / {auditLogs.length} logs
            </span>
          )}

          {page === 'audit' && auditLogs.length > 0 && (
            <input
              className="audit-search-input"
              value={auditSearch}
              onChange={(event) => setAuditSearch(event.target.value)}
              placeholder="Rechercher audit..."
              title="Rechercher dans les audit logs"
            />
          )}

          {page === 'audit' && auditLogs.length > 0 && (
            <select
              className="audit-action-select"
              value={auditActionFilter}
              onChange={(event) => setAuditActionFilter(event.target.value)}
              title="Filtrer par action"
            >
              <option value="all">Toutes les actions</option>
              {auditActionOptions.map(action => (
                <option key={action} value={action}>{auditActionLabels[action] || action}</option>
              ))}
            </select>
          )}

          {page === 'audit' && (auditSearch || auditActionFilter !== 'all') && (
            <button
              type="button"
              className="reset-audit-filters-button"
              onClick={() => {
                setAuditSearch('')
                setAuditActionFilter('all')
                setAuditPage(1)
              }}
            >
              Réinitialiser
            </button>
          )}

          {page === 'audit' && auditLogs.length > 0 && (
            <select
              className="audit-page-size-select"
              value={auditPageSize}
              onChange={(event) => setAuditPageSize(Number(event.target.value))}
              title="Nombre d’audit logs affichés par page"
            >
              <option value={20}>20 / page</option>
              <option value={50}>50 / page</option>
              <option value={100}>100 / page</option>
            </select>
          )}

          {page === 'audit' && filteredAuditLogs.length > auditPageSize && (
            <div className="audit-pagination-controls">
              <button
                type="button"
                disabled={auditPage <= 1}
                onClick={() => setAuditPage(current => Math.max(1, current - 1))}
              >
                ‹
              </button>

              <span>{auditPage} / {auditTotalPages}</span>

              <button
                type="button"
                disabled={auditPage >= auditTotalPages}
                onClick={() => setAuditPage(current => Math.min(auditTotalPages, current + 1))}
              >
                ›
              </button>
            </div>
          )}

          {page === 'audit' && auditLogs.length > 0 && (
            <button
              type="button"
              className="export-audit-button"
              onClick={exportAuditLogsCsv}
            >
              Export CSV
            </button>
          )}

          <button onClick={refreshAll}>Actualiser</button>
          </div>
        </header>

        <main className={`main page-${page}`}>
          <LiveRefreshFloatingBadge
            page={page}
            liveRefreshEnabled={liveRefreshEnabled}
            setLiveRefreshEnabled={setLiveRefreshEnabled}
            lastLiveRefreshAt={lastLiveRefreshAt}
          />

          <BackToTopButton page={page} />

          {message && (
            <div className={`notice toast-notice ${
              /erreur|impossible|invalide|manquante|refusée|échoué|échec/i.test(message)
                ? 'toast-error'
                : 'toast-success'
            }`}>
              {message}
            </div>
          )}

          <AgentSystemBanner agentStatus={agentStatus} agentConfig={agentConfig} />

          {page === 'overview' && (
            <OverviewPage
              stats={stats}
              requests={requests}
              agentStatus={agentStatus}
              setPage={setPage}
              setSelectedRequest={setSelectedRequest}
            />
          )}

          {page === 'requests' && (
            <RequestsPage
              requests={paginatedRequests}
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
              selectedRequestIds={selectedRequestIds}
              setSelectedRequestIds={setSelectedRequestIds}
              selectedRequestCount={selectedRequests.length}
              selectedApprovableCount={selectedApprovableRequests.length}
              selectedRetryableCount={selectedRetryableRequests.length}
              clearRequestSelection={clearRequestSelection}
              approveSelectedRequests={approveSelectedRequests}
              retrySelectedRequests={retrySelectedRequests}
              exportSelectedRequestsCsv={exportSelectedRequestsCsv}
              downloadSelectedAdCheckPowerShellFile={runSelectedAdCheckJob}
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

          {page === 'csvImport' && (
            <CsvImportPage
              apiFetch={apiFetch}
              loadRequests={loadRequests}
              setMessage={setMessage}
              templates={templates}
              requests={requests}
            />
          )}

          {page === 'offboarding' && (
            <OffboardingPage
              requests={requests}
              form={offboardingForm}
              updateForm={updateOffboardingForm}
              createOffboardingRequest={createOffboardingRequest}
              loadRequestIntoOffboarding={loadRequestIntoOffboarding}
              runAdLookup={() => runAdLookupForForm('offboarding')}
              adLookupRunning={adLookupPanel.loading && adLookupPanel.target === 'offboarding'}
            />
          )}

          {page === 'modification' && (
            <ModificationPage
              requests={requests}
              form={modificationForm}
              updateForm={updateModificationForm}
              createModificationRequest={createModificationRequest}
              loadRequestIntoModification={loadRequestIntoModification}
              runAdLookup={() => runAdLookupForForm('modification')}
              adLookupRunning={adLookupPanel.loading && adLookupPanel.target === 'modification'}
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
              auditLogs={paginatedAuditLogs}
              loadAuditLogs={loadAuditLogs}
              auditFocusId={auditFocusId}
              setAuditFocusId={setAuditFocusId}
            />
          )}

          {page === 'agentOps' && (
            <AgentOperationsPage requests={requests} agentStatus={agentStatus} agentConfig={agentConfig} loadAgentStatus={loadAgentStatus} loadAgentConfig={loadAgentConfig} updateAgentInterval={updateAgentInterval} updateAgentPause={updateAgentPause} agentHistory={agentHistory} loadAgentHistory={loadAgentHistory} />
          )}

          {page === 'adChecks' && (
            <AdChecksPage
              jobs={adCheckJobs}
              loadAdCheckJobs={loadAdCheckJobs}
              openAdCheckJobFromHistory={openAdCheckJobFromHistory}
              copyAdCheckJobOutput={copyAdCheckJobOutput}
              downloadAdCheckJobOutput={downloadAdCheckJobOutput}
            />
          )}

          {page === 'agentMode' && (
            <AgentModePage
              agentModeControl={agentModeControl}
              loadAgentMode={loadAgentMode}
              updateAgentMode={updateAgentMode}
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

          {adLookupPanel.open && (
            <div className="ad-lookup-overlay">
              <div className="ad-lookup-panel">
                <div className="ad-lookup-header">
                  <div>
                    <strong>Recherche Active Directory</strong>
                    <span>
                      {adLookupPanel.jobId ? `Job ${adLookupPanel.jobId}` : `Query ${adLookupPanel.query || '-'}`}
                    </span>
                  </div>

                  <button type="button" onClick={closeAdLookupPanel}>Fermer</button>
                </div>

                <div className="ad-lookup-status">
                  <span className={`ad-check-status-dot ${adLookupPanel.status || 'unknown'}`} />
                  <strong>{adLookupPanel.status || 'unknown'}</strong>
                  <span>{adLookupPanel.message || '-'}</span>
                </div>

                {adLookupPanel.error && (
                  <div className="ad-check-terminal-error">
                    {adLookupPanel.error}
                  </div>
                )}

                {adLookupPanel.result?.found && (
                  <div className="ad-lookup-result-grid">
                    <div>
                      <span>Login</span>
                      <strong>{adLookupPanel.result.username || adLookupPanel.result.sam_account_name || '-'}</strong>
                    </div>

                    <div>
                      <span>Nom</span>
                      <strong>{adLookupPanel.result.display_name || adLookupPanel.result.name || '-'}</strong>
                    </div>

                    <div>
                      <span>Compte actif</span>
                      <strong>{String(adLookupPanel.result.enabled)}</strong>
                    </div>

                    <div>
                      <span>Mail</span>
                      <strong>{adLookupPanel.result.mail || '-'}</strong>
                    </div>

                    <div>
                      <span>Service</span>
                      <strong>{adLookupPanel.result.department || '-'}</strong>
                    </div>

                    <div>
                      <span>Poste</span>
                      <strong>{adLookupPanel.result.title || '-'}</strong>
                    </div>
                  </div>
                )}

                {adLookupPanel.result && !adLookupPanel.result.found && (
                  <div className="ad-lookup-not-found">
                    <strong>Utilisateur introuvable dans Active Directory</strong>
                    <span>Query : {adLookupPanel.query || '-'}</span>
                  </div>
                )}

                {adLookupPanel.result?.found && (
                  <div className="ad-lookup-ou-card">
                    <span>OU actuelle</span>
                    <code>{adLookupPanel.result.ou || adLookupPanel.result.distinguished_name || '-'}</code>
                  </div>
                )}

                {adLookupPanel.result?.found && (
                  <div className="ad-lookup-groups-card">
                    <strong>Groupes AD</strong>
                    <div>
                      {(adLookupPanel.result.groups || []).length === 0 ? (
                        <span>Aucun groupe retourné</span>
                      ) : (
                        adLookupPanel.result.groups.map(group => (
                          <span key={group}>{group}</span>
                        ))
                      )}
                    </div>
                  </div>
                )}

                <div className="ad-check-console-card ad-lookup-console">
                  <div className="ad-check-console-header">
                    <span>Sortie agent Windows</span>
                    <strong>{adLookupPanel.result ? 'Résultat reçu' : 'En attente'}</strong>
                  </div>

                  <pre className="ad-check-terminal-output">
{(adLookupPanel.output || 'En attente du résultat agent...').trim()}
                  </pre>
                </div>

                <div className="ad-lookup-actions">
                  <button type="button" onClick={() => adLookupPanel.jobId && refreshAdLookupJob(adLookupPanel.jobId, adLookupPanel.target)}>
                    Rafraîchir
                  </button>

                  {adLookupPanel.result?.found && (
                    <>
                      <button type="button" onClick={() => applyAdLookupResultToForm(adLookupPanel.result, 'offboarding')}>
                        Utiliser pour offboarding
                      </button>

                      <button type="button" onClick={() => applyAdLookupResultToForm(adLookupPanel.result, 'modification')}>
                        Utiliser pour modification
                      </button>
                    </>
                  )}

                  {adLookupPanel.loading && (
                    <span>En attente de l’agent Windows...</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {adCheckTerminal.open && (
        <div className="ad-check-terminal-overlay">
          <div className="ad-check-terminal-panel">
            <div className="ad-check-terminal-header">
              <div>
                <strong>Contrôle Active Directory</strong>
                <span>
                  {adCheckTerminal.jobId ? `Job ${adCheckTerminal.jobId}` : 'Création du job...'}
                </span>
              </div>

              <button type="button" onClick={closeAdCheckTerminal}>Fermer</button>
            </div>

            <div className="ad-check-terminal-status">
              <span className={`ad-check-status-dot ${adCheckTerminal.status || 'unknown'}`} />
              <strong>{adCheckTerminal.status || 'unknown'}</strong>
              <span>{adCheckTerminal.message || '-'}</span>
            </div>

            {adCheckTerminal.summary && (
              <div className="ad-check-terminal-summary">
                <span>Contrôlées : <strong>{adCheckTerminal.summary.checked ?? '-'}</strong></span>
                <span>Trouvés : <strong>{adCheckTerminal.summary.found ?? '-'}</strong></span>
                <span>Introuvables : <strong>{adCheckTerminal.summary.missing ?? '-'}</strong></span>
                <span>OU OK : <strong>{adCheckTerminal.summary.ou_ok ?? '-'}</strong></span>
                <span>Warnings : <strong>{adCheckTerminal.summary.warnings ?? '-'}</strong></span>
              </div>
            )}

            {adCheckTerminal.error && (
              <div className="ad-check-terminal-error">
                {adCheckTerminal.error}
              </div>
            )}

            <div className="ad-check-console-card">
              <div className="ad-check-console-header">
                <span>Sortie agent Windows</span>
                <strong>{adCheckTerminal.summary ? 'Rapport terminé' : 'En attente'}</strong>
              </div>

              <pre className="ad-check-terminal-output">
{(adCheckTerminal.output || 'En attente du résultat agent...').trim()}
              </pre>
            </div>

            <div className="ad-check-terminal-actions">
              <button type="button" onClick={() => adCheckTerminal.jobId && refreshAdCheckJob(adCheckTerminal.jobId)}>
                Rafraîchir
              </button>

              <button type="button" onClick={copyAdCheckTerminalOutput}>
                Copier résultat
              </button>

              <button type="button" onClick={downloadAdCheckTerminalOutput}>
                Télécharger TXT
              </button>

              {adCheckTerminal.loading && (
                <span>En attente de l’agent Windows...</span>
              )}
            </div>
          </div>
        </div>
      )}

      {selectedRequest && (
            <SmartRequestDrawer
              request={selectedRequest}
              auditLogs={auditLogs}
              onClose={() => setSelectedRequest(null)}
              approveRequest={approveRequest}
              rejectRequest={rejectRequest}
              retryRequest={retryRequest}
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




function LiveRefreshFloatingBadge({ page, liveRefreshEnabled, setLiveRefreshEnabled, lastLiveRefreshAt }) {
  return (
    <button
      type="button"
      className={`live-refresh-floating ${['overview', 'dashboard'].includes(page) ? 'hidden' : 'visible'} ${liveRefreshEnabled ? 'active' : 'paused'}`}
      onClick={() => setLiveRefreshEnabled(current => !current)}
      title="Activer ou mettre en pause le rafraîchissement automatique de l’interface"
    >
      <span>{liveRefreshEnabled ? 'Temps réel actif' : 'Temps réel en pause'}</span>
      <small>
        {lastLiveRefreshAt
          ? `Synchro ${lastLiveRefreshAt.toLocaleTimeString('fr-FR')}`
          : 'En attente synchro'}
      </small>
    </button>
  )
}


function AgentSystemBanner({ agentStatus, agentConfig }) {
  const alerts = []

  if (agentConfig?.pause_processing) {
    alerts.push({
      type: 'warning',
      title: 'Agent en pause',
      message: 'Le heartbeat continue, mais les demandes validées ne seront pas traitées.'
    })
  }

  if (agentStatus && agentStatus.online === false) {
    alerts.push({
      type: 'error',
      title: 'Agent hors ligne',
      message: 'Aucun heartbeat récent reçu depuis le serveur Windows.'
    })
  }

  if (agentStatus?.task?.enabled === false) {
    alerts.push({
      type: 'error',
      title: 'Tâche Windows désactivée',
      message: 'La tâche planifiée agent est désactivée sur le serveur Windows.'
    })
  }

  const resultCode = Number(agentStatus?.task?.last_task_result)

  if (
    agentStatus?.task?.last_task_result !== undefined &&
    agentStatus?.task?.last_task_result !== null &&
    ![0, 267008, 267009].includes(resultCode)
  ) {
    alerts.push({
      type: 'warning',
      title: 'Résultat Windows à vérifier',
      message: `Dernier code tâche Windows : ${agentStatus.task.last_task_result}`
    })
  }

  if (alerts.length === 0) {
    return null
  }

  return (
    <div className="agent-system-alerts">
      {alerts.map(alert => (
        <div className={`agent-system-alert ${alert.type}`} key={`${alert.title}-${alert.message}`}>
          <strong>{alert.title}</strong>
          <span>{alert.message}</span>
        </div>
      ))}
    </div>
  )
}


function OverviewPage({ requests, agentStatus, setPage }) {
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


function AgentOperationsPage({ requests, agentStatus, agentConfig, loadAgentStatus, loadAgentConfig, updateAgentInterval, updateAgentPause, agentHistory, loadAgentHistory }) {
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
  selectedRequestIds,
  setSelectedRequestIds,
  selectedRequestCount,
  selectedApprovableCount,
  selectedRetryableCount,
  clearRequestSelection,
  approveSelectedRequests,
  retrySelectedRequests,
  exportSelectedRequestsCsv,
  downloadSelectedAdCheckPowerShellFile,
  setSelectedRequest
}) {
  return (
    <section className="panel">
      <PanelHeader
        title="Liste des demandes"
        subtitle="Recherche, filtrage, sélection et validation."
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

      {selectedRequestCount > 0 && (
        <div className="request-selection-toolbar">
          <strong>{selectedRequestCount} sélectionnée(s)</strong>

          <div>
            {selectedApprovableCount > 0 && (
              <button type="button" className="selection-approve-button" onClick={approveSelectedRequests}>
                Approuver sélection ({selectedApprovableCount})
              </button>
            )}

            {selectedRetryableCount > 0 && (
              <button type="button" className="selection-retry-button" onClick={retrySelectedRequests}>
                Relancer sélection ({selectedRetryableCount})
              </button>
            )}

            <button type="button" className="selection-export-button" onClick={exportSelectedRequestsCsv}>
              Export sélection
            </button>

            <button type="button" className="selection-ad-check-button" onClick={downloadSelectedAdCheckPowerShellFile}>
              Contrôle AD sélection
            </button>

            <button type="button" className="selection-clear-button" onClick={clearRequestSelection}>
              Vider
            </button>
          </div>
        </div>
      )}

      <RequestsTable
        requests={requests}
        approveRequest={approveRequest}
        rejectRequest={rejectRequest}
        retryRequest={retryRequest}
        selectedRequestIds={selectedRequestIds}
        setSelectedRequestIds={setSelectedRequestIds}
        setSelectedRequest={setSelectedRequest}
      />
    </section>
  )
}

function RequestsTable({
  requests,
  approveRequest,
  rejectRequest,
  retryRequest,
  selectedRequestIds,
  setSelectedRequestIds,
  setSelectedRequest
}) {
  const pageRequestIds = requests
    .map(request => request.id || request.request_id)
    .filter(Boolean)

  const allPageSelected = pageRequestIds.length > 0 && pageRequestIds.every(id => selectedRequestIds.includes(id))

  function togglePageSelection() {
    setSelectedRequestIds(currentIds => {
      if (allPageSelected) {
        return currentIds.filter(id => !pageRequestIds.includes(id))
      }

      return Array.from(new Set([...currentIds, ...pageRequestIds]))
    })
  }

  function toggleRequestSelection(requestId) {
    setSelectedRequestIds(currentIds => {
      if (currentIds.includes(requestId)) {
        return currentIds.filter(id => id !== requestId)
      }

      return [...currentIds, requestId]
    })
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th className="request-select-col">
              <input
                type="checkbox"
                checked={allPageSelected}
                onChange={togglePageSelection}
                title="Sélectionner la page"
              />
            </th>
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
              <td colSpan="9" className="empty">Aucune demande à afficher.</td>
            </tr>
          )}

          {requests.map(request => {
            const payload = request.ad_payload || {}
            const requestId = request.id || request.request_id
            const selected = selectedRequestIds.includes(requestId)

            return (
              <tr key={requestId || request.id} className={selected ? 'request-row-selected' : ''}>
                <td className="request-select-col">
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => toggleRequestSelection(requestId)}
                    title="Sélectionner cette demande"
                  />
                </td>

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
                      <button className="success" onClick={() => approveRequest(requestId)}>Approuver</button>
                      <button className="danger" onClick={() => rejectRequest(requestId)}>Rejeter</button>
                    </div>
                  ) : request.status === 'failed' || request.status === 'rejected' ? (
                    <div className="row-actions">
                      <button onClick={() => retryRequest(requestId)}>Relancer</button>
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


