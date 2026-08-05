import assert from 'node:assert/strict'
import test from 'node:test'
import {
  readFile,
} from 'node:fs/promises'

const path =
  new URL(
    '../src/features/active-directory/hooks/useHabSenioritySimulation.js',
    import.meta.url
  )

const source = await readFile(
  path,
  'utf8'
)

test(
  'utilise exclusivement les routes HAB dédiées',
  () => {
    assert.match(
      source,
      /hab-seniority\/validate/
    )
    assert.match(
      source,
      /hab-seniority\/jobs/
    )
    assert.doesNotMatch(
      source,
      /ldap\/update\/jobs/
    )
  }
)

test(
  'exige une validation à jour avant le job',
  () => {
    assert.match(
      source,
      /validationIsCurrent/
    )
    assert.match(
      source,
      /Une validation HAB à jour est obligatoire/
    )
  }
)

test(
  'refuse toute autorisation Production ou exécution',
  () => {
    assert.match(
      source,
      /production_authorized !== false/
    )
    assert.match(
      source,
      /execution_authorized !== false/
    )
  }
)

test(
  'contrôle le type integer32',
  () => {
    assert.match(
      source,
      /HAB_VALUE_TYPE/
    )
    assert.match(
      source,
      /Le type HAB validé doit rester integer32/
    )
  }
)

test(
  'suit le job par la route AD Admin existante',
  () => {
    assert.match(
      source,
      /\/api\/ad-admin\/jobs\//
    )
    assert.match(
      source,
      /status === 'completed'/
    )
    assert.match(
      source,
      /status === 'failed'/
    )
  }
)

test(
  'transmet created_by uniquement lors de la création',
  () => {
    assert.match(
      source,
      /createdBy: 'react-admin'/
    )
    assert.match(
      source,
      /buildHabSenioritySimulationJobPayload/
    )
  }
)
