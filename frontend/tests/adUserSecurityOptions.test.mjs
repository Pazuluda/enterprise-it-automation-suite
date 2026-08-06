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

const hook = fs.readFileSync(
  new URL(
    '../src/features/active-directory/hooks/useAdObjectUpdate.js',
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

const copyUtility = fs.readFileSync(
  new URL(
    '../src/features/active-directory/utils/adUserCopy.js',
    import.meta.url
  ),
  'utf8'
)

test(
  'initialise les deux options de securite depuis AD',
  () => {
    assert.match(
      hook,
      /smartcardLogonRequired:[\s\S]*'smartcard_logon_required'/
    )

    assert.match(
      hook,
      /accountNotDelegated:[\s\S]*'account_not_delegated'/
    )
  }
)

test(
  'exige les quatre booleens autoritatifs',
  () => {
    assert.match(
      hook,
      /hasAuthoritativeUserAccountOptions[\s\S]*smartcardLogonRequired/
    )

    assert.match(
      hook,
      /hasAuthoritativeUserAccountOptions[\s\S]*accountNotDelegated/
    )
  }
)

test(
  'affiche un panneau de securite dedie',
  () => {
    assert.match(
      form,
      /Options de s\u00e9curit\u00e9 du compte/
    )

    assert.match(
      form,
      /Exiger une carte \u00e0 puce/
    )

    assert.match(
      form,
      /Compte sensible et non d\u00e9l\u00e9gable/
    )
  }
)

test(
  'utilise deux cases controlees independantes',
  () => {
    assert.match(
      form,
      /updateForm\.smartcardLogonRequired[\s\S]*=== true/
    )

    assert.match(
      form,
      /updateForm\.accountNotDelegated[\s\S]*=== true/
    )

    assert.match(
      form,
      /'smartcardLogonRequired',[\s\S]*event\.target\.checked/
    )

    assert.match(
      form,
      /'accountNotDelegated',[\s\S]*event\.target\.checked/
    )
  }
)

test(
  'affiche les valeurs dans les proprietes utilisateur',
  () => {
    assert.match(
      panel,
      /Carte \u00e0 puce obligatoire[\s\S]*smartcard_logon_required/
    )

    assert.match(
      panel,
      /Compte sensible non d\u00e9l\u00e9gable[\s\S]*account_not_delegated/
    )
  }
)

test(
  'exclut les options de securite de la copie utilisateur',
  () => {
    for (const forbidden of [
      'smartcardLogonRequired',
      'smartcard_logon_required',
      'SmartcardLogonRequired',
      'accountNotDelegated',
      'account_not_delegated',
      'AccountNotDelegated',
    ]) {
      assert.match(
        copyUtility,
        new RegExp(`['"]${forbidden}['"]`)
      )
    }
  }
)

test(
  'ne propose pas les options de delegation dangereuses',
  () => {
    assert.doesNotMatch(
      form,
      /DoesNotRequirePreAuth/
    )

    assert.doesNotMatch(
      form,
      /TrustedForDelegation/
    )
  }
)
