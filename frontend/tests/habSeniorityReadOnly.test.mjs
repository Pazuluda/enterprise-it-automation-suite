import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(
  new URL(
    '../src/features/active-directory/components/ObjectDetailsPanel.jsx',
    import.meta.url
  ),
  'utf8'
)

let passed = 0

function test(name, callback) {
  callback()
  passed += 1
  console.log(`OK - ${name}`)
}

test(
  'lit les alias de la valeur HAB',
  () => {
    assert.match(source, /hab_seniority_index/)
    assert.match(source, /msDS-HABSeniorityIndex/)
  }
)

test(
  'affiche un libelle HAB explicite',
  () => {
    assert.match(
      source,
      /Index de hiérarchie HAB/
    )
  }
)

test(
  'affiche Non défini lorsque la valeur est absente',
  () => {
    assert.match(source, /Non défini/)
  }
)

test(
  'limite la ligne HAB aux utilisateurs',
  () => {
    assert.match(
      source,
      /isUser[\s\S]{0,500}Index de hiérarchie HAB/
    )
  }
)

console.log(
  `LECTURE HAB FRONTEND : ${passed} TESTS REUSSIS`
)
