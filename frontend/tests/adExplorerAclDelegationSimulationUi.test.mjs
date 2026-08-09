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

test("C8.3D1 wires ACL Simulation through existing AD Admin jobs", () => {
  assert.match(
    page,
    /action: "simulate_acl_delegation"/
  )

  assert.match(
    page,
    /await runAdAdminJob/
  )

  assert.match(
    page,
    /onSimulateAclDelegation=/
  )
})

test("C8.3D1 validates all non-authorizing runtime invariants", () => {
  for (const token of [
    'output.mode !== "Simulation"',
    "output.simulated !== true",
    "output.write_performed !== false",
    "output.production_authorized !== false",
    "output.ad_write_authorized !== false",
    'output.execution_policy !== "simulation_only"',
  ]) {
    assert.ok(page.includes(token))
  }
})

test("C8.3D1 exposes Simulation only to AD managers", () => {
  assert.match(
    page,
    /canManageActiveDirectory\s*\?\s*simulateAclDelegation/
  )
})

test("C8.3D1 renders delegation controls in Security tab", () => {
  const block = securityBlock()

  for (const token of [
    "Délégation — Simulation",
    "Simulation uniquement",
    "Principal",
    "Droits",
    "Portée",
    "Simuler la délégation",
  ]) {
    assert.ok(block.includes(token))
  }
})

test("C8.3D1 exposes only the approved rights set", () => {
  const block = securityBlock()

  for (const right of [
    "ReadProperty",
    "WriteProperty",
    "CreateChild",
    "DeleteChild",
    "ListChildren",
    "ReadControl",
    "ExtendedRight",
    "GenericRead",
  ]) {
    assert.ok(block.includes(right))
  }

  assert.equal(
    block.includes("GenericAll"),
    false
  )
})

test("C8.3D1 keeps Allow fixed and does not expose Deny selection", () => {
  assert.match(
    page,
    /access_control_type: "Allow"/
  )

  const block = securityBlock()

  assert.ok(
    block.includes(
      "Les ACE Refuser ne sont pas proposées dans C8.3."
    )
  )

  assert.equal(
    block.includes(
      'value="Deny"'
    ),
    false
  )
})

test("C8.3D1 renders explicit no-write result", () => {
  const block = securityBlock()

  for (const token of [
    "Aucune ACL Active Directory modifiée",
    "simulated = true",
    "write_performed = false",
    "production_authorized = false",
    "ad_write_authorized = false",
  ]) {
    assert.ok(block.includes(token))
  }
})

test("C8.3D1 has no production apply control", () => {
  const block = securityBlock()

  assert.equal(
    block.includes("Appliquer la délégation"),
    false
  )

  assert.equal(
    block.includes("Mode Production"),
    false
  )
})

test("C8.3D2 keeps polished responsive styling", () => {
  for (const token of [
    "/* C8.3D2 - ACL delegation simulation visual polish */",
    ".aduc-acl-delegation-simulation",
    ".aduc-acl-delegation-right-grid",
    ".aduc-acl-delegation-result",
    "@media (max-width: 780px)",
  ]) {
    assert.ok(css.includes(token))
  }
})
