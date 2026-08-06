import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const details = readFileSync(
  new URL(
    '../src/features/active-directory/'
      + 'components/ObjectDetailsPanel.jsx',
    import.meta.url
  ),
  'utf8'
)

const copyPolicy = readFileSync(
  new URL(
    '../src/features/active-directory/'
      + 'utils/adUserCopy.js',
    import.meta.url
  ),
  'utf8'
)

test('affiche les cinq proprietes POSIX', () => {
  for (const label of [
    'UID Unix',
    'GID Unix',
    'Répertoire personnel Unix',
    'Shell de connexion',
    'Informations GECOS'
  ]) {
    assert.ok(details.includes(label), label)
  }
})

test('lit les alias canoniques et normalises', () => {
  for (const field of [
    'uid_number',
    'uidNumber',
    'gid_number',
    'gidNumber',
    'unix_home_directory',
    'unixHomeDirectory',
    'login_shell',
    'loginShell',
    'gecos'
  ]) {
    assert.ok(details.includes(`'${field}'`), field)
  }
})

test('exclut le profil POSIX de la copie utilisateur', () => {
  for (const field of [
    'uidNumber',
    'uid_number',
    'gidNumber',
    'gid_number',
    'unixHomeDirectory',
    'unix_home_directory',
    'loginShell',
    'login_shell',
    'gecos'
  ]) {
    assert.ok(
      copyPolicy.includes(`'${field}'`),
      field
    )
  }
})
