import assert from "node:assert/strict"
import fs from "node:fs"
import test from "node:test"

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

test("C8.2A keeps dedicated local filter state", () => {
  for (const token of [
    "securityRuleQuery",
    "securityRuleType",
    "securityRuleOrigin",
  ]) {
    assert.ok(panel.includes(token))
  }

  assert.ok(
    panel.includes("setSecurityRuleQuery('')")
  )

  assert.ok(
    panel.includes("setSecurityRuleType('all')")
  )

  assert.ok(
    panel.includes("setSecurityRuleOrigin('all')")
  )
})

test("C8.2A filters ACE locally", () => {
  const block = securityBlock()

  for (const token of [
    "filteredSecurityRules",
    "normalizedSecurityRuleQuery",
    "access_control_type",
    "is_inherited",
    "active_directory_rights",
    "object_type_guid",
    "inherited_object_type_guid",
  ]) {
    assert.ok(block.includes(token))
  }
})

test("C8.2A exposes search type and origin filters", () => {
  const block = securityBlock()

  for (const token of [
    "Rechercher dans les ACE",
    "Filtrer par type d'ACE",
    "Autoriser",
    "Refuser",
    "Filtrer par origine d'ACE",
    "Explicites",
    "Héritées",
    "ACE affichée",
  ]) {
    assert.ok(block.includes(token))
  }
})

test("C8.2A renders only filtered ACE", () => {
  const block = securityBlock()

  assert.ok(
    block.includes(
      "filteredSecurityRules.map"
    )
  )

  assert.ok(
    block.includes(
      "Aucune ACE ne correspond aux filtres actifs."
    )
  )
})

test("C8.2A remains strictly read only", () => {
  const block = securityBlock()

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

test("C8.2A has dedicated filter styling", () => {
  for (const token of [
    ".aduc-security-tools",
    ".aduc-security-search",
    ".aduc-security-filter-group",
    ".aduc-security-filter-result",
  ]) {
    assert.ok(css.includes(token))
  }
})
