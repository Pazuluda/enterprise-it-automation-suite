import assert from 'node:assert/strict'
import test from 'node:test'

import {
  getAdAccountEnabledState,
  getAdAccountLockedState,
  getAdAccountPasswordExpiredState,
  getAdAccountStatus,
  getAdAccountStatusClass,
  getAdAccountToggleAction,
  normalizeAdBoolean,
} from '../src/features/active-directory/utils/adAccountState.js'

test(
  'normalise les representations booleennes AD',
  () => {
    assert.equal(normalizeAdBoolean(true), true)
    assert.equal(normalizeAdBoolean(false), false)
    assert.equal(normalizeAdBoolean('TRUE'), true)
    assert.equal(normalizeAdBoolean('0'), false)
    assert.equal(normalizeAdBoolean('oui'), true)
    assert.equal(normalizeAdBoolean('non'), false)
    assert.equal(normalizeAdBoolean('inconnu'), null)
    assert.equal(normalizeAdBoolean(''), null)
  },
)

test(
  'resout enabled avant le fallback disabled',
  () => {
    assert.equal(
      getAdAccountEnabledState({
        enabled: false,
        disabled: false,
      }),
      false,
    )

    assert.equal(
      getAdAccountEnabledState({
        Disabled: true,
      }),
      false,
    )

    assert.equal(
      getAdAccountEnabledState({
        disabled: false,
      }),
      true,
    )

    assert.equal(
      getAdAccountEnabledState({}),
      null,
    )
  },
)

test(
  'lit les etats verrouille et mot de passe expire',
  () => {
    assert.equal(
      getAdAccountLockedState({
        lockedOut: 'true',
      }),
      true,
    )

    assert.equal(
      getAdAccountPasswordExpiredState({
        PasswordExpired: 1,
      }),
      true,
    )
  },
)

test(
  'priorise verrouillage puis desactivation puis expiration',
  () => {
    assert.equal(
      getAdAccountStatus({
        enabled: true,
        locked_out: true,
        password_expired: true,
      }),
      'Verrouillé',
    )

    assert.equal(
      getAdAccountStatus({
        enabled: false,
        password_expired: true,
      }),
      'Désactivé',
    )

    assert.equal(
      getAdAccountStatus({
        enabled: true,
        password_expired: true,
      }),
      'MDP expiré',
    )

    assert.equal(
      getAdAccountStatus({
        enabled: true,
      }),
      'Activé',
    )

    assert.equal(
      getAdAccountStatus({}),
      'État inconnu',
    )
  },
)

test(
  'retourne une classe et une action coherentes',
  () => {
    assert.equal(
      getAdAccountStatusClass({
        locked_out: true,
      }),
      'locked',
    )

    assert.equal(
      getAdAccountStatusClass({
        enabled: false,
      }),
      'disabled',
    )

    assert.equal(
      getAdAccountToggleAction({
        enabled: true,
      }),
      'disable_account',
    )

    assert.equal(
      getAdAccountToggleAction({
        enabled: false,
      }),
      'enable_account',
    )

    assert.equal(
      getAdAccountToggleAction({}),
      null,
    )
  },
)

console.log(
  'ETAT COMPTE AD C3.1 : TESTS REUSSIS',
)
