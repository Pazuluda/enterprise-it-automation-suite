import {
  normalizeLdapTypedEditorValue,
  parseLdapTypedInputValue,
} from './ldapAttributeValueTypes.js'

const LDAP_ATTRIBUTE_UPDATE_ACTION =
  'update_ldap_attributes'

const LDAP_ATTRIBUTE_UPDATE_MAX_CHANGES = 5

const LDAP_ATTRIBUTE_EDITOR_DEFINITIONS =
  Object.freeze([
    Object.freeze({
      name: 'employeeType',
      valueType: 'single_text',
      label: 'Type d’employé',
      objectClasses: Object.freeze([
        'user',
      ]),
      minLength: 1,
      maxLength: 256,
      aliases: Object.freeze([
        'employeeType',
        'employee_type',
      ]),
    }),
    Object.freeze({
      name: 'preferredLanguage',
      valueType: 'single_text',
      label: 'Langue préférée',
      objectClasses: Object.freeze([
        'user',
      ]),
      minLength: 0,
      maxLength: 64,
      aliases: Object.freeze([
        'preferredLanguage',
        'preferred_language',
      ]),
    }),
    Object.freeze({
      name: 'personalTitle',
      valueType: 'single_text',
      label: 'Titre personnel',
      objectClasses: Object.freeze([
        'user',
        'contact',
      ]),
      minLength: 1,
      maxLength: 64,
      aliases: Object.freeze([
        'personalTitle',
        'personal_title',
      ]),
    }),
    Object.freeze({
      name: 'middleName',
      valueType: 'single_text',
      label: 'Deuxième prénom',
      objectClasses: Object.freeze([
        'user',
        'contact',
      ]),
      minLength: 0,
      maxLength: 64,
      aliases: Object.freeze([
        'middleName',
        'middle_name',
      ]),
    }),
    Object.freeze({
      name: 'comment',
      valueType: 'single_text',
      label: 'Commentaire LDAP',
      objectClasses: Object.freeze([
        'user',
        'contact',
      ]),
      minLength: 0,
      maxLength: 1024,
      aliases: Object.freeze([
        'comment',
      ]),
    }),
  ])

const LDAP_ATTRIBUTE_DEFINITION_BY_NAME =
  new Map(
    LDAP_ATTRIBUTE_EDITOR_DEFINITIONS.map(
      definition => [
        definition.name.toLowerCase(),
        definition,
      ]
    )
  )

function getLdapEditorDefinitionValueType(
  definition
) {
  return definition?.valueType ||
    definition?.value_type ||
    'single_text'
}

function normalizeLdapEditorValueForDefinition(
  definition,
  rawValue
) {
  const valueType =
    getLdapEditorDefinitionValueType(
      definition
    )

  const parsedValue =
    parseLdapTypedInputValue(
      valueType,
      rawValue
    )

  return normalizeLdapTypedEditorValue({
    valueType,
    value: parsedValue,
    minLength:
      definition?.minLength ?? 0,
    maxLength:
      definition?.maxLength ?? null,
    minValue:
      definition?.minValue ?? null,
    maxValue:
      definition?.maxValue ?? null,
  })
}

function readLdapEditorValueForDefinition(
  definition,
  rawValue
) {
  if (
    rawValue === null ||
    rawValue === undefined ||
    rawValue === ''
  ) {
    return ''
  }

  const valueType =
    getLdapEditorDefinitionValueType(
      definition
    )

  if (valueType === 'single_text') {
    return String(rawValue)
  }

  return parseLdapTypedInputValue(
    valueType,
    rawValue
  )
}

function normalizeClassValues(value) {
  const source = Array.isArray(value)
    ? value
    : [value]

  return source
    .map(item =>
      String(item || '')
        .trim()
        .toLowerCase()
    )
    .filter(Boolean)
}

function normalizeLdapEditorObjectClass(object) {
  const classValues = [
    ...normalizeClassValues(
      object?.object_class
    ),
    ...normalizeClassValues(
      object?.objectClass
    ),
    ...normalizeClassValues(
      object?.type
    ),
  ]

  if (classValues.includes('computer')) {
    return 'computer'
  }

  if (classValues.includes('contact')) {
    return 'contact'
  }

  if (classValues.includes('group')) {
    return 'group'
  }

  if (classValues.includes('user')) {
    return 'user'
  }

  if (
    object?.user_principal_name ||
    object?.userPrincipalName
  ) {
    return 'user'
  }

  return classValues[0] || ''
}

function getLdapEditorDefinitions(object) {
  const objectClass =
    normalizeLdapEditorObjectClass(object)

  return LDAP_ATTRIBUTE_EDITOR_DEFINITIONS
    .filter(definition =>
      definition.objectClasses.includes(
        objectClass
      )
    )
}

