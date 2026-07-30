import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const appSource = readFileSync(
  new URL('../src/App.jsx', import.meta.url),
  'utf8'
)

const settingsSource = readFileSync(
  new URL(
    '../src/components/SettingsPage.jsx',
    import.meta.url
  ),
  'utf8'
)

let passed = 0

function test(name, callback) {
  callback()
  passed += 1
  console.log(`OK - ${name}`)
}

test(
  'expose le compte EITAS Identity dans le tableau de bord',
  () => {
    assert.match(
      appSource,
      /Mon compte EITAS Identity/
    )

    assert.match(
      appSource,
      /\/auth\/realms\/eitas\/account\//
    )
  }
)

test(
  'limite administration Identity aux responsables sécurité',
  () => {
    assert.match(
      appSource,
      /canManageSecurity[\s\S]{0,900}Administrer EITAS Identity/
    )

    assert.match(
      settingsSource,
      /canManageSecurity[\s\S]{0,900}Administrer EITAS Identity/
    )
  }
)

test(
  'utilise la console administration du realm eitas',
  () => {
    assert.match(
      appSource,
      /\/auth\/admin\/master\/console\/#\/eitas/
    )

    assert.match(
      settingsSource,
      /\/auth\/admin\/master\/console\/#\/eitas/
    )
  }
)

test(
  'ouvre les accès Identity dans un nouvel onglet protégé',
  () => {
    for (const source of [appSource, settingsSource]) {
      assert.match(source, /'_blank'/)
      assert.match(source, /'noopener,noreferrer'/)
    }
  }
)

test(
  'transmet le droit sécurité à SettingsPage',
  () => {
    assert.match(
      appSource,
      /<SettingsPage[\s\S]{0,400}canManageSecurity=\{canManageSecurity\}/
    )

    assert.match(
      settingsSource,
      /function SettingsPage\(\{[\s\S]{0,300}canManageSecurity/
    )
  }
)

console.log(
  `ACCES EITAS IDENTITY : ${passed} TESTS REUSSIS`
)
