import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'

const config = fs.readFileSync(
  'frontend/vite.config.js',
  'utf8'
)

test('production assets use the FastAPI static mount', () => {
  assert.match(
    config,
    /base:\s*['"]\/static\/app\/['"]/
  )

  assert.doesNotMatch(
    config,
    /base:\s*['"]\/app\/['"]/
  )
})
