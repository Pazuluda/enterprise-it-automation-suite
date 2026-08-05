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

const form = fs.readFileSync(
  new URL(
    '../src/features/active-directory/components/UpdateObjectForm.jsx',
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
  'initialise les options avec leurs alias AD',
  () => {
    assert.match(
      hook,
      /passwordNeverExpires:[\s\S]*'password_never_expires'/
    )

    assert.match(
      hook,
      /cannotChangePassword:[\s\S]*'cannot_change_password'/
    )
  }
)

test(
  'regroupe les options dans un panneau unique',
  () => {
    assert.match(
      form,
      /key="passwordAccountOptions"/
    )

    assert.match(
      form,
      /className="aduc-account-options-group"/
    )

    assert.match(
      form,
      /Options du mot de passe/
    )
  }
)

test(
  'affiche les deux options avec leurs descriptions',
  () => {
    assert.match(
      form,
      /Le mot de passe n’expire jamais/
    )

    assert.match(
      form,
      /L’utilisateur ne peut pas changer/
    )

    assert.match(
      form,
      /Désactive l’expiration automatique/
    )

    assert.match(
      form,
      /Seul un administrateur autorisé/
    )
  }
)

test(
  'utilise deux cases controlees independantes',
  () => {
    assert.match(
      form,
      /updateForm\.passwordNeverExpires[\s\S]*=== true/
    )

    assert.match(
      form,
      /updateForm\.cannotChangePassword[\s\S]*=== true/
    )

    assert.match(
      form,
      /'passwordNeverExpires',[\s\S]*event\.target\.checked/
    )

    assert.match(
      form,
      /'cannotChangePassword',[\s\S]*event\.target\.checked/
    )
  }
)

test(
  'masque le second emplacement historique',
  () => {
    assert.match(
      form,
      /name === 'cannotChangePassword'[\s\S]*return null/
    )
  }
)

test(
  'utilise une presentation compacte sur toute la largeur',
  () => {
    assert.match(
      css,
      /\.aduc-account-options-group/
    )

    assert.match(
      css,
      /grid-column: 1 \/ -1/
    )

    assert.match(
      css,
      /\.aduc-account-option-row/
    )

    assert.match(
      css,
      /\.aduc-account-option-copy/
    )

    assert.doesNotMatch(
      form,
      /aduc-account-option-field/
    )
  }
)

console.log(
  'C3.3 OPTIONS UTILISATEUR COMPACTES : TESTS REUSSIS'
)
