import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(
  new URL(
    '../src/features/active-directory/AdExplorerPage.jsx',
    import.meta.url
  ),
  'utf8'
)

const start = source.indexOf(
  '  async function runGlobalAdSearch('
)

const end = source.indexOf(
  '  function normalizeDeleteConfirmationDn(value) {',
  start
)

assert.ok(start >= 0)
assert.ok(end > start)

const block = source.slice(start, end)

test('C6.1 global search uses one unified AD Explorer job', () => {
  assert.ok(block.includes("'search_objects'"))
  assert.ok(block.includes('recursive: true'))
  assert.ok(block.includes('limit: 1000'))
})

test('C6.1 removes the legacy multi-source search fanout', () => {
  assert.ok(!block.includes('adDomainCatalog.search'))
  assert.ok(!block.includes('adSnapshot.search'))
  assert.ok(!block.includes("'search_users'"))
  assert.ok(!block.includes("'search_computers'"))
  assert.ok(!block.includes("'list_groups'"))
})

test('C6.1 keeps DN deduplication and search result view', () => {
  assert.ok(block.includes('const seen = new Set()'))
  assert.ok(block.includes('getObjectDn(item)'))
  assert.ok(block.includes("setViewType('search')"))
  assert.ok(block.includes('setViewItems(uniqueResults)'))
})

console.log('C6.1 UNIFIED AD SEARCH UI: OK')
