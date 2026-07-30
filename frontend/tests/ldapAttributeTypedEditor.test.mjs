import assert from 'node:assert/strict'

import {
  LDAP_ATTRIBUTE_EDITOR_DEFINITIONS,
  buildLdapAttributeEditorChanges,
  createLdapAttributeEditorDraft,
  getLdapEditorDefinitionValueType,
  normalizeLdapEditorValueForDefinition,
  readLdapEditorValueForDefinition,
} from '../src/features/active-directory/utils/ldapAttributeEditor.js'

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
  'déclare cinq attributs texte',
  () => {
    assert.equal(
      LDAP_ATTRIBUTE_EDITOR_DEFINITIONS
        .length,
      5
    )

    assert.equal(
      LDAP_ATTRIBUTE_EDITOR_DEFINITIONS
        .every(
          definition =>
            definition.valueType ===
            'single_text'
        ),
      true
    )
  }
)

test(
  'conserve la normalisation texte',
  () => {
    assert.equal(
      normalizeLdapEditorValueForDefinition(
        {
          valueType: 'single_text',
          minLength: 1,
          maxLength: 20,
        },
        ' Interne '
      ),
      'Interne'
    )
  }
)

test(
  'normalise un booléen futur',
  () => {
    const definition = {
      valueType: 'boolean',
    }

    assert.equal(
      normalizeLdapEditorValueForDefinition(
        definition,
        true
      ),
      true
    )

    assert.equal(
      normalizeLdapEditorValueForDefinition(
        definition,
        'false'
      ),
      false
    )
  }
)

test(
  'normalise un entier futur',
  () => {
    const value =
      normalizeLdapEditorValueForDefinition(
        {
          valueType: 'integer32',
          minValue: 0,
          maxValue: 100,
        },
        '42'
      )

    assert.equal(value, 42)
    assert.equal(typeof value, 'number')

    assert.throws(
      () =>
        normalizeLdapEditorValueForDefinition(
          {
            valueType: 'integer32',
            minValue: 0,
            maxValue: 100,
          },
          '101'
        ),
      /maximum/
    )
  }
)

test(
  'lit les valeurs snapshot typées',
  () => {
    assert.equal(
      readLdapEditorValueForDefinition(
        { valueType: 'boolean' },
        'false'
      ),
      false
    )

    assert.equal(
      readLdapEditorValueForDefinition(
        { valueType: 'integer32' },
        '42'
      ),
      42
    )
  }
)

test(
  'expose le type dans le brouillon',
  () => {
    const draft =
      createLdapAttributeEditorDraft({
        object_class: 'user',
        distinguished_name:
          'CN=Test,OU=Users,DC=API,DC=LOCAL',
      })

    assert.equal(draft.length, 5)

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

test(
  'préserve les types des changements',
  () => {
    const changes =
      buildLdapAttributeEditorChanges([
        {
          attribute_name:
            'futureBoolean',
          operation: 'set',
          value: true,
        },
        {
          attribute_name:
            'futureInteger',
          operation: 'set',
          value: 42,
        },
      ])

    assert.equal(
      changes[0].value,
      true
    )
    assert.equal(
      typeof changes[0].value,
      'boolean'
    )

    assert.equal(
      changes[1].value,
      42
    )
    assert.equal(
      typeof changes[1].value,
      'number'
    )
  }
)

test(
  'le type par défaut reste texte',
  () => {
    assert.equal(
      getLdapEditorDefinitionValueType(
        {}
      ),
      'single_text'
    )
  }
)

if (failures > 0) {
  process.exitCode = 1
} else {
  console.log(
    'INTEGRATION TYPES LDAP UTILITAIRE : 8 TESTS REUSSIS'
  )
}
