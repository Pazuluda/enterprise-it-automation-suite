import assert from 'node:assert/strict'

import {
  buildAdUserDetailsJobPayload,
  extractAdUserDetails,
  isUserObject,
  mergeAdUserDetails,
} from '../src/features/active-directory/utils/adUserDetails.js'

let passed = 0

function test(name, callback) {
  callback()
  passed += 1
  console.log(`OK - ${name}`)
}

test(
  'reconnait uniquement les objets utilisateur',
  () => {
    assert.equal(isUserObject({ type: 'user' }), true)
    assert.equal(isUserObject({ object_class: 'USER' }), true)
    assert.equal(isUserObject({ type: 'group' }), false)
    assert.equal(isUserObject(null), false)
  }
)

test(
  'construit un job get_user avec une identite stable',
  () => {
    const payload = buildAdUserDetailsJobPayload({
      type: 'user',
      distinguished_name:
        'CN=Liam Ve,OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL',
      sam_account_name: 'l.ve',
    })

    assert.deepEqual(payload, {
      action: 'get_user',
      query:
        'CN=Liam Ve,OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL',
      created_by: 'react-admin',
    })
  }
)

test(
  'extrait exclusivement result.item',
  () => {
    const item = {
      type: 'user',
      hab_seniority_index: 42,
    }

    assert.deepEqual(
      extractAdUserDetails({
        status: 'completed',
        success: true,
        result: { item },
      }),
      item
    )

    assert.equal(
      extractAdUserDetails({
        status: 'completed',
        success: true,
        result: { items: [item] },
      }),
      null
    )
  }
)

test(
  'fusionne les details sans perdre les donnees initiales',
  () => {
    const initial = {
      type: 'user',
      name: 'Liam Ve',
      description: 'Compte EITAS',
    }

    const details = {
      type: 'user',
      description: '',
      hab_seniority_index: 42,
    }

    assert.deepEqual(
      mergeAdUserDetails(initial, details),
      {
        type: 'user',
        name: 'Liam Ve',
        description: '',
        hab_seniority_index: 42,
      }
    )

    assert.deepEqual(
      mergeAdUserDetails(initial, null),
      initial
    )
  }
)

console.log(
  `DETAILS UTILISATEUR AD : ${passed} TESTS REUSSIS`
)
