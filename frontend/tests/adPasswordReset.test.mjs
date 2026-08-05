import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildAdPasswordResetPayload,
  buildAdPasswordResetSafeSummary,
  createAdPasswordResetDraft,
  getAdPasswordResetInputType,
  normalizeAdPasswordResetBoolean,
} from '../src/features/active-directory/utils/adPasswordReset.js'

test(
  'cree un brouillon securise avec les options historiques',
  () => {
    assert.deepEqual(
      createAdPasswordResetDraft(),
      {
        temporaryPassword: '',
        showPassword: false,
        forceChangeAtLogon: true,
        unlockAfterReset: true,
      }
    )
  }
)

test(
  'masque le mot de passe par defaut',
  () => {
    assert.equal(
      getAdPasswordResetInputType(false),
      'password'
    )

    assert.equal(
      getAdPasswordResetInputType(true),
      'text'
    )
  }
)

test(
  'normalise les options booleennes',
  () => {
    assert.equal(
      normalizeAdPasswordResetBoolean('false', true),
      false
    )

    assert.equal(
      normalizeAdPasswordResetBoolean('oui', false),
      true
    )

    assert.equal(
      normalizeAdPasswordResetBoolean('', true),
      true
    )
  }
)

test(
  'construit un payload avec des choix explicites',
  () => {
    assert.deepEqual(
      buildAdPasswordResetPayload({
        temporaryPassword: ' Temporaire-123! ',
        forceChangeAtLogon: false,
        unlockAfterReset: false,
      }),
      {
        temporary_password: 'Temporaire-123!',
        force_change_at_logon: false,
        unlock_after_reset: false,
      }
    )
  }
)

test(
  'refuse un mot de passe vide',
  () => {
    assert.throws(
      () => buildAdPasswordResetPayload({
        temporaryPassword: '   ',
      }),
      /obligatoire/
    )
  }
)

test(
  'exclut le mot de passe du resume non sensible',
  () => {
    const redactionMarker = 'C32-Redaction-Marker-Frontend!'

    const summary =
      buildAdPasswordResetSafeSummary({
        temporaryPassword: redactionMarker,
        forceChangeAtLogon: true,
        unlockAfterReset: false,
      })

    assert.deepEqual(
      summary,
      {
        force_change_at_logon: true,
        unlock_after_reset: false,
      }
    )

    assert.equal(
      JSON.stringify(summary).includes(redactionMarker),
      false
    )

    assert.equal(
      Object.hasOwn(
        summary,
        'temporary_password'
      ),
      false
    )
  }
)

console.log(
  'C3.2 RESET MOT DE PASSE : TESTS REUSSIS'
)
