import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const page = readFileSync(new URL('../src/features/active-directory/AdExplorerPage.jsx', import.meta.url), 'utf8')
const panel = readFileSync(new URL('../src/features/active-directory/components/ObjectDetailsPanel.jsx', import.meta.url), 'utf8')
const css = readFileSync(new URL('../src/styles/07-active-directory.css', import.meta.url), 'utf8')

assert.ok(page.includes("const [membersMode, setMembersMode] = useState('direct')"))
assert.ok(page.includes('options.recursive === undefined'))
assert.ok(page.includes('Boolean(options.forceJob || recursive)'))
assert.ok(page.includes('recursive,'))
assert.ok(page.includes('loadGroupMembers(item, { recursive: false })'))
assert.ok(page.includes('membersMode={membersMode}'))
assert.ok(page.includes('onMembersModeChange'))
assert.ok(panel.includes("membersMode = 'direct'"))
assert.ok(panel.includes('aria-label="Portée des membres"'))
assert.ok(css.includes('.aduc-members-scope button[aria-pressed="false"]'))
assert.ok(css.includes('.aduc-members-scope button[aria-pressed="true"]'))
assert.ok(css.includes('background: linear-gradient(135deg, #4f46e5, #2563eb)'))
assert.ok(css.includes('box-shadow: none'))
assert.ok(panel.includes('>Directs</button>'))
assert.ok(panel.includes('>Imbriqués</button>'))
assert.ok(panel.includes('member.direct === false'))
assert.ok(panel.includes('member.depth'))
assert.ok(panel.includes('member.parent_group_dn'))
assert.ok(panel.includes('member.direct !== false'))
assert.ok(panel.includes('Retrait via le groupe parent'))

console.log('C4.2D4E FRONTEND RECURSIVE MEMBERS UI: OK')
