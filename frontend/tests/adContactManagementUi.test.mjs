import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const hook = fs.readFileSync(
  'frontend/src/features/active-directory/hooks/useAdAdminCreation.js',
  'utf8'
)

const modal = fs.readFileSync(
  'frontend/src/features/active-directory/components/AdminCreationModal.jsx',
  'utf8'
)

const page = fs.readFileSync(
  'frontend/src/features/active-directory/AdExplorerPage.jsx',
  'utf8'
)

const menu = fs.readFileSync(
  'frontend/src/features/active-directory/components/AdContextMenu.jsx',
  'utf8'
)

const history = fs.readFileSync(
  'frontend/src/features/active-directory/utils/adHistory.js',
  'utf8'
)

const details = fs.readFileSync(
  'frontend/src/features/active-directory/components/ObjectDetailsPanel.jsx',
  'utf8'
)

function extract(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker)
  assert.ok(start >= 0, `missing start marker: ${startMarker}`)

  const end = source.indexOf(endMarker, start)
  assert.ok(end > start, `missing end marker: ${endMarker}`)

  return source.slice(start, end)
}

test('C5.3 opens contact creation only inside the managed EITAS perimeter', () => {
  const block = extract(
    hook,
    'function openCreateContact(',
    'function openCreateGroup('
  )

  assert.match(block, /isEitasManagedObject\(target\)/)
  assert.match(block, /getCreateAdminParentDn\(target\)/)
  assert.match(block, /isEitasManagedDn\(parentDn\)/)
  assert.match(block, /action:\s*'create_contact'/)
  assert.match(block, /title:\s*'Créer un contact'/)
  assert.match(block, /search_base_dn:\s*EITAS_DN/)
})

test('C5.3 initializes the complete contact creation form', () => {
  const block = extract(
    hook,
    'function openCreateContact(',
    'function openCreateGroup('
  )

  for (const field of [
    'name',
    'display_name',
    'first_name',
    'last_name',
    'mail',
    'telephone_number',
    'mobile',
    'company',
    'title',
    'department',
    'description',
    'parent_dn',
    'protected_from_accidental_deletion',
  ]) {
    assert.match(block, new RegExp(`${field}:`))
  }
})

test('C5.3 sends the complete create_contact payload behind Production confirmation', () => {
  const block = extract(
    hook,
    'async function submitAdAdminJob(event)',
    '\n  return {'
  )

  assert.match(block, /adminModal\.action === 'create_contact'/)
  assert.match(block, /confirmProductionAdAction\(/)
  assert.match(block, /action:\s*adminModal\.action/)
  assert.match(block, /parent_dn:\s*parentDn/)
  assert.match(block, /created_by:\s*'react-admin'/)

  for (const field of [
    'display_name',
    'first_name',
    'last_name',
    'mail',
    'telephone_number',
    'mobile',
    'company',
    'title',
    'department',
    'protected_from_accidental_deletion',
  ]) {
    assert.match(block, new RegExp(field))
  }
})

test('C5.3 contact modal exposes identity, communication, organization and native protection', () => {
  assert.match(modal, /adminModal\.action === 'create_contact'/)
  assert.match(modal, /Nom du contact/)
  assert.match(modal, /Nom d’affichage/)
  assert.match(modal, /Prénom/)
  assert.match(modal, /Nom de famille/)
  assert.match(modal, /Adresse e-mail/)
  assert.match(modal, /Téléphone/)
  assert.match(modal, /Mobile/)
  assert.match(modal, /Société/)
  assert.match(modal, /Fonction/)
  assert.match(modal, /Département/)
  assert.match(modal, /Description/)
  assert.match(modal, /Protégé contre la suppression accidentelle/)
})

test('C5.3 contact creation is wired from explorer and context menu', () => {
  assert.match(page, /openCreateContact/)
  assert.match(page, /Créer un contact/)
  assert.match(menu, /openCreateContact/)
  assert.match(menu, /Créer un contact/)
})

test('C5.3 history treats create_contact as a creation action', () => {
  assert.match(history, /create_contact:\s*'Créer un contact'/)
  assert.match(history, /job\?\.action === 'create_contact'/)
  assert.match(
    details,
    /\['create_ou',\s*'create_group',\s*'create_user',\s*'create_computer',\s*'create_contact'\]/
  )
})
