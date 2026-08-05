import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import {
  HAB_MINIMUM_VALUE,
  HAB_VALUE_TYPE,
  buildHabSenioritySimulationJobPayload,
  buildHabSenioritySimulationPayload,
  getHabCurrentValue,
  getHabSimulationEligibility,
  normalizeHabOperation,
} from '../utils/habSenioritySimulation'

import {
  getObjectDn,
} from '../utils/adExplorerCore'

const HAB_VALIDATION_PATH =
  '/api/ad-explorer/ldap/hab-seniority/validate'

const HAB_JOB_PATH =
  '/api/ad-explorer/ldap/hab-seniority/jobs'

const HAB_POLL_ATTEMPTS = 75
const HAB_POLL_DELAY_MS = 800

function wait(milliseconds) {
  return new Promise(resolve => {
    window.setTimeout(
      resolve,
      milliseconds
    )
  })
}

function createInitialDraft(object) {
  let currentValue = null

  try {
    currentValue = getHabCurrentValue(object)
  } catch {
    currentValue = null
  }

  return {
    operation: 'set',
    value:
      currentValue === null
        ? String(HAB_MINIMUM_VALUE)
        : String(currentValue),
  }
}

function getHabFailureMessage(job) {
  return (
    job?.message ||
    job?.output ||
    'La simulation HAB a échoué.'
  )
}

function assertHabValidationResponse(
  response,
  payload
) {
  if (
    !response ||
    typeof response !== 'object'
  ) {
    throw new Error(
      'La réponse de validation HAB est invalide.'
    )
  }

  if (
    response.action !== payload.action ||
    response.object_identity !==
      payload.object_identity ||
    response.object_class !== 'user' ||
    response.attribute_name !==
      payload.attribute_name ||
    response.operation !== payload.operation
  ) {
    throw new Error(
      'La réponse HAB ne correspond pas à la demande.'
    )
  }

  if (response.value_type !== HAB_VALUE_TYPE) {
    throw new Error(
      'Le type HAB validé doit rester integer32.'
    )
  }

  if (
    response.production_authorized !== false ||
    response.execution_authorized !== false
  ) {
    throw new Error(
      'La validation HAB a autorisé une exécution interdite.'
    )
  }

  if (
    response.simulation_validation_authorized
    !== true
  ) {
    throw new Error(
      'La validation HAB Simulation est refusée.'
    )
  }

  if (
    payload.operation === 'set' &&
    (
      typeOfInteger(response.value) === false ||
      response.value !== payload.value
    )
  ) {
    throw new Error(
      'La valeur HAB normalisée est invalide.'
    )
  }

  if (
    payload.operation === 'clear' &&
    response.value !== null
  ) {
    throw new Error(
      'La suppression HAB doit conserver une valeur nulle.'
    )
  }

  return response
}

function typeOfInteger(value) {
  return (
    typeof value === 'number' &&
    Number.isInteger(value)
  )
}

