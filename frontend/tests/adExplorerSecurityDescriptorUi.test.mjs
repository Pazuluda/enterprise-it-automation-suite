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

const panel = fs.readFileSync(
  new URL(
    "../src/features/active-directory/components/ObjectDetailsPanel.jsx",
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

function securityBlock() {
  const start = panel.indexOf(
    "function renderSecurityTab()"
  )

  const end = panel.indexOf(
    "function renderAccountTab()",
    start
  )

  assert.ok(start >= 0)
  assert.ok(end > start)

  return panel.slice(start, end)
}

test("C8.1C keeps dedicated security descriptor state", () => {
  assert.match(page, /securityDescriptor/)
  assert.match(page, /securityDescriptorLoading/)
  assert.match(page, /securityDescriptorError/)
  assert.match(page, /securityDescriptorTargetDn/)
})

test("C8.1C uses dedicated security descriptor job", () => {
  assert.match(
    page,
    /action: "get_security_descriptor"/
  )

  assert.match(
    page,
    /result\.read_only !== true/
  )
})

test("C8.1C caches descriptor unless refresh is forced", () => {
  assert.match(page, /!options\.force/)
  assert.match(page, /securityDescriptor\?\.read_only === true/)
})

test("C8.1C wires security data into details panel", () => {
  assert.match(page, /securityDescriptor=\{securityDescriptor\}/)
  assert.match(page, /onLoadSecurityDescriptor=\{loadSecurityDescriptor\}/)
})

test("C8.1C exposes managed-scope security tab", () => {
  assert.match(
    panel,
    /isManagedScope && dn/
  )

  assert.match(
    panel,
    /\["security", "Sécurité"\]/
  )
})

test("C8.1C loads ACL lazily from security tab", () => {
  assert.match(
    panel,
    /value === "security"/
  )

  assert.match(
    panel,
    /onLoadSecurityDescriptor\?\.\(displayed\)/
  )
})

test("C8.1C renders owner inheritance and DACL counters", () => {
  const block = securityBlock()

  for (const token of [
    "Propriétaire",
    "Héritage",
    "ACE explicites",
    "ACE héritées",
    "Total DACL",
  ]) {
    assert.ok(block.includes(token))
  }
})

test("C8.1C renders allow deny and explicit inherited rules", () => {
  const block = securityBlock()

  for (const token of [
    "Autoriser",
    "Refuser",
    "Explicite",
    "Héritée",
    "active_directory_rights",
    "object_type_guid",
  ]) {
    assert.ok(block.includes(token))
  }
})

test("C8.1C security panel remains strictly read only", () => {
  const block = securityBlock()

  assert.ok(block.includes("Lecture seule"))
  assert.ok(block.includes("SACL non chargée"))

  for (const token of [
    "Set-Acl",
    "SetAccessRule",
    "AddAccessRule",
    "RemoveAccessRule",
    "SetOwner",
  ]) {
    assert.equal(
      block.includes(token),
      false
    )
  }
})

test("C8.1C includes dedicated security styling", () => {
  for (const token of [
    ".aduc-security-tab",
    ".aduc-security-summary",
    ".aduc-security-table",
    ".aduc-security-row",
    ".aduc-security-readonly",
  ]) {
    assert.ok(css.includes(token))
  }
})
