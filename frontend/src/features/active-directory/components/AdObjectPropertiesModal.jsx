import {
  useEffect,
  useState,
} from 'react'

import ObjectDetailsPanel from './ObjectDetailsPanel'
import UpdateObjectForm from './UpdateObjectForm'
import LdapAttributeEditor from './LdapAttributeEditor'
import HabSenioritySimulationEditor from './HabSenioritySimulationEditor'
import useLdapAttributeUpdate from '../hooks/useLdapAttributeUpdate'
import useHabSenioritySimulation from '../hooks/useHabSenioritySimulation'
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
  canManageActiveDirectory,
  onClose,
}) {
  const [editing, setEditing] = useState(false)
  const [habSimulationActive, setHabSimulationActive] = useState(false)

  const objectIdentity = String(
    getObjectDn(object) || ''
  )
    .trim()
    .toLowerCase()

  const ldapEditor = useLdapAttributeUpdate({
    object,
    agentMode,
    apiFetch,
  })

  const habSimulation = useHabSenioritySimulation({
    object,
    agentMode,
    canManageActiveDirectory,
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

  const isHabWarningNotice =
    String(visibleSaveNotice || '')
      .includes('Simulation HAB indisponible')

  useEffect(() => {
    setEditing(false)
    setSaveNotice('')
    setHabSimulationActive(false)
  }, [objectIdentity])

  useEffect(() => {
    if (hasChanges) {
      setSaveNotice('')
    }
  }, [hasChanges])

  function discardAndClose() {
    if (loading) return

    ldapEditor.close()
    update?.closeUpdateObject?.()
    habSimulation.close()
    setHabSimulationActive(false)
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
      habSimulationActive ||
      !ldapEditor.eligible
    ) {
      return
    }

    await loadAgentMode?.()

    update?.closeUpdateObject?.()
    habSimulation.close()
    setHabSimulationActive(false)
    setEditing(false)
    ldapEditor.open()
  }

  async function beginHabSimulation() {
    if (
      loading ||
      editing ||
      ldapEditor.active
    ) {
      return
    }

    const loadedMode =
      await loadAgentMode?.()

    const effectiveMode =
      loadedMode ||
      agentMode ||
      'Inconnu'

    const opened =
      habSimulation.open(effectiveMode)

    if (!opened) {
      setHabSimulationActive(false)
      setSaveNotice(
        'Simulation HAB indisponible : '
        + 'le mode agent doit être Simulation.'
      )
      return
    }

    setSaveNotice('')
    update?.closeUpdateObject?.()
    ldapEditor.close()
    setEditing(false)
    setHabSimulationActive(true)
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
  const isUserObject = objectType.includes('Utilisateur')
  const canManageHab =
    Boolean(canManageActiveDirectory) &&
    isUserObject

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
                : habSimulationActive
                  ? 'Simulation HAB'
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
              className={
                `aduc-object-properties-notice${
                  isHabWarningNotice
                    ? ' warning'
                    : ''
                }`
              }
              role={
                isHabWarningNotice
                  ? 'alert'
                  : 'status'
              }
              aria-live={
                isHabWarningNotice
                  ? 'assertive'
                  : 'polite'
              }
            >
              <span aria-hidden="true">
                {isHabWarningNotice
                  ? '!'
                  : '✓'}
              </span>
              <strong>{visibleSaveNotice}</strong>
            </div>
          )}

        <div className="aduc-object-properties-body">
          {habSimulationActive ? (
            <HabSenioritySimulationEditor
              editor={habSimulation}
            />
          ) : ldapEditor.active ? (
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

          {habSimulationActive ? (
            <button
              type="button"
              onClick={() => {
                habSimulation.close()
                setHabSimulationActive(false)
              }}
              disabled={loading}
            >
              Retour aux propriétés
            </button>
          ) : ldapEditor.active ? (
            <button
              type="button"
              onClick={ldapEditor.close}
              disabled={loading}
            >
              Retour aux propriétés
            </button>
          ) : !editing ? (
            <>
              {canManageHab && (
                <button
                  type="button"
                  className="aduc-properties-hab-button"
                  onClick={beginHabSimulation}
                  disabled={loading}
                >
                  Simulation HAB
                </button>
              )}

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