function useHabSenioritySimulation({
  object,
  agentMode,
  canManageActiveDirectory,
  apiFetch,
}) {
  const [active, setActive] = useState(false)
  const [draft, setDraft] = useState(
    () => createInitialDraft(object)
  )
  const [interactionError, setInteractionError] =
    useState('')
  const [validating, setValidating] =
    useState(false)
  const [validatedPreview, setValidatedPreview] =
    useState(null)
  const [
    validatedFingerprint,
    setValidatedFingerprint,
  ] = useState('')
  const [submitting, setSubmitting] =
    useState(false)
  const [submissionStatus, setSubmissionStatus] =
    useState('')
  const [submittedJob, setSubmittedJob] =
    useState(null)

  /*
   * Conserve la dernière instance de l'objet sans
   * utiliser sa référence comme identité fonctionnelle.
   */
  const latestObjectRef = useRef(object)
  latestObjectRef.current = object

  const objectIdentity = useMemo(
    () =>
      String(
        getObjectDn(object) || ''
      )
        .trim()
        .toLowerCase(),
    [object]
  )

  const eligibility = useMemo(
    () =>
      getHabSimulationEligibility({
        object,
        agentMode,
        canManageActiveDirectory,
      }),
    [
      object,
      agentMode,
      canManageActiveDirectory,
    ]
  )

  const payloadState = useMemo(() => {
    try {
      const payload =
        buildHabSenioritySimulationPayload({
          object,
          operation: draft.operation,
          value: draft.value,
        })

      return {
        payload,
        fingerprint:
          JSON.stringify(payload),
        error: '',
      }
    } catch (error) {
      return {
        payload: null,
        fingerprint: '',
        error:
          error?.message ||
          'La demande HAB est invalide.',
      }
    }
  }, [
    object,
    draft.operation,
    draft.value,
  ])

  const validationIsCurrent =
    Boolean(validatedPreview) &&
    Boolean(validatedFingerprint) &&
    validatedFingerprint ===
      payloadState.fingerprint

  function resetRuntimeState() {
    setInteractionError('')
    setValidating(false)
    setValidatedPreview(null)
    setValidatedFingerprint('')
    setSubmitting(false)
    setSubmissionStatus('')
    setSubmittedJob(null)
  }

  function resetEditorState() {
    setDraft(createInitialDraft(object))
    resetRuntimeState()
  }

  useEffect(() => {
    setActive(false)

    setDraft(
      createInitialDraft(
        latestObjectRef.current
      )
    )

    setInteractionError('')
    setValidating(false)
    setValidatedPreview(null)
    setValidatedFingerprint('')
    setSubmitting(false)
    setSubmissionStatus('')
    setSubmittedJob(null)
  }, [objectIdentity])

  function invalidateValidation() {
    setValidatedPreview(null)
    setValidatedFingerprint('')
    setSubmissionStatus('')
    setSubmittedJob(null)
  }

  function open(modeOverride = agentMode) {
    const openEligibility =
      getHabSimulationEligibility({
        object,
        agentMode: modeOverride,
        canManageActiveDirectory,
      })

    if (!openEligibility.eligible) {
      setInteractionError(
        openEligibility.reason ||
        'La simulation HAB est indisponible.'
      )
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

  function updateOperation(operation) {
    try {
      const normalized =
        normalizeHabOperation(operation)

      setDraft(current => ({
        ...current,
        operation: normalized,
      }))
      setInteractionError('')
      invalidateValidation()

      return true
    } catch (error) {
      setInteractionError(
        error?.message ||
        'Opération HAB invalide.'
      )
      return false
    }
  }

  function updateValue(value) {
    setDraft(current => ({
      ...current,
      value: String(value ?? ''),
    }))
    setInteractionError('')
    invalidateValidation()
  }

  async function validateDraft() {
    if (validating || submitting) {
      return false
    }

    if (!eligibility.eligible) {
      setInteractionError(
        eligibility.reason ||
        'La simulation HAB est indisponible.'
      )
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

    if (
      payloadState.error ||
      !payloadState.payload
    ) {
      setInteractionError(
        payloadState.error ||
        'La demande HAB est invalide.'
      )
      return false
    }

    setValidating(true)
    setInteractionError('')
    setValidatedPreview(null)
    setValidatedFingerprint('')
    setSubmissionStatus('')
    setSubmittedJob(null)

    try {
      const response = await apiFetch(
        HAB_VALIDATION_PATH,
        {
          method: 'POST',
          body: JSON.stringify(
            payloadState.payload
          ),
        }
      )

      const validated =
        assertHabValidationResponse(
          response,
          payloadState.payload
        )

      setValidatedPreview(validated)
      setValidatedFingerprint(
        payloadState.fingerprint
      )

      return true
    } catch (error) {
      setInteractionError(
        error?.message ||
        'La validation HAB a échoué.'
      )
      return false
    } finally {
      setValidating(false)
    }
  }

  async function pollSimulationJob(jobId) {
    for (
      let attempt = 0;
      attempt < HAB_POLL_ATTEMPTS;
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

      await wait(HAB_POLL_DELAY_MS)
    }

    throw new Error(
      'Le job HAB a été créé, mais '
      + 'l’agent principal n’a pas répondu.'
    )
  }

  async function submitSimulation() {
    if (submitting || validating) {
      return false
    }

    if (!eligibility.eligible) {
      setInteractionError(
        eligibility.reason ||
        'La simulation HAB est indisponible.'
      )
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

    if (
      !validationIsCurrent ||
      !validatedPreview
    ) {
      setInteractionError(
        'Une validation HAB à jour est obligatoire.'
      )
      return false
    }

    setSubmitting(true)
    setInteractionError('')
    setSubmissionStatus(
      'Création du job HAB de simulation...'
    )
    setSubmittedJob(null)

    try {
      const jobPayload =
        buildHabSenioritySimulationJobPayload({
          object,
          operation: draft.operation,
          value: draft.value,
          createdBy: 'react-admin',
        })

      const created = await apiFetch(
        HAB_JOB_PATH,
        {
          method: 'POST',
          body: JSON.stringify(jobPayload),
        }
      )

      const jobId = String(
        created?.job?.id || ''
      ).trim()

      if (!jobId) {
        throw new Error(
          'La réponse API ne contient '
          + 'aucun identifiant de job HAB.'
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
          getHabFailureMessage(finalJob)
        )
      }

      setSubmissionStatus(
        finalJob?.message ||
        'Simulation HAB terminée avec succès.'
      )

      return true
    } catch (error) {
      setInteractionError(
        error?.message ||
        'Impossible de terminer '
        + 'la simulation HAB.'
      )
      setSubmissionStatus('')

      return false
    } finally {
      setSubmitting(false)
    }
  }

  return {
    active,
    eligible: eligibility.eligible,
    eligibilityReason: eligibility.reason,
    currentValue:
      (() => {
        try {
          return getHabCurrentValue(object)
        } catch {
          return null
        }
      })(),
    operation: draft.operation,
    value: draft.value,
    payload: payloadState.payload,
    payloadError: payloadState.error,
    validating,
    validatedPreview,
    validationIsCurrent,
    submitting,
    submissionStatus,
    submittedJob,
    error:
      interactionError ||
      payloadState.error,
    agentMode:
      agentMode || 'Inconnu',
    open,
    close,
    updateOperation,
    updateValue,
    validateDraft,
    submitSimulation,
  }
}

export default useHabSenioritySimulation