function getLdapEditorCurrentValue(
  object,
  definitionOrName
) {
  const definition =
    typeof definitionOrName === 'string'
      ? LDAP_ATTRIBUTE_DEFINITION_BY_NAME.get(
          definitionOrName.toLowerCase()
        )
      : definitionOrName

  if (!definition) {
    return ''
  }

  for (const key of definition.aliases) {
    if (!Object.hasOwn(object || {}, key)) {
      continue
    }

    const value = object[key]

    if (Array.isArray(value)) {
      return value.length > 0
        ? readLdapEditorValueForDefinition(
            definition,
            value[0]
          )
        : ''
    }

    return readLdapEditorValueForDefinition(
      definition,
      value
    )
  }

  return ''
}

function normalizeLdapEditorChange(
  change,
  objectClass
) {
  const attributeName = String(
    change?.attribute_name ||
    change?.attributeName ||
    ''
  ).trim()

  const definition =
    LDAP_ATTRIBUTE_DEFINITION_BY_NAME.get(
      attributeName.toLowerCase()
    )

  if (!definition) {
    throw new Error(
      `Attribut LDAP non autorisé : ${attributeName || 'inconnu'}.`
    )
  }

  if (
    !definition.objectClasses.includes(
      objectClass
    )
  ) {
    throw new Error(
      `${definition.label} n’est pas autorisé pour la classe ${objectClass || 'inconnue'}.`
    )
  }

  const operation = String(
    change?.operation || ''
  )
    .trim()
    .toLowerCase()

  if (!['set', 'clear'].includes(operation)) {
    throw new Error(
      `Opération LDAP invalide pour ${definition.label}.`
    )
  }

  if (operation === 'clear') {
    return {
      attribute_name: definition.name,
      operation: 'clear',
      value: null,
    }
  }

  const valueType =
    getLdapEditorDefinitionValueType(
      definition
    )

  let value

  if (valueType === 'single_text') {
    if (typeof change?.value !== 'string') {
      throw new Error(
        `${definition.label} doit être une chaîne de caractères.`
      )
    }

    const textValue = change.value.trim()

    if (!textValue) {
      throw new Error(
        `${definition.label} ne peut pas être vide avec l’opération set.`
      )
    }

    const hasForbiddenControlCharacter =
      textValue.includes(
        String.fromCharCode(0)
      ) ||
      textValue.includes('\r') ||
      textValue.includes('\n')

    if (hasForbiddenControlCharacter) {
      throw new Error(
        `${definition.label} contient un caractère interdit.`
      )
    }

    if (
      definition.minLength > 0 &&
      textValue.length <
        definition.minLength
    ) {
      throw new Error(
        `${definition.label} est trop court.`
      )
    }

    if (
      textValue.length >
      definition.maxLength
    ) {
      throw new Error(
        `${definition.label} dépasse ${definition.maxLength} caractères.`
      )
    }

    value =
      normalizeLdapEditorValueForDefinition(
        definition,
        textValue
      )
  } else {
    try {
      value =
        normalizeLdapEditorValueForDefinition(
          definition,
          change?.value
        )
    } catch (error) {
      throw new Error(
        `${definition.label} : ${
          error?.message ||
          'valeur LDAP invalide.'
        }`
      )
    }
  }

  return {
    attribute_name: definition.name,
    operation: 'set',
    value,
  }
}

function buildLdapAttributeUpdatePayload({
  object,
  changes,
}) {
  const objectIdentity = String(
    object?.distinguished_name ||
    object?.dn ||
    ''
  ).trim()

  if (
    !objectIdentity ||
    !objectIdentity.includes('=') ||
    !objectIdentity.includes(',')
  ) {
    throw new Error(
      'Le DN LDAP de l’objet est invalide.'
    )
  }

  const objectClass =
    normalizeLdapEditorObjectClass(object)

  if (!['user', 'contact'].includes(objectClass)) {
    throw new Error(
      'Cet objet ne prend pas en charge l’éditeur LDAP contrôlé.'
    )
  }

  if (!Array.isArray(changes)) {
    throw new Error(
      'Les changements LDAP doivent être une liste.'
    )
  }

  if (changes.length === 0) {
    throw new Error(
      'Au moins un changement LDAP est obligatoire.'
    )
  }

  if (
    changes.length >
    LDAP_ATTRIBUTE_UPDATE_MAX_CHANGES
  ) {
    throw new Error(
      'Un job LDAP est limité à cinq changements.'
    )
  }

  const normalizedChanges = changes.map(
    change =>
      normalizeLdapEditorChange(
        change,
        objectClass
      )
  )

  const names = new Set()

  for (const change of normalizedChanges) {
    const key =
      change.attribute_name.toLowerCase()

    if (names.has(key)) {
      throw new Error(
        'Un attribut LDAP ne peut apparaître qu’une fois par job.'
      )
    }

    names.add(key)
  }

  return {
    action: LDAP_ATTRIBUTE_UPDATE_ACTION,
    object_identity: objectIdentity,
    object_class: objectClass,
    changes: normalizedChanges,
  }
}


