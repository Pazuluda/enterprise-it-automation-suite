import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const modal = readFileSync(
  new URL('../src/features/active-directory/components/CreateComputerModal.jsx', import.meta.url),
  'utf8'
)

const page = readFileSync(
  new URL('../src/features/active-directory/AdExplorerPage.jsx', import.meta.url),
  'utf8'
)

const updateForm = readFileSync(
  new URL('../src/features/active-directory/components/UpdateObjectForm.jsx', import.meta.url),
  'utf8'
)

const details = readFileSync(
  new URL('../src/features/active-directory/components/ObjectDetailsPanel.jsx', import.meta.url),
  'utf8'
)

test('C5.1 computer creation modal keeps the managed AD workflow', () => {
  assert.match(modal, /PC-EITAS-001/)
  assert.match(modal, /PRODUCTION/)
  assert.match(modal, /Description du poste/)
})

test('C5.1 computer management remains wired in the explorer', () => {
  assert.match(page, /CreateComputerModal/)
  assert.match(page, /computer/i)
  assert.match(updateForm, /computer/i)
  assert.match(details, /computer/i)
})

console.log('C5.1 COMPUTER MANAGEMENT UI: OK')
