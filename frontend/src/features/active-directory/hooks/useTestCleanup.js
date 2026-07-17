import { useState } from 'react'

import {
  DOMAIN_DN,
  getObjectDn,
} from '../utils/adExplorerCore'

function useTestCleanup({
  apiFetch,
  selectedNode,
  getCreateUserSearchBaseDn,
  waitForAdExplorerJob,
  getCreateUserOuItemsFromJob,
  setStatus,
  adAgentMode,
  setAdAgentMode,
  runAdAdminJob,
  loadAdAgentMode,
}) {
  const [testCleanupModal, setTestCleanupModal] = useState(false)
  const [testCleanupLoading, setTestCleanupLoading] = useState(false)
  const [testCleanupItems, setTestCleanupItems] = useState([])
  const [testCleanupError, setTestCleanupError] = useState('')
  const [testCleanupDeletingDn, setTestCleanupDeletingDn] = useState('')
  const [testCleanupResults, setTestCleanupResults] = useState({})
  const [testCleanupBulkRunning, setTestCleanupBulkRunning] = useState(false)

  function getTestCleanupIdentity(item) {
    return String(
      item?.sam_account_name
      || item?.samAccountName
      || item?.name
      || item?.display_name
      || item?.displayName
      || ''
    ).trim()
  }

  function getTestCleanupReason(item) {
    const identity = getTestCleanupIdentity(item)
    const dn = getObjectDn(item)
    const combined = `${identity} ${dn}`.toLowerCase()

    if (/^gg_tmp_/i.test(identity)) return 'Groupe temporaire GG_TMP_*'
    if (/^tmp_/i.test(identity)) return 'Objet temporaire TMP_*'
    if (/^test_/i.test(identity)) return 'Objet test TEST_*'
    if (/^test[._-]/i.test(identity)) return 'Identifiant test.*'
    if (/(^|,)(cn|ou)=tmp_/i.test(dn)) return 'DN temporaire TMP_*'
    if (/(^|,)(cn|ou)=test_/i.test(dn)) return 'DN test TEST_*'
    if (combined.includes('tmp_react_dest')) return 'Objet créé pendant les tests React'

    return 'Objet détecté comme test'
  }

  function isPotentialTestCleanupObject(item) {
    const identity = getTestCleanupIdentity(item)
    const dn = getObjectDn(item)
    const combined = `${identity} ${dn}`

    return (
      /^gg_tmp_/i.test(identity)
      || /^tmp_/i.test(identity)
      || /^test_/i.test(identity)
      || /^test[._-]/i.test(identity)
      || /(^|,)(cn|ou)=tmp_/i.test(dn)
      || /(^|,)(cn|ou)=test_/i.test(dn)
      || /tmp_react_dest/i.test(combined)
    )
  }

  async function runTestCleanupExplorerJob(action, payload = {}) {
    const created = await apiFetch('/api/ad-explorer/jobs', {
      method: 'POST',
      body: JSON.stringify({
        action,
        ...payload,
        created_by: 'react-test-cleanup-scanner'
      })
    })

    const jobId = created?.job?.id

    if (!jobId) {
      throw new Error(`Job ${action} introuvable`)
    }

    const completedJob = await waitForAdExplorerJob(jobId)
    return getCreateUserOuItemsFromJob(completedJob)
  }

  async function scanTestCleanupObjects() {
    const selectedDn = getObjectDn(selectedNode)
    const baseDn = getCreateUserSearchBaseDn(selectedDn || DOMAIN_DN) || selectedDn || DOMAIN_DN

    setTestCleanupLoading(true)
    setTestCleanupError('')
    setTestCleanupResults({})

    try {
      const jobs = await Promise.allSettled([
        runTestCleanupExplorerJob('list_ou_tree', {
          base_dn: baseDn,
          baseDn,
          limit: 2000
        }),
        runTestCleanupExplorerJob('list_groups', {
          base_dn: baseDn,
          baseDn,
          recursive: true,
          limit: 2000
        }),
        runTestCleanupExplorerJob('search_users', {
          query: 'test',
          base_dn: baseDn,
          baseDn,
          recursive: true,
          limit: 1000
        }),
        runTestCleanupExplorerJob('search_users', {
          query: 'tmp',
          base_dn: baseDn,
          baseDn,
          recursive: true,
          limit: 1000
        })
      ])

      const rawItems = []

      for (const job of jobs) {
        if (job.status === 'fulfilled' && Array.isArray(job.value)) {
          rawItems.push(...job.value)
        }
      }

      const seen = new Set()
      const filtered = rawItems
        .filter(isPotentialTestCleanupObject)
        .filter(item => {
          const key = (getObjectDn(item) || getTestCleanupIdentity(item)).toUpperCase()

          if (!key) return false
          if (seen.has(key)) return false

          seen.add(key)
          return true
        })
        .map(item => ({
          ...item,
          cleanup_reason: getTestCleanupReason(item)
        }))
        .sort((a, b) => {
          const typeA = String(a?.type || a?.objectClass || '').localeCompare(String(b?.type || b?.objectClass || ''), 'fr')
          if (typeA !== 0) return typeA

          return getTestCleanupIdentity(a).localeCompare(getTestCleanupIdentity(b), 'fr', { sensitivity: 'base' })
        })

      setTestCleanupItems(filtered)
      setStatus(`${filtered.length} objet(s) de test détecté(s).`)
    } catch (error) {
      setTestCleanupItems([])
      setTestCleanupError(error?.message || 'Scan des objets de test impossible.')
    } finally {
      setTestCleanupLoading(false)
    }
  }

  function isTestCleanupOu(item) {
    const dn = getObjectDn(item)
    const type = String(item?.type || item?.objectClass || '').toLowerCase()

    return type === 'ou'
      || type.includes('organizational')
      || /^OU=/i.test(String(dn || '').trim())
  }

  function normalizeOuEmptyCheckOutput(job) {
    const raw = job?.output || job?.result || job?.data || {}

    if (typeof raw === 'string') {
      try {
        return JSON.parse(raw)
      } catch {
        return { message: raw }
      }
    }

    return raw
  }

  async function checkTestCleanupOuEmpty(item) {
    const dn = getObjectDn(item)

    if (!dn) {
      throw new Error('DN introuvable pour cette OU.')
    }

    const created = await apiFetch('/api/ad-explorer/jobs', {
      method: 'POST',
      body: JSON.stringify({
        action: 'check_ou_empty',
        ou_dn: dn,
        base_dn: dn,
        created_by: 'react-test-cleanup-ou-check'
      })
    })

    const jobId = created?.job?.id

    if (!jobId) {
      throw new Error('Job check_ou_empty introuvable.')
    }

    const job = await waitForAdExplorerJob(jobId)
    const output = normalizeOuEmptyCheckOutput(job)

    if (!job.success) {
      throw new Error(output?.error || job.message || 'Verification de l OU impossible.')
    }

    return {
      isEmpty: Boolean(output?.is_empty ?? output?.isEmpty),
      childCount: Number(output?.child_count ?? output?.childCount ?? 0),
      children: Array.isArray(output?.children) ? output.children : [],
      message: output?.message || job.message || ''
    }
  }

  async function deleteTestCleanupObject(item) {
    const dn = getObjectDn(item)
    const identity = getTestCleanupIdentity(item) || item?.name || 'Objet AD'

    if (!dn) {
      setTestCleanupError('DN introuvable pour cet objet.')
      return
    }

    setTestCleanupDeletingDn(dn)
    setTestCleanupError('')
    setTestCleanupResults(current => ({
      ...current,
      [dn]: {
        type: 'pending',
        message: 'Action en cours...'
      }
    }))

    try {
      const modeData = await apiFetch('/api/agent/mode')
      const currentMode = modeData?.mode || adAgentMode || 'Inconnu'
      const isProduction = String(currentMode).toLowerCase() === 'production'
      const isOu = isTestCleanupOu(item)

      setAdAgentMode(currentMode)

      if (isOu) {
        setTestCleanupResults(current => ({
          ...current,
          [dn]: {
            type: 'pending',
            message: 'Verification que l OU est vide...'
          }
        }))

        const check = await checkTestCleanupOuEmpty(item)

        if (!check.isEmpty) {
          const message = `OU non vide : ${check.childCount} objet(s) enfant(s). Suppression bloquee.`

          setTestCleanupResults(current => ({
            ...current,
            [dn]: {
              type: 'error',
              message
            }
          }))

          setTestCleanupError(message)
          return
        }

        setTestCleanupResults(current => ({
          ...current,
          [dn]: {
            type: 'pending',
            message: 'OU vide verifiee. Suppression possible.'
          }
        }))
      }

      if (isProduction) {
        const warning = isOu
          ? `ATTENTION : mode Production AD.\n\nOU vide verifiee.\n\nSuppression reelle de l OU :\n${identity}\n\n${dn}\n\nContinuer ?`
          : `ATTENTION : mode Production AD.\n\nSuppression reelle de l objet :\n${identity}\n\n${dn}\n\nContinuer ?`

        const ok = window.confirm(warning)

        if (!ok) {
          setTestCleanupResults(current => ({
            ...current,
            [dn]: {
              type: 'muted',
              message: 'Action annulee.'
            }
          }))
          return
        }
      }

      const job = await runAdAdminJob({
        action: 'delete_object',
        object_identity: dn,
        confirm_dn: dn
      })

      const message = isProduction
        ? 'Suppression Production OK.'
        : isOu
          ? 'OU vide verifiee. Simulation OK — aucun objet AD reel n a ete supprime.'
          : 'Simulation OK — aucun objet AD reel n a ete supprime.'

      setStatus(job?.message || message)

      setTestCleanupResults(current => ({
        ...current,
        [dn]: {
          type: 'success',
          message
        }
      }))

      if (isProduction) {
        setTestCleanupItems(current => current.filter(entry => getObjectDn(entry) !== dn))
      }
    } catch (error) {
      const message = error?.message || `Suppression impossible : ${identity}`

      setTestCleanupResults(current => ({
        ...current,
        [dn]: {
          type: 'error',
          message
        }
      }))

      setTestCleanupError(message)
    } finally {
      setTestCleanupDeletingDn('')
    }
  }

  async function runBulkTestCleanup() {
    if (testCleanupItems.length < 1) {
      setTestCleanupError('Aucun objet de test à traiter.')
      return
    }

    const modeData = await apiFetch('/api/agent/mode')
    const currentMode = modeData?.mode || adAgentMode || 'Inconnu'
    const isProduction = String(currentMode).toLowerCase() === 'production'

    setAdAgentMode(currentMode)

    if (isProduction) {
      const names = testCleanupItems
        .map(item => `- ${getTestCleanupIdentity(item) || item?.name || getObjectDn(item)}`)
        .join('\n')

      const ok = window.confirm(
        `ATTENTION : mode Production AD.\n\nTu vas supprimer ${testCleanupItems.length} objet(s) de test détecté(s).\n\n${names}\n\nLes OU seront vérifiées vides avant suppression.\n\nContinuer ?`
      )

      if (!ok) {
        setTestCleanupError('Nettoyage global annulé.')
        return
      }
    }

    setTestCleanupBulkRunning(true)
    setTestCleanupError('')

    try {
      const snapshot = [...testCleanupItems]

      for (const item of snapshot) {
        await deleteTestCleanupObject(item)
      }

      if (isProduction) {
        await scanTestCleanupObjects()
      }
    } catch (error) {
      setTestCleanupError(error?.message || 'Nettoyage global interrompu.')
    } finally {
      setTestCleanupBulkRunning(false)
    }
  }

  function openTestCleanupScanner() {
    loadAdAgentMode()
    setTestCleanupModal(true)
    setTestCleanupItems([])
    setTestCleanupError('')
    scanTestCleanupObjects()
  }

  return {
    testCleanupModal,
    setTestCleanupModal,
    testCleanupLoading,
    setTestCleanupLoading,
    testCleanupItems,
    setTestCleanupItems,
    testCleanupError,
    setTestCleanupError,
    testCleanupDeletingDn,
    setTestCleanupDeletingDn,
    testCleanupResults,
    setTestCleanupResults,
    testCleanupBulkRunning,
    setTestCleanupBulkRunning,
    getTestCleanupIdentity,
    getTestCleanupReason,
    isPotentialTestCleanupObject,
    runTestCleanupExplorerJob,
    scanTestCleanupObjects,
    isTestCleanupOu,
    normalizeOuEmptyCheckOutput,
    checkTestCleanupOuEmpty,
    deleteTestCleanupObject,
    runBulkTestCleanup,
    openTestCleanupScanner,
  }
}

export default useTestCleanup
