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

const frontendRoot = resolve(
  currentDirectory,
  '..'
)

const source = readFileSync(
  resolve(
    frontendRoot,
    'src/features/active-directory/hooks/'
      + 'useHabSenioritySimulation.js'
  ),
  'utf8'
)

test(
  'utilise le DN comme identite stable',
  () => {
    assert.match(
      source,
      /const objectIdentity = useMemo\(/
    )

    assert.match(
      source,
      /getObjectDn\(object\)/
    )

    assert.match(
      source,
      /latestObjectRef\.current = object/
    )
  }
)

test(
  'ne reinitialise pas sur une nouvelle reference du meme objet',
  () => {
    const match = source.match(
      /useEffect\(\(\) => \{\s*setActive\(false\)[\s\S]*?\}, \[([^\]]+)\]\)/
    )

    assert.ok(
      match,
      'effet de reinitialisation HAB introuvable'
    )

    assert.equal(
      match[1].trim(),
      'objectIdentity'
    )

    assert.match(
      match[0],
      /createInitialDraft\(\s*latestObjectRef\.current\s*\)/
    )

    assert.doesNotMatch(
      match[0],
      /\}, \[object\]\)/
    )
  }
)

test(
  'preserve le resultat durant un enrichissement du meme DN',
  () => {
    const effectStart = source.indexOf(
      'useEffect(() => {\n    setActive(false)'
    )

    const effectEnd = source.indexOf(
      '}, [objectIdentity])',
      effectStart
    )

    assert.ok(effectStart >= 0)
    assert.ok(effectEnd > effectStart)

    const effect = source.slice(
      effectStart,
      effectEnd
    )

    assert.match(
      effect,
      /setSubmissionStatus\(''\)/
    )

    assert.match(
      effect,
      /setSubmittedJob\(null\)/
    )

    assert.match(
      source,
      /setSubmittedJob\(finalJob\)/
    )
  }
)
