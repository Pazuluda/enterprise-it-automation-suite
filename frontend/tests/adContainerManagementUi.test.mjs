import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = path => readFileSync(path, 'utf8')

const move = read(
  'frontend/src/features/active-directory/hooks/useAdObjectMove.js'
)
const update = read(
  'frontend/src/features/active-directory/hooks/useAdObjectUpdate.js'
)
const form = read(
  'frontend/src/features/active-directory/components/UpdateObjectForm.jsx'
)
const details = read(
  'frontend/src/features/active-directory/components/ObjectDetailsPanel.jsx'
)
const history = read(
  'frontend/src/features/active-directory/utils/adHistory.js'
)
const page = read(
  'frontend/src/features/active-directory/AdExplorerPage.jsx'
)

test('C5.4 move supports native container destinations', () => {
  assert.match(move, /isContainerObject\(item\)/)
  assert.match(move, /isMoveStructuralDestination/)
  assert.match(move, /\^CN=/)
  assert.match(
    move,
    /La destination doit .* une OU ou/,
  )
  assert.match(
    move,
    /un conteneur Active Directory/,
  )
})

test('C5.4 update recognizes containers', () => {
  assert.match(update, /isUpdateContainerTarget/)
  assert.match(update, /isContainerObject\(target\)/)
})

test('C5.4 container exposes native protection', () => {
  assert.match(
    form,
    /isUpdateContainerTarget\(currentTarget\)/,
  )
  assert.match(
    form,
    /protectedFromAccidentalDeletion/,
  )
})

test('C5.4 details support native containers', () => {
  assert.match(details, /Explorer ce conteneur/)
  assert.match(details, /onCreateContainer/)
  assert.match(details, /Conteneur ici/)
})

test('C5.4 history recognizes create_container', () => {
  assert.match(history, /create_container/)
  assert.match(history, /Créer un conteneur/)
  assert.match(details, /create_container/)
})

test('C5.4 page wires details container actions', () => {
  assert.match(
    page,
    /onCreateContainer=\{target => openCreateContainer\(target\)\}/,
  )
  assert.match(
    page,
    /onCreateContainer:\s*target =>/,
  )
})
