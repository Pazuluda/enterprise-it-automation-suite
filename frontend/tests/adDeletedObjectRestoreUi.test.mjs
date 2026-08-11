import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const page = readFileSync(
  'frontend/src/features/active-directory/AdExplorerPage.jsx',
  'utf8'
)

const component = readFileSync(
  'frontend/src/features/active-directory/components/'
    + 'DeletedObjectRestorePanel.jsx',
  'utf8'
)

test(
  'C9-FINAL branche la corbeille dans AD Explorer',
  () => {
    assert.match(
      page,
      /import DeletedObjectRestorePanel/
    )

    assert.match(
      page,
      /<DeletedObjectRestorePanel/
    )

    assert.match(
      page,
      /apiFetch=\{apiFetch\}/
    )
  }
)

test(
  'B1 conserve inventaire preflight revalidation et simulation',
  () => {
    assert.match(
      component,
      /action:\s*'get_deleted_objects'/
    )

    assert.match(
      component,
      /\/api\/ad-explorer\/deleted-objects\/preflight/
    )

    assert.match(
      component,
      /revalidate_deleted_object_preflight/
    )

    assert.match(
      component,
      /restore-simulation\/prepare/
    )
  }
)

test(
  'B2 branche challenge autorisation et post-autorisation',
  () => {
    assert.match(
      component,
      /deleted-object-restore\/'[\s\S]*ticket-challenge/
    )

    assert.match(
      component,
      /deleted-object-restore\/'[\s\S]*authorization/
    )

    assert.match(
      component,
      /deleted-object-restore\/'[\s\S]*post-authorization/
    )
  }
)

test(
  'la queue de restauration réelle reste absente',
  () => {
    assert.doesNotMatch(
      component,
      /execution\/queue/
    )

    assert.match(
      component,
      /Exécution toujours verrouillée/
    )
  }
)

test(
  'les confirmations humaines exactes sont obligatoires',
  () => {
    assert.match(
      component,
      /exactObjectConfirmed/
    )

    assert.match(
      component,
      /exactTargetConfirmed/
    )

    assert.match(
      component,
      /acknowledge_exact_object:\s*true/
    )

    assert.match(
      component,
      /acknowledge_exact_target:\s*true/
    )

    assert.match(
      component,
      /acknowledge_restore_write:\s*true/
    )

    assert.match(
      component,
      /authorizationReason/
    )

    assert.match(
      component,
      /length >= 8/
    )
  }
)

test(
  'post-autorisation exige une nouvelle preuve live',
  () => {
    assert.match(
      component,
      /postAuthLiveJobId/
    )

    assert.match(
      component,
      /authorization\?\.fresh_live_job_id/
    )

    assert.match(
      component,
      /La preuve live post-autorisation doit être nouvelle/
    )
  }
)

test(
  'les invariants sensibles restent fail-closed',
  () => {
    for (const marker of [
      'production_authorized = false',
      'restore_authorized = false',
      'execution_authorized = false',
      'write_performed = false',
      'authorization_consumed = true',
      'execution_ticket_consumed = true',
      'confirmation_text',
    ]) {
      assert.match(
        component,
        new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      )
    }
  }
)


test(
  'C9-FINAL place la corbeille hors du panneau étroit',
  () => {
    assert.match(
      page,
      /className="aduc-deleted-restore-wide"/
    )

    const detailsStart =
      page.indexOf('<ObjectDetailsPanel')

    const detailsSectionClose =
      page.indexOf('</section>', detailsStart)

    const recyclePanel =
      page.indexOf('<DeletedObjectRestorePanel')

    assert.ok(detailsStart >= 0)
    assert.ok(detailsSectionClose >= 0)
    assert.ok(recyclePanel > detailsSectionClose)
  }
)


test(
  'C9-FINAL garde le nom et le type visibles dans la corbeille',
  () => {
    const css = readFileSync(
      'frontend/src/styles/07-active-directory.css',
      'utf8'
    )

    assert.match(
      css,
      /\.aduc-deleted-restore-list > button \{[\s\S]*color: #0f172a;/
    )

    assert.match(
      css,
      /\.aduc-deleted-restore-list > button strong/
    )

    assert.match(
      css,
      /\.aduc-deleted-restore-list > button span/
    )
  }
)


test(
  'C9-FINAL exige une preuve live plus récente que la Simulation',
  () => {
    assert.match(
      component,
      /challengeLiveJobId/
    )

    assert.match(
      component,
      /challengeLiveReady/
    )

    assert.match(
      component,
      /Revalider après Simulation/
    )

    assert.match(
      component,
      /Revalidation post-Simulation terminée/
    )

    assert.match(
      component,
      /fresh_live_job_id:\s*[\s\S]*challengeLiveJobId/
    )

    assert.doesNotMatch(
      component,
      /fresh_live_job_id:\s*liveJobId/
    )
  }
)


test(
  'C9-FINAL affiche et bloque un challenge humain expiré',
  () => {
    assert.match(
      component,
      /Challenge valable 2 minutes/
    )

    assert.match(
      component,
      /challenge\?\.expires_at/
    )

    assert.match(
      component,
      /isTimestampExpired/
    )

    assert.match(
      component,
      /challengeExpired/
    )

    assert.match(
      component,
      /Challenge humain expiré/
    )

    assert.match(
      component,
      /autorisation[\s\S]*bloquée localement/
    )
  }
)
