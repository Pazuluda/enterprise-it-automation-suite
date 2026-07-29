function formatPreviewValue(value) {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return '—'
  }

  return String(value)
}

function getSimulationStatusLabel(job) {
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

function getSimulationResultText(job) {
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

function LdapAttributeEditor({
  editor,
}) {
  const draft = Array.isArray(
    editor?.draft
  )
    ? editor.draft
    : []

  const resultText =
    getSimulationResultText(
      editor?.submittedJob
    )

  async function handleSimulationSubmit() {
    if (
      !editor?.preview ||
      !editor?.isSimulationMode ||
      editor?.submitting
    ) {
      return
    }

    const target =
      editor.preview.payload.object_identity

    const confirmed = window.confirm(
      'Créer un job LDAP de simulation ?'
      + `\n\nCible : ${target}`
      + `\nChangements : ${editor.changeCount}`
      + '\n\nAucune écriture réelle ne sera '
      + 'effectuée dans Active Directory.'
    )

    if (!confirmed) {
      return
    }

    await editor.submitSimulation()
  }

  return (
    <section className="aduc-ldap-editor">
      <header className="aduc-ldap-editor-header">
        <div>
          <span>Éditeur contrôlé C2</span>

          <h4>Attributs LDAP avancés</h4>

          <p>
            Seuls les attributs explicitement
            autorisés par EITAS sont disponibles.
          </p>
        </div>

        <strong
          className={
            editor?.isSimulationMode
              ? 'simulation'
              : 'locked'
          }
        >
          Mode {editor?.agentMode || 'Inconnu'}
        </strong>
      </header>

      <div className="aduc-ldap-editor-safety">
        <strong>
          Exécution strictement contrôlée
        </strong>

        <span>
          La création du job est autorisée
          uniquement en mode Simulation.
          Le backend vérifie à nouveau le mode
          avant toute création.
        </span>
      </div>

      {editor?.error && (
        <div
          className="aduc-ldap-editor-error"
          role="alert"
        >
          {editor.error}
        </div>
      )}

      <div className="aduc-ldap-editor-grid">
        {draft.map(entry => {
          const isSet =
            entry.operation === 'set'

          const isComment =
            entry.attribute_name ===
            'comment'

          return (
            <article
              key={entry.attribute_name}
              className="aduc-ldap-editor-field"
            >
              <div className="aduc-ldap-editor-field-title">
                <div>
                  <strong>
                    {entry.label}
                  </strong>

                  <code>
                    {entry.attribute_name}
                  </code>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    editor.resetAttribute(
                      entry.attribute_name
                    )
                  }
                  disabled={
                    editor?.submitting ||
                    entry.operation ===
                    'unchanged'
                  }
                >
                  Réinitialiser
                </button>
              </div>

              <label>
                <span>Opération</span>

                <select
                  value={entry.operation}
                  disabled={editor?.submitting}
                  onChange={event =>
                    editor.updateDraft(
                      entry.attribute_name,
                      {
                        operation:
                          event.target.value,
                      }
                    )
                  }
                >
                  <option value="unchanged">
                    Ne pas modifier
                  </option>

                  <option value="set">
                    Définir la valeur
                  </option>

                  <option value="clear">
                    Supprimer l’attribut
                  </option>
                </select>
              </label>

              <label>
                <span>Valeur</span>

                {isComment ? (
                  <textarea
                    value={entry.value}
                    maxLength={
                      entry.max_length
                    }
                    disabled={
                      editor?.submitting ||
                      !isSet
                    }
                    onChange={event =>
                      editor.updateDraft(
                        entry.attribute_name,
                        {
                          value:
                            event.target.value,
                        }
                      )
                    }
                  />
                ) : (
                  <input
                    type="text"
                    value={entry.value}
                    maxLength={
                      entry.max_length
                    }
                    disabled={
                      editor?.submitting ||
                      !isSet
                    }
                    onChange={event =>
                      editor.updateDraft(
                        entry.attribute_name,
                        {
                          value:
                            event.target.value,
                        }
                      )
                    }
                  />
                )}

                <small>
                  {String(
                    entry.value || ''
                  ).length}
                  {' / '}
                  {entry.max_length}
                  {' caractères'}
                </small>
              </label>

              <div className="aduc-ldap-editor-current">
                <span>Valeur actuelle</span>

                <strong>
                  {formatPreviewValue(
                    entry.original_value
                  )}
                </strong>
              </div>
            </article>
          )
        })}
      </div>

      <section className="aduc-ldap-editor-preview">
        <div>
          <span>Aperçu avant envoi</span>

          <strong>
            {editor?.changeCount || 0}
            {' changement(s)'}
          </strong>
        </div>

        {!editor?.preview ? (
          <p>
            Sélectionne une opération pour
            afficher le résultat attendu.
          </p>
        ) : (
          <div className="aduc-ldap-preview-list">
            {editor.preview.rows.map(row => (
              <article
                key={row.attribute_name}
              >
                <div>
                  <strong>{row.label}</strong>
                  <code>
                    {row.attribute_name}
                  </code>
                </div>

                <span>
                  {formatPreviewValue(
                    row.before
                  )}
                </span>

                <b aria-hidden="true">→</b>

                <span>
                  {formatPreviewValue(
                    row.after
                  )}
                </span>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="aduc-ldap-editor-submit">
        <div>
          <strong>
            Job de simulation LDAP
          </strong>

          {!editor?.isSimulationMode ? (
            <p>
              Indisponible en mode Production.
              Aucun job LDAP ne peut être créé.
            </p>
          ) : (
            <p>
              Une confirmation sera demandée
              avant la création du job.
            </p>
          )}
        </div>

        <button
          type="button"
          className="aduc-ldap-simulation-button"
          onClick={handleSimulationSubmit}
          disabled={
            !editor?.isSimulationMode ||
            !editor?.preview ||
            Boolean(editor?.error) ||
            editor?.submitting
          }
        >
          {editor?.submitting
            ? 'Simulation en cours...'
            : 'Créer le job de simulation'}
        </button>
      </section>

      {editor?.submissionStatus && (
        <div
          className="aduc-ldap-submission-status"
          role="status"
        >
          {editor.submissionStatus}
        </div>
      )}

      {editor?.submittedJob && (
        <section className="aduc-ldap-simulation-result">
          <div>
            <strong>
              {getSimulationStatusLabel(
                editor.submittedJob
              )}
            </strong>

            <code>
              {editor.submittedJob.id}
            </code>
          </div>

          {editor.submittedJob.message && (
            <p>
              {editor.submittedJob.message}
            </p>
          )}

          {resultText && (
            <pre>{resultText}</pre>
          )}
        </section>
      )}
    </section>
  )
}

export default LdapAttributeEditor
