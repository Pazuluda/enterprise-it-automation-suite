import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const hook = fs.readFileSync(
  new URL(
    '../src/features/active-directory/hooks/useAdObjectUpdate.js',
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
  'declare les six champs RDS avec leurs alias',
  () => {
    for (const field of [
      ...camelFields,
      ...snakeFields,
    ]) {
      assert.match(
        hook,
        new RegExp(`['"]${field}['"]`)
      )
    }
  }
)

test(
  'preserve les trois etats de msTSAllowLogon',
  () => {
    assert.match(
      hook,
      /value === 'allow'[\s\S]*return true/
    )

    assert.match(
      hook,
      /value === 'deny'[\s\S]*return false/
    )

    assert.match(
      hook,
      /function getMsTsAllowLogonSubmissionValue[\s\S]*return null/
    )
  }
)

test(
  'initialise le formulaire depuis snapshot ou lookup',
  () => {
    assert.match(
      hook,
      /msTSAllowLogon:[\s\S]*getMsTsAllowLogonFormValue/
    )

    for (const field of camelFields.slice(1)) {
      assert.match(
        hook,
        new RegExp(
          `${field}:[\\s\\S]*['"]${field}['"]`
        )
      )
    }
  }
)

test(
  'charge les champs RDS manquants en arriere-plan',
  () => {
    assert.match(
      hook,
      /getMissingUserRdsProfileFields/
    )

    assert.match(
      hook,
      /pendingAccountFields[\s\S]*getMissingUserRdsProfileFields/
    )

    assert.match(
      hook,
      /getUserRdsProfilePatch/
    )
  }
)

test(
  'preserve les saisies et rejette les reponses obsoletes',
  () => {
    assert.match(
      hook,
      /updateDirtyFieldsRef\.current\.has/
    )

    assert.match(
      hook,
      /updatePreparationRequestIdRef\.current/
    )
  }
)

test(
  'convertit msTSAllowLogon dans le payload API',
  () => {
    assert.match(
      hook,
      /key === 'msTSAllowLogon'[\s\S]*getMsTsAllowLogonSubmissionValue/
    )
  }
)
