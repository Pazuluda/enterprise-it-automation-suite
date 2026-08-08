import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const css = fs.readFileSync(
  'frontend/src/styles/07-active-directory.css',
  'utf8'
)

test('C5.3 contact modal stays compact and usable', () => {
  assert.match(css, /C5\.3 contact creation modal polish/)
  assert.match(css, /input\[type="checkbox"\]/)
  assert.match(css, /width:\s*18px/)
  assert.match(css, /height:\s*18px/)
  assert.match(css, /:has\(> input\[type="checkbox"\]\)/)
  assert.match(css, /position:\s*sticky/)
  assert.match(css, /bottom:\s*0/)
  assert.match(css, /max-height:\s*calc\(100vh - 24px\)/)
})
