import UpdateObjectForm from './UpdateObjectForm'

function UpdateObjectModal({
  update,
}) {
  const {
    updateModal,
    loading,
    closeUpdateObject,
  } = update

  if (!updateModal) return null

  return (
    <div
      className="aduc-modal-backdrop"
      onClick={() =>
        !loading &&
        closeUpdateObject()
      }
    >
      <section
        className="aduc-modal aduc-update-object-modal"
        onClick={event =>
          event.stopPropagation()
        }
      >
        <header>
          <div>
            <span>Active Directory</span>
            <h3>Modifier les propriétés</h3>
          </div>

          <button
            type="button"
            onClick={() =>
              closeUpdateObject()
            }
            disabled={loading}
          >
            ×
          </button>
        </header>

        <UpdateObjectForm
          update={update}
        />
      </section>
    </div>
  )
}

export default UpdateObjectModal
