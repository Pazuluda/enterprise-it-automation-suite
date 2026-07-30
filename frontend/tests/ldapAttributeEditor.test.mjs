import assert from 'node:assert/strict'

import {
  buildLdapAttributeUpdatePayload,
  buildLdapAttributeEditorChanges,
  buildLdapAttributeEditorPreview,
  createLdapAttributeEditorDraft,
  getLdapAttributeEditorChangeCount,
  getLdapEditorCurrentValue,
  getLdapEditorDefinitions,
  normalizeLdapEditorObjectClass,
  updateLdapAttributeEditorDraft,
} from '../src/features/active-directory/utils/ldapAttributeEditor.js'

let passed = 0

function test(name, callback) {
  callback()
  passed += 1
  console.log(`OK - ${name}`)
}

const user = {
  type: 'user',
  distinguished_name:
    'CN=Liam Ve,OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL',
  employee_type: 'Interne',
}

const contact = {
  objectClass: [
    'top',
    'person',
    'organizationalPerson',
    'contact',
  ],
  dn:
    'CN=Contact Test,OU=Contacts,OU=EITAS,DC=API,DC=LOCAL',
}

test(
  'détecte correctement la classe utilisateur',
  () => {
    assert.equal(
      normalizeLdapEditorObjectClass(user),
      'user'
    )
  }
)

test(
  'priorise computer sur user dans objectClass',
  () => {
    assert.equal(
      normalizeLdapEditorObjectClass({
        objectClass: [
          'top',
          'person',
          'user',
          'computer',
        ],
      }),
      'computer'
    )
  }
)

