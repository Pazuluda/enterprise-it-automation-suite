import assert from 'node:assert/strict'
import test from 'node:test'
import {
  readFile,
} from 'node:fs/promises'

const path =
  new URL(
    '../src/features/active-directory/components/HabSenioritySimulationEditor.jsx',
    import.meta.url
  )

const source = await readFile(
  path,
  'utf8'
)

test(
  'affiche un contrôle HAB dédié',
  () => {
    assert.match(
      source,
      /Simulation HAB Seniority Index/
    )
    assert.match(
      source,
      /msDS-HABSeniorityIndex/
    )
  }
)

test(
  'propose uniquement set et clear',
  () => {
    assert.match(
      source,
      /option value="set"/
    )
    assert.match(
      source,
      /option value="clear"/
    )
    assert.doesNotMatch(
      source,
      /option value="unchanged"/
    )
  }
)

test(
  'utilise un champ entier borné',
  () => {
    assert.match(
      source,
      /type="number"/
    )
    assert.match(
      source,
      /HAB_MINIMUM_VALUE/
    )
    assert.match(
      source,
      /HAB_MAXIMUM_VALUE/
    )
    assert.match(
      source,
      /step="1"/
    )
  }
)

test(
  'valide avant de créer le job',
  () => {
    assert.match(
      source,
      /validateDraft/
    )
    assert.match(
      source,
      /validationIsCurrent/
    )
    assert.match(
      source,
      /submitSimulation/
    )
  }
)

test(
  'demande une confirmation explicite',
  () => {
    assert.match(
      source,
      /window\.confirm/
    )
    assert.match(
      source,
      /Aucune écriture réelle/
    )
  }
)

test(
  'n’expose aucun choix Production',
  () => {
    assert.match(
      source,
      /Simulation uniquement/
    )
    assert.doesNotMatch(
      source,
      /value="Production"/
    )
    assert.doesNotMatch(
      source,
      /Set-AD/
    )
  }
)

test(
  'affiche la valeur actuelle nullable',
  () => {
    assert.match(
      source,
      /Valeur actuelle/
    )
    assert.match(
      source,
      /Non défini/
    )
  }
)

test(
  'affiche le résultat final du job',
  () => {
    assert.match(
      source,
      /submittedJob/
    )
    assert.match(
      source,
      /Simulation terminée/
    )
    assert.match(
      source,
      /Simulation en erreur/
    )
  }
)
