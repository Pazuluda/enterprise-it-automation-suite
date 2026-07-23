import { useState } from 'react'

import {
  cleanAdHistoryText,
  formatAdHistoryAction,
  formatAdHistoryStatus,
  formatAdHistoryJson,
  copyText,
} from '../utils/adExplorerCore'

function useAdActivity({
  adAdminHistory,
  refreshAdAdminHistoryQuietly,
}) {
  const [adActivityModal, setAdActivityModal] = useState(false)
  const [adActivitySearch, setAdActivitySearch] = useState('')
  const [adActivityScope, setAdActivityScope] = useState('all')
  const [adActivityShowSimulations, setAdActivityShowSimulations] = useState(true)
  const [adActivityTimeRange, setAdActivityTimeRange] = useState('all')
  const [adActivitySortOrder, setAdActivitySortOrder] = useState('newest')

  function getAdActivityJobStatus(job) {
    if (job?.status === 'failed' || job?.success === false) return 'failed'
    if (job?.status === 'processing') return 'processing'
    if (job?.status === 'pending') return 'pending'
    if (job?.status === 'completed' || job?.success === true) return 'completed'
    return job?.status || 'unknown'
  }

  function getAdActivityStatusLabel(job) {
    return formatAdHistoryStatus(job)
  }

  function getAdHistoryDetailSummary(job) {
    if (!job) return ''

    return [
      `Action : ${getAdActivityActionLabel(job.action)}`,
      `Statut : ${getAdActivityStatusLabel(job)}`,
      `Agent : ${job.claimed_by || job.created_by || '—'}`,
      `Date : ${formatAdActivityDate(getAdActivityDate(job))}`,
      `Message : ${getAdActivityMessage(job)}`,
      `Simulation : ${isAdActivitySimulation(job) ? 'oui' : 'non'}`,
      `ID : ${job.id || job.job_id || '—'}`
    ].join('\n')
  }

  function copyAdHistoryDetailSummary(job) {
    copyText(getAdHistoryDetailSummary(job))
  }

  function copyAdHistoryDetailJson(job) {
    copyText(formatAdHistoryJson(job))
  }

  function getAdActivityResult(job) {
    const raw = job?.result || job?.output || {}

    if (typeof raw === 'string') {
      try {
        return JSON.parse(raw)
      } catch {
        return { message: raw }
      }
    }

    return raw || {}
  }

  function getAdActivityPayload(job) {
    const raw = job?.payload || {}

    if (typeof raw === 'string') {
      try {
        return JSON.parse(raw)
      } catch {
        return {}
      }
    }

    return raw || {}
  }

  function pickAdActivityValue(...values) {
    for (const value of values) {
      if (value !== null && value !== undefined && String(value).trim()) {
        return String(value).trim()
      }
    }

    return ''
  }

  function getAdActivityTargetDn(job) {
    const result = getAdActivityResult(job)
    const payload = getAdActivityPayload(job)

    return pickAdActivityValue(
      result?.object_dn,
      result?.distinguished_name,
      result?.dn,
      result?.confirm_dn,
      result?.target_ou_dn,
      result?.target_parent_dn,
      result?.parent_dn,
      result?.group_dn,
      result?.member_dn,
      result?.new_dn,
      result?.old_parent_dn,
      result?.deleted_object?.dn,
      result?.deleted_object?.distinguished_name,
      result?.updated_object?.dn,
      result?.updated_object?.distinguished_name,
      result?.renamed_object?.dn,
      result?.renamed_object?.distinguished_name,
      result?.created_user?.dn,
      result?.created_user?.distinguished_name,
      payload?.object_identity,
      payload?.object_dn,
      payload?.distinguished_name,
      payload?.dn,
      payload?.confirm_dn,
      payload?.target_ou_dn,
      payload?.target_parent_dn,
      payload?.parent_dn,
      payload?.group_dn,
      payload?.member_dn
    )
  }

  function getAdActivityTargetNameFromDn(dn) {
    if (!dn) return ''

    const first = String(dn).split(',')[0] || ''
    const idx = first.indexOf('=')

    return idx >= 0 ? first.slice(idx + 1) : first
  }

  function getAdActivityTargetLabel(job) {
    const result = getAdActivityResult(job)
    const payload = getAdActivityPayload(job)
    const dn = getAdActivityTargetDn(job)

    return pickAdActivityValue(
      result?.object,
      result?.name,
      result?.user,
      result?.group,
      result?.member,
      result?.sam_account_name,
      result?.deleted_object?.name,
      result?.updated_object?.name,
      result?.renamed_object?.name,
      result?.created_user?.name,
      payload?.name,
      payload?.sam_account_name,
      payload?.object_identity,
      payload?.group_identity,
      payload?.member_identity,
      getAdActivityTargetNameFromDn(dn)
    )
  }

  function getAdActivityActionLabel(action) {
    return formatAdHistoryAction(action)
  }

  function getAdActivityDate(job) {
    return job?.completed_at
      || job?.updated_at
      || job?.claimed_at
      || job?.created_at
      || ''
  }

  function formatAdActivityDate(value) {
    if (!value) return '—'

    try {
      return new Date(value).toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return value
    }
  }

  function getAdActivityMessage(job) {
    const result = getAdActivityResult(job)

    return cleanAdHistoryText(
      job?.message
      || result?.message
      || result?.error
      || 'Aucun message'
    )
  }

  function isAdActivityCritical(job) {
    return [
      'delete_object',
      'move_object',
      'rename_object',
      'update_object_properties'
    ].includes(job?.action)
  }

  function getAdActivityJobs() {
    return Array.isArray(adAdminHistory) ? adAdminHistory : []
  }

  function getAdActivityStats() {
    const jobs = getAdActivityJobs()

    return {
      total: jobs.length,
      success: jobs.filter(job => getAdActivityJobStatus(job) === 'completed').length,
      failed: jobs.filter(job => getAdActivityJobStatus(job) === 'failed').length,
      running: jobs.filter(job => ['processing', 'pending'].includes(getAdActivityJobStatus(job))).length,
      critical: jobs.filter(isAdActivityCritical).length
    }
  }

  function getAdActivityStatCards() {
    const stats = getAdActivityStats()

    return [
      { key: 'total', label: 'Actions chargées', value: stats.total },
      { key: 'success', label: 'Succès', value: stats.success },
      { key: 'failed', label: 'Échecs', value: stats.failed },
      { key: 'running', label: 'En cours', value: stats.running },
      { key: 'critical', label: 'Actions critiques', value: stats.critical }
    ]
  }

  function getAdActivitySearchText(job) {
    const result = getAdActivityResult(job)
    const payload = getAdActivityPayload(job)

    return [
      job?.id,
      job?.job_id,
      job?.action,
      job?.status,
      job?.success,
      job?.created_by,
      job?.claimed_by,
      job?.message,
      getAdActivityActionLabel(job?.action),
      getAdActivityStatusLabel(job),
      getAdActivityMessage(job),
      getAdActivityTargetLabel(job),
      getAdActivityTargetDn(job),
      JSON.stringify(payload),
      JSON.stringify(result),
      JSON.stringify(job)
    ].filter(Boolean).join(' ').toLowerCase()
  }

  function isAdActivitySimulation(job) {
    const result = getAdActivityResult(job)
    const message = getAdActivityMessage(job)

    return result?.simulated === true
      || result?.simulation === true
      || String(message || '').toLowerCase().includes('simulation')
  }

  function isAdActivityInsideTimeRange(job) {
    if (adActivityTimeRange === 'all') return true

    const dateValue = getAdActivityDate(job) || job?.created_at

    if (!dateValue) return true

    const timestamp = new Date(dateValue).getTime()

    if (!Number.isFinite(timestamp)) return true

    const ageMs = Date.now() - timestamp

    if (adActivityTimeRange === '24h') return ageMs <= 24 * 60 * 60 * 1000
    if (adActivityTimeRange === '7d') return ageMs <= 7 * 24 * 60 * 60 * 1000

    return true
  }

  function sortAdActivityJobs(jobs) {
    return [...jobs].sort((a, b) => {
      const dateA = new Date(getAdActivityDate(a) || a?.created_at || 0).getTime() || 0
      const dateB = new Date(getAdActivityDate(b) || b?.created_at || 0).getTime() || 0

      return adActivitySortOrder === 'oldest'
        ? dateA - dateB
        : dateB - dateA
    })
  }

  function getAdActivityFilteredJobs() {
    const query = adActivitySearch.trim().toLowerCase()

    const filtered = getAdActivityJobs().filter(job => {
      const status = getAdActivityJobStatus(job)

      if (adActivityScope === 'critical' && !isAdActivityCritical(job)) return false
      if (adActivityScope === 'failed' && status !== 'failed') return false
      if (!adActivityShowSimulations && isAdActivitySimulation(job)) return false
      if (!isAdActivityInsideTimeRange(job)) return false
      if (query && !getAdActivitySearchText(job).includes(query)) return false

      return true
    })

    return sortAdActivityJobs(filtered)
  }

  function getAdActivityExportRows() {
    return getAdActivityFilteredJobs().map(job => ({
      id: job?.id || job?.job_id || '',
      action: job?.action || '',
      action_label: getAdActivityActionLabel(job?.action),
      status: getAdActivityJobStatus(job),
      status_label: getAdActivityStatusLabel(job),
      success: job?.success,
      created_by: job?.created_by || '',
      claimed_by: job?.claimed_by || '',
      created_at: job?.created_at || '',
      claimed_at: job?.claimed_at || '',
      completed_at: job?.completed_at || job?.updated_at || '',
      target_label: getAdActivityTargetLabel(job),
      target_dn: getAdActivityTargetDn(job),
      message: getAdActivityMessage(job),
      critical: isAdActivityCritical(job),
      simulation: isAdActivitySimulation(job)
    }))
  }

  function downloadAdActivityFile(filename, content, type) {
    const blob = new Blob([content], { type })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')

    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  function escapeAdActivityCsv(value) {
    const text = value === null || value === undefined ? '' : String(value)

    if (/[",\n;]/.test(text)) {
      return `"${text.replaceAll('"', '""')}"`
    }

    return text
  }

  function resetAdActivityFilters() {
    setAdActivitySearch('')
    setAdActivityScope('all')
    setAdActivityShowSimulations(true)
    setAdActivityTimeRange('all')
    setAdActivitySortOrder('newest')
  }

  function getAdActivityScopeLabel() {
    if (adActivityScope === 'critical') return 'Critiques'
    if (adActivityScope === 'failed') return 'Échecs'

    return 'Tout'
  }

  function getAdActivityTimeRangeLabel() {
    if (adActivityTimeRange === '24h') return 'Dernières 24h'
    if (adActivityTimeRange === '7d') return 'Derniers 7j'

    return 'Toute période'
  }

  function getAdActivitySortLabel() {
    return adActivitySortOrder === 'oldest' ? 'Plus ancien' : 'Plus récent'
  }

  function getAdActivityFilterSummary() {
    return [
      `Résultats : ${getAdActivityFilteredJobs().length}/${getAdActivityJobs().length}`,
      `Périmètre : ${getAdActivityScopeLabel()}`,
      `Période : ${getAdActivityTimeRangeLabel()}`,
      `Tri : ${getAdActivitySortLabel()}`,
      `Simulations : ${adActivityShowSimulations ? 'visibles' : 'masquées'}`,
      adActivitySearch.trim() ? `Recherche : ${adActivitySearch.trim()}` : 'Recherche : aucune'
    ].join(' • ')
  }

  function copyAdActivitySummary() {
    const jobs = getAdActivityFilteredJobs()
    const lines = [
      'Synthèse activité AD Admin',
      getAdActivityFilterSummary(),
      '',
      ...jobs.slice(0, 20).map(job => [
        `- ${getAdActivityActionLabel(job.action)}`,
        `${getAdActivityStatusLabel(job)}`,
        `${job.claimed_by || job.created_by || '—'}`,
        `${formatAdActivityDate(getAdActivityDate(job))}`,
        `${getAdActivityTargetLabel(job) || 'sans cible'}`,
        `${getAdActivityMessage(job)}`
      ].join(' | '))
    ]

    copyText(lines.join('\n'))
  }

  function exportAdActivityJson() {
    const jobs = getAdActivityFilteredJobs()
    const payload = {
      exported_at: new Date().toISOString(),
      search: adActivitySearch,
      scope: adActivityScope,
      scope_label: getAdActivityScopeLabel(),
      time_range: adActivityTimeRange,
      time_range_label: getAdActivityTimeRangeLabel(),
      sort_order: adActivitySortOrder,
      sort_label: getAdActivitySortLabel(),
      simulations_visible: adActivityShowSimulations,
      summary: getAdActivityFilterSummary(),
      count: jobs.length,
      jobs
    }

    downloadAdActivityFile(
      `eitas-ad-activity-${new Date().toISOString().slice(0, 19).replaceAll(':', '-')}.json`,
      JSON.stringify(payload, null, 2),
      'application/json;charset=utf-8'
    )
  }

  function exportAdActivityCsv() {
    const rows = getAdActivityExportRows()
    const headers = [
      'id',
      'action',
      'action_label',
      'status',
      'status_label',
      'success',
      'created_by',
      'claimed_by',
      'created_at',
      'claimed_at',
      'completed_at',
      'target_label',
      'target_dn',
      'message',
      'critical',
      'simulation'
    ]

    const csv = [
      headers.join(';'),
      ...rows.map(row => headers.map(header => escapeAdActivityCsv(row[header])).join(';'))
    ].join('\n')

    downloadAdActivityFile(
      `eitas-ad-activity-${new Date().toISOString().slice(0, 19).replaceAll(':', '-')}.csv`,
      csv,
      'text/csv;charset=utf-8'
    )
  }

  function getAdActivityRecentJobs(limit = 12) {
    return getAdActivityFilteredJobs().slice(0, limit)
  }

  function getAdActivityCriticalJobs(limit = 8) {
    return getAdActivityFilteredJobs()
      .filter(job => isAdActivityCritical(job) || getAdActivityJobStatus(job) === 'failed')
      .slice(0, limit)
  }

  async function openAdActivityCenter() {
    setAdActivityModal(true)
    await refreshAdAdminHistoryQuietly()
  }

  return {
    adActivityModal,
    setAdActivityModal,
    adActivitySearch,
    setAdActivitySearch,
    adActivityScope,
    setAdActivityScope,
    adActivityShowSimulations,
    setAdActivityShowSimulations,
    adActivityTimeRange,
    setAdActivityTimeRange,
    adActivitySortOrder,
    setAdActivitySortOrder,
    getAdActivityJobStatus,
    getAdActivityStatusLabel,
    getAdHistoryDetailSummary,
    copyAdHistoryDetailSummary,
    copyAdHistoryDetailJson,
    getAdActivityResult,
    getAdActivityPayload,
    pickAdActivityValue,
    getAdActivityTargetDn,
    getAdActivityTargetNameFromDn,
    getAdActivityTargetLabel,
    getAdActivityActionLabel,
    getAdActivityDate,
    formatAdActivityDate,
    getAdActivityMessage,
    isAdActivityCritical,
    getAdActivityJobs,
    getAdActivityStats,
    getAdActivityStatCards,
    getAdActivitySearchText,
    isAdActivitySimulation,
    isAdActivityInsideTimeRange,
    sortAdActivityJobs,
    getAdActivityFilteredJobs,
    getAdActivityExportRows,
    downloadAdActivityFile,
    escapeAdActivityCsv,
    resetAdActivityFilters,
    getAdActivityScopeLabel,
    getAdActivityTimeRangeLabel,
    getAdActivitySortLabel,
    getAdActivityFilterSummary,
    copyAdActivitySummary,
    exportAdActivityJson,
    exportAdActivityCsv,
    getAdActivityRecentJobs,
    getAdActivityCriticalJobs,
    openAdActivityCenter,
  }
}

export default useAdActivity
