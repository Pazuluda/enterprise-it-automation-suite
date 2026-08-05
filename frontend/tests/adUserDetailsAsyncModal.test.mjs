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
    'src/features/active-directory/'
      + 'AdExplorerPage.jsx'
  ),
  'utf8'
)

function getOpenPropertiesSource() {
  const start = source.indexOf(
    'async function openProperties(target)'
  )

  const end = source.indexOf(
    'async function runGlobalAdSearch',
    start
  )

  assert.notEqual(
    start,
    -1,
    'openProperties doit exister'
  )

  assert.notEqual(
    end,
    -1,
    'la fin de openProperties doit être détectable'
  )

  return source.slice(start, end)
}

test(
  'ouvre la modal avant la fin du lookup détaillé',
  () => {
    const block = getOpenPropertiesSource()

    const modalPosition = block.indexOf(
      'setPropertiesModal(target)'
    )

    const lookupPosition = block.indexOf(
      'await runAdUserDetailsJob(target)'
    )

    assert.notEqual(modalPosition, -1)
    assert.notEqual(lookupPosition, -1)

    assert.ok(
      modalPosition < lookupPosition,
      'la modal doit être ouverte avant le job get_user'
    )
  }
)

test(
  'protège la modal contre une réponse utilisateur périmée',
  () => {
    const block = getOpenPropertiesSource()

    assert.match(
      block,
      /propertiesDetailsRequestIdRef\.current/
    )

    assert.match(
      block,
      /setPropertiesModal\(previous =>/
    )

    assert.match(
      block,
      /matchesTarget\(previous\)/
    )
  }
)

test(
  'enrichit la modal sans la fermer ni la rouvrir',
  () => {
    const block = getOpenPropertiesSource()

    assert.match(
      block,
      /mergeAdUserDetails\(target, details\)/
    )

    assert.doesNotMatch(
      block,
      /setPropertiesModal\(null\)/
    )
  }
)
