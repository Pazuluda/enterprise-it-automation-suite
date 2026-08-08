import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildAdBreadcrumbs,
  buildAdNavigationNode,
  buildOuTree,
  isContainerObject,
} from '../src/features/active-directory/utils/adExplorerObjects.js'

const BASE = 'OU=EITAS,DC=API,DC=LOCAL'

test('C5.4 recognizes native containers', () => {
  assert.equal(
    isContainerObject({
      type: 'container',
      distinguished_name: `CN=Apps,${BASE}`,
    }),
    true,
  )
})

test('C5.4 tree includes OU and container', () => {
  const tree = buildOuTree([
    {
      type: 'organizationalunit',
      name: 'Team',
      distinguished_name: `OU=Team,${BASE}`,
    },
    {
      type: 'container',
      name: 'Apps',
      distinguished_name: `CN=Apps,OU=Team,${BASE}`,
    },
    {
      type: 'user',
      name: 'User',
      distinguished_name: `CN=User,OU=Team,${BASE}`,
    },
  ])

  assert.equal(tree.length, 2)
  assert.equal(
    tree.some(item => item.name === 'Apps'),
    true,
  )
})

test('C5.4 navigation node keeps container type', () => {
  const node = buildAdNavigationNode(
    `CN=Apps,OU=Team,${BASE}`
  )

  assert.equal(node.type, 'container')
})

test('C5.4 breadcrumbs include container', () => {
  const crumbs = buildAdBreadcrumbs(
    `CN=Apps,OU=Team,${BASE}`
  )

  assert.deepEqual(
    crumbs.map(item => item.label),
    ['API.LOCAL', 'EITAS', 'Team', 'Apps'],
  )
})
