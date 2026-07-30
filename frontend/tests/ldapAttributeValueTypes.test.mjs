import assert from 'node:assert/strict'

import {
  LDAP_INTEGER_BOUNDS,
  LDAP_SUPPORTED_VALUE_TYPES,
  formatLdapTypedEditorValue,
  normalizeLdapTypedEditorValue,
  normalizeLdapValueType,
  parseLdapTypedInputValue,
} from '../src/features/active-directory/utils/ldapAttributeValueTypes.js'

import {
  LDAP_ATTRIBUTE_EDITOR_DEFINITIONS,
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
  'déclare explicitement quatre types',
  () => {
    assert.deepEqual(
      [...LDAP_SUPPORTED_VALUE_TYPES],
      [
        'single_text',
        'boolean',
        'integer32',
        'integer64',
      ]
    )
  }
)

test(
  'normalise le nom du type',
  () => {
    assert.equal(
      normalizeLdapValueType(
        ' INTEGER32 '
      ),
      'integer32'
    )

    assert.throws(
      () =>
        normalizeLdapValueType(
          'binary'
        ),
      /non pris en charge/
    )
  }
)

test(
  'normalise une valeur texte',
  () => {
    assert.equal(
      normalizeLdapTypedEditorValue({
        valueType: 'single_text',
        value: ' Interne ',
        minLength: 1,
        maxLength: 20,
      }),
      'Interne'
    )
  }
)

test(
  'valide strictement les booléens',
  () => {
    assert.equal(
      normalizeLdapTypedEditorValue({
        valueType: 'boolean',
        value: true,
      }),
      true
    )

    assert.throws(
      () =>
        normalizeLdapTypedEditorValue({
          valueType: 'boolean',
          value: 'true',
        }),
      /booléenne/
    )
  }
)

test(
  'convertit les entrées booléennes UI',
  () => {
    assert.equal(
      parseLdapTypedInputValue(
        'boolean',
        'true'
      ),
      true
    )

    assert.equal(
      parseLdapTypedInputValue(
        'boolean',
        'false'
      ),
      false
    )
  }
)

test(
  'convertit une entrée entière UI',
  () => {
    const value =
      parseLdapTypedInputValue(
        'integer32',
        '42'
      )

    assert.equal(value, 42)
    assert.equal(typeof value, 'number')

    assert.throws(
      () =>
        parseLdapTypedInputValue(
          'integer32',
          '4.2'
        ),
      /entière/
    )
  }
)

test(
  'applique les bornes integer32',
  () => {
    assert.equal(
      normalizeLdapTypedEditorValue({
        valueType: 'integer32',
        value: 42,
      }),
      42
    )

    assert.throws(
      () =>
        normalizeLdapTypedEditorValue({
          valueType: 'integer32',
          value: 2147483648,
        }),
      /maximum/
    )
  }
)

test(
  'applique les bornes personnalisées',
  () => {
    assert.throws(
      () =>
        normalizeLdapTypedEditorValue({
          valueType: 'integer32',
          value: -1,
          minValue: 0,
          maxValue: 100,
        }),
      /minimum/
    )

    assert.throws(
      () =>
        normalizeLdapTypedEditorValue({
          valueType: 'integer32',
          value: 101,
          minValue: 0,
          maxValue: 100,
        }),
      /maximum/
    )
  }
)

test(
  'protège la précision integer64',
  () => {
    assert.equal(
      LDAP_INTEGER_BOUNDS
        .integer64
        .maximum,
      Number.MAX_SAFE_INTEGER
    )

    assert.throws(
      () =>
        parseLdapTypedInputValue(
          'integer64',
          '9223372036854775807'
        ),
      /précision sûre/
    )
  }
)

test(
  'formate les valeurs typées',
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

    assert.equal(
      formatLdapTypedEditorValue(
        'integer32',
        42
      ),
      '42'
    )
  }
)

test(
  'ne publie aucun nouvel attribut',
  () => {
    assert.deepEqual(
      LDAP_ATTRIBUTE_EDITOR_DEFINITIONS
        .map(item => item.name),
      [
        'employeeType',
        'preferredLanguage',
        'personalTitle',
        'middleName',
        'comment',
      ]
    )
  }
)

if (failures > 0) {
  process.exitCode = 1
} else {
  console.log(
    'VALIDATION TYPES LDAP FRONTEND : 11 TESTS REUSSIS'
  )
}
