import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const modal = fs.readFileSync(
  new URL(
    '../src/features/active-directory/components/AccountActionModal.jsx',
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

const css = fs.readFileSync(
  new URL(
    '../src/styles/07-active-directory.css',
    import.meta.url
  ),
  'utf8'
)

test(
  'masque le mot de passe et permet son affichage controle',
  () => {
    assert.match(
      modal,
      /getAdPasswordResetInputType/
    )

    assert.match(
      modal,
      /showPassword/
    )

    assert.match(
      modal,
      /Afficher/
    )

    assert.match(
      modal,
      /Masquer/
    )

    assert.match(
      modal,
      /autoComplete="new-password"/
    )
  }
)

test(
  'expose les deux choix de reset',
  () => {
    assert.match(
      modal,
      /forceChangeAtLogon/
    )

    assert.match(
      modal,
      /unlockAfterReset/
    )

    assert.match(
      modal,
      /type="checkbox"/
    )
  }
)

test(
  'construit le payload avec l utilitaire securise',
  () => {
    assert.match(
      hook,
      /buildAdPasswordResetPayload/
    )

    assert.match(
      hook,
      /Object\.assign/
    )

    assert.doesNotMatch(
      hook,
      /payload\.force_change_at_logon = true/
    )

    assert.doesNotMatch(
      hook,
      /payload\.unlock_after_reset = true/
    )
  }
)

test(
  'ajoute les styles de la modale avancee',
  () => {
    assert.match(
      css,
      /\.aduc-password-input-row/
    )

    assert.match(
      css,
      /\.aduc-password-reset-options/
    )
  }
)

console.log(
  'C3.2 INTEGRATION RESET : TESTS REUSSIS'
)
