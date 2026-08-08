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

test('C5.2 creation OU is limited to the EITAS perimeter', () => {
  const start = hook.indexOf('function openCreateOu(')
  const end = hook.indexOf('function openCreateGroup(', start)
  const block = hook.slice(start, end)

  assert.ok(start >= 0)
  assert.ok(end > start)
  assert.match(block, /isEitasManagedObject\(target\)/)
  assert.match(block, /isEitasManagedDn\(parentDn\)/)
  assert.match(block, /action:\s*'create_ou'/)
  assert.match(block, /title:\s*'Créer une OU'/)
  assert.match(block, /search_base_dn:\s*EITAS_DN/)
})

test('C5.2 creation OU payload sends normalized creation fields', () => {
  const start = hook.indexOf('async function submitAdAdminJob(')
  const end = hook.indexOf('\n  return {', start)
  const block = hook.slice(start, end)

  assert.ok(start >= 0)
  assert.ok(end > start)
  assert.match(block, /const name = adminForm\.name\.trim\(\)/)
  assert.match(block, /adminForm\.description\.trim\(\)/)
  assert.match(block, /adminForm\.parent_dn/)
  assert.match(block, /action:\s*adminModal\.action/)
  assert.match(block, /parent_dn:\s*parentDn/)
  assert.match(block, /name,/)
  assert.match(block, /description,/)
  assert.match(block, /created_by:\s*'react-admin'/)
  assert.match(block, /runAdAdminJob\(payload\)/)
})

test('C5.2 Production OU creation remains behind explicit confirmation', () => {
  assert.match(
    hook,
    /confirmProductionAdAction\(\s*actionLabel,\s*targetSummary\s*\)/
  )
  assert.match(
    hook,
    /adminModal\.action === 'create_ou'[\s\S]*La création de l’OU/
  )
})

test('C5.2 OU modal exposes mode, destination, advanced DN, name and description', () => {
  assert.match(modal, /L’OU sera réellement créée dans Active Directory\./)
  assert.match(modal, /Simulation active : aucun objet réel ne sera créé\./)
  assert.match(modal, /Emplacement de création/)
  assert.match(modal, /DN personnalisé \/ avancé/)
  assert.match(modal, /Nom de l’OU/)
  assert.match(modal, /adminForm\.description/)
})

test('C5.2 OU creation remains wired from explorer and context menu', () => {
  assert.match(page, /openCreateOu/)
  assert.match(page, /Créer une OU/)
  assert.match(menu, /openCreateOu/)
  assert.match(menu, /Créer une OU/)
})
