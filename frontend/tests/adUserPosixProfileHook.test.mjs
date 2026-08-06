import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(
  new URL(
    '../src/features/active-directory/'
      + 'hooks/useAdObjectUpdate.js',
    import.meta.url
  ),
  'utf8'
)

test('declare les cinq champs POSIX dans le profil avance', () => {
  for (const field of [
    'uidNumber',
    'gidNumber',
    'unixHomeDirectory',
    'loginShell',
    'gecos'
  ]) {
    assert.match(
      source,
      new RegExp(`field: '${field}'`)
    )
  }
})

test('declare les alias POSIX', () => {
  for (const alias of [
    'uid_number',
    'gid_number',
    'unix_home_directory',
    'login_shell'
  ]) {
    assert.ok(
      source.includes(`'${alias}'`),
      alias
    )
  }
})

test('initialise les cinq valeurs depuis snapshot ou lookup', () => {
  for (const field of [
    'uidNumber',
    'gidNumber',
    'unixHomeDirectory',
    'loginShell',
    'gecos'
  ]) {
    assert.match(
      source,
      new RegExp(
        `${field}: getAdAttributeValue\\(`
      )
    )
  }
})

test('reutilise le chargement autoritatif non bloquant', () => {
  assert.match(
    source,
    /hasAuthoritativeUserAdvancedProfile/
  )

  assert.match(
    source,
    /getMissingUserAdvancedProfileFields/
  )

  assert.match(
    source,
    /getUserAdvancedProfilePatch/
  )

  assert.match(
    source,
    /updateDirtyFieldsRef\.current\.has/
  )
})
