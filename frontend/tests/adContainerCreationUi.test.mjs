import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = path => readFileSync(path, 'utf8')

const creation = read(
  'frontend/src/features/active-directory/hooks/useAdAdminCreation.js'
)
const modal = read(
  'frontend/src/features/active-directory/components/AdminCreationModal.jsx'
)
const page = read(
  'frontend/src/features/active-directory/AdExplorerPage.jsx'
)
const context = read(
  'frontend/src/features/active-directory/components/AdContextMenu.jsx'
)
const snapshotHook = read(
  'frontend/src/features/active-directory/hooks/useAdSnapshot.js'
)

test('C5.4 creation hook exposes container', () => {
  assert.match(creation, /openCreateContainer/)
  assert.match(creation, /create_container/)
  assert.match(creation, /normalizeAdminParentOptions/)
})

test('C5.4 modal exposes container protection', () => {
  assert.match(modal, /Créer le conteneur/)
  assert.match(
    modal,
    /protected_from_accidental_deletion/,
  )
})

test('C5.4 toolbar exposes container', () => {
  assert.match(page, /create-container-toolbar/)
})

test('C5.4 context exposes container', () => {
  assert.match(context, /create-container-context/)
})

test('C5.4 double click explores container', () => {
  assert.match(page, /isContainerObject\(item\)/)
})

test('C5.4 snapshot hook exposes structural nodes', () => {
  assert.match(snapshotHook, /getNavigationNodes/)
  assert.match(snapshotHook, /getNavigationNodesSync/)
})
