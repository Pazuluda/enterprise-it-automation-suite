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

const css = fs.readFileSync(
  new URL(
    "../src/styles/07-active-directory.css",
    import.meta.url
  ),
  "utf8"
)

test("C7.3 keeps drag state in explorer", () => {
  assert.match(page, /draggedAdExplorerObject/)
  assert.match(page, /dragOverAdExplorerDn/)
})

test("C7.3 makes managed rows draggable", () => {
  assert.match(page, /draggable=\{/)
  assert.match(page, /isEitasManagedObject\(/)
})

test("C7.3 wires native drag events", () => {
  assert.match(page, /onDragStart=\{event =>/)
  assert.match(page, /onDragEnd=\{/)
})

test("C7.3 wires tree drop targets", () => {
  assert.match(page, /data-drop-state=\{/)
  assert.match(page, /onDragEnter=\{/)
  assert.match(page, /onDragOver=\{event =>/)
  assert.match(page, /onDrop=\{event =>/)
})

test("C7.3 blocks multi-selection drag", () => {
  assert.match(
    page,
    /selectedObjectIds\.length > 1/
  )

  assert.match(
    page,
    /un seul objet à la fois/
  )
})

test("C7.3 only accepts structural destinations", () => {
  assert.match(
    page,
    /isOuObject\(destination\)/
  )

  assert.match(
    page,
    /isContainerObject\(destination\)/
  )
})

test("C7.3 refuses unmanaged destinations", () => {
  assert.match(
    page,
    /isEitasManagedObject\(destination\)/
  )
})

test("C7.3 refuses current parent and descendants", () => {
  assert.match(
    page,
    /getParentDn\(sourceDn\)/
  )

  assert.match(
    page,
    /destinationKey\.endsWith/
  )
})

test("C7.3 prepares existing move modal", () => {
  assert.match(
    page,
    /openMoveObject\(source\)/
  )

  assert.match(
    page,
    /setMoveTargetDn\(/
  )
})

test("C7.3 keeps one canonical move job", () => {
  const pageJobs =
    page.match(
      /action:\s*["]move_object["]/g
    ) || []

  const hookJobs =
    moveHook.match(
      /action:\s*["']move_object["']/g
    ) || []

  assert.equal(pageJobs.length, 0)
  assert.equal(hookJobs.length, 1)

  assert.match(
    css,
    /C7\.3 - drag and drop/
  )

  assert.match(
    css,
    /data-drop-state="valid"/
  )

  assert.match(
    css,
    /data-drop-state="blocked"/
  )
})
