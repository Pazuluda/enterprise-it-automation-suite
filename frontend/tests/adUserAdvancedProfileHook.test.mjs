import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(
  'frontend/src/features/active-directory/'
  + 'hooks/useAdObjectUpdate.js',
  'utf8'
)

test('déclare les quatre attributs avancés', () => {
  for (const field of [
    'personalTitle',
    'initials',
    'preferredLanguage',
    'info',
  ]) {
    assert.ok(
      source.includes(`field: '${field}'`)
    )
  }
})

test('déclare tous les alias', () => {
  for (const alias of [
    'personal_title',
    'preferred_language',
    'notes',
    'remarks',
    'user_notes',
  ]) {
    assert.ok(source.includes(`'${alias}'`))
  }
})

test('détecte les champs avancés absents', () => {
  assert.ok(
    source.includes(
      'hasAuthoritativeUserAdvancedProfile'
    )
  )
  assert.ok(
    source.includes(
      'getMissingUserAdvancedProfileFields'
    )
  )
})

test('ouvre la fenêtre avant le lookup détaillé', () => {
  const openIndex = source.indexOf(
    'setUpdateEditorOpen(openModal)'
  )
  const lookupIndex = source.indexOf(
    'void resolveUserUpdateTarget(target)'
  )

  assert.ok(openIndex >= 0)
  assert.ok(lookupIndex > openIndex)
})

test('fusionne les détails avancés', () => {
  assert.ok(
    source.includes(
      '...getUserAdvancedProfilePatch('
    )
  )
  assert.ok(
    source.includes(
      '!updateDirtyFieldsRef.current.has('
    )
  )
})

test('initialise les quatre valeurs localement', () => {
  for (const token of [
    'personalTitle: getAdAttributeValue(',
    'initials: getAdAttributeValue(',
    'preferredLanguage: getAdAttributeValue(',
    'info: getAdAttributeValue(',
  ]) {
    assert.ok(source.includes(token))
  }
})
