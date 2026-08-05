import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const page = fs.readFileSync(
  new URL(
    '../src/features/active-directory/AdExplorerPage.jsx',
    import.meta.url
  ),
  'utf8'
)

const hook = fs.readFileSync(
  new URL(
    '../src/features/active-directory/hooks/useAdAccountActions.js',
    import.meta.url
  ),
  'utf8'
)

const panel = fs.readFileSync(
  new URL(
    '../src/features/active-directory/components/ObjectDetailsPanel.jsx',
    import.meta.url
  ),
  'utf8'
)

test(
  'centralise la resolution des etats de compte',
  () => {
    assert.match(
      hook,
      /getAdAccountToggleAction/
    )

    assert.match(
      panel,
      /getAdAccountStatus/
    )

    assert.match(
      panel,
      /getAdAccountStatusClass/
    )

    assert.doesNotMatch(
      panel,
      /function getAccountStatus\(/
    )

    assert.doesNotMatch(
      page,
      /function getSelectedAccountEnabledState\(/
    )

    assert.doesNotMatch(
      hook,
      /getSelectedAccountEnabledState/
    )
  }
)

test(
  'actualise la cible utilisateur apres le job',
  () => {
    assert.match(
      page,
      /async function refreshAccountTarget\(target\)/
    )

    assert.match(
      page,
      /await runAdUserDetailsJob\(target\)/
    )

    assert.match(
      page,
      /setSelectedObject\(mergeTarget\)/
    )

    assert.match(
      page,
      /setPropertiesModal\(mergeTarget\)/
    )

    assert.match(
      page,
      /setViewItems\(items =>/
    )

    assert.match(
      hook,
      /await refreshAccountTarget\(/
    )
  }
)

test(
  'bloque les actions de compte incoherentes',
  () => {
    assert.match(
      panel,
      /\|\| !accountToggleAction/
    )

    assert.match(
      panel,
      /accountLocked !== true/
    )

    assert.match(
      panel,
      /accountToggleAction === 'enable_account'/
    )
  }
)

console.log(
  'C3.1 ACTIONS COMPTE : TESTS REUSSIS'
)
