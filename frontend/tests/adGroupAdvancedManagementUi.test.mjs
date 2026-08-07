import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const creation = readFileSync(
  new URL(
    '../src/features/active-directory/hooks/useAdAdminCreation.js',
    import.meta.url,
  ),
  'utf8',
)

const form = readFileSync(
  new URL(
    '../src/features/active-directory/components/UpdateObjectForm.jsx',
    import.meta.url,
  ),
  'utf8',
)

const updateHook = readFileSync(
  new URL(
    '../src/features/active-directory/hooks/useAdObjectUpdate.js',
    import.meta.url,
  ),
  'utf8',
)

const members = readFileSync(
  new URL(
    '../src/features/active-directory/hooks/useAdGroupMembers.js',
    import.meta.url,
  ),
  'utf8',
)

assert.ok(
  creation.includes(
    "modal.action === 'create_group'",
  ),
)

assert.ok(
  creation.includes(
    "action: 'create_group'",
  ),
)

for (const value of [
  "'Global'",
  "'Universal'",
  "'DomainLocal'",
  "'Security'",
  "'Distribution'",
]) {
  assert.ok(creation.includes(value))
}

assert.ok(
  creation.includes(
    "return 'Le scope du groupe est invalide.'",
  ),
)

assert.ok(
  creation.includes(
    "return 'Le type du groupe est invalide.'",
  ),
)

assert.ok(
  form.includes(
    '<span>Portée du groupe</span>',
  ),
)

assert.ok(
  form.includes(
    "'groupScope'",
  ),
)

assert.ok(
  form.includes(
    '<span>Catégorie du groupe</span>',
  ),
)

assert.ok(
  form.includes(
    "'groupCategory'",
  ),
)

assert.ok(
  form.includes(
    '<span>Gestionnaire — Nom distinctif</span>',
  ),
)

assert.ok(
  form.includes(
    'value={updateForm.managedBy || \'\'}',
  ),
)

assert.ok(
  form.includes(
    'onClick={clearManagerSelection}',
  ),
)

assert.ok(
  updateHook.includes(
    "groupScope: getAdAttributeValue(",
  ),
)

assert.ok(
  updateHook.includes(
    "groupCategory: getAdAttributeValue(",
  ),
)

assert.ok(
  updateHook.includes(
    "managedBy: getAdAttributeValue(",
  ),
)

for (const alias of [
  "'managedBy'",
  "'managed_by'",
  "'managed_by_dn'",
  "'managedByDn'",
]) {
  assert.ok(updateHook.includes(alias))
}

assert.ok(
  updateHook.includes(
    'isUpdateGroupTarget(target)',
  ),
)

assert.ok(
  updateHook.includes(
    "return 'managedBy'",
  ),
)

assert.ok(
  updateHook.includes(
    'async function prepareClearManager(',
  ),
)

assert.ok(
  members.includes(
    "action: 'add_group_member'",
  ),
)

assert.ok(
  members.includes(
    "action: 'remove_group_member'",
  ),
)

assert.ok(
  members.includes(
    'if (!isEitasManagedObject(group))',
  ),
)

console.log(
  'C4-FINAL GROUP ADVANCED MANAGEMENT UI: OK',
)
