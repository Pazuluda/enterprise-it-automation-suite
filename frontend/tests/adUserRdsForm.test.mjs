import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const form = fs.readFileSync(
  new URL(
    '../src/features/active-directory/components/UpdateObjectForm.jsx',
    import.meta.url
  ),
  'utf8'
)

const rdsFields = [
  'msTSAllowLogon',
  'msTSProfilePath',
  'msTSHomeDirectory',
  'msTSHomeDrive',
  'msTSInitialProgram',
  'msTSWorkDirectory',
]

test(
  'affiche une section RDS dediee',
  () => {
    assert.match(
      form,
      /Services Bureau à distance/
    )

    for (const field of rdsFields) {
      assert.match(
        form,
        new RegExp(`['"]${field}['"]`)
      )
    }
  }
)

test(
  'rend les trois etats de connexion RDS',
  () => {
    assert.match(
      form,
      /option value="inherit"[\s\S]*Non configur/
    )

    assert.match(
      form,
      /option value="allow"[\s\S]*Autoriser la connexion RDS/
    )

    assert.match(
      form,
      /option value="deny"[\s\S]*Refuser la connexion RDS/
    )
  }
)

test(
  'desactive uniquement les champs RDS inconnus',
  () => {
    assert.match(
      form,
      /includes\('msTSAllowLogon'\)/
    )

    assert.match(
      form,
      /name\.startsWith\('msTS'\)[\s\S]*includes\(name\)/
    )
  }
)

test(
  'valide et normalise le lecteur RDS',
  () => {
    assert.match(
      form,
      /name === 'msTSHomeDrive'[\s\S]*'\[A-Za-z\]:'/
    )

    assert.match(
      form,
      /name === 'msTSHomeDrive'[\s\S]*toUpperCase/
    )

    assert.match(
      form,
      /name === 'msTSHomeDrive'[\s\S]*\? 2/
    )
  }
)

test(
  'borne les textes RDS selon le schema',
  () => {
    assert.match(
      form,
      /name\.startsWith\('msTS'\)[\s\S]*\? 32767/
    )
  }
)

test(
  'n expose pas les options RDS avancees',
  () => {
    for (const forbidden of [
      'msTSRemoteControl',
      'msTSMaxIdleTime',
      'msTSMaxConnectionTime',
      'msTSBrokenConnectionAction',
      'msTSReconnectionAction',
      'msTSConnectClientDrives',
      'msTSConnectPrinterDrives',
      'msTSDefaultToMainPrinter',
    ]) {
      assert.doesNotMatch(
        form,
        new RegExp(forbidden)
      )
    }
  }
)
