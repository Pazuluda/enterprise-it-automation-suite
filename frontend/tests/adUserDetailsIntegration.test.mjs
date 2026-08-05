import assert from 'node:assert/strict'
import {
  readFileSync,
} from 'node:fs'

const page = readFileSync(
  new URL(
    '../src/features/active-directory/AdExplorerPage.jsx',
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
  'importe les helpers de details utilisateur',
  () => {
    assert.match(
      page,
      /buildAdUserDetailsJobPayload/
    )
    assert.match(
      page,
      /extractAdUserDetails/
    )
    assert.match(
      page,
      /mergeAdUserDetails/
    )
    assert.match(
      page,
      /from '\.\/utils\/adUserDetails'/
    )
  }
)

test(
  'utilise un job AD Explorer get_user dedie',
  () => {
    assert.match(
      page,
      /async function runAdUserDetailsJob/
    )
    assert.match(
      page,
      /apiFetch\('\/api\/ad-explorer\/jobs'/
    )
    assert.match(
      page,
      /apiFetch\(`\/api\/ad-explorer\/jobs\/\$\{jobId\}`\)/
    )
    assert.match(
      page,
      /extractAdUserDetails\(job\)/
    )
  }
)

test(
    'ouvre la modale avant le lookup puis fusionne les details',
    () => {
      const start = page.indexOf(
        'async function openProperties'
      )
      const end = page.indexOf(
        'async function runGlobalAdSearch',
        start
      )
      const source = page.slice(start, end)

      assert.ok(start >= 0)
      assert.ok(end > start)

      const modalPosition = source.indexOf(
        'setPropertiesModal(target)'
      )

      const lookupPosition = source.indexOf(
        'await runAdUserDetailsJob(target)'
      )

      assert.ok(modalPosition >= 0)
      assert.ok(lookupPosition >= 0)

      assert.ok(
        modalPosition < lookupPosition
      )

      assert.match(
        source,
        /mergeAdUserDetails\(target, details\)/
      )

      assert.match(
        source,
        /setPropertiesModal\(previous =>/
      )

      assert.match(
        source,
        /matchesTarget\(previous\)/
      )
    }
  )

  test(
    'conserve la modale si le lookup detaille echoue',
    () => {
      const start = page.indexOf(
        'async function openProperties'
      )
      const end = page.indexOf(
        'async function runGlobalAdSearch',
        start
      )
      const source = page.slice(start, end)

      assert.ok(start >= 0)
      assert.ok(end > start)

      assert.match(
        source,
        /setSelectedObject\(target\)/
      )

      assert.match(
        source,
        /setPropertiesModal\(target\)/
      )

      assert.match(
        source,
        /catch \(error\)/
      )

      assert.match(
        source,
        /Lecture détaillée utilisateur impossible/
      )

      assert.doesNotMatch(
        source,
        /setPropertiesModal\(null\)/
      )
    }
  )

  console.log(
  `INTEGRATION DETAILS UTILISATEUR AD : `
  + `${passed} TESTS REUSSIS`
)
