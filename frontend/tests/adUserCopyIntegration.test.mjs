import assert from 'node:assert/strict'
import test from 'node:test'
import {
  readFileSync,
} from 'node:fs'

const hook = readFileSync(
  new URL(
    '../src/features/active-directory/hooks/useAdUserCreation.js',
    import.meta.url
  ),
  'utf8'
)

const modal = readFileSync(
  new URL(
    '../src/features/active-directory/components/CreateUserModal.jsx',
    import.meta.url
  ),
  'utf8'
)


const css = readFileSync(
  new URL(
    '../src/styles/07-active-directory.css',
    import.meta.url
  ),
  'utf8'
)

const propertiesModal = readFileSync(
  new URL(
    '../src/features/active-directory/components/AdObjectPropertiesModal.jsx',
    import.meta.url
  ),
  'utf8'
)

const details = readFileSync(
  new URL(
    '../src/features/active-directory/components/ObjectDetailsPanel.jsx',
    import.meta.url
  ),
  'utf8'
)

const page = readFileSync(
  new URL(
    '../src/features/active-directory/AdExplorerPage.jsx',
    import.meta.url
  ),
  'utf8'
)

function sliceBetween(
  source,
  startMarker,
  endMarker
) {
  const start = source.indexOf(startMarker)

  assert.notEqual(
    start,
    -1,
    `Marqueur absent : ${startMarker}`
  )

  const end = source.indexOf(
    endMarker,
    start + startMarker.length
  )

  assert.notEqual(
    end,
    -1,
    `Marqueur absent : ${endMarker}`
  )

  return source.slice(start, end)
}

test(
  'importe le constructeur de copie securise',
  () => {
    assert.match(
      hook,
      /buildCopyUserPreparation/
    )

    assert.match(
      hook,
      /from '\.\.\/utils\/adUserCopy'/
    )
  }
)

test(
  'charge la source utilisateur detaillee',
  () => {
    const block = sliceBetween(
      hook,
      'async function openCopyUser',
      'function closeCreateUserModal'
    )

    assert.match(
      block,
      /resolveUserUpdateTarget\(base\)/
    )

    assert.match(
      block,
      /buildCopyUserPreparation/
    )

    assert.ok(
      block.indexOf(
        'resolveUserUpdateTarget'
      )
      < block.lastIndexOf(
        'buildCopyUserPreparation'
      )
    )
  }
)

test(
  'ouvre la creation avec une source de copie',
  () => {
    const block = sliceBetween(
      hook,
      'async function openCopyUser',
      'function closeCreateUserModal'
    )

    assert.match(
      block,
      /copy_source:\s*preparation\.source/
    )

    assert.match(
      block,
      /setCreateUserForm\(\s*preparation\.form\s*\)/
    )
  }
)

test(
  'transmet explicitement le profil autorise',
  () => {
    const submit = sliceBetween(
      hook,
      'async function submitCreateUser',
      '\n  return {'
    )

    for (const field of [
      'title',
      'department',
      'division',
      'company',
      'manager',
      'office',
      'telephone_number',
      'mobile',
      'street_address',
      'postal_code',
      'city',
      'state',
    ]) {
      assert.match(
        submit,
        new RegExp(
          `${field}:\\s*createUserForm\\.${field}`
        )
      )
    }
  }
)

test(
  'n ajoute aucun champ interdit au payload',
  () => {
    const submit = sliceBetween(
      hook,
      'async function submitCreateUser',
      '\n  return {'
    )

    for (const forbidden of [
      'member_of:',
      'memberOf:',
      'groups:',
      'mail:',
      'employee_id:',
      'employee_number:',
      'object_guid:',
      'sid:',
      'hab_seniority_index:',
    ]) {
      assert.equal(
        submit.includes(forbidden),
        false,
        `Champ interdit : ${forbidden}`
      )
    }
  }
)

test(
  'affiche Copier dans les actions utilisateur gerees',
  () => {
    const userActions = sliceBetween(
      details,
      '{isUser && (',
      '</>'
    )

    assert.match(
      userActions,
      /data-eitas-action="copy-user"/
    )

    assert.match(
      userActions,
      /!isManagedScope/
    )

    assert.match(
      userActions,
      /onCopyUser\?\.\(displayed\)/
    )
  }
)