test(
  'expose cinq attributs pour un utilisateur',
  () => {
    assert.deepEqual(
      getLdapEditorDefinitions(user)
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

test(
  'expose trois attributs pour un contact',
  () => {
    assert.deepEqual(
      getLdapEditorDefinitions(contact)
        .map(item => item.name),
      [
        'personalTitle',
        'middleName',
        'comment',
      ]
    )
  }
)

test(
  'n’expose rien pour un ordinateur',
  () => {
    assert.equal(
      getLdapEditorDefinitions({
        type: 'computer',
      }).length,
      0
    )
  }
)

test(
  'lit les alias snake_case du snapshot',
  () => {
    assert.equal(
      getLdapEditorCurrentValue(
        user,
        'employeeType'
      ),
      'Interne'
    )
  }
)

test(
  'construit un payload set et clear',
  () => {
    assert.deepEqual(
      buildLdapAttributeUpdatePayload({
        object: user,
        changes: [
          {
            attribute_name:
              'employeeType',
            operation: 'set',
            value: ' Externe ',
          },
          {
            attribute_name:
              'preferredLanguage',
            operation: 'clear',
          },
        ],
      }),
      {
        action:
          'update_ldap_attributes',
        object_identity:
          user.distinguished_name,
        object_class: 'user',
        changes: [
          {
            attribute_name:
              'employeeType',
            operation: 'set',
            value: 'Externe',
          },
          {
            attribute_name:
              'preferredLanguage',
            operation: 'clear',
            value: null,
          },
        ],
      }
    )
  }
)

test(
  'refuse un attribut dupliqué',
  () => {
    assert.throws(
      () =>
        buildLdapAttributeUpdatePayload({
          object: user,
          changes: [
            {
              attribute_name:
                'comment',
              operation: 'set',
              value: 'A',
            },
            {
              attribute_name:
                'comment',
              operation: 'clear',
            },
          ],
        }),
      /qu’une fois/
    )
  }
)

test(
  'refuse employeeType pour un contact',
  () => {
    assert.throws(
      () =>
        buildLdapAttributeUpdatePayload({
          object: contact,
          changes: [{
            attribute_name:
              'employeeType',
            operation: 'set',
            value: 'Interne',
          }],
        }),
      /n’est pas autorisé/
    )
  }
)

test(
  'refuse set avec une valeur vide',
  () => {
    assert.throws(
      () =>
        buildLdapAttributeUpdatePayload({
          object: user,
          changes: [{
            attribute_name:
              'middleName',
            operation: 'set',
            value: '   ',
          }],
        }),
      /ne peut pas être vide/
    )
  }
)

test(
  'refuse les retours à la ligne',
  () => {
    assert.throws(
      () =>
        buildLdapAttributeUpdatePayload({
          object: user,
          changes: [{
            attribute_name:
              'comment',
            operation: 'set',
            value: 'Ligne 1\nLigne 2',
          }],
        }),
      /caractère interdit/
    )
  }
)

test(
  'refuse une valeur trop longue',
  () => {
    assert.throws(
      () =>
        buildLdapAttributeUpdatePayload({
          object: user,
          changes: [{
            attribute_name:
              'preferredLanguage',
            operation: 'set',
            value: 'x'.repeat(65),
          }],
        }),
      /dépasse 64/
    )
  }
)


test(
  'crée un brouillon utilisateur complet',
  () => {
    const draft =
      createLdapAttributeEditorDraft(user)

    assert.equal(draft.length, 5)

    const employeeType = draft.find(
      item =>
        item.attribute_name ===
        'employeeType'
    )

    assert.equal(
      employeeType.original_value,
      'Interne'
    )

    assert.equal(
      employeeType.operation,
      'unchanged'
    )
  }
)

test(
  'met à jour le brouillon sans mutation',
  () => {
    const original =
      createLdapAttributeEditorDraft(user)

    const updated =
      updateLdapAttributeEditorDraft(
        original,
        'employeeType',
        {
          operation: 'set',
          value: 'Externe',
        }
      )

    assert.equal(
      original[0].operation,
      'unchanged'
    )

    assert.equal(
      updated[0].operation,
      'set'
    )

    assert.equal(
      updated[0].value,
      'Externe'
    )
  }
)

test(
  'ignore les attributs inchangés',
  () => {
    const draft =
      createLdapAttributeEditorDraft(user)

    assert.deepEqual(
      buildLdapAttributeEditorChanges(
        draft
      ),
      []
    )
  }
)

test(
  'construit une opération clear',
  () => {
    const draft =
      updateLdapAttributeEditorDraft(
        createLdapAttributeEditorDraft(
          user
        ),
        'preferredLanguage',
        {
          operation: 'clear',
        }
      )

    assert.deepEqual(
      buildLdapAttributeEditorChanges(
        draft
      ),
      [{
        attribute_name:
          'preferredLanguage',
        operation: 'clear',
        value: null,
      }]
    )
  }
)

test(
  'compte uniquement les changements actifs',
  () => {
    let draft =
      createLdapAttributeEditorDraft(user)

    draft =
      updateLdapAttributeEditorDraft(
        draft,
        'employeeType',
        {
          operation: 'set',
          value: 'Externe',
        }
      )

    draft =
      updateLdapAttributeEditorDraft(
        draft,
        'comment',
        {
          operation: 'clear',
        }
      )

    assert.equal(
      getLdapAttributeEditorChangeCount(
        draft
      ),
      2
    )
  }
)

test(
  'construit un aperçu before after',
  () => {
    const draft =
      updateLdapAttributeEditorDraft(
        createLdapAttributeEditorDraft(
          user
        ),
        'employeeType',
        {
          operation: 'set',
          value: 'Externe',
        }
      )

    const preview =
      buildLdapAttributeEditorPreview({
        object: user,
        draft,
      })

    assert.equal(
      preview.change_count,
      1
    )

    assert.deepEqual(
      preview.rows[0],
      {
        attribute_name:
          'employeeType',
        label:
          'Type d’employé',
        operation: 'set',
        value_type: 'single_text',
        before: 'Interne',
        after: 'Externe',
      }
    )

    assert.equal(
      preview.payload.object_class,
      'user'
    )
  }
)

test(
  'refuse une opération de brouillon inconnue',
  () => {
    assert.throws(
      () =>
        updateLdapAttributeEditorDraft(
          createLdapAttributeEditorDraft(
            user
          ),
          'employeeType',
          {
            operation: 'delete',
          }
        ),
      /Opération LDAP invalide/
    )
  }
)

test(
  'refuse un attribut absent du brouillon',
  () => {
    assert.throws(
      () =>
        updateLdapAttributeEditorDraft(
          [],
          'employeeType',
          {
            operation: 'set',
            value: 'Interne',
          }
        ),
      /ne contient pas/
    )
  }
)

console.log(
  `VALIDATION LDAP FRONTEND : ${passed} TESTS REUSSIS`
)
