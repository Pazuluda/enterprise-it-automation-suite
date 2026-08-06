import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const details = readFileSync(
  'frontend/src/features/active-directory/'
  + 'components/ObjectDetailsPanel.jsx',
  'utf8'
)

const copyPolicy = readFileSync(
  'frontend/src/features/active-directory/'
  + 'utils/adUserCopy.js',
  'utf8'
)

test('affiche les quatre valeurs avancées', () => {
  for (const label of [
    'Titre de civilité',
    'Initiales',
    'Langue préférée',
    'Remarques',
  ]) {
    assert.ok(details.includes(label))
  }
})

test('lit les alias canoniques et normalisés', () => {
  for (const alias of [
    'personalTitle',
    'personal_title',
    'initials',
    'preferredLanguage',
    'preferred_language',
    'info',
    'notes',
    'remarks',
    'user_notes',
  ]) {
    assert.ok(details.includes(`'${alias}'`))
  }
})

test('distingue les valeurs absentes', () => {
  assert.ok(details.includes("'Non défini'"))
  assert.ok(details.includes("'Non définie'"))
  assert.ok(details.includes("'Non définies'"))
})

test('exclut ces valeurs de la copie utilisateur', () => {
  for (const field of [
    'personalTitle',
    'personal_title',
    'initials',
    'preferredLanguage',
    'preferred_language',
    'info',
    'notes',
    'remarks',
    'user_notes',
  ]) {
    assert.ok(copyPolicy.includes(`'${field}'`))
  }
})
