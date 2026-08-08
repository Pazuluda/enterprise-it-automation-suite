import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

import {
  adHistoryJobMatchesObject,
} from '../src/features/active-directory/utils/adHistory.js'

const sourceDn =
  'CN=C54-SOURCE-0808,OU=C54-BROWSER-0808,OU=EITAS,DC=API,DC=LOCAL'

const destDn =
  'CN=C54-DEST-0808,OU=C54-BROWSER-0808,OU=EITAS,DC=API,DC=LOCAL'

test(
  'history matches the displayed object identity',
  () => {
    assert.equal(
      adHistoryJobMatchesObject(
        {
          action: 'update_object_properties',
          payload: {
            object_identity: sourceDn,
          },
        },
        sourceDn,
      ),
      true,
    )
  },
)

test(
  'history rejects another object identity',
  () => {
    assert.equal(
      adHistoryJobMatchesObject(
        {
          action: 'delete_object',
          payload: {
            object_identity: sourceDn,
          },
        },
        destDn,
      ),
      false,
    )
  },
)

test(
  'history follows a rename destination identity',
  () => {
    const renamedDn =
      'CN=C54-SOURCE-SIM,OU=C54-BROWSER-0808,OU=EITAS,DC=API,DC=LOCAL'

    assert.equal(
      adHistoryJobMatchesObject(
        {
          action: 'rename_object',
          payload: {
            object_identity: sourceDn,
            new_name: 'C54-SOURCE-SIM',
          },
        },
        renamedDn,
      ),
      true,
    )
  },
)

test(
  'history follows a move destination identity',
  () => {
    const movedDn =
      'CN=C54-SOURCE-0808,CN=C54-DEST-0808,OU=C54-BROWSER-0808,OU=EITAS,DC=API,DC=LOCAL'

    assert.equal(
      adHistoryJobMatchesObject(
        {
          action: 'move_object',
          payload: {
            object_identity: sourceDn,
            target_parent_dn: destDn,
          },
        },
        movedDn,
      ),
      true,
    )
  },
)

test(
  'history derives a created container identity',
  () => {
    const createdDn =
      'CN=C54-SIM-ONLY,CN=C54-DEST-0808,OU=C54-BROWSER-0808,OU=EITAS,DC=API,DC=LOCAL'

    assert.equal(
      adHistoryJobMatchesObject(
        {
          action: 'create_container',
          payload: {
            name: 'C54-SIM-ONLY',
            parent_dn: destDn,
          },
        },
        createdDn,
      ),
      true,
    )
  },
)

test(
  'details scope history and update rename show success messages',
  () => {
    const details = readFileSync(
      'frontend/src/features/active-directory/components/ObjectDetailsPanel.jsx',
      'utf8',
    )

    const update = readFileSync(
      'frontend/src/features/active-directory/hooks/useAdObjectUpdate.js',
      'utf8',
    )

    const rename = readFileSync(
      'frontend/src/features/active-directory/hooks/useAdObjectRename.js',
      'utf8',
    )

    assert.match(
      details,
      /adHistoryJobMatchesObject\(\s*job,\s*dn\s*\)/,
    )

    assert.match(
      update,
      /setStatus\(message\)\s*setMessage\?\.\(message\)/,
    )

    assert.match(
      rename,
      /setStatus\(message\)\s*setMessage\?\.\(message\)/,
    )
  },
)

test(
  'object history loads the complete bounded AD Admin window',
  () => {
    const page = readFileSync(
      'frontend/src/features/active-directory/AdExplorerPage.jsx',
      'utf8',
    )

    assert.equal(
      page.split('/api/ad-admin/jobs?limit=1000').length - 1,
      2,
    )

    assert.equal(
      page.includes('/api/ad-admin/jobs?limit=50'),
      false,
    )
  },
)
