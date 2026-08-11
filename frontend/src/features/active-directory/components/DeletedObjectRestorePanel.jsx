import { useState } from 'react'

const DECISION_LABELS = {
  candidate_preflight:
    'Éligible à la Simulation contrôlée',
  needs_live_revalidation:
    'Revalidation Windows requise',
  needs_parent_restore_or_target_path:
    'Parent indisponible : cible alternative requise',
}

function clean(value) {
  return String(value ?? '').trim()
}

function getTimestampMs(value) {
  const raw = clean(value)

  if (!raw) {
    return null
  }

  const timestamp = Date.parse(raw)

  return Number.isFinite(timestamp)
    ? timestamp
    : null
}

function isTimestampExpired(value) {
  const timestamp = getTimestampMs(value)

  return (
    timestamp !== null
    && Date.now() >= timestamp
  )
}

function formatTimestamp(value) {
  const timestamp = getTimestampMs(value)

  if (timestamp === null) {
    return 'Expiration gérée par le backend'
  }

  return new Date(timestamp).toLocaleString(
    'fr-FR',
    {
      dateStyle: 'short',
      timeStyle: 'medium',
    }
  )
}

function getField(item, ...keys) {
  for (const key of keys) {
    const value = item?.[key]

    if (
      value !== undefined
      && value !== null
      && clean(value)
    ) {
      return value
    }
  }

  return ''
}

function getObjectGuid(item) {
  return clean(
    getField(
      item,
      'object_guid',
      'objectGuid',
      'objectGUID',
      'guid'
    )
  )
}

function getObjectName(item) {
  return clean(
    getField(
      item,
      'last_known_rdn',
      'lastKnownRdn',
      'name',
      'display_name'
    )
  )
}

function getObjectClass(item) {
  return clean(
    getField(
      item,
      'object_class',
      'objectClass',
      'type'
    )
  )
}

function sleep(milliseconds) {
  return new Promise(resolve =>
    window.setTimeout(resolve, milliseconds)
  )
}

