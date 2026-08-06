import assert from 'node:assert/strict'
import test from 'node:test'

import {
  COPY_USER_NEVER_FORM_FIELDS,
  COPY_USER_PROFILE_FIELDS,
  buildCopiedUserProfile,
  buildCopyUserPreparation,
  getCopyUserSourceParentDn,
  isCopyableUserSource,
} from '../src/features/active-directory/utils/adUserCopy.js'

const sourcePassword =
  'SourceSecret!2026'

const sourceUser = {
  type: 'user',
  name: 'Liam Ve',
  display_name: 'Liam Ve',
  distinguished_name:
    'CN=Liam Ve,OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL',
  sam_account_name: 'liam.ve',
  user_principal_name:
    'liam.ve@api.local',

  description:
    'Technicien infrastructure',
  title: 'Technicien systèmes',
  department: 'Infrastructure',
  division: 'IT',
  company: 'EITAS',
  manager:
    'CN=Responsable IT,OU=Users,OU=EITAS,DC=API,DC=LOCAL',
  office: 'Bordeaux',
  telephone_number: '0102030405',
  mobile: '0607080910',
  street_address:
    '1 rue de la République',
  postal_code: '33000',
  city: 'Bordeaux',
  state: 'Nouvelle-Aquitaine',

  temporary_password: sourcePassword,
  password: sourcePassword,
  mail: 'liam.ve@api.local',
  employee_id: 'EMP-0001',
  employee_number: '42',

  member_of: [
    'CN=Admins,OU=Groups,OU=EITAS,DC=API,DC=LOCAL',
  ],
  primary_group_id: 513,

  password_never_expires: true,
  cannot_change_password: true,
  password_last_set:
    '2026-08-01T10:00:00Z',

  object_guid:
    '00000000-0000-0000-0000-000000000001',
  sid: 'S-1-5-21-1-2-3-1001',

  created_at:
    '2026-01-01T00:00:00Z',
  updated_at:
    '2026-08-01T00:00:00Z',

  bad_logon_count: 3,
  hab_seniority_index: 12,
}

test(
  'accepte uniquement une source utilisateur',
  () => {
    assert.equal(
      isCopyableUserSource(sourceUser),
      true
    )

    assert.equal(
      isCopyableUserSource({
        type: 'user',
        objectClass: [
          'top',
          'person',
          'organizationalPerson',
          'user',
          'computer',
        ],
      }),
      false
    )

    assert.equal(
      isCopyableUserSource({
        type: 'group',
      }),
      false
    )
  }
)

test(
  'derive l OU parente de la source EITAS',
  () => {
    assert.equal(
      getCopyUserSourceParentDn(sourceUser),
      'OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL'
    )
  }
)

test(
  'gere les virgules LDAP echappees',
  () => {
    const source = {
      ...sourceUser,
      distinguished_name:
        'CN=Doe\\, John,OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL',
    }

    assert.equal(
      getCopyUserSourceParentDn(source),
      'OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL'
    )
  }
)

test(
  'copie uniquement la liste blanche',
  () => {
    const profile =
      buildCopiedUserProfile(sourceUser)

    assert.deepEqual(
      Object.keys(profile).sort(),
      Object.keys(
        COPY_USER_PROFILE_FIELDS
      ).sort()
    )

    assert.equal(
      profile.department,
      'Infrastructure'
    )

    assert.equal(
      profile.manager,
      sourceUser.manager
    )

    assert.equal(
      profile.mobile,
      '0607080910'
    )
  }
)

test(
  'laisse identite et mot de passe vides',
  () => {
    const prepared =
      buildCopyUserPreparation(sourceUser)

    assert.equal(
      prepared.form.first_name,
      ''
    )

    assert.equal(
      prepared.form.last_name,
      ''
    )

    assert.equal(
      prepared.form.sam_account_name,
      ''
    )

    assert.equal(
      prepared.form.user_principal_name,
      ''
    )

    assert.equal(
      prepared.form.temporary_password,
      ''
    )
  }
)

test(
  'cree le compte desactive par defaut',
  () => {
    const prepared =
      buildCopyUserPreparation(sourceUser)

    assert.equal(
      prepared.form.enabled,
      false
    )

    assert.equal(
      prepared.form.force_change_at_logon,
      true
    )
  }
)

test(
  'accepte une OU EITAS explicite',
  () => {
    const targetOuDn =
      'OU=Users,OU=EITAS,DC=API,DC=LOCAL'

    const prepared =
      buildCopyUserPreparation(
        sourceUser,
        {
          targetOuDn,
        }
      )

    assert.equal(
      prepared.form.target_ou_dn,
      targetOuDn
    )
  }
)

test(
  'refuse une destination hors EITAS',
  () => {
    const prepared =
      buildCopyUserPreparation(
        sourceUser,
        {
          targetOuDn:
            'OU=External,DC=API,DC=LOCAL',
        }
      )

    assert.equal(
      prepared.form.target_ou_dn,
      'OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL'
    )
  }
)

test(
  'ne transfere aucun champ source interdit',
  () => {
    const prepared =
      buildCopyUserPreparation(sourceUser)

    for (
      const field
      of COPY_USER_NEVER_FORM_FIELDS
    ) {
      assert.equal(
        Object.hasOwn(prepared.form, field),
        false,
        `Champ interdit présent : ${field}`
      )
    }

    const serialized =
      JSON.stringify(prepared.form)

    assert.equal(
      serialized.includes('CN=Admins'),
      false
    )

    assert.equal(
      serialized.includes(
        sourceUser.object_guid
      ),
      false
    )

    assert.equal(
      serialized.includes(sourceUser.sid),
      false
    )

    assert.equal(
      serialized.includes(sourcePassword),
      false
    )

    assert.equal(
      prepared.form.temporary_password,
      ''
    )
  }
)

test(
  'ne modifie jamais l objet source',
  () => {
    const snapshot =
      JSON.parse(JSON.stringify(sourceUser))

    buildCopyUserPreparation(sourceUser)

    assert.deepEqual(
      sourceUser,
      snapshot
    )
  }
)

test(
  'rejette une source non utilisateur',
  () => {
    assert.throws(
      () =>
        buildCopyUserPreparation({
          type: 'computer',
          distinguished_name:
            'CN=PC01,OU=Computers,OU=EITAS,DC=API,DC=LOCAL',
        }),
      /doit être un utilisateur/
    )
  }
)

console.log(
  'C3.4 COPIE UTILISATEUR CONTROLEE : '
  + 'TESTS REUSSIS'
)
