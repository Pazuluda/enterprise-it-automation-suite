import {
  copyText,
  isEitasManagedObject,
} from '../utils/adExplorerCore'

function AdContextMenu({
  menu,
}) {
  const {
    contextMenu,
    actionSoon,
    setContextMenu,
    openMoveObject,
    selectedObject,
    selectedNode,
    openSearchOuModal,
    openNewObjectMenu,
    openCreateOu,
    openCreateGroup,
    openCreateUser,
    openUpdateObject,
    openRenameObject,
    openDeleteObject,
    loadNodeContent,
    viewType,
    setMessage,
    openProperties,
  } = menu

  if (!contextMenu) return null

  return (
    <div
              className="aduc-context-menu"
              style={{
                left: contextMenu.x,
                top: contextMenu.y
              }}
              onClick={event => event.stopPropagation()}
            >
              <button type="button" onClick={() => actionSoon('Délégation de contrôle')}>👥 Délégation de contrôle...</button>
              <button
                  type="button"
                  onClick={() => {
                    setContextMenu(null)
                    openMoveObject(contextMenu?.target || contextMenu?.item || contextMenu?.object || selectedObject || selectedNode)
                  }}
                >
                  📁 Déplacer...
                </button>
              <button
                type="button"
                onClick={() => openSearchOuModal(contextMenu?.target || selectedObject || selectedNode)}
              >
                🔎 Rechercher...
              </button>

              <hr />

              <button type="button" onClick={() => openNewObjectMenu(contextMenu?.target || selectedNode)}>＋ Nouveau ›</button>
              <button type="button" onClick={() => openCreateOu(selectedNode)}>📁 Créer une OU</button>
              <button type="button" onClick={() => openCreateGroup(selectedNode)}>👥 Créer un groupe</button>
                <button
                  type="button"
                  data-eitas-action="create-user-context"
                  disabled={
                    !isEitasManagedObject(
                      contextMenu?.target
                      || selectedNode
                    )
                  }
                  onClick={() =>
                    openCreateUser(
                      contextMenu?.target
                      || selectedNode
                    )
                  }
                >
                  👤 Créer un utilisateur
                </button>

              <hr />

              <button type="button" onClick={() => {
                  setContextMenu(null)
                  openUpdateObject(contextMenu?.target || selectedObject || selectedNode)
                }}>✎ Modifier</button>
              <button
                type="button"
                onClick={() => {
                  setContextMenu(null)
                  openRenameObject(contextMenu.target || selectedObject || selectedNode)
                }}
              >
                A↕ Renommer
              </button>
              <button type="button" className="danger" onClick={() => {
                  setContextMenu(null)
                  openDeleteObject(contextMenu?.target || selectedObject || selectedNode)
                }}>🗑 Supprimer</button>
              <button type="button" onClick={() => loadNodeContent(selectedNode, viewType, { forceRefresh: true })}>⟳ Actualiser</button>
              <button type="button" onClick={() => copyText(contextMenu.target?.distinguished_name || '').then(() => setMessage?.('DN copié.'))}>⎙ Exporter / Copier DN</button>

              <hr />

              <button type="button" onClick={() => openProperties(contextMenu.target)}>ⓘ Propriétés</button>
            </div>
  )
}

export default AdContextMenu
