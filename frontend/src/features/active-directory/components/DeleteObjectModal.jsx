import {
  getObjectName,
  getObjectType,
  getObjectDn,
} from '../utils/adExplorerCore'

function DeleteObjectModal({
  deletion,
}) {
  const {
    deleteModal,
    loading,
    setDeleteModal,
    deleteConfirmDn,
    setDeleteConfirmDn,
    deleteError,
    setDeleteError,
    submitDeleteObject,
  } = deletion

  if (!deleteModal) return null

  return (
    <div
        className="aduc-modal-backdrop"
        onClick={() => {
          if (!loading) {
            setDeleteModal(null)
            setDeleteConfirmDn('')
            setDeleteError('')
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
              <h3>Supprimer l’objet</h3>
            </div>

            <button
              type="button"
              onClick={() => {
                setDeleteModal(null)
                setDeleteConfirmDn('')
                setDeleteError('')
              }}
              disabled={loading}
            >
              ×
            </button>
          </header>

          <form onSubmit={submitDeleteObject}>
            <div className="aduc-update-object-target">
              <div>
                <span>Objet cible</span>
                <strong>{getObjectName(deleteModal)}</strong>
              </div>

              <div>
                <span>Type</span>
                <strong>{getObjectType(deleteModal)}</strong>
              </div>

              <div className="wide">
                <span>DN de l’objet</span>
                <code>{getObjectDn(deleteModal)}</code>
              </div>
            </div>

            <div className="aduc-account-action-warning production">
              <strong>Suppression définitive</strong>

              <p>
                Cette action supprimera réellement l’objet
                dans Active Directory.
              </p>
            </div>

            <label className="aduc-account-action-field">
              <span>Confirmation par Distinguished Name</span>

              <input
                type="text"
                className="mono"
                value={deleteConfirmDn}
                onChange={event => {
                  setDeleteConfirmDn(event.target.value)
                  setDeleteError('')
                }}
                placeholder={getObjectDn(deleteModal)}
                autoComplete="off"
                autoFocus
                disabled={loading}
              />

              <small>
                Recopie le DN affiché au-dessus. La casse
                des lettres n’a pas d’importance.
              </small>
            </label>

            {deleteError && (
              <div className="aduc-member-submit-error">
                <strong>Suppression impossible</strong>
                <span>{deleteError}</span>
              </div>
            )}

            <footer className="aduc-modal-actions">
              <button
                type="button"
                onClick={() => {
                  setDeleteModal(null)
                  setDeleteConfirmDn('')
                  setDeleteError('')
                }}
                disabled={loading}
              >
                Annuler
              </button>

              <button
                type="button"
                className="danger"
                onClick={submitDeleteObject}
                disabled={
                  loading ||
                  !deleteConfirmDn.trim()
                }
              >
                {loading
                  ? 'Suppression...'
                  : 'Supprimer définitivement'}
              </button>
            </footer>
          </form>
        </section>
      </div>
  )
}

export default DeleteObjectModal
