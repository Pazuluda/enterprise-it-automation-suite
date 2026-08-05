import test from 'node:test'
import assert from 'node:assert/strict'
import {
  readFileSync,
} from 'node:fs'
import {
  dirname,
  resolve,
} from 'node:path'
import {
  fileURLToPath,
} from 'node:url'

const currentDirectory = dirname(
  fileURLToPath(import.meta.url)
)

const source = readFileSync(
  resolve(
    currentDirectory,
    '../src/features/active-directory/components/'
      + 'AdObjectPropertiesModal.jsx'
  ),
  'utf8'
)

test(
  'utilise le DN comme identite de la modale',
  () => {
    assert.match(
      source,
      /const objectIdentity = String\([\s\S]*?getObjectDn\(object\)[\s\S]*?\.trim\(\)[\s\S]*?\.toLowerCase\(\)/
    )
  }
)

test(
  'reinitialise HAB uniquement quand le DN change',
  () => {
    const effect = source.match(
      /useEffect\(\(\) => \{[\s\S]*?setHabSimulationActive\(false\)[\s\S]*?\}, \[([^\]]+)\]\)/
    )

    assert.ok(
      effect,
      'effet de reinitialisation introuvable'
    )

    assert.equal(
      effect[1].trim(),
      'objectIdentity'
    )
  }
)

test(
  'ne ferme plus HAB sur une nouvelle reference du meme objet',
  () => {
    assert.doesNotMatch(
      source,
      /setHabSimulationActive\(false\)[\s\S]*?\}, \[object\]\)/
    )
  }
)
