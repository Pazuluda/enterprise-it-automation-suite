import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  buildLdapAttributeEditorPreview,
  createLdapAttributeEditorDraft,
  getLdapAttributeEditorChangeCount,
  getLdapEditorDefinitions,
  updateLdapAttributeEditorDraft,
} from '../utils/ldapAttributeEditor'

const LDAP_SIMULATION_JOB_PATH =
  '/api/ad-explorer/ldap/update/jobs'

const LDAP_SIMULATION_POLL_ATTEMPTS = 75
const LDAP_SIMULATION_POLL_DELAY_MS = 800

function wait(milliseconds) {
  return new Promise(resolve => {
    window.setTimeout(
      resolve,
      milliseconds
    )
  })
}

function getLdapSimulationFailureMessage(job) {
  return (
    job?.message ||
    job?.output ||
    'La simulation LDAP a échoué.'
  )
}

function useLdapAttributeUpdate({
  object,
  agentMode,
  apiFetch,
}) {
  const [active, setActive] = useState(false)
  const [draft, setDraft] = useState(
    () => createLdapAttributeEditorDraft(object)
  )
  const [interactionError, setInteractionError] =
    useState('')
  const [submitting, setSubmitting] =
    useState(false)
  const [submissionStatus, setSubmissionStatus] =
    useState('')
  const [submittedJob, setSubmittedJob] =
    useState(null)

  function resetEditorState() {
    setDraft(
      createLdapAttributeEditorDraft(object)
    )
    setInteractionError('')
    setSubmitting(false)
    setSubmissionStatus('')
    setSubmittedJob(null)
  }

  useEffect(() => {
    setActive(false)
    setDraft(
      createLdapAttributeEditorDraft(object)
    )
    setInteractionError('')
    setSubmitting(false)
    setSubmissionStatus('')
    setSubmittedJob(null)
  }, [object])

  const definitions = useMemo(
    () => getLdapEditorDefinitions(object),
    [object]
  )

  const eligible = definitions.length > 0

  const changeCount = useMemo(
    () =>
      getLdapAttributeEditorChangeCount(
        draft
      ),
    [draft]
  )

  const previewState = useMemo(() => {
    if (changeCount === 0) {
      return {
        preview: null,
        error: '',
      }
    }

    try {
      return {
        preview:
          buildLdapAttributeEditorPreview({
            object,
            draft,
          }),
        error: '',
      }
    } catch (error) {
      return {
        preview: null,
        error:
          error?.message ||
          'Aperçu LDAP invalide.',
      }
    }
  }, [
    object,
    draft,
    changeCount,
  ])

  const normalizedMode = String(
    agentMode || ''
  )
    .trim()
    .toLowerCase()

  const isSimulationMode =
    normalizedMode === 'simulation'

  function open() {
    if (!eligible) {
      return false
    }

    resetEditorState()
    setActive(true)

    return true
  }

  function close() {
    setActive(false)
    resetEditorState()
  }

  function updateDraft(
    attributeName,
    patch
  ) {
    try {
      const nextDraft =
        updateLdapAttributeEditorDraft(
          draft,
          attributeName,
          patch
        )

      setDraft(nextDraft)
      setInteractionError('')
      setSubmissionStatus('')
      setSubmittedJob(null)

      return true
    } catch (error) {
      setInteractionError(
        error?.message ||
        'Modification LDAP invalide.'
      )

      return false
    }
  }

  function resetAttribute(attributeName) {
    const entry = draft.find(
      item =>
        item.attribute_name ===
        attributeName
    )

    if (!entry) {
      return false
    }

    return updateDraft(
      attributeName,
      {
        operation: 'unchanged',
        value: entry.original_value,
      }
    )
  }

  async function pollSimulationJob(jobId) {
    for (
      let attempt = 0;
      attempt <
        LDAP_SIMULATION_POLL_ATTEMPTS;
      attempt += 1
    ) {
      const job = await apiFetch(
        `/api/ad-admin/jobs/${
          encodeURIComponent(jobId)
        }`
      )

      if (
        job?.status === 'completed' ||
        job?.status === 'failed'
      ) {
        return job
      }

      await wait(
        LDAP_SIMULATION_POLL_DELAY_MS
      )
    }

    throw new Error(
      'Le job LDAP a été créé, mais '
      + 'l’agent principal n’a pas répondu.'
    )
  }

  async function submitSimulation() {
    if (submitting) {
      return false
    }

    if (
      typeof apiFetch !== 'function'
    ) {
      setInteractionError(
        'Le client API authentifié est indisponible.'
      )
      return false
    }

    if (!isSimulationMode) {
      setInteractionError(
        'La création d’un job LDAP est '
        + 'autorisée uniquement en mode Simulation.'
      )
      return false
    }

    if (
      previewState.error ||
      !previewState.preview ||
      changeCount === 0
    ) {
      setInteractionError(
        previewState.error ||
        'Un aperçu LDAP valide est obligatoire.'
      )
      return false
    }

    setSubmitting(true)
    setInteractionError('')
    setSubmissionStatus(
      'Création du job LDAP de simulation...'
    )
    setSubmittedJob(null)

    try {
      const created = await apiFetch(
        LDAP_SIMULATION_JOB_PATH,
        {
          method: 'POST',
          body: JSON.stringify({
            ...previewState.preview.payload,
            created_by: 'react-admin',
          }),
        }
      )

      const jobId = String(
        created?.job?.id || ''
      ).trim()

      if (!jobId) {
        throw new Error(
          'La réponse API ne contient '
          + 'aucun identifiant de job.'
        )
      }

      setSubmissionStatus(
        `Job ${jobId} créé, `
        + 'simulation en cours...'
      )

      const finalJob =
        await pollSimulationJob(jobId)

      setSubmittedJob(finalJob)

      if (
        finalJob?.status === 'failed' ||
        finalJob?.success === false
      ) {
        throw new Error(
          getLdapSimulationFailureMessage(
            finalJob
          )
        )
      }

      setSubmissionStatus(
        finalJob?.message ||
        'Simulation LDAP terminée avec succès.'
      )

      setDraft(
        createLdapAttributeEditorDraft(
          object
        )
      )

      return true
    } catch (error) {
      setInteractionError(
        error?.message ||
        'Impossible de terminer '
        + 'la simulation LDAP.'
      )
      setSubmissionStatus('')

      return false
    } finally {
      setSubmitting(false)
    }
  }

  return {
    active,
    eligible,
    definitions,
    draft,
    changeCount,
    preview: previewState.preview,
    error:
      interactionError ||
      previewState.error,
    agentMode:
      agentMode || 'Inconnu',
    isSimulationMode,
    submitting,
    submissionStatus,
    submittedJob,
    open,
    close,
    updateDraft,
    resetAttribute,
    submitSimulation,
  }
}

export default useLdapAttributeUpdate
