import assert from 'node:assert/strict'
import {
  readFileSync,
} from 'node:fs'

const hook = readFileSync(
  new URL(
    '../src/features/active-directory/'
      + 'hooks/useLdapAttributeUpdate.js',
    import.meta.url
  ),
  'utf8'
)

const component = readFileSync(
  new URL(
    '../src/features/active-directory/'
      + 'components/LdapAttributeEditor.jsx',
    import.meta.url
  ),
  'utf8'
)

const modal = readFileSync(
  new URL(
    '../src/features/active-directory/'
      + 'components/AdObjectPropertiesModal.jsx',
    import.meta.url
  ),
  'utf8'
)

const page = readFileSync(
  new URL(
    '../src/features/active-directory/'
      + 'AdExplorerPage.jsx',
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
  'utilise exclusivement la route POST LDAP dédiée',
  () => {
    assert.match(
      hook,
      /\/api\/ad-explorer\/ldap\/update\/jobs/
    )

    assert.doesNotMatch(
      hook,
      /apiFetch\('\/api\/ad-admin\/jobs',\s*\{/
    )
  }
)

test(
  'utilise le stockage AD Admin uniquement pour le polling',
  () => {
    assert.match(
      hook,
      /\/api\/ad-admin\/jobs\/\$\{/
    )
  }
)

test(
  'refuse côté frontend hors Simulation',
  () => {
    const guard = hook.indexOf(
      'if (!isSimulationMode)'
    )

    const post = hook.indexOf(
      'LDAP_SIMULATION_JOB_PATH'
    )

    assert.ok(guard >= 0)
    assert.ok(post >= 0)
    assert.ok(guard < hook.lastIndexOf(
      'LDAP_SIMULATION_JOB_PATH'
    ))
  }
)

test(
  'exige un aperçu valide avant le POST',
  () => {
    assert.match(
      hook,
      /!previewState\.preview/
    )

    assert.match(
      hook,
      /changeCount === 0/
    )
  }
)

test(
  'demande une confirmation explicite',
  () => {
    assert.match(
      component,
      /window\.confirm/
    )

    assert.match(
      component,
      /Aucune écriture réelle/
    )
  }
)

test(
  'désactive le bouton hors Simulation',
  () => {
    assert.match(
      component,
      /!editor\?\.isSimulationMode/
    )

    assert.match(
      component,
      /Créer le job de simulation/
    )
  }
)

test(
  'transmet apiFetch sans gestion manuelle du Bearer',
  () => {
    assert.match(
      modal,
      /useLdapAttributeUpdate\(\{[\s\S]*apiFetch/
    )

    assert.match(
      page,
      /apiFetch=\{apiFetch\}/
    )

    assert.doesNotMatch(
      hook,
      /Authorization|Bearer/
    )
  }
)


test(
  'sérialise les résultats objet au lieu d’afficher object Object',
  () => {
    assert.match(
      component,
      /typeof result === 'object'/
    )

    assert.match(
      component,
      /JSON\.stringify/
    )

    assert.doesNotMatch(
      component,
      /String\(job\?\.output/
    )
  }
)

console.log(
  `INTEGRATION LDAP FRONTEND : `
  + `${passed} TESTS REUSSIS`
)