test(
  'distingue visuellement copie et creation',
  () => {
    assert.match(
      modal,
      /Copier un utilisateur/
    )

    assert.match(
      modal,
      /data-eitas-copy-source="true"/
    )

    assert.match(
      modal,
      /Les groupes, mots de passe et identifiants/
    )
  }
)

test(
  'cable la copie dans la page et les proprietes',
  () => {
    assert.match(
      page,
      /resolveUserUpdateTarget,/
    )

    assert.match(
      page,
      /openCopyUser,/
    )

    assert.match(
      page,
      /onCopyUser=\{target => openCopyUser\(target\)\}/
    )

    assert.match(
      page,
      /onCopyUser: target => \{/
    )
  }
)

test(
  'rend tous les champs de profil editables',
  () => {
    for (const field of [
      'title',
      'department',
      'division',
      'company',
      'manager',
      'office',
      'telephone_number',
      'mobile',
      'street_address',
      'postal_code',
      'city',
      'state',
    ]) {
      assert.match(
        modal,
        new RegExp(
          `createUserForm\\.${field}`
        )
      )

      assert.match(
        modal,
        new RegExp(
          `updateCreateUserField\\(\\s*'${field}'`
        )
      )
    }
  }
)

test(
  'ouvre le profil lors d une copie',
  () => {
    assert.match(
      modal,
      /data-eitas-copy-profile="true"/
    )

    assert.match(
      modal,
      /open=\{Boolean\(\s*createUserModal\.copy_source\s*\)\}/
    )

    assert.match(
      modal,
      /Profil utilisateur optionnel/
    )
  }
)

test(
  'ne propose aucun attribut interdit',
  () => {
    for (const forbidden of [
      "updateCreateUserField('member_of'",
      "updateCreateUserField('groups'",
      "updateCreateUserField('mail'",
      "updateCreateUserField('employee_id'",
      "updateCreateUserField('employee_number'",
      "updateCreateUserField('object_guid'",
      "updateCreateUserField('sid'",
      "updateCreateUserField('hab_seniority_index'",
    ]) {
      assert.equal(
        modal.includes(forbidden),
        false,
        `Attribut interdit dans la modale : ${forbidden}`
      )
    }
  }
)


test(
  'affiche la copie dans la vraie fenetre de proprietes',
  () => {
    assert.match(
      propertiesModal,
      /data-eitas-action="copy-user-from-properties"/
    )

    assert.match(
      propertiesModal,
      /Copier cet utilisateur/
    )
  }
)

test(
  'preserve le bloc HAB au debut du footer',
  () => {
    assert.match(
      propertiesModal,
      /<footer className="aduc-modal-actions">\s+\{habSimulationActive \? \(/
    )

    const footer = sliceBetween(
      propertiesModal,
      '<footer className="aduc-modal-actions">',
      '</footer>'
    )

    assert.ok(
      footer.indexOf(
        '{habSimulationActive ? ('
      )
      < footer.indexOf(
        'copy-user-from-properties'
      )
    )
  }
)

test(
  'ferme l editeur avant d ouvrir la copie',
  () => {
    const handler = sliceBetween(
      propertiesModal,
      'function copyCurrentUser',
      '\n\n  return ('
    )

    assert.match(
      handler,
      /const copyTarget/
    )

    assert.match(
      handler,
      /update\?\.closeUpdateObject\?\.\(\)/
    )

    assert.match(
      handler,
      /details\.onCopyUser\(copyTarget\)/
    )

    assert.ok(
      handler.indexOf(
        'closeUpdateObject'
      )
      < handler.indexOf(
        'details.onCopyUser'
      )
    )
  }
)

test(
  'protege les changements non enregistres',
  () => {
    const button = sliceBetween(
      propertiesModal,
      'data-eitas-action="copy-user-from-properties"',
      '</button>'
    )

    assert.match(
      button,
      /editing && hasChanges/
    )

    assert.match(
      button,
      /typeof details\?\.onCopyUser/
    )
  }
)

test(
  'affiche le chargement de la source detaillee',
  () => {
    assert.match(
      propertiesModal,
      /loading\s*\? 'Chargement\.\.\.'/
    )
  }
)


test(
  'normalise les valeurs saisies ou collees',
  () => {
    const helpers = sliceBetween(
      hook,
      'function normalizeCreateUserFieldInput',
      'function validateCreateUserForm'
    )

    assert.match(
      helpers,
      /String\(value \?\? ''\)/
    )

    assert.match(
      helpers,
      /getSafeSuggestedSamAccountName/
    )

    assert.match(
      helpers,
      /getSafeSuggestedUserPrincipalName/
    )
  }
)

test(
  'ne fait plus confiance aux suggestions absentes',
  () => {
    const update = sliceBetween(
      hook,
      'function updateCreateUserField',
      'function getCreateUserDefaultOuDn'
    )

    assert.match(
      update,
      /const safeValue/
    )

    assert.match(
      update,
      /\[name\]: safeValue/
    )

    assert.match(
      update,
      /getSafeSuggestedSamAccountName/
    )

    assert.match(
      update,
      /getSafeSuggestedUserPrincipalName/
    )
  }
)

test(
  'applique la presentation dediee a la copie',
  () => {
    assert.match(
      modal,
      /is-copy-mode/
    )

    assert.match(
      modal,
      /data-eitas-create-user-field="first_name"/
    )

    assert.match(
      css,
      /C3\.4M7 - Copy user modal stability and polish/
    )

    assert.match(
      css,
      /\.aduc-create-user-modal\.is-copy-mode/
    )

    assert.match(
      css,
      /details\[data-eitas-copy-profile="true"\]/
    )

    assert.match(
      css,
      /position: sticky/
    )
  }
)



test(
  'ouvre la fenetre avant le lookup detaille',
  () => {
    const block = sliceBetween(
      hook,
      'async function openCopyUser',
      'function closeCreateUserModal'
    )

    const openIndex =
      block.indexOf('copy_preparing: true')

    const lookupIndex =
      block.indexOf('await Promise.all')

    assert.ok(openIndex >= 0)
    assert.ok(lookupIndex >= 0)
    assert.ok(openIndex < lookupIndex)
  }
)

test(
  'charge le profil et le mode en parallele',
  () => {
    const block = sliceBetween(
      hook,
      'async function openCopyUser',
      'function closeCreateUserModal'
    )

    assert.match(
      block,
      /await Promise\.all/
    )

    assert.match(
      block,
      /resolveUserUpdateTarget\(base\)/
    )

    assert.match(
      block,
      /loadAdAgentMode\(\)/
    )
  }
)

test(
  'ignore une ancienne reponse de copie',
  () => {
    assert.match(
      hook,
      /copyUserRequestIdRef/
    )

    assert.match(
      hook,
      /requestId\s*!==\s*copyUserRequestIdRef\.current/
    )

    assert.match(
      hook,
      /copyUserRequestIdRef\.current \+= 1/
    )
  }
)

test(
  'affiche le chargement dans la fenetre ouverte',
  () => {
    assert.match(
      modal,
      /aduc-copy-user-preparing/
    )

    assert.match(
      modal,
      /Chargement du profil complet/
    )

    assert.match(
      modal,
      /aria-busy/
    )

    assert.match(
      css,
      /C3\.4M8 - Immediate copy modal/
    )
  }
)



test(
  'utilise un fallback local pour le SAM et l UPN',
  () => {
    const helpers = sliceBetween(
      hook,
      'function getSafeSuggestedSamAccountName',
      'function validateCreateUserForm'
    )

    assert.match(
      helpers,
      /normalizeCreateUserPart\(firstName\)/
    )

    assert.match(
      helpers,
      /normalizeCreateUserPart\(lastName\)/
    )

    assert.match(
      helpers,
      /`\$\{first\}\.\$\{last\}`\.slice\(0, 20\)/
    )

    assert.match(
      helpers,
      /\.filter\(part => \/\^DC=\/i\.test\(part\)\)/
    )

    assert.match(
      helpers,
      /return `\$\{sam\}@\$\{domain\}`/
    )
  }
)


console.log(
  'C3.4 INTEGRATION COPIE UTILISATEUR : '
  + 'TESTS REUSSIS'
)
