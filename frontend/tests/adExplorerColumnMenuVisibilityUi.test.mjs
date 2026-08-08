import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const page = readFileSync(
  new URL(
    '../src/features/active-directory/AdExplorerPage.jsx',
    import.meta.url,
  ),
  'utf8',
)

const css = readFileSync(
  new URL(
    '../src/styles/07-active-directory.css',
    import.meta.url,
  ),
  'utf8',
)

test(
  'C6.2 keeps the column menu trigger explicit and accessible',
  () => {
    assert.ok(
      page.includes(
        'className="aduc-column-options-trigger"',
      ),
    )
    assert.ok(
      page.includes(
        'aria-label="Choisir les colonnes affichées"',
      ),
    )
    assert.ok(
      page.includes('<span>Colonnes</span>'),
    )
  },
)

test(
  'C6.2 raises the column menu above the table stacking context',
  () => {
    assert.ok(
      css.includes(
        '/* C6.2B - menu de colonnes visible au-dessus du tableau */',
      ),
    )
    assert.ok(
      css.includes('z-index: 40;'),
    )
    assert.ok(
      css.includes('z-index: 100;'),
    )
    assert.ok(
      css.includes(
        '.aduc-column-options-trigger {',
      ),
    )
  },
)

console.log('C6.2 COLUMN MENU VISIBILITY: OK')
