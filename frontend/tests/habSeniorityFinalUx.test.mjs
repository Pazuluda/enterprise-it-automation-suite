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

const hook = readFileSync(
  resolve(
    frontendRoot,
    'src/features/active-directory/hooks/'
      + 'useHabSenioritySimulation.js'
  ),
  'utf8'
)

const editor = readFileSync(
  resolve(
    frontendRoot,
    'src/features/active-directory/components/'
      + 'HabSenioritySimulationEditor.jsx'
  ),
  'utf8'
)

function getInitialDraftSource() {
  const start = hook.indexOf(
    'function createInitialDraft(object)'
  )

  const end = hook.indexOf(
    'function getHabFailureMessage',
    start
  )

  assert.ok(start >= 0)
  assert.ok(end > start)

  return hook.slice(start, end)
}

test(
  'initialise une valeur integer32 valide si HAB est absent',
  () => {
    const source = getInitialDraftSource()

    assert.match(
      hook,
      /HAB_MINIMUM_VALUE/
    )

    assert.match(
      source,
      /currentValue === null[\s\S]*?\? String\(HAB_MINIMUM_VALUE\)/
    )

    assert.doesNotMatch(
      source,
      /\? ''/
    )
  }
)

test(
  'fait defiler la modale vers le resultat final',
  () => {
    assert.match(
      editor,
      /const resultRef = useRef\(null\)/
    )

    assert.match(
      editor,
      /scrollIntoView\(\{/
    )

    assert.match(
      editor,
      /behavior: 'smooth'/
    )

    assert.match(
      editor,
      /ref=\{resultRef\}/
    )
  }
)

test(
  'declenche le defilement lorsque le job final apparait',
  () => {
    assert.match(
      editor,
      /\}, \[submittedJob\]\)/
    )

    assert.match(
      editor,
      /const submittedJob =[\s\S]*?editor\?\.submittedJob/
    )
  }
)
