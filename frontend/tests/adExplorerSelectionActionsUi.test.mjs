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

const css = fs.readFileSync(
  new URL(
    "../src/styles/07-active-directory.css",
    import.meta.url
  ),
  "utf8"
)

test("C7.2 exposes the selection toolbar", () => {
  assert.match(
    page,
    /aduc-selection-actions/
  )
})

test("C7.2 copies selected DNs", () => {
  assert.match(
    page,
    /Copier les DN/
  )

  assert.match(
    page,
    /copyAdExplorerSelection\(\s*"dn"/
  )
})

test("C7.2 copies selected names", () => {
  assert.match(
    page,
    /Copier les noms/
  )

  assert.match(
    page,
    /copyAdExplorerSelection\(\s*"name"/
  )
})

test("C7.2 exposes CSV copy", () => {
  assert.match(
    page,
    /Copier CSV/
  )

  assert.match(
    page,
    /Nom;Type;Compte SAM;E-mail;DN/
  )
})

test("C7.2 uses the existing clipboard helper", () => {
  assert.match(
    page,
    /await copyText\(text\)/
  )
})

test("C7.2 keeps copy user single selection only", () => {
  assert.match(
    page,
    /selectedObjectIds\.length === 1/
  )

  assert.match(
    page,
    /isCopyableUserSource\(\s*selectedObject/
  )

  assert.match(
    page,
    /openCopyUser\(\s*selectedObject/
  )
})

test("C7.2 exposes explicit deselection", () => {
  assert.match(
    page,
    /Désélectionner/
  )

  assert.match(
    page,
    /clearAdExplorerSelection/
  )
})

test("C7.2 toolbar is inside the table", () => {
  const tableStart =
    page.indexOf(
      "className=\"aduc-table\""
    )

  const toolbarStart =
    page.indexOf(
      "className=\"aduc-selection-actions\""
    )

  const headerStart =
    page.indexOf(
      "className=\"aduc-table-row header\"",
      toolbarStart
    )

  assert.ok(
    tableStart >= 0
  )

  assert.ok(
    toolbarStart > tableStart
  )

  assert.ok(
    headerStart > toolbarStart
  )
})

test("C7.2 does not add destructive bulk jobs", () => {
  const toolbarStart =
    page.indexOf(
      "className=\"aduc-selection-actions\""
    )

  const headerStart =
    page.indexOf(
      "className=\"aduc-table-row header\"",
      toolbarStart
    )

  const toolbar =
    page.slice(
      toolbarStart,
      headerStart
    )

  assert.doesNotMatch(
    toolbar,
    /delete_object/
  )

  assert.doesNotMatch(
    toolbar,
    /move_object/
  )
})

test("C7.2 has compact dedicated styling", () => {
  assert.match(
    css,
    /C7\.2 - selection action bar/
  )

  assert.match(
    css,
    /align-self: flex-start/
  )

  assert.match(
    css,
    /flex: 0 0 auto/
  )
})
