import {
  useEffect,
  useRef,
} from 'react'

import {
  HAB_MAXIMUM_VALUE,
  HAB_MINIMUM_VALUE,
} from '../utils/habSenioritySimulation'

function formatCurrentValue(value) {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return 'Non défini'
  }

  return String(value)
}

function getJobStatusLabel(job) {
  if (!job) {
    return ''
  }

  if (
    job.status === 'completed' &&
    job.success !== false
  ) {
    return 'Simulation terminée'
  }

  if (
    job.status === 'failed' ||
    job.success === false
  ) {
    return 'Simulation en erreur'
  }

  return 'Simulation en cours'
}

function getJobResultText(job) {
  const result =
    job?.result ??
    job?.details ??
    job?.output

  if (
    result === null ||
    result === undefined ||
    result === ''
  ) {
    return ''
  }

  if (typeof result === 'object') {
    return JSON.stringify(
      result,
      null,
      2
    )
  }

  return String(result).trim()
}

function formatPreviewOperation(preview) {
  if (!preview) {
    return ''
  }

  if (preview.operation === 'clear') {
    return 'Suppression de la valeur'
  }

  return `Définition à ${preview.value}`
}

function HabSenioritySimulationEditor({
  editor,
}) {
  const resultRef = useRef(null)

  const preview =
    editor?.validationIsCurrent
      ? editor.validatedPreview
      : null

  const submittedJob =
    editor?.submittedJob || null

  const resultText =
    getJobResultText(submittedJob)

  useEffect(() => {
    if (
      !submittedJob ||
      !resultRef.current
    ) {
      return
    }

    resultRef.current.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
  }, [submittedJob])

  async function handleSubmit() {
    if (
      !preview ||
      editor?.validating ||
      editor?.submitting
    ) {
      return
    }

    const operationLabel =
      preview.operation === 'clear'
        ? 'Supprimer la valeur actuelle'
        : `Définir la valeur à ${preview.value}`

    const confirmed = window.confirm(
      'Créer un job HAB de simulation ?'
      + `\n\nCible : ${preview.object_identity}`
      + `\nOpération : ${operationLabel}`
      + '\n\nAucune écriture réelle ne sera '
      + 'effectuée dans Active Directory.'
    )

    if (!confirmed) {
      return
    }

    await editor.submitSimulation()
  }

  return (
    <section className="aduc-hab-editor">
      <header className="aduc-hab-editor-header">
        <div>
          <h4>
            Simulation HAB Seniority Index
          </h4>

          <p>
            Attribut Active Directory
            {' '}
            <code>
              msDS-HABSeniorityIndex
            </code>
          </p>
        </div>

        <strong className="simulation">
          Mode {editor?.agentMode || 'Inconnu'}
        </strong>
      </header>

      <div className="aduc-hab-editor-safety">
        <strong>
          Simulation uniquement
        </strong>

        <span>
          Ce contrôle ne dispose d’aucun chemin
          Production et n’autorise aucune écriture
          réelle dans Active Directory.
        </span>
      </div>

      <div className="aduc-hab-current-value">
        <span>Valeur actuelle</span>

        <strong>
          {formatCurrentValue(
            editor?.currentValue
          )}
        </strong>
      </div>

      {!editor?.eligible && (
        <div
          className="aduc-hab-editor-error"
          role="alert"
        >
          {editor?.eligibilityReason ||
            'La simulation HAB est indisponible.'}
        </div>
      )}

      {editor?.error && (
        <div
          className="aduc-hab-editor-error"
          role="alert"
        >
          {editor.error}
        </div>
      )}

      <div className="aduc-hab-editor-form">
        <label>
          <span>Opération</span>

          <select
            value={editor?.operation || 'set'}
            disabled={
              editor?.validating ||
              editor?.submitting
            }
            onChange={event =>
              editor?.updateOperation?.(
                event.target.value
              )
            }
          >
            <option value="set">
              Définir la valeur
            </option>

            <option value="clear">
              Supprimer la valeur
            </option>
          </select>
        </label>

        <label>
          <span>
            Valeur Integer32
          </span>

          <input
            type="number"
            min={HAB_MINIMUM_VALUE}
            max={HAB_MAXIMUM_VALUE}
            step="1"
            value={editor?.value ?? ''}
            disabled={
              editor?.operation === 'clear' ||
              editor?.validating ||
              editor?.submitting
            }
            placeholder="0"
            onChange={event =>
              editor?.updateValue?.(
                event.target.value
              )
            }
          />

          <small>
            Valeur autorisée de
            {' '}
            {HAB_MINIMUM_VALUE}
            {' '}
            à
            {' '}
            {HAB_MAXIMUM_VALUE}.
          </small>
        </label>

        <button
          type="button"
          onClick={() =>
            editor?.validateDraft?.()
          }
          disabled={
            !editor?.eligible ||
            editor?.validating ||
            editor?.submitting ||
            Boolean(editor?.payloadError)
          }
        >
          {editor?.validating
            ? 'Validation...'
            : 'Valider l’aperçu'}
        </button>
      </div>

      {preview && (
        <section className="aduc-hab-preview">
          <header>
            <strong>
              Aperçu HAB validé
            </strong>

            <span>
              {preview.value_type}
            </span>
          </header>

          <dl>
            <div>
              <dt>Cible</dt>
              <dd>
                {preview.object_identity}
              </dd>
            </div>

            <div>
              <dt>Attribut</dt>
              <dd>
                {preview.attribute_name}
              </dd>
            </div>

            <div>
              <dt>Opération</dt>
              <dd>
                {formatPreviewOperation(
                  preview
                )}
              </dd>
            </div>

            <div>
              <dt>Politique</dt>
              <dd>
                Simulation uniquement
              </dd>
            </div>
          </dl>

          <button
            type="button"
            className="aduc-properties-edit-button"
            onClick={handleSubmit}
            disabled={
              editor?.validating ||
              editor?.submitting ||
              !editor?.validationIsCurrent
            }
          >
            {editor?.submitting
              ? 'Simulation en cours...'
              : 'Créer le job de simulation'}
          </button>
        </section>
      )}

      {editor?.submissionStatus && (
        <div
          className="aduc-hab-editor-status"
          role="status"
        >
          {editor.submissionStatus}
        </div>
      )}

      {submittedJob && (
        <section
          ref={resultRef}
          className="aduc-hab-result"
        >
          <header>
            <strong>
              {getJobStatusLabel(
                submittedJob
              )}
            </strong>

            <span>
              {submittedJob.id || ''}
            </span>
          </header>

          {resultText && (
            <pre>{resultText}</pre>
          )}
        </section>
      )}
    </section>
  )
}

export default HabSenioritySimulationEditor
