import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(
  new URL(
    '../src/features/active-directory/'
      + 'components/UpdateObjectForm.jsx',
    import.meta.url
  ),
  'utf8'
)

test('affiche une section Unix POSIX dediee', () => {
  assert.match(
    source,
    /title: 'Profil Unix \/ POSIX'/
  )

  assert.match(
    source,
    /Identifiant utilisateur Unix \(UID\)/
  )

  assert.match(
    source,
    /Identifiant de groupe Unix \(GID\)/
  )
})

test('utilise les cinq attributs POSIX canoniques', () => {
  for (const field of [
    'uidNumber',
    'gidNumber',
    'unixHomeDirectory',
    'loginShell',
    'gecos'
  ]) {
    assert.ok(source.includes(`'${field}'`), field)
  }
})

test('utilise des controles Integer32 pour UID et GID', () => {
  assert.match(
    source,
    /name === 'uidNumber'/
  )

  assert.match(
    source,
    /name === 'gidNumber'/
  )

  assert.match(
    source,
    /type="number"/
  )

  assert.match(
    source,
    /min=\{-2147483648\}/
  )

  assert.match(
    source,
    /max=\{2147483647\}/
  )
})

test('applique les limites du schema POSIX', () => {
  assert.match(
    source,
    /name === 'unixHomeDirectory'[\s\S]*?2048/
  )

  assert.match(
    source,
    /name === 'loginShell'[\s\S]*?1024/
  )

  assert.match(
    source,
    /maxLength=\{10240\}/
  )
})

test('utilise une zone multiligne pour GECOS', () => {
  assert.match(
    source,
    /name === 'gecos'[\s\S]*?<textarea/
  )

  assert.match(
    source,
    /value=\{updateForm\.gecos \|\| ''\}/
  )
})

test('protege les champs POSIX pendant le chargement', () => {
  assert.match(
    source,
    /pendingUserAccountOptionFields/
  )

  assert.match(
    source,
    /includes\(name\)/
  )

  assert.match(
    source,
    /includes\('gecos'\)/
  )
})