export default function DeletedObjectRestorePanel({
  apiFetch,
  canManageActiveDirectory = false,
}) {
  const [inventoryLoaded, setInventoryLoaded] =
    useState(false)
  const [items, setItems] = useState([])
  const [recycleBin, setRecycleBin] = useState(null)
  const [selected, setSelected] = useState(null)
  const [newName, setNewName] = useState('')
  const [targetPath, setTargetPath] = useState('')
  const [preflight, setPreflight] = useState(null)
  const [liveJobId, setLiveJobId] = useState('')
  const [liveResult, setLiveResult] = useState(null)
  const [simulation, setSimulation] = useState(null)
  const [challengeLiveJobId, setChallengeLiveJobId] =
    useState('')
  const [challengeLiveResult, setChallengeLiveResult] =
    useState(null)
  const [challenge, setChallenge] = useState(null)
  const [confirmObject, setConfirmObject] = useState('')
  const [confirmTarget, setConfirmTarget] = useState('')
  const [acknowledgeWrite, setAcknowledgeWrite] =
    useState(false)
  const [authorizationReason, setAuthorizationReason] =
    useState('')
  const [authorization, setAuthorization] = useState(null)
  const [postAuthLiveJobId, setPostAuthLiveJobId] =
    useState('')
  const [postAuthLiveResult, setPostAuthLiveResult] =
    useState(null)
  const [postAuthorization, setPostAuthorization] =
    useState(null)
  const [busyAction, setBusyAction] = useState('')
  const [error, setError] = useState('')

  const guid = getObjectGuid(selected)
  const policy = preflight?.policy || {}
  const decision = clean(policy?.decision)

  const eligible = (
    decision === 'candidate_preflight'
    && policy?.preflight_passed === true
  )

  const liveReady = (
    preflight?.live_revalidation_performed === true
    && Boolean(clean(preflight?.live_job_id))
  )

  const decisionLabel = (
    DECISION_LABELS[decision]
    || decision
    || 'Évaluation requise'
  )

  const policyReason = clean(
    policy?.reason
    || policy?.message
    || policy?.block_reason
  )

  const simulationPayload = (
    simulation?.job?.payload
    || simulation?.job
    || {}
  )

  const simulationJobId = clean(
    simulation?.job?.id
  )

  const challengeLiveReady = Boolean(
    simulationJobId
    && clean(challengeLiveJobId)
    && challengeLiveResult
  )

  const challengeExpiresAt = clean(
    challenge?.expires_at
    || challenge?.ticket_expires_at
  )

  const challengeExpired =
    isTimestampExpired(challengeExpiresAt)

  const challengeReady = Boolean(
    clean(challenge?.ticket_id)
    && clean(challenge?.ticket_digest)
    && clean(challenge?.consumption_id)
    && clean(challenge?.object_guid)
    && clean(challenge?.effective_new_name)
    && clean(challenge?.effective_target_path)
  )

  const exactObjectConfirmed = (
    challengeReady
    && clean(confirmObject)
      === clean(challenge?.object_guid)
  )

  const exactTargetConfirmed = (
    challengeReady
    && clean(confirmTarget)
      === clean(challenge?.effective_target_path)
  )

  const humanConfirmationReady = (
    challengeReady
    && exactObjectConfirmed
    && exactTargetConfirmed
    && acknowledgeWrite === true
    && !challengeExpired
    && clean(authorizationReason).length >= 8
    && clean(authorizationReason).length <= 512
  )

  const authorizationReady = Boolean(
    clean(authorization?.authorization_id)
    && clean(authorization?.authorization_digest)
    && authorization?.human_authorized === true
    && authorization?.authorization_consumed === false
    && authorization?.runtime_authorized === false
    && authorization?.production_authorized === false
    && authorization?.restore_authorized === false
    && authorization?.execution_authorized === false
    && authorization?.write_performed === false
  )

  const postAuthLiveReady = Boolean(
    authorizationReady
    && clean(postAuthLiveJobId)
    && postAuthLiveResult
    && (
      clean(postAuthLiveJobId)
      !== clean(authorization?.fresh_live_job_id)
    )
  )

  async function pollAdExplorerJob(jobId) {
    for (
      let attempt = 0;
      attempt < 75;
      attempt += 1
    ) {
      const job = await apiFetch(
        `/api/ad-explorer/jobs/${jobId}`
      )

      if (
        job?.status === 'completed'
        || job?.status === 'failed'
      ) {
        return job
      }

      await sleep(800)
    }

    throw new Error(
      'Le worker Windows n’a pas répondu dans le délai prévu.'
    )
  }

  function resetSensitiveWorkflow() {
    setChallengeLiveJobId('')
    setChallengeLiveResult(null)
    setChallenge(null)
    setConfirmObject('')
    setConfirmTarget('')
    setAcknowledgeWrite(false)
    setAuthorizationReason('')
    setAuthorization(null)
    setPostAuthLiveJobId('')
    setPostAuthLiveResult(null)
    setPostAuthorization(null)
  }

  function resetWorkflow() {
    setPreflight(null)
    setLiveJobId('')
    setLiveResult(null)
    setSimulation(null)
    resetSensitiveWorkflow()
    setError('')
  }

  function selectDeletedObject(item) {
    setSelected(item)
    setNewName(
      clean(
        getField(
          item,
          'last_known_rdn',
          'lastKnownRdn',
          'name'
        )
      )
    )
    setTargetPath(
      clean(
        getField(
          item,
          'last_known_parent',
          'lastKnownParent'
        )
      )
    )
    resetWorkflow()
  }

  async function loadDeletedObjects() {
    if (busyAction) return

    setBusyAction('inventory')
    setError('')

    try {
      const created = await apiFetch(
        '/api/ad-explorer/jobs',
        {
          method: 'POST',
          body: JSON.stringify({
            action: 'get_deleted_objects',
          }),
        }
      )

      const jobId = clean(created?.job?.id)

      if (!jobId) {
        throw new Error(
          'Le job d’inventaire ne contient aucun identifiant.'
        )
      }

      const finalJob =
        await pollAdExplorerJob(jobId)

      if (
        finalJob?.status !== 'completed'
        || finalJob?.success !== true
      ) {
        throw new Error(
          finalJob?.message
          || 'Inventaire des objets supprimés en erreur.'
        )
      }

      const result = finalJob?.result || {}
      const nextItems = Array.isArray(result?.items)
        ? result.items
        : []

      setItems(nextItems)
      setRecycleBin(result?.recycle_bin || null)
      setInventoryLoaded(true)
      setSelected(null)
      resetWorkflow()
    } catch (caught) {
      setError(
        caught?.message
        || 'Chargement de la corbeille impossible.'
      )
    } finally {
      setBusyAction('')
    }
  }

  async function runPreflight(boundLiveJobId = '') {
    if (!guid) {
      throw new Error(
        'GUID de l’objet supprimé introuvable.'
      )
    }

    return apiFetch(
      '/api/ad-explorer/deleted-objects/preflight',
      {
        method: 'POST',
        body: JSON.stringify({
          object_guid: guid,
          new_name: clean(newName) || null,
          target_path: clean(targetPath) || null,
          live_job_id:
            clean(boundLiveJobId) || null,
        }),
      }
    )
  }

  async function evaluateEligibility() {
    if (busyAction || !selected) return

    setBusyAction('preflight')
    setError('')
    setSimulation(null)

    try {
      const result = await runPreflight()

      setPreflight(result)
      setLiveJobId(
        clean(result?.live_job_id)
      )
      setLiveResult(null)
    } catch (caught) {
      setError(
        caught?.message
        || 'Évaluation d’éligibilité impossible.'
      )
    } finally {
      setBusyAction('')
    }
  }

  async function runLiveRevalidation() {
    if (busyAction || !selected || !guid) return

    setBusyAction('revalidation')
    setError('')
    setSimulation(null)

    try {
      const created = await apiFetch(
        '/api/ad-explorer/jobs',
        {
          method: 'POST',
          body: JSON.stringify({
            action:
              'revalidate_deleted_object_preflight',
            query: guid,
            filters: {
              new_name: clean(newName),
              target_path: clean(targetPath),
            },
          }),
        }
      )

      const jobId = clean(created?.job?.id)

      if (!jobId) {
        throw new Error(
          'La revalidation ne contient aucun job ID.'
        )
      }

      const finalJob =
        await pollAdExplorerJob(jobId)

      if (
        finalJob?.status !== 'completed'
        || finalJob?.success !== true
      ) {
        throw new Error(
          finalJob?.message
          || 'Revalidation Windows en erreur.'
        )
      }

      setLiveJobId(jobId)
      setLiveResult(finalJob?.result || null)

      const freshPreflight =
        await runPreflight(jobId)

      setPreflight(freshPreflight)
    } catch (caught) {
      setError(
        caught?.message
        || 'Revalidation Windows impossible.'
      )
    } finally {
      setBusyAction('')
    }
  }

  async function prepareSimulation() {
    if (
      busyAction
      || !selected
      || !eligible
      || !liveReady
      || !liveJobId
      || !canManageActiveDirectory
    ) {
      return
    }

    setBusyAction('simulation')
    setError('')
    resetSensitiveWorkflow()

    try {
      const result = await apiFetch(
        '/api/ad-explorer/deleted-objects/'
          + 'restore-simulation/prepare',
        {
          method: 'POST',
          body: JSON.stringify({
            object_guid: guid,
            new_name: clean(newName) || null,
            target_path:
              clean(targetPath) || null,
            live_job_id: liveJobId,
          }),
        }
      )

      setSimulation(result)
    } catch (caught) {
      setError(
        caught?.message
        || 'Préparation de la Simulation impossible.'
      )
    } finally {
      setBusyAction('')
    }
  }

  async function runChallengeRevalidation() {
    if (
      busyAction
      || !simulationJobId
      || !selected
      || !guid
      || !canManageActiveDirectory
    ) {
      return
    }

    setBusyAction('challenge-revalidation')
    setError('')
    setChallengeLiveJobId('')
    setChallengeLiveResult(null)
    setChallenge(null)
    setAuthorization(null)
    setPostAuthLiveJobId('')
    setPostAuthLiveResult(null)
    setPostAuthorization(null)

    try {
      const created = await apiFetch(
        '/api/ad-explorer/jobs',
        {
          method: 'POST',
          body: JSON.stringify({
            action:
              'revalidate_deleted_object_preflight',
            query: guid,
            filters: {
              new_name: clean(newName),
              target_path: clean(targetPath),
            },
          }),
        }
      )

      const jobId = clean(created?.job?.id)

      if (!jobId) {
        throw new Error(
          'La revalidation post-Simulation ne contient aucun job ID.'
        )
      }

      const finalJob =
        await pollAdExplorerJob(jobId)

      if (
        finalJob?.status !== 'completed'
        || finalJob?.success !== true
      ) {
        throw new Error(
          finalJob?.message
          || 'Revalidation post-Simulation en erreur.'
        )
      }

      setChallengeLiveJobId(jobId)
      setChallengeLiveResult(
        finalJob?.result || {}
      )
    } catch (caught) {
      setError(
        caught?.message
        || 'Revalidation post-Simulation impossible.'
      )
    } finally {
      setBusyAction('')
    }
  }

  async function createHumanChallenge() {
    if (
      busyAction
      || !simulationJobId
      || !challengeLiveReady
      || !challengeLiveJobId
      || !canManageActiveDirectory
    ) {
      return
    }

    setBusyAction('challenge')
    setError('')
    setChallenge(null)
    setAuthorization(null)
    setPostAuthLiveJobId('')
    setPostAuthLiveResult(null)
    setPostAuthorization(null)

    try {
      const result = await apiFetch(
        '/api/ad-admin/deleted-object-restore/'
          + 'ticket-challenge',
        {
          method: 'POST',
          body: JSON.stringify({
            simulation_job_id: simulationJobId,
            fresh_live_job_id:
              challengeLiveJobId,
          }),
        }
      )

      if (
        !clean(result?.ticket_id)
        || !clean(result?.ticket_digest)
        || !clean(result?.consumption_id)
        || !clean(result?.object_guid)
        || !clean(result?.effective_new_name)
        || !clean(result?.effective_target_path)
      ) {
        throw new Error(
          'Le challenge humain est incomplet.'
        )
      }

      if (
        result?.runtime_authorized !== false
        || result?.production_authorized !== false
        || result?.restore_authorized !== false
        || result?.execution_authorized !== false
        || result?.write_performed !== false
      ) {
        throw new Error(
          'Le challenge a retourné un état de sécurité inattendu.'
        )
      }

      setChallenge(result)
      setConfirmObject('')
      setConfirmTarget('')
      setAcknowledgeWrite(false)
      setAuthorizationReason('')
    } catch (caught) {
      setError(
        caught?.message
        || 'Création du challenge humain impossible.'
      )
    } finally {
      setBusyAction('')
    }
  }

  async function createHumanAuthorization() {
    if (isTimestampExpired(challengeExpiresAt)) {
      setError(
        'Challenge humain expiré. Préparez une nouvelle '
        + 'Simulation puis une nouvelle revalidation '
        + 'post-Simulation.'
      )
      return
    }

    if (
      busyAction
      || !humanConfirmationReady
      || !canManageActiveDirectory
    ) {
      return
    }

    setBusyAction('authorization')
    setError('')
    setAuthorization(null)
    setPostAuthLiveJobId('')
    setPostAuthLiveResult(null)
    setPostAuthorization(null)

    try {
      const result = await apiFetch(
        '/api/ad-admin/deleted-object-restore/'
          + 'authorization',
        {
          method: 'POST',
          body: JSON.stringify({
            ticket_id: challenge.ticket_id,
            ticket_digest: challenge.ticket_digest,
            consumption_id: challenge.consumption_id,
            object_guid: challenge.object_guid,
            effective_new_name:
              challenge.effective_new_name,
            effective_target_path:
              challenge.effective_target_path,
            acknowledge_exact_object: true,
            acknowledge_exact_target: true,
            acknowledge_restore_write: true,
            authorization_reason:
              clean(authorizationReason),
          }),
        }
      )

      if (
        result?.human_authorized !== true
        || result?.authorization_consumed !== false
        || result?.runtime_authorized !== false
        || result?.production_authorized !== false
        || result?.restore_authorized !== false
        || result?.execution_authorized !== false
        || result?.write_performed !== false
        || !clean(result?.authorization_id)
        || !clean(result?.authorization_digest)
      ) {
        throw new Error(
          'L’autorisation humaine a retourné un état inattendu.'
        )
      }

      setAuthorization(result)
    } catch (caught) {
      setError(
        caught?.message
        || 'Autorisation humaine impossible.'
      )
    } finally {
      setBusyAction('')
    }
  }

  async function runPostAuthorizationRevalidation() {
    if (
      busyAction
      || !authorizationReady
      || !canManageActiveDirectory
    ) {
      return
    }

    setBusyAction('post-auth-revalidation')
    setError('')
    setPostAuthLiveJobId('')
    setPostAuthLiveResult(null)
    setPostAuthorization(null)

    try {
      const created = await apiFetch(
        '/api/ad-explorer/jobs',
        {
          method: 'POST',
          body: JSON.stringify({
            action:
              'revalidate_deleted_object_preflight',
            query: challenge.object_guid,
            filters: {
              new_name:
                challenge.effective_new_name,
              target_path:
                challenge.effective_target_path,
            },
          }),
        }
      )

      const jobId = clean(created?.job?.id)

      if (!jobId) {
        throw new Error(
          'La seconde revalidation ne contient aucun job ID.'
        )
      }

      if (
        jobId
        === clean(authorization?.fresh_live_job_id)
      ) {
        throw new Error(
          'La preuve live post-autorisation doit être nouvelle.'
        )
      }

      const finalJob =
        await pollAdExplorerJob(jobId)

      if (
        finalJob?.status !== 'completed'
        || finalJob?.success !== true
      ) {
        throw new Error(
          finalJob?.message
          || 'Seconde revalidation Windows en erreur.'
        )
      }

      setPostAuthLiveJobId(jobId)
      setPostAuthLiveResult(
        finalJob?.result || {}
      )
    } catch (caught) {
      setError(
        caught?.message
        || 'Seconde revalidation Windows impossible.'
      )
    } finally {
      setBusyAction('')
    }
  }

  async function preparePostAuthorization() {
    if (
      busyAction
      || !postAuthLiveReady
      || !canManageActiveDirectory
    ) {
      return
    }

    setBusyAction('post-authorization')
    setError('')
    setPostAuthorization(null)

    try {
      const result = await apiFetch(
        '/api/ad-admin/deleted-object-restore/'
          + 'post-authorization',
        {
          method: 'POST',
          body: JSON.stringify({
            authorization_id:
              authorization.authorization_id,
            authorization_digest:
              authorization.authorization_digest,
            fresh_live_job_id:
              postAuthLiveJobId,
          }),
        }
      )

      if (
        result?.human_authorized !== true
        || result?.revalidation_passed !== true
        || result?.authorization_consumed !== true
        || result?.execution_ticket_consumed !== true
        || result?.runtime_authorized !== false
        || result?.production_authorized !== false
        || result?.restore_authorized !== false
        || result?.execution_authorized !== false
        || result?.write_performed !== false
        || !clean(result?.execution_consumption_id)
        || !clean(result?.confirmation_text)
      ) {
        throw new Error(
          'La post-autorisation a retourné un état inattendu.'
        )
      }

      setPostAuthorization(result)
    } catch (caught) {
      setError(
        caught?.message
        || 'Préparation post-autorisation impossible.'
      )
    } finally {
      setBusyAction('')
    }
  }

  return (
    <section className="aduc-deleted-restore">
      <header className="aduc-deleted-restore-head">
        <div>
          <span className="aduc-deleted-restore-eyebrow">
            Corbeille Active Directory
          </span>

          <h3>Objets supprimés et restauration</h3>

          <p>
            Inventaire, éligibilité et Simulation
            contrôlée. Aucun changement de mode ni
            aucune restauration réelle automatique.
          </p>
        </div>

        <button
          type="button"
          onClick={loadDeletedObjects}
          disabled={Boolean(busyAction)}
        >
          {busyAction === 'inventory'
            ? 'Inventaire Windows…'
            : 'Actualiser la corbeille'}
        </button>
      </header>

      <div className="aduc-deleted-restore-safety">
        <strong>
          Chaîne fail-closed
        </strong>

        <span>
          L’inventaire, le preflight et la
          revalidation restent en lecture seule.
          La Simulation ne constitue jamais une
          autorisation d’écriture.
        </span>
      </div>

      {recycleBin && (
        <div className="aduc-deleted-restore-meta">
          <span>Corbeille AD</span>
          <strong>
            {recycleBin?.enabled === true
              ? 'Activée'
              : 'Non confirmée'}
          </strong>
        </div>
      )}

      {error && (
        <div className="aduc-deleted-restore-error">
          {error}
        </div>
      )}

      {!inventoryLoaded && (
        <div className="aduc-deleted-restore-empty">
          Chargez l’inventaire Windows pour afficher
          les objets supprimés.
        </div>
      )}

      {inventoryLoaded && items.length === 0 && (
        <div className="aduc-deleted-restore-empty">
          Aucun objet supprimé disponible dans le
          dernier inventaire.
        </div>
      )}

      {items.length > 0 && (
        <div className="aduc-deleted-restore-list">
          {items.map((item, index) => {
            const itemGuid = getObjectGuid(item)
            const itemName =
              getObjectName(item) || 'Objet supprimé'

            return (
              <button
                type="button"
                key={itemGuid || index}
                className={
                  itemGuid === guid
                    ? 'selected'
                    : ''
                }
                onClick={() =>
                  selectDeletedObject(item)
                }
              >
                <strong>{itemName}</strong>
                <span>
                  {getObjectClass(item) || 'Objet AD'}
                </span>
                <code>{itemGuid || 'GUID inconnu'}</code>
              </button>
            )
          })}
        </div>
      )}

      {selected && (
        <div className="aduc-deleted-restore-workflow">
          <div className="aduc-deleted-restore-target">
            <div>
              <span>GUID immuable</span>
              <code>{guid || '—'}</code>
            </div>

            <label>
              <span>Nom restauré</span>
              <input
                value={newName}
                onChange={event => {
                  setNewName(event.target.value)
                  resetWorkflow()
                }}
                disabled={Boolean(busyAction)}
              />
            </label>

            <label>
              <span>OU / parent cible</span>
              <input
                value={targetPath}
                onChange={event => {
                  setTargetPath(event.target.value)
                  resetWorkflow()
                }}
                disabled={Boolean(busyAction)}
              />
            </label>
          </div>

          <div className="aduc-deleted-restore-actions">
            <button
              type="button"
              onClick={evaluateEligibility}
              disabled={Boolean(busyAction)}
            >
              {busyAction === 'preflight'
                ? 'Évaluation…'
                : 'Évaluer l’éligibilité'}
            </button>

            {preflight && !liveReady && (
              <button
                type="button"
                onClick={runLiveRevalidation}
                disabled={Boolean(busyAction)}
              >
                {busyAction === 'revalidation'
                  ? 'Revalidation Windows…'
                  : 'Revalider sur Windows'}
              </button>
            )}
          </div>

          {preflight && (
            <div
              className={
                'aduc-deleted-restore-decision '
                + (eligible ? 'eligible' : 'blocked')
              }
            >
              <span>Décision du preflight</span>
              <strong>{decisionLabel}</strong>

              <code>
                {decision || 'decision_absente'}
              </code>

              {policyReason && (
                <small>{policyReason}</small>
              )}

              <div>
                <span>
                  live_revalidation_performed ={' '}
                  {String(
                    preflight
                      ?.live_revalidation_performed
                    === true
                  )}
                </span>

                <span>
                  execution_authorized ={' '}
                  {String(
                    preflight
                      ?.execution_authorized
                    === true
                  )}
                </span>

                <span>
                  write_authorized ={' '}
                  {String(
                    preflight?.write_authorized
                    === true
                  )}
                </span>
              </div>
            </div>
          )}

          {liveResult && (
            <div className="aduc-deleted-restore-live">
              <strong>
                Revalidation Windows terminée
              </strong>

              <span>
                Objet confirmé :{' '}
                {liveResult?.object_found === true
                  ? 'oui'
                  : 'non'}
              </span>

              <span>
                Parent présent :{' '}
                {liveResult?.parent_exists === true
                  ? 'oui'
                  : 'non'}
              </span>

              <span>
                Collision cible :{' '}
                {liveResult?.target_collision === true
                  ? 'oui'
                  : 'non'}
              </span>
            </div>
          )}

          {eligible && liveReady && (
            <div className="aduc-deleted-restore-simulation">
              <div>
                <strong>
                  Simulation contrôlée disponible
                </strong>

                <span>
                  Cette étape prépare uniquement le
                  dossier de Simulation C9.5.
                </span>
              </div>

              <button
                type="button"
                onClick={prepareSimulation}
                disabled={
                  Boolean(busyAction)
                  || !canManageActiveDirectory
                }
              >
                {busyAction === 'simulation'
                  ? 'Préparation…'
                  : 'Préparer la Simulation'}
              </button>

              {!canManageActiveDirectory && (
                <small>
                  Droits de gestion Active Directory
                  requis.
                </small>
              )}
            </div>
          )}

          {simulation && (
            <div className="aduc-deleted-restore-result">
              <strong>
                Simulation préparée
              </strong>

              <span>
                Job :{' '}
                <code>
                  {simulation?.job?.id || '—'}
                </code>
              </span>

              <span>
                Mode :{' '}
                <b>
                  {simulationPayload?.mode
                    || 'Simulation'}
                </b>
              </span>

              <span>
                write_authorized ={' '}
                <b>
                  {String(
                    simulationPayload
                      ?.write_authorized
                    === true
                  )}
                </b>
              </span>

              <span>
                restore_performed ={' '}
                <b>
                  {String(
                    simulationPayload
                      ?.restore_performed
                    === true
                  )}
                </b>
              </span>
            </div>
          )}

          {simulation && (
            <div className="aduc-deleted-restore-sensitive">
              <div className="aduc-deleted-restore-sensitive-head">
                <div>
                  <strong>
                    Autorisation humaine C9.5
                  </strong>

                  <span>
                    Cette chaîne crée des preuves
                    éphémères et anti-rejeu, mais
                    n’exécute aucune restauration.
                  </span>
                </div>

                {!challengeLiveReady && (
                  <button
                    type="button"
                    onClick={runChallengeRevalidation}
                    disabled={
                      Boolean(busyAction)
                      || !canManageActiveDirectory
                    }
                  >
                    {
                      busyAction
                      === 'challenge-revalidation'
                        ? 'Revalidation post-Simulation…'
                        : 'Revalider après Simulation'
                    }
                  </button>
                )}

                {
                  challengeLiveReady
                  && !challenge
                  && (
                    <button
                      type="button"
                      onClick={createHumanChallenge}
                      disabled={
                        Boolean(busyAction)
                        || !canManageActiveDirectory
                      }
                    >
                      {busyAction === 'challenge'
                        ? 'Création du challenge…'
                        : 'Créer le challenge humain'}
                    </button>
                  )
                }
              </div>

              {challengeLiveResult && (
                <div className="aduc-deleted-restore-live">
                  <strong>
                    Revalidation post-Simulation terminée
                  </strong>

                  <span>
                    Job :{' '}
                    <code>{challengeLiveJobId}</code>
                  </span>

                  <span>
                    Objet confirmé :{' '}
                    {challengeLiveResult?.object_found === true
                      ? 'oui'
                      : 'non'}
                  </span>

                  <span>
                    Parent présent :{' '}
                    {challengeLiveResult?.parent_exists === true
                      ? 'oui'
                      : 'non'}
                  </span>

                  <span>
                    Collision cible :{' '}
                    {challengeLiveResult?.target_collision === true
                      ? 'oui'
                      : 'non'}
                  </span>

                  <small>
                    Cette preuve a été créée après la
                    Simulation et peut être utilisée
                    pour le challenge humain.
                  </small>
                </div>
              )}

              {challenge && (
                <div className="aduc-deleted-restore-challenge">
                  <div className="aduc-deleted-restore-proof-grid">
                    <div>
                      <span>Ticket</span>
                      <code>{challenge.ticket_id}</code>
                    </div>

                    <div>
                      <span>GUID exact</span>
                      <code>{challenge.object_guid}</code>
                    </div>

                    <div>
                      <span>Nom exact</span>
                      <code>
                        {challenge.effective_new_name}
                      </code>
                    </div>

                    <div>
                      <span>Cible exacte</span>
                      <code>
                        {challenge.effective_target_path}
                      </code>
                    </div>
                  </div>

                  <div className="aduc-deleted-restore-expiry">
                    <strong>
                      Challenge valable 2 minutes
                    </strong>

                    <span>
                      Expiration :{' '}
                      <code>
                        {formatTimestamp(
                          challengeExpiresAt
                        )}
                      </code>
                    </span>

                    {challengeExpired && (
                      <b>
                        Challenge expiré — autorisation
                        bloquée localement.
                      </b>
                    )}

                    <small>
                      En cas d’expiration, ne réutilisez
                      pas ce ticket : préparez une nouvelle
                      Simulation puis une nouvelle preuve
                      Windows post-Simulation.
                    </small>
                  </div>

                  {!authorization && (
                    <>
                      <div className="aduc-deleted-restore-confirm">
                        <label>
                          <span>
                            Recopiez exactement le GUID
                          </span>

                          <input
                            value={confirmObject}
                            onChange={event =>
                              setConfirmObject(
                                event.target.value
                              )
                            }
                            autoComplete="off"
                            disabled={Boolean(busyAction)}
                          />

                          <small>
                            {exactObjectConfirmed
                              ? 'GUID confirmé'
                              : 'Confirmation requise'}
                          </small>
                        </label>

                        <label>
                          <span>
                            Recopiez exactement le DN cible
                          </span>

                          <input
                            value={confirmTarget}
                            onChange={event =>
                              setConfirmTarget(
                                event.target.value
                              )
                            }
                            autoComplete="off"
                            disabled={Boolean(busyAction)}
                          />

                          <small>
                            {exactTargetConfirmed
                              ? 'Cible confirmée'
                              : 'Confirmation requise'}
                          </small>
                        </label>

                        <label>
                          <span>
                            Justification
                          </span>

                          <textarea
                            value={authorizationReason}
                            minLength={8}
                            maxLength={512}
                            onChange={event =>
                              setAuthorizationReason(
                                event.target.value
                              )
                            }
                            disabled={Boolean(busyAction)}
                            placeholder={
                              'Justification de la restauration contrôlée'
                            }
                          />

                          <small>
                            8 à 512 caractères
                          </small>
                        </label>

                        <label className="aduc-deleted-restore-check">
                          <input
                            type="checkbox"
                            checked={acknowledgeWrite}
                            onChange={event =>
                              setAcknowledgeWrite(
                                event.target.checked
                              )
                            }
                            disabled={Boolean(busyAction)}
                          />

                          <span>
                            Je confirme que cette opération
                            prépare une restauration pouvant
                            entraîner une écriture Active
                            Directory lors d’une étape finale
                            distincte.
                          </span>
                        </label>
                      </div>

                      <button
                        type="button"
                        onClick={createHumanAuthorization}
                        disabled={
                          Boolean(busyAction)
                          || !humanConfirmationReady
                          || !canManageActiveDirectory
                        }
                      >
                        {busyAction === 'authorization'
                          ? 'Autorisation…'
                          : 'Autoriser cet objet et cette cible'}
                      </button>
                    </>
                  )}
                </div>
              )}

              {authorization && (
                <div className="aduc-deleted-restore-authorization">
                  <strong>
                    Autorisation humaine créée
                  </strong>

                  <span>
                    ID :{' '}
                    <code>
                      {authorization.authorization_id}
                    </code>
                  </span>

                  <span>
                    Expiration :{' '}
                    <code>
                      {authorization.expires_at || '—'}
                    </code>
                  </span>

                  <div className="aduc-deleted-restore-invariants">
                    <span>
                      human_authorized = true
                    </span>
                    <span>
                      authorization_consumed = false
                    </span>
                    <span>
                      production_authorized = false
                    </span>
                    <span>
                      restore_authorized = false
                    </span>
                    <span>
                      execution_authorized = false
                    </span>
                    <span>
                      write_performed = false
                    </span>
                  </div>

                  {!postAuthLiveResult && (
                    <button
                      type="button"
                      onClick={
                        runPostAuthorizationRevalidation
                      }
                      disabled={
                        Boolean(busyAction)
                        || !canManageActiveDirectory
                      }
                    >
                      {
                        busyAction
                        === 'post-auth-revalidation'
                          ? 'Nouvelle revalidation Windows…'
                          : 'Revalider après autorisation'
                      }
                    </button>
                  )}
                </div>
              )}

              {postAuthLiveResult && (
                <div className="aduc-deleted-restore-live">
                  <strong>
                    Nouvelle preuve Windows obtenue
                  </strong>

                  <span>
                    Job :{' '}
                    <code>{postAuthLiveJobId}</code>
                  </span>

                  <span>
                    Preuve différente de celle ayant
                    servi à l’autorisation.
                  </span>

                  {!postAuthorization && (
                    <button
                      type="button"
                      onClick={preparePostAuthorization}
                      disabled={
                        Boolean(busyAction)
                        || !postAuthLiveReady
                        || !canManageActiveDirectory
                      }
                    >
                      {
                        busyAction
                        === 'post-authorization'
                          ? 'Préparation des preuves…'
                          : 'Préparer la confirmation finale'
                      }
                    </button>
                  )}
                </div>
              )}

              {postAuthorization && (
                <div className="aduc-deleted-restore-final-proof">
                  <strong>
                    Chaîne prête pour confirmation finale
                  </strong>

                  <span>
                    Execution consumption :
                  </span>

                  <code>
                    {
                      postAuthorization
                        .execution_consumption_id
                    }
                  </code>

                  <span>
                    Texte exact requis :
                  </span>

                  <code className="aduc-deleted-restore-confirmation-text">
                    {postAuthorization.confirmation_text}
                  </code>

                  <div className="aduc-deleted-restore-invariants">
                    <span>
                      human_authorized = true
                    </span>
                    <span>
                      revalidation_passed = true
                    </span>
                    <span>
                      authorization_consumed = true
                    </span>
                    <span>
                      execution_ticket_consumed = true
                    </span>
                    <span>
                      production_authorized = false
                    </span>
                    <span>
                      restore_authorized = false
                    </span>
                    <span>
                      execution_authorized = false
                    </span>
                    <span>
                      write_performed = false
                    </span>
                  </div>

                  <div className="aduc-deleted-restore-no-queue">
                    <strong>
                      Exécution toujours verrouillée
                    </strong>

                    <span>
                      Aucune mise en file d’exécution
                      réelle n’est disponible dans
                      cette étape.
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="aduc-deleted-restore-real-lock">
            <strong>
              Restauration réelle verrouillée
            </strong>

            <span>
              Aucune mise en file d’exécution réelle
              n’est déclenchée par ce panneau. La
              chaîne sensible C9.5 exige une
              confirmation humaine distincte et reste
              fermée par défaut.
            </span>
          </div>
        </div>
      )}
    </section>
  )
}
