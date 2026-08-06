import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(
  'frontend/src/features/active-directory/'
  + 'components/UpdateObjectForm.jsx',
  'utf8'
)

test('affiche une section profil avancé', () => {
  assert.ok(
    source.includes("title: 'Profil avancé'")
  )

  for (const label of [
    'Titre de civilité',
    'Initiales',
    'Langue préférée',
    'Remarques',
  ]) {
    assert.ok(source.includes(label))
  }
})

test('utilise les quatre champs canoniques', () => {
  for (const field of [
    "'personalTitle'",
    "'initials'",
    "'preferredLanguage'",
    "'info'",
  ]) {
    assert.ok(source.includes(field))
  }
})

test('applique les bornes du schéma', () => {
  for (const token of [
    "name === 'personalTitle'",
    "name === 'initials'",
    "name === 'preferredLanguage'",
    "name === 'info'",
    '? 64',
    '? 6',
    '? 32767',
    '? 1024',
  ]) {
    assert.ok(source.includes(token))
  }
})

test('désactive chaque champ encore en chargement', () => {
  assert.ok(
    source.includes(
      '?.pendingUserAccountOptionFields'
    )
  )
  assert.ok(
    source.includes('?.includes(name)')
  )
})

test('utilise une zone multiligne pour les remarques', () => {
  const infoBranchIndex = source.indexOf(
    "if (name === 'info')"
  )

  assert.ok(infoBranchIndex >= 0)

  const infoBranch = source.slice(
    infoBranchIndex,
    infoBranchIndex + 1400
  )

  for (const token of [
    '<textarea',
    'rows="4"',
    'maxLength={1024}',
    "updateForm.info || ''",
    "'info'",
    'limitée à 1 024 caractères',
  ]) {
    assert.ok(infoBranch.includes(token))
  }
})
