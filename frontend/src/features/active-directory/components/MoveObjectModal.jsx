import {
  getObjectDn,
  getObjectName,
  getObjectType,
} from '../utils/adExplorerCore'

function MoveObjectModal({
  move,
}) {
  const {
    moveModal,
    closeMoveModal,
    adminLoading,
    submitMoveObject,
    getMoveCurrentParentDn,
    moveOuOptions,
    moveTargetDn,
    setMoveTargetDn,
    setMoveOuError,
    moveOuLoading,
    getMoveOuDisplayLabel,
    moveOuError,
    isAdProductionMode,
    getAdAgentModeLabel,
    adAgentModeLoading,
    getMoveValidationError,
  } = move

  if (!moveModal) return null

  return (
    <div
        className="aduc-modal-backdrop"
        onClick={closeMoveModal}
      >
        <section
          className="aduc-modal aduc-move-modal"
          onClick={event =>
            event.stopPropagation()
          }
        >
          <header>
            <div>
              <span>Active Directory</span>
              <h3>Déplacer l’objet</h3>
            </div>

            <button
              type="button"
              onClick={closeMoveModal}
              disabled={adminLoading}
            >
              ×
            </button>
          </header>

          <form onSubmit={submitMoveObject}>
            <div className="aduc-update-object-target">
              <div>
                <span>Objet cible</span>
                <strong>
                  {getObjectName(moveModal)}
                </strong>
              </div>

              <div>
                <span>Type</span>
                <strong>
                  {getObjectType(moveModal)}
                </strong>
              </div>

              <div className="wide">
                <span>DN actuel</span>
                <code>
                  {getObjectDn(moveModal)}
                </code>
              </div>

              <div className="wide">
                <span>OU actuelle</span>
                <code>
                  {getMoveCurrentParentDn(
                    getObjectDn(moveModal)
                  )}
                </code>
              </div>
            </div>

            <label className="aduc-account-action-field">
              <span>OU de destination</span>

              <select
                key={
                  moveOuOptions
                    .map(option => option.dn)
                    .join('|')
                  || 'move-ou-loading'
                }
                value={moveTargetDn}
                onChange={event => {
                  setMoveTargetDn(
                    event.target.value
                  )
                  setMoveOuError('')
                }}
                autoFocus
                disabled={
                  adminLoading
                  || moveOuLoading
                }
              >
                <option value="" disabled>
                  {moveOuLoading
                    ? 'Chargement des OU...'
                    : 'Choisir une OU de destination'}
                </option>

                {!moveOuLoading
                  && moveTargetDn
                  && !moveOuOptions.some(
                    option =>
                      option.dn.toUpperCase()
                      === moveTargetDn
                        .toUpperCase()
                  )
                  && (
                  <option value={moveTargetDn}>
                    {getMoveOuDisplayLabel(
                      moveTargetDn
                    )} — personnalisée
                  </option>
                )}

                {moveOuOptions.map(option => (
                  <option
                    key={option.dn}
                    value={option.dn}
                  >
                    {option.label}
                  </option>
                ))}
              </select>

              <small>
                {moveOuLoading
                  ? 'Chargement de l’arbre Active Directory...'
                  : `${moveOuOptions.length} OU disponible${moveOuOptions.length > 1 ? 's' : ''}.`}
              </small>
            </label>

            <details className="aduc-create-user-advanced-dn">
              <summary>
                DN personnalisé / avancé
              </summary>

              <input
                type="text"
                className="mono"
                value={moveTargetDn}
                onChange={event => {
                  setMoveTargetDn(
                    event.target.value
                  )
                  setMoveOuError('')
                }}
                placeholder="OU=Destination,OU=EITAS,DC=API,DC=LOCAL"
                disabled={adminLoading}
              />
            </details>

            <div className="aduc-move-destination-summary">
              <span>Nouvel emplacement</span>

              <strong>
                {moveTargetDn
                  ? getMoveOuDisplayLabel(
                      moveTargetDn
                    )
                  : 'Aucune destination'}
              </strong>

              <code>
                {moveTargetDn || '—'}
              </code>
            </div>

            <div
              className={`aduc-account-action-warning ${
                isAdProductionMode()
                  ? 'production'
                  : 'simulation'
              }`}
            >
              <strong>
                {getAdAgentModeLabel()}
              </strong>

              <p>
                {isAdProductionMode()
                  ? 'Le déplacement modifiera réellement Active Directory.'
                  : 'Simulation active : aucun objet réel ne sera déplacé.'}
              </p>
            </div>

            {moveOuError && (
              <div className="aduc-member-submit-error">
                <strong>
                  Déplacement impossible
                </strong>

                <span>{moveOuError}</span>
              </div>
            )}

            <footer className="aduc-modal-actions">
              <button
                type="button"
                onClick={closeMoveModal}
                disabled={adminLoading}
              >
                Annuler
              </button>

              <button
                type="submit"
                disabled={
                  adminLoading
                  || moveOuLoading
                  || adAgentModeLoading
                  || Boolean(
                    getMoveValidationError()
                  )
                }
              >
                {adminLoading
                  ? 'Déplacement...'
                  : moveOuLoading
                    ? 'Chargement des OU...'
                    : adAgentModeLoading
                      ? 'Vérification du mode...'
                      : 'Déplacer'}
              </button>
            </footer>
          </form>
        </section>
      </div>
  )
}

export default MoveObjectModal
