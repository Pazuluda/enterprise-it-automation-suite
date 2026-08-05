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
    '../src/features/active-directory/hooks/useAdObjectUpdate.js',
    import.meta.url
  ),
  'utf8'
)

const modal = fs.readFileSync(
  new URL(
    '../src/features/active-directory/components/AdObjectPropertiesModal.jsx',
    import.meta.url
  ),
  'utf8'
)

test(
  'reutilise le lookup utilisateur detaille',
  () => {
    assert.match(
      page,
      /async function resolveUserUpdateTarget/
    )

    assert.match(
      page,
      /await runAdUserDetailsJob\(target\)/
    )

    assert.match(
      page,
      /mergeAdUserDetails\([\s\S]*target,[\s\S]*details/
    )

    assert.match(
      page,
      /resolveUserUpdateTarget,/
    )
  }
)

test(
  'exige les deux valeurs booleennes autoritatives',
  () => {
    assert.match(
      hook,
      /hasAuthoritativeUserAccountOptions/
    )

    assert.match(
      hook,
      /'password_never_expires'/
    )

    assert.match(
      hook,
      /'cannot_change_password'/
    )
  }
)

test(
  'charge les details avant de construire le formulaire',
  () => {
    assert.match(
      hook,
      /async function prepareUpdateObject/
    )

    assert.match(
      hook,
      /await resolveUserUpdateTarget\(target\)/
    )

    assert.match(
      hook,
      /target = resolvedTarget/
    )
  }
)

test(
  'bloque l edition quand la source detaillee echoue',
  () => {
    assert.match(
      hook,
      /Modification bloquée/
    )

    assert.match(
      hook,
      /return false/
    )

    assert.match(
      hook,
      /setUpdateSaveError\(message\)/
    )
  }
)

test(
  'attend la preparation dans la modale integree',
  () => {
    assert.match(
      modal,
      /async function beginEditing/
    )

    assert.match(
      modal,
      /await update\?\.prepareUpdateObject/
    )

    assert.match(
      modal,
      /async function beginClearingManager/
    )

    assert.match(
      modal,
      /await update\?\.prepareClearManager/
    )
  }
)

test(
  'securise aussi le retrait du gestionnaire',
  () => {
    assert.match(
      hook,
      /async function prepareClearManager/
    )

    assert.match(
      hook,
      /const prepared = await prepareUpdateObject/
    )
  }
)

console.log(
  'C3.3 SOURCE DE VERITE UTILISATEUR : TESTS REUSSIS'
)
