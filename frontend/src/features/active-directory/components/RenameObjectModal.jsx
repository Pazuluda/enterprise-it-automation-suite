import {
  getObjectName,
  getObjectType,
  getObjectDn,
} from '../utils/adExplorerCore'

function RenameObjectModal({
  rename,
}) {
  const {
    renameModal,
    loading,
    setRenameModal,
    renameNewName,
    setRenameNewName,
    submitRenameObject,
  } = rename

  if (!renameModal) return null

  return (
    <div
        className="aduc-modal-backdrop"
        onClick={() => {
          if (!loading) {
            setRenameModal(null)
            setRenameNewName('')
          }
        }}
      >
        <section
          className="aduc-modal"
          onClick={event => event.stopPropagation()}
        >
          <header>
            <div>
              <span>Active Directory</span>
              <h3>Renommer l’objet</h3>
            </div>

            <button
              type="button"
              onClick={() => {
                setRenameModal(null)
                setRenameNewName('')
              }}
              disabled={loading}
            >
              ×
            </button>
          </header>

          <form onSubmit={submitRenameObject}>
            <div className="aduc-update-object-target">
              <div>
                <span>Objet cible</span>
                <strong>{getObjectName(renameModal)}</strong>
              </div>

              <div>
                <span>Type</span>
                <strong>{getObjectType(renameModal)}</strong>
              </div>

              <div className="wide">
                <span>DN actuel</span>
                <code>{getObjectDn(renameModal)}</code>
              </div>
            </div>

            <label className="aduc-account-action-field">
              <span>Nouveau nom</span>
              <input
                type="text"
                value={renameNewName}
                onChange={event =>
                  setRenameNewName(event.target.value)
                }
                placeholder="Saisir le nouveau nom"
                autoFocus
                disabled={loading}
              />
            </label>

            <p className="aduc-update-object-help">
              Le renommage sera exécuté réellement dans Active
              Directory par le worker AD Admin.
            </p>

            <footer className="aduc-modal-actions">
              <button
                type="button"
                onClick={() => {
                  setRenameModal(null)
                  setRenameNewName('')
                }}
                disabled={loading}
              >
                Annuler
              </button>

              <button
                type="submit"
                disabled={
                  loading ||
                  !renameNewName.trim() ||
                  renameNewName.trim() ===
                    String(getObjectName(renameModal) || '').trim()
                }
              >
                {loading
                  ? 'Renommage...'
                  : 'Renommer'}
              </button>
            </footer>
          </form>
        </section>
      </div>
  )
}

export default RenameObjectModal
