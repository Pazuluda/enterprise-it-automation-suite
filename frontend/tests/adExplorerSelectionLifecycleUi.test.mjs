import assert from "node:assert/strict"
import fs from "node:fs"
import test from "node:test"

const page = fs.readFileSync(
  new URL(
    "../src/features/active-directory/AdExplorerPage.jsx",
    import.meta.url
  ),
  "utf8"
)

const moveHook = fs.readFileSync(
  new URL(
    "../src/features/active-directory/hooks/useAdObjectMove.js",
    import.meta.url
  ),
  "utf8"
)

test("C7-FINAL clears ids when primary selection disappears", () => {
  const start = page.indexOf(
    "useEffect(() => {\n    if (selectedObject)"
  )

  assert.ok(start >= 0)

  const block = page.slice(
    start,
    start + 320
  )

  assert.match(
    block,
    /setSelectedObjectIds\(\[\]\)/
  )

  assert.match(
    block,
    /setSelectionAnchorId\(""\)/
  )
})

test("C7-FINAL node navigation clears the primary object", () => {
  const start = page.indexOf(
    "async function loadNodeContent("
  )

  assert.ok(start >= 0)

  const block = page.slice(
    start,
    start + 900
  )

  assert.match(
    block,
    /setSelectedNode\(node\)/
  )

  assert.match(
    block,
    /setSelectedObject\(null\)/
  )

  assert.match(
    block,
    /setViewType\(kind\)/
  )
})

test("C7-FINAL explicit deselection clears complete selection state", () => {
  const start = page.indexOf(
    "function clearAdExplorerSelection()"
  )

  assert.ok(start >= 0)

  const block = page.slice(
    start,
    start + 500
  )

  assert.match(
    block,
    /setSelectedObjectIds\(\[\]\)/
  )

  assert.match(
    block,
    /setSelectionAnchorId\(""\)/
  )

  assert.match(
    block,
    /setSelectedObject\(null\)/
  )

  assert.match(
    block,
    /setMembersMode\("direct"\)/
  )
})

test("C7-FINAL alternative views also discard stale primary selection", () => {
  const occurrences =
    page.match(
      /setSelectedObject\(null\)/g
    ) || []

  assert.ok(
    occurrences.length >= 5
  )
})

test("C7-FINAL drag end clears transient drag state", () => {
  const start = page.indexOf(
    "function finishAdExplorerDrag()"
  )

  assert.ok(start >= 0)

  const block = page.slice(
    start,
    start + 320
  )

  assert.match(
    block,
    /setDraggedAdExplorerObject\(null\)/
  )

  assert.match(
    block,
    /setDragOverAdExplorerDn\(""\)/
  )
})

test("C7-FINAL successful move clears selected object before refresh", () => {
  const movePattern =
    /action:\s*["\x27]move_object["\x27]/

  const match =
    moveHook.match(movePattern)

  assert.ok(match)

  const start =
    moveHook.indexOf(match[0])

  assert.ok(start >= 0)

  const block = moveHook.slice(
    start,
    start + 2200
  )

  assert.match(
    block,
    /setSelectedObject\(null\)/
  )

  assert.match(
    block,
    /await loadTree\(\)/
  )
})

test("C7-FINAL keeps one move job and no destructive bulk", () => {
  const pattern =
    /action:\s*["\x27]move_object["\x27]/g

  const pageJobs =
    page.match(pattern) || []

  const hookJobs =
    moveHook.match(pattern) || []

  assert.equal(
    pageJobs.length,
    0
  )

  assert.equal(
    hookJobs.length,
    1
  )

  const source =
    page + "\n" + moveHook

  for (const token of [
    "move_objects",
    "delete_objects",
    "bulk_move",
    "bulk_delete"
  ]) {
    assert.equal(
      source.includes(token),
      false
    )
  }
})
