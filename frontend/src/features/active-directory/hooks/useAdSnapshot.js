import {
  useEffect,
  useRef,
  useState,
} from 'react'

import {
  adSnapshotCoversDn,
  findAdSnapshotObject,
  getAdSnapshotChildren,
  getAdSnapshotItems,
  getAdSnapshotOus,
  isAdSnapshotUsable,
  normalizeAdSnapshot,
} from '../utils/adSnapshot'

function useAdSnapshot({
  apiFetch,
  enabled = true,
  intervalMs = 5000,
}) {
  const [snapshot, setSnapshot] = useState(null)
  const [snapshotLoading, setSnapshotLoading] =
    useState(false)
  const [snapshotError, setSnapshotError] =
    useState('')

  const apiFetchRef = useRef(apiFetch)
  const snapshotRef = useRef(snapshot)
  const requestPromiseRef = useRef(null)
  const mountedRef = useRef(false)

  apiFetchRef.current = apiFetch
  snapshotRef.current = snapshot

  async function refreshSnapshot(
    options = {}
  ) {
    const silent = Boolean(options.silent)

    if (
      !enabled ||
      typeof apiFetchRef.current !== 'function'
    ) {
      return null
    }

    if (requestPromiseRef.current) {
      return requestPromiseRef.current
    }

    if (
      !silent &&
      mountedRef.current
    ) {
      setSnapshotLoading(true)
    }

    const requestPromise = (
      async () => {
        try {
          const payload =
            await apiFetchRef.current(
              '/api/ad-snapshot'
            )

          const normalized =
            normalizeAdSnapshot(payload)

          if (!normalized) {
            throw new Error(
              'Snapshot Active Directory invalide.'
            )
          }

          snapshotRef.current = normalized

          if (mountedRef.current) {
            setSnapshot(normalized)
            setSnapshotError('')
          }

          return normalized
        } catch (error) {
          const message =
            error?.message ||
            'Chargement du snapshot Active Directory impossible.'

          if (mountedRef.current) {
            setSnapshotError(message)
          }

          return null
        } finally {
          if (
            requestPromiseRef.current ===
            requestPromise
          ) {
            requestPromiseRef.current = null
          }

          if (
            !silent &&
            mountedRef.current
          ) {
            setSnapshotLoading(false)
          }
        }
      }
    )()

    requestPromiseRef.current =
      requestPromise

    return requestPromise
  }

  async function resolveSnapshot(
    options = {}
  ) {
    const force = Boolean(options.force)

    if (force) {
      const refreshed =
        await refreshSnapshot({
          silent: true,
        })

      if (
        isAdSnapshotUsable(refreshed)
      ) {
        return refreshed
      }
    }

    const current =
      snapshotRef.current

    if (isAdSnapshotUsable(current)) {
      return current
    }

    const refreshed =
      await refreshSnapshot({
        silent: true,
      })

    return isAdSnapshotUsable(refreshed)
      ? refreshed
      : null
  }

  async function getOus(
    options = {}
  ) {
    const current =
      await resolveSnapshot(options)

    if (!current) {
      return null
    }

    return getAdSnapshotOus(current)
  }

  async function getChildren(
    distinguishedName,
    options = {}
  ) {
    const current =
      await resolveSnapshot(options)

    if (
      !current ||
      !adSnapshotCoversDn(
        current,
        distinguishedName
      )
    ) {
      return null
    }

    return getAdSnapshotChildren(
      current,
      distinguishedName
    )
  }

  function getOusSync() {
    return getAdSnapshotOus(
      snapshotRef.current
    )
  }

  function getChildrenSync(
    distinguishedName
  ) {
    return getAdSnapshotChildren(
      snapshotRef.current,
      distinguishedName
    )
  }

  function findByDnSync(
    distinguishedName
  ) {
    return findAdSnapshotObject(
      snapshotRef.current,
      distinguishedName
    )
  }

  function canServeDn(
    distinguishedName
  ) {
    return adSnapshotCoversDn(
      snapshotRef.current,
      distinguishedName
    )
  }

  useEffect(() => {
    mountedRef.current = true

    if (!enabled) {
      return () => {
        mountedRef.current = false
      }
    }

    refreshSnapshot({
      silent: false,
    })

    const cleanIntervalMs = Math.max(
      1000,
      Number(intervalMs) || 5000
    )

    const intervalId =
      window.setInterval(() => {
        refreshSnapshot({
          silent: true,
        })
      }, cleanIntervalMs)

    return () => {
      mountedRef.current = false
      window.clearInterval(intervalId)
    }
  }, [enabled, intervalMs])

  const snapshotIsUsable =
    isAdSnapshotUsable(snapshot)

  const snapshotRevision = String(
    snapshot?.version ||
    snapshot?.generated_at ||
    snapshot?.received_at ||
    ''
  )

  return {
    snapshot,
    snapshotItems:
      getAdSnapshotItems(snapshot),
    snapshotLoading,
    snapshotError,
    snapshotIsUsable,
    snapshotRevision,
    refreshSnapshot,
    getOus,
    getChildren,
    getOusSync,
    getChildrenSync,
    findByDnSync,
    canServeDn,
  }
}

export default useAdSnapshot
