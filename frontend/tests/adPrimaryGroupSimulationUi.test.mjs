import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const page = readFileSync(
  new URL(
    '../src/features/active-directory/AdExplorerPage.jsx',
    import.meta.url,
  ),
  'utf8',
)

const panel = readFileSync(
  new URL(
    '../src/features/active-directory/components/ObjectDetailsPanel.jsx',
    import.meta.url,
  ),
  'utf8',
)

assert.ok(
  panel.includes(
    'Définir comme groupe principal',
  ),
)

assert.ok(
  panel.includes(
    '!group.is_primary_group',
  ),
)

assert.ok(
  panel.includes(
    '(isUser || isComputer)',
  ),
)

assert.ok(
  panel.includes(
    'isEitasManagedDn(',
  ),
)

assert.ok(
  panel.includes(
    'typeof onSetPrimaryGroup ===',
  ),
)

assert.ok(
  panel.includes(
    "'set_primary_group'",
  ),
)

assert.ok(
  page.includes(
    'async function setPrimaryGroupSimulation(group, subject)',
  ),
)

assert.ok(
  page.includes(
    "!isEitasManagedDn(subjectDn)",
  ),
)

assert.ok(
  page.includes(
    "!isEitasManagedDn(groupDn)",
  ),
)

assert.ok(
  page.includes(
    ".toLowerCase() !== 'simulation'",
  ),
)

assert.ok(
  page.includes(
    "action: 'set_primary_group'",
  ),
)

assert.ok(
  page.includes(
    'object_identity: subjectDn',
  ),
)

assert.ok(
  page.includes(
    'group_identity: groupDn',
  ),
)

assert.ok(
  page.includes(
    'output.simulated !== true',
  ),
)

assert.ok(
  page.includes(
    'output.production_authorized !== false',
  ),
)

assert.ok(
  page.includes(
    'onSetPrimaryGroup={',
  ),
)

assert.ok(
  page.includes(
    '? setPrimaryGroupSimulation',
  ),
)

assert.equal(
  (page.match(/action: 'set_primary_group'/g) || []).length,
  1,
)

assert.equal(
  (
    panel.match(
      /Définir comme groupe principal/g,
    ) || []
  ).length,
  1,
)

assert.equal(
  (
    panel.match(
      /'set_primary_group'/g,
    ) || []
  ).length,
  2,
)

console.log(
  'C4.3C4B3A PRIMARY GROUP SIMULATION UI: OK',
)
