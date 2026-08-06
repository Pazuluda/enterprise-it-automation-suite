import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const panel = fs.readFileSync(
  new URL(
    '../src/features/active-directory/components/ObjectDetailsPanel.jsx',
    import.meta.url
  ),
  'utf8'
)

const copyUtility = fs.readFileSync(
  new URL(
    '../src/features/active-directory/utils/adUserCopy.js',
    import.meta.url
  ),
  'utf8'
)

const camelFields = [
  'msTSAllowLogon',
  'msTSProfilePath',
  'msTSHomeDirectory',
  'msTSHomeDrive',
  'msTSInitialProgram',
  'msTSWorkDirectory',
]

const snakeFields = [
  'ms_ts_allow_logon',
  'ms_ts_profile_path',
  'ms_ts_home_directory',
  'ms_ts_home_drive',
  'ms_ts_initial_program',
  'ms_ts_work_directory',
]

test(
  'affiche les six valeurs RDS dans les proprietes',
  () => {
    assert.match(
      panel,
      /RDS — Connexion autorisée[\s\S]*msTsAllowLogonLabel/
    )

    assert.match(
      panel,
      /RDS — Chemin du profil/
    )

    assert.match(
      panel,
      /RDS — Dossier de base/
    )

    assert.match(
      panel,
      /RDS — Lecteur de connexion/
    )

    assert.match(
      panel,
      /RDS — Programme initial/
    )

    assert.match(
      panel,
      /RDS — Dossier de démarrage/
    )

    for (const field of [
      ...camelFields,
      ...snakeFields,
    ]) {
      assert.match(
        panel,
        new RegExp(`['"]${field}['"]`)
      )
    }
  }
)

test(
  'distingue valeur absente et refus explicite',
  () => {
    assert.match(
      panel,
      /msTsAllowLogonValue === null/
    )

    assert.match(
      panel,
      /msTsAllowLogonValue === undefined/
    )

    assert.match(
      panel,
      /Non configuré/
    )

    assert.match(
      panel,
      /boolLabel\(msTsAllowLogonValue\)/
    )
  }
)

test(
  'exclut les douze alias RDS de la copie',
  () => {
    for (const field of [
      ...camelFields,
      ...snakeFields,
    ]) {
      assert.match(
        copyUtility,
        new RegExp(`['"]${field}['"]`)
      )
    }
  }
)

test(
  'ne montre pas les options RDS avancees',
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
        panel,
        new RegExp(forbidden)
      )

      assert.doesNotMatch(
        copyUtility,
        new RegExp(forbidden)
      )
    }
  }
)
