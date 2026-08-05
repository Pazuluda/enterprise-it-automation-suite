import assert from 'node:assert/strict'
import test from 'node:test'

import {
  HAB_ATTRIBUTE_NAME,
  HAB_MAXIMUM_VALUE,
  HAB_SIMULATION_ACTION,
  buildHabSenioritySimulationJobPayload,
  buildHabSenioritySimulationPayload,
  getHabCurrentValue,
  getHabSimulationEligibility,
  normalizeHabInteger32,
} from '../src/features/active-directory/utils/habSenioritySimulation.js'

const user = {
  object_class: 'user',
  distinguished_name:
    'CN=Test HAB,OU=Users,DC=EXAMPLE,DC=LOCAL',
  hab_seniority_index: null,
}

test(
  'construit un payload HAB set dédié',
  () => {
    const payload =
      buildHabSenioritySimulationPayload({
        object: user,
        operation: 'set',
        value: '100',
      })

    assert.deepEqual(
      payload,
      {
        action: HAB_SIMULATION_ACTION,
        object_identity:
          user.distinguished_name,
        object_class: 'user',
        attribute_name:
          HAB_ATTRIBUTE_NAME,
        operation: 'set',
        value: 100,
      }
    )

    assert.equal(
      typeof payload.value,
      'number'
    )
  }
)

test(
  'préserve la valeur entière zéro',
  () => {
    const payload =
      buildHabSenioritySimulationPayload({
        object: user,
        operation: 'set',
        value: 0,
      })

    assert.equal(payload.value, 0)
  }
)

test(
  'accepte la borne Integer32 maximale',
  () => {
    assert.equal(
      normalizeHabInteger32(
        HAB_MAXIMUM_VALUE
      ),
      HAB_MAXIMUM_VALUE
    )
  }
)

test(
  'rejette les décimales et valeurs hors bornes',
  () => {
    assert.throws(
      () => normalizeHabInteger32('1.5'),
      /entier/
    )

    assert.throws(
      () => normalizeHabInteger32(-1),
      /comprise/
    )

    assert.throws(
      () =>
        normalizeHabInteger32(
          HAB_MAXIMUM_VALUE + 1
        ),
      /comprise/
    )
  }
)

test(
  'construit un payload HAB clear sans valeur',
  () => {
    const payload =
      buildHabSenioritySimulationPayload({
        object: user,
        operation: 'clear',
        value: 900,
      })

    assert.equal(
      payload.operation,
      'clear'
    )
    assert.equal(payload.value, null)
  }
)

test(
  'ajoute created_by seulement au payload de job',
  () => {
    const validation =
      buildHabSenioritySimulationPayload({
        object: user,
        operation: 'set',
        value: 42,
      })

    const job =
      buildHabSenioritySimulationJobPayload({
        object: user,
        operation: 'set',
        value: 42,
      })

    assert.equal(
      'created_by' in validation,
      false
    )
    assert.equal(
      job.created_by,
      'react-admin'
    )
  }
)

test(
  'refuse les objets non utilisateurs',
  () => {
    assert.throws(
      () =>
        buildHabSenioritySimulationPayload({
          object: {
            ...user,
            object_class: 'computer',
          },
          operation: 'set',
          value: 10,
        }),
      /utilisateurs/
    )
  }
)

test(
  'lit une valeur HAB nullable',
  () => {
    assert.equal(
      getHabCurrentValue(user),
      null
    )

    assert.equal(
      getHabCurrentValue({
        ...user,
        hab_seniority_index: 0,
      }),
      0
    )

    assert.equal(
      getHabCurrentValue({
        ...user,
        hab_seniority_index: 125,
      }),
      125
    )
  }
)

test(
  'exige rôle AD et mode Simulation',
  () => {
    assert.equal(
      getHabSimulationEligibility({
        object: user,
        agentMode: 'Simulation',
        canManageActiveDirectory: true,
      }).eligible,
      true
    )

    assert.equal(
      getHabSimulationEligibility({
        object: user,
        agentMode: 'Production',
        canManageActiveDirectory: true,
      }).eligible,
      false
    )

    assert.equal(
      getHabSimulationEligibility({
        object: user,
        agentMode: 'Simulation',
        canManageActiveDirectory: false,
      }).eligible,
      false
    )
  }
)
