import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const page = fs.readFileSync(
  new URL(
    '../src/features/active-directory/AdExplorerPage.jsx',
    import.meta.url
  ),
  'utf8'
)

const css = fs.readFileSync(
  new URL(
    '../src/styles/07-active-directory.css',
    import.meta.url
  ),
  'utf8'
)

test('AD Explorer exposes two draggable pane separators', () => {
  assert.equal(
    (
      page.match(
        /className="aduc-console-splitter"/g
      ) || []
    ).length,
    2
  )

  assert.match(
    page,
    /startAdExplorerPaneResize/
  )

  assert.match(
    page,
    /role="separator"/
  )
})

test('AD Explorer persists pane dimensions', () => {
  assert.match(
    page,
    /eitas_ad_explorer_pane_sizes_v1/
  )

  assert.match(
    page,
    /localStorage\.setItem/
  )

  assert.match(
    page,
    /resetAdExplorerPaneSizes/
  )
})

test('AD Explorer splitter keeps responsive fallback', () => {
  assert.match(
    css,
    /cursor:\s*col-resize/
  )

  assert.match(
    css,
    /--aduc-tree-width/
  )

  assert.match(
    css,
    /--aduc-details-width/
  )

  assert.match(
    css,
    /@media \(max-width: 980px\)/
  )
})
