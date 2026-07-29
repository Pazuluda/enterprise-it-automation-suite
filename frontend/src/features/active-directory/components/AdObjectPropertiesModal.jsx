import {
  useEffect,
  useState,
} from 'react'

import ObjectDetailsPanel from './ObjectDetailsPanel'
import UpdateObjectForm from './UpdateObjectForm'
import LdapAttributeEditor from './LdapAttributeEditor'
import useLdapAttributeUpdate from '../hooks/useLdapAttributeUpdate'
import {
  getObjectDn,
  getObjectName,
  getObjectType,
} from '../utils/adExplorerCore'

function AdObjectPropertiesModal({
  object,
  selectedNode,
  details,
  update,
  agentMode,
  loadAgentMode,
  apiFetch,
  onClose,
}) {
  const [editing, setEditing] = useState(false)

  const ldapEditor = useLdapAttributeUpdate({
    object,
    agentMode,
    apiFetch,
  })

  const [saveNotice, setSaveNotice] = useState('')
  const loading = Boolean(update?.loading)
  const hasChanges = Boolean(
    update?.hasUpdateChanges
  )

  const visibleSaveNotice =
    update?.updateSaveNotice || saveNotice

  const visibleSaveError =
    update?.updateSaveError || ''

  useEffect(() => {
    setEditing(false)
    setSaveNotice('')
  }, [object])

  useEffect(() => {
    if (hasChanges) {
      setSaveNotice('')
    }
  }, [hasChanges])

  function discardAndClose() {
    if (loading) return

    ldapEditor.close()
    update?.closeUpdateObject?.()
    setEditing(false)
    onClose?.()
  }
  function cancelEditing() {
    if (loading) return

    update?.closeUpdateObject?.()
    setEditing(false)
    setSaveNotice('')
  }


  function beginEditing(target = object) {
    if (loading || editing) return

    setSaveNotice('')

    const prepared =
      update?.prepareUpdateObject?.(
        target,
        { openModal: false }
      )

    if (prepared) {
      setEditing(true)
    }
  }

  function beginClearingManager(
    target = object
  ) {
    if (loading || editing) return

    setSaveNotice('')

    const prepared =
      update?.prepareClearManager?.(
        target,
        { openModal: false }
      )

    if (prepared) {
      setEditing(true)
    }
  }


  async function beginLdapEditing() {
    if (
      loading ||
      editing ||
      !ldapEditor.eligible
    ) {
      return
    }

    await loadAgentMode?.()

    update?.closeUpdateObject?.()
    setEditing(false)
    ldapEditor.open()
  }

  async function applyChanges() {
    if (
      loading ||
      !editing ||
      !hasChanges
    ) {
      return false
    }

    setSaveNotice('')

    const saved = (
      await update?.submitUpdateObject?.(
        null,
        { closeOnSuccess: false }
      )
    ) === true

    if (saved) {
      setSaveNotice(
        'Propriétés enregistrées avec succès.'
      )
    }

    return saved
  }

  async function handleOk() {
    if (loading) return

    if (editing && hasChanges) {
      const saved = await applyChanges()

      if (!saved) return
    }

    update?.closeUpdateObject?.()
    setEditing(false)
    onClose?.()
  }

  useEffect(() => {
    if (!object) return undefined

    function handleKeyDown(event) {
      if (
        event.key === 'Escape' &&
        !loading
      ) {
        discardAndClose()
      }
    }

    window.addEventListener(
      'keydown',
      handleKeyDown
    )

    return () => {
      window.removeEventListener(
        'keydown',
        handleKeyDown
      )
    }
  })

  if (!object) return null

  const objectName = getObjectName(object)
  const objectType = getObjectType(object)
  const objectDn = getObjectDn(object)

  return (
    <div
      className="
        aduc-modal-backdrop
        aduc-object-properties-backdrop
      "
      role="presentation"
      onMouseDown={event => {
        if (
          event.target === event.currentTarget
        ) {
          discardAndClose()
        }
      }}
    >
      <section
        className="
          aduc-modal
          aduc-object-properties-modal
        "
        role="dialog"
        aria-modal="true"
        aria-label={`Propriétés de ${objectName}`}
        onMouseDown={event =>
          event.stopPropagation()
        }
      >
        <header>
          <div className="aduc-object-properties-title">
            <span>Active Directory</span>

            <h3>
              Propriétés de {objectName}
            </h3>

            <p>
              {objectType}
              {objectDn
                ? ` • ${objectDn}`
                : ''}
            </p>
          </div>

          <div className="aduc-object-properties-header-actions">
            <span className="aduc-object-properties-mode">
              {ldapEditor.active
                ? 'Éditeur LDAP'
                : editing
                  ? 'Modification'
                  : 'Consultation'}
            </span>

            <button
              type="button"
              aria-label="Fermer"
              title="Fermer"
              onClick={discardAndClose}
              disabled={loading}
            >
              ×
            </button>
          </div>
        </header>
          {visibleSaveError && (
            <div
              className="aduc-object-properties-notice error"
              role="alert"
              aria-live="assertive"
            >
              <span aria-hidden="true">!</span>
              <strong>{visibleSaveError}</strong>
            </div>
          )}

          {visibleSaveNotice && (
            <div
              className="aduc-object-properties-notice"
              role="status"
              aria-live="polite"
            >
              <span aria-hidden="true">✓</span>
              <strong>{visibleSaveNotice}</strong>
            </div>
          )}

        <div className="aduc-object-properties-body">
          {ldapEditor.active ? (
            <LdapAttributeEditor
              editor={ldapEditor}
            />
          ) : editing ? (
            <div className="aduc-object-properties-editor">
              <UpdateObjectForm
                update={update}
                target={object}
                showTargetSummary={false}
                showActions={false}
              />
            </div>
          ) : (
            <ObjectDetailsPanel
              key={objectDn || objectName}
              object={object}
              selectedNode={selectedNode}
              {...details}
              onOpenUpdateObject={target =>
                beginEditing(
                  target || object
                )
              }
              onClearManagedBy={target =>
                beginClearingManager(
                  target || object
                )
              }
            />
          )}
        </div>

        <footer className="aduc-modal-actions">

          {ldapEditor.active ? (
            <button
              type="button"
              onClick={ldapEditor.close}
              disabled={loading}
            >
              Retour aux propriétés
            </button>
          ) : !editing ? (
            <>
              {ldapEditor.eligible && (
                <button
                  type="button"
                  className="aduc-properties-edit-button"
                  onClick={beginLdapEditing}
                  disabled={loading}
                >
                  Attributs LDAP
                </button>
              )}

              <button
                type="button"
                onClick={discardAndClose}
                disabled={loading}
              >
                Fermer
              </button>
            </>
          ) : (
            <>

          <button
            type="button"
            onClick={cancelEditing}
            disabled={loading}
          >
            Annuler
          </button>

          <button
            type="button"
            onClick={applyChanges}
            disabled={
              loading ||
              !editing ||
              !hasChanges
            }
          >
            {loading
              ? 'Enregistrement...'
              : 'Appliquer'}
          </button>
              <button
                type="button"
                onClick={handleOk}
                disabled={
                  loading ||
                  !hasChanges
                }
              >
                {loading
                  ? "Enregistrement..."
                  : "Enregistrer et fermer"}
              </button>
            </>
          )}
        </footer>
      </section>
    </div>
  )
}

export default AdObjectPropertiesModal
