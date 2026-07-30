import assert from 'node:assert/strict'
import fs from 'node:fs'

import {
  buildLdapAttributeEditorPreview,
  createLdapAttributeEditorDraft,
  updateLdapAttributeEditorDraft,
} from '../src/features/active-directory/utils/ldapAttributeEditor.js'

import {
  formatLdapTypedEditorValue,
} from '../src/features/active-directory/utils/ldapAttributeValueTypes.js'

const componentSource = fs.readFileSync(
  new URL(
    '../src/features/active-directory/components/LdapAttributeEditor.jsx',
    import.meta.url
  ),
  'utf8'
)

let failures = 0

function test(label, callback) {
  try {
    callback()
    console.log(`OK - ${label}`)
  } catch (error) {
    failures += 1
    console.error(`ECHEC - ${label}`)
    console.error(error)
  }
}

test(
  'importe le formateur typé',
  () => {
    assert.match(
      componentSource,
      /formatLdapTypedEditorValue/
    )
  }
)

test(
  'prévoit un sélecteur booléen',
  () => {
    assert.match(
      componentSource,
      /valueType === 'boolean'/
    )

    assert.match(
      componentSource,
      /<option value="true">/
    )

    assert.match(
      componentSource,
      /<option value="false">/
    )
  }
)

test(
  'prévoit un champ entier',
  () => {
    assert.match(
      componentSource,
      /valueType === 'integer32'/
    )

    assert.match(
      componentSource,
      /valueType === 'integer64'/
    )

    assert.match(
      componentSource,
      /type="number"/
    )

    assert.match(
      componentSource,
      /step="1"/
    )
  }
)

test(
  'conserve les contrôles texte',
  () => {
    assert.match(
      componentSource,
      /type="text"/
    )

    assert.match(
      componentSource,
      /<textarea/
    )
  }
)

test(
  'formate les booléens en français',
  () => {
    assert.equal(
      formatLdapTypedEditorValue(
        'boolean',
        true
      ),
      'Oui'
    )

    assert.equal(
      formatLdapTypedEditorValue(
        'boolean',
        false
      ),
      'Non'
    )
  }
)

test(
  'l’aperçu reçoit le type de valeur',
  () => {
    let draft =
      createLdapAttributeEditorDraft({
        object_class: 'user',
        distinguished_name:
          'CN=Test,OU=Users,DC=API,DC=LOCAL',
        employeeType: 'Interne',
      })

    draft =
      updateLdapAttributeEditorDraft(
        draft,
        'employeeType',
        {
          operation: 'set',
          value: 'Externe',
        }
      )

    const preview =
      buildLdapAttributeEditorPreview({
        object: {
          object_class: 'user',
          distinguished_name:
            'CN=Test,OU=Users,DC=API,DC=LOCAL',
        },
        draft,
      })

    assert.equal(
      preview.rows[0].value_type,
      'single_text'
    )

    assert.equal(
      preview.rows[0].after,
      'Externe'
    )
  }
)

test(
  'aucun attribut typé n’est public',
  () => {
    const draft =
      createLdapAttributeEditorDraft({
        object_class: 'user',
        distinguished_name:
          'CN=Test,OU=Users,DC=API,DC=LOCAL',
      })

    assert.equal(
      draft.every(
        entry =>
          entry.value_type ===
          'single_text'
      ),
      true
    )
  }
)

if (failures > 0) {
  process.exitCode = 1
} else {
  console.log(
    'INTEGRATION COMPOSANT LDAP TYPE : 7 TESTS REUSSIS'
  )
}