function createLdapAttributeEditorDraft(object) {
  return getLdapEditorDefinitions(object)
    .map(definition => {
      const originalValue =
        getLdapEditorCurrentValue(
          object,
          definition
        )

      return {
        attribute_name: definition.name,
        label: definition.label,
        operation: 'unchanged',
        value: originalValue,
        original_value: originalValue,
        value_type:
          getLdapEditorDefinitionValueType(
            definition
          ),
        min_length:
          definition.minLength,
        max_length:
          definition.maxLength,
        min_value:
          definition.minValue ?? null,
        max_value:
          definition.maxValue ?? null,
      }
    })
}

function updateLdapAttributeEditorDraft(
  draft,
  attributeName,
  patch
) {
  if (!Array.isArray(draft)) {
    throw new Error(
      'Le brouillon LDAP doit être une liste.'
    )
  }

  const normalizedName = String(
    attributeName || ''
  )
    .trim()
    .toLowerCase()

  const definition =
    LDAP_ATTRIBUTE_DEFINITION_BY_NAME.get(
      normalizedName
    )

  if (!definition) {
    throw new Error(
      `Attribut LDAP non autorisé : ${attributeName || 'inconnu'}.`
    )
  }

  let found = false

  const updated = draft.map(entry => {
    if (
      String(entry?.attribute_name || '')
        .toLowerCase() !== normalizedName
    ) {
      return entry
    }

    found = true

    const nextOperation = String(
      patch?.operation ??
      entry.operation ??
      'unchanged'
    )
      .trim()
      .toLowerCase()

    if (
      ![
        'unchanged',
        'set',
        'clear',
      ].includes(nextOperation)
    ) {
      throw new Error(
        `Opération LDAP invalide pour ${definition.label}.`
      )
    }

    const nextValue = Object.hasOwn(
      patch || {},
      'value'
    )
      ? patch.value ?? ''
      : entry.value ?? ''

    return {
      ...entry,
      operation: nextOperation,
      value: nextValue,
    }
  })

  if (!found) {
    throw new Error(
      `Le brouillon ne contient pas l’attribut ${definition.name}.`
    )
  }

  return updated
}

function buildLdapAttributeEditorChanges(
  draft
) {
  if (!Array.isArray(draft)) {
    throw new Error(
      'Le brouillon LDAP doit être une liste.'
    )
  }

  return draft
    .filter(entry =>
      ['set', 'clear'].includes(
        String(entry?.operation || '')
          .toLowerCase()
      )
    )
    .map(entry => {
      const operation = String(
        entry.operation
      ).toLowerCase()

      return {
        attribute_name:
          entry.attribute_name,
        operation,
        value:
          operation === 'clear'
            ? null
            : entry.value ?? '',
      }
    })
}

function getLdapAttributeEditorChangeCount(
  draft
) {
  return buildLdapAttributeEditorChanges(
    draft
  ).length
}

function buildLdapAttributeEditorPreview({
  object,
  draft,
}) {
  const changes =
    buildLdapAttributeEditorChanges(draft)

  const payload =
    buildLdapAttributeUpdatePayload({
      object,
      changes,
    })

  const entriesByName = new Map(
    draft.map(entry => [
      String(
        entry?.attribute_name || ''
      ).toLowerCase(),
      entry,
    ])
  )

  const rows = payload.changes.map(
    change => {
      const entry = entriesByName.get(
        change.attribute_name.toLowerCase()
      )

      return {
        attribute_name:
          change.attribute_name,
        label:
          entry?.label ||
          change.attribute_name,
        operation:
          change.operation,
        value_type:
          entry?.value_type ||
          'single_text',
        before:
          entry?.original_value ?? '',
        after:
          change.operation === 'clear'
            ? null
            : change.value,
      }
    }
  )

  return {
    payload,
    rows,
    change_count: rows.length,
  }
}


export {
  LDAP_ATTRIBUTE_EDITOR_DEFINITIONS,
  LDAP_ATTRIBUTE_UPDATE_ACTION,
  LDAP_ATTRIBUTE_UPDATE_MAX_CHANGES,
  buildLdapAttributeUpdatePayload,
  buildLdapAttributeEditorChanges,
  buildLdapAttributeEditorPreview,
  createLdapAttributeEditorDraft,
  getLdapAttributeEditorChangeCount,
  getLdapEditorCurrentValue,
  getLdapEditorDefinitionValueType,
  getLdapEditorDefinitions,
  normalizeLdapEditorChange,
  normalizeLdapEditorObjectClass,
  normalizeLdapEditorValueForDefinition,
  readLdapEditorValueForDefinition,
  updateLdapAttributeEditorDraft,
}
