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

test("C8.2B translates common Active Directory rights", () => {
  const block = securityBlock()

  for (const token of [
    'delete: "Supprimer"',
    'deletechild: "Supprimer des objets enfants"',
    'deletetree: "Supprimer la sous-arborescence"',
    'genericall: "Contrôle total"',
    'readproperty: "Lire les propriétés"',
    'writeproperty: "Modifier les propriétés"',
    'writedacl: "Modifier les autorisations"',
    'writeowner: "Modifier le propriétaire"',
  ]) {
    assert.ok(block.includes(token))
  }
})

test("C8.2B keeps unknown rights and supports combined rights", () => {
  const block = securityBlock()

  assert.ok(
    block.includes(
      "return labels[raw.toLowerCase()] || raw"
    )
  )

  assert.ok(block.includes('.split(",")'))
  assert.ok(block.includes(".map(securityRightLabel)"))
  assert.ok(block.includes('.join(" · ")'))
})

test("C8.2B translates Active Directory inheritance scope", () => {
  const block = securityBlock()

  for (const token of [
    'none: "Cet objet uniquement"',
    'all: "Cet objet et tous ses descendants"',
    'descendents: "Tous les descendants uniquement"',
    'selfandchildren: "Cet objet et ses enfants directs"',
    'children: "Enfants directs uniquement"',
  ]) {
    assert.ok(block.includes(token))
  }
})

test("C8.2B renders semantic and native technical values", () => {
  const block = securityBlock()

  assert.ok(block.includes('className="rights"'))
  assert.ok(block.includes('className="scope"'))

  assert.ok(
    block.includes(
      "rule?.active_directory_rights || \"—\""
    )
  )

  assert.ok(
    block.includes(
      "rule?.inheritance_type || \"None\""
    )
  )
})

test("C8.2B has dedicated semantic label styling", () => {
  for (const token of [
    "/* C8.2B - Semantic ACL labels */",
    ".aduc-security-row .rights",
    ".aduc-security-row .scope",
    ".aduc-security-row .rights small",
    ".aduc-security-row .scope small",
  ]) {
    assert.ok(css.includes(token))
  }
})

test("C8.2B remains strictly read only", () => {
  const block = securityBlock()

  for (const token of [
    "Set-Acl",
    "SetAccessRule",
    "AddAccessRule",
    "RemoveAccessRule",
    "SetOwner",
  ]) {
    assert.equal(block.includes(token), false)
  }
})
