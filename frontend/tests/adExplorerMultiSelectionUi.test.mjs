import assert from "node:assert/strict"
import fs from "node:fs"
import test from "node:test"

import {
  normalizeAdExplorerSelectionId,
  resolveAdExplorerSelection,
  selectAllAdExplorerSelection,
} from "../src/features/active-directory/utils/adExplorerSelection.js"

const page = fs.readFileSync(
  new URL(
    "../src/features/active-directory/AdExplorerPage.jsx",
    import.meta.url
  ),
  "utf8"
)

const css = fs.readFileSync(
  new URL(
    "../src/styles/07-active-directory.css",
    import.meta.url
  ),
  "utf8"
)

test("C7.1 normalizes selection identities", () => {
  assert.equal(
    normalizeAdExplorerSelectionId(
      " cn=Liam,ou=Users "
    ),
    "CN=LIAM,OU=USERS"
  )
})

test("C7.1 normal click replaces selection", () => {
  const result = resolveAdExplorerSelection({
    currentIds: ["A", "B"],
    clickedId: "C",
    visibleIds: ["A", "B", "C"],
  })

  assert.deepEqual(result.ids, ["C"])
  assert.equal(result.anchorId, "C")
})

test("C7.1 ctrl click adds an object", () => {
  const result = resolveAdExplorerSelection({
    currentIds: ["A"],
    clickedId: "B",
    visibleIds: ["A", "B", "C"],
    ctrlKey: true,
  })

  assert.deepEqual(result.ids, ["A", "B"])
})

test("C7.1 meta click behaves like ctrl", () => {
  const result = resolveAdExplorerSelection({
    currentIds: ["A"],
    clickedId: "B",
    visibleIds: ["A", "B"],
    metaKey: true,
  })

  assert.deepEqual(result.ids, ["A", "B"])
})

test("C7.1 ctrl click removes an object", () => {
  const result = resolveAdExplorerSelection({
    currentIds: ["A", "B"],
    clickedId: "B",
    visibleIds: ["A", "B"],
    ctrlKey: true,
  })

  assert.deepEqual(result.ids, ["A"])
})

test("C7.1 shift click selects a range", () => {
  const result = resolveAdExplorerSelection({
    currentIds: ["B"],
    clickedId: "D",
    anchorId: "B",
    visibleIds: ["A", "B", "C", "D", "E"],
    shiftKey: true,
  })

  assert.deepEqual(
    result.ids,
    ["B", "C", "D"]
  )
})

test("C7.1 ctrl shift adds a range", () => {
  const result = resolveAdExplorerSelection({
    currentIds: ["A"],
    clickedId: "D",
    anchorId: "B",
    visibleIds: ["A", "B", "C", "D"],
    ctrlKey: true,
    shiftKey: true,
  })

  assert.deepEqual(
    result.ids,
    ["A", "B", "C", "D"]
  )
})

test("C7.1 invalid shift anchor falls back", () => {
  const result = resolveAdExplorerSelection({
    currentIds: ["A"],
    clickedId: "C",
    anchorId: "Z",
    visibleIds: ["A", "B", "C"],
    shiftKey: true,
  })

  assert.deepEqual(result.ids, ["C"])
  assert.equal(result.anchorId, "C")
})

test("C7.1 select all deduplicates ids", () => {
  assert.deepEqual(
    selectAllAdExplorerSelection([
      "A",
      "b",
      "B",
      "",
      "C",
    ]),
    ["A", "B", "C"]
  )
})

test("C7.1 wires row multi selection", () => {
  assert.match(
    page,
    /selectedObjectIds/
  )

  assert.match(
    page,
    /selectionAnchorId/
  )

  assert.match(
    page,
    /selectObject\(\s*item,\s*event,\s*filteredViewItems/
  )

  assert.match(
    page,
    /primary-selected-object/
  )

  assert.match(
    page,
    /aria-selected=/
  )
})

test("C7.1 wires keyboard selection", () => {
  assert.match(
    page,
    /aria-multiselectable="true"/
  )

  assert.match(
    page,
    /handleAdExplorerSelectionKeyDown/
  )

  assert.match(
    page,
    /selectAllAdExplorerSelection/
  )

  assert.match(
    page,
    /event\.key === "Escape"/
  )
})

test("C7.1 exposes selection styling", () => {
  assert.match(
    css,
    /C7\.1 - multi-selection/
  )

  assert.match(
    css,
    /\.aduc-table-row\.primary-selected-object/
  )
})
