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

test("C8.4D-A3B1 preserves trusted job provenance", () => {
  assert.match(
    page,
    /security_descriptor_job_id:\s*jobId/
  )

  assert.match(
    page,
    /const simulationJobId = String\(/
  )

  assert.match(
    page,
    /simulation_job_id:\s*simulationJobId/
  )

  assert.match(
    page,
    /Identifiant du job de Simulation ACL absent/
  )
})

test("C8.4D-A3B1 keeps existing UI result shapes usable", () => {
  assert.match(
    page,
    /const resultWithEvidence = \{[\s\S]*?\.\.\.result,[\s\S]*?security_descriptor_job_id: jobId/
  )

  assert.match(
    page,
    /const resultWithEvidence = \{[\s\S]*?\.\.\.output,[\s\S]*?simulation_job_id: simulationJobId/
  )
})

test("C8.4D-A3B1 keeps Production execution control absent", () => {
  const block = securityBlock()

  assert.equal(
    block.includes(
      "Appliquer la délégation"
    ),
    false
  )

  assert.equal(
    page.includes(
      "/api/admin/agent/mode"
    ),
    false
  )
})

test("C8.4D-A3C2 prepares Production from server evidence only", () => {
  assert.ok(
    page.includes(
      "/api/ad-admin/acl-delegation/"
      + "production-preparation"
    )
  )

  assert.match(
    page,
    /simulation_job_id:\s*simulationJobId/
  )

  assert.match(
    page,
    /security_descriptor_job_id:\s*securityDescriptorJobId/
  )

  assert.ok(
    page.includes(
      "trusted_evidence_loaded"
    )
  )

  assert.ok(
    page.includes(
      "binding_validated"
    )
  )
})

test("C8.4D-A3C2 requires Simulation mode for preparation", () => {
  assert.ok(
    page.includes(
      "l’agent doit rester en mode Simulation"
    )
  )

  assert.match(
    page,
    /await loadAdAgentMode\(\)/
  )
})

test("C8.4D-A3C2 renders the controlled preparation UI", () => {
  const block = securityBlock()

  for (const token of [
    "Préparation Production contrôlée",
    "Préparer Production",
    "Fingerprint ACL",
    "DACL SHA-256",
    "Aucun claim créé",
    "claim_created = false",
    "replay_consumed = false",
    "production_authorized = false",
    "ad_write_authorized = false",
  ]) {
    assert.ok(
      block.includes(token)
    )
  }
})

test("C8.4D-A3C2 is available only to AD managers", () => {
  assert.match(
    page,
    /canManageActiveDirectory\s*\?\s*prepareAclDelegationProduction/
  )
})

test("C8.4D-A3C2 forwards only the server fingerprint", () => {
  assert.equal(
    page.includes(
      "crypto.subtle"
    ),
    false
  )

  assert.match(
    page,
    /expected_acl_fingerprint:\s*aclFingerprint/
  )

  assert.match(
    page,
    /preparation\?\.dacl[\s\S]*?acl_fingerprint/
  )
})

test("C8.4D-A3C2 keeps ACL execution control absent", () => {
  assert.ok(
    page.includes(
      "/api/ad-admin/acl-delegation/production-preparation"
    )
  )

  const block = securityBlock()

  assert.equal(
    block.includes(
      "Appliquer la délégation"
    ),
    false
  )
})

test("C8.4D-A3C3D1 wires the complete human pre-write chain", () => {
  for (const token of [
    "write-intent/identity-envelope",
    "write-intent/claim",
    "prewrite-ticket",
    "prewrite-status/",
  ]) {
    assert.ok(
      page.includes(token),
      `missing frontend ACL token: ${token}`
    )
  }

  assert.ok(
    page.includes(
      "startAclDelegationPrewrite"
    )
  )

  assert.ok(
    page.includes(
      "waitForAclDelegationPrewriteStatus"
    )
  )
})

test("C8.4D-A3C3D1 rechecks Production before anti-replay consumption", () => {
  const start = page.indexOf(
    "async function startAclDelegationPrewrite("
  )

  const end = page.indexOf(
    "async function runAdAdminJob(",
    start
  )

  assert.ok(start >= 0)
  assert.ok(end > start)

  const block = page.slice(
    start,
    end
  )

  const modeRead = block.indexOf(
    "await loadAdAgentMode()"
  )

  const productionGuard = block.indexOf(
    '!== "production"',
    modeRead
  )

  const claimCall = block.indexOf(
    '"write-intent/claim"',
    productionGuard
  )

  assert.ok(
    modeRead >= 0
  )

  assert.ok(
    productionGuard > modeRead
  )

  assert.ok(
    claimCall > productionGuard
  )

  assert.ok(
    block.includes(
      "passez d’abord manuellement l’agent"
    )
  )

  assert.ok(
    block.includes(
      "en mode Production."
    )
  )
})

test("C8.4D-A3C3D1 never calls worker pre-write APIs from React", () => {
  assert.equal(
    page.includes(
      "/api/agent/acl-delegation/prewrite"
    ),
    false
  )
})

test("C8.4D-A3C3D1 validates non-authorizing responses", () => {
  assert.ok(
    page.includes(
      "assertAclNonAuthorizingResponse"
    )
  )

  for (const token of [
    "job_creation_authorized",
    "runtime_authorized",
    "production_authorized",
    "ad_write_authorized",
    "prewrite_validation_runtime_authorized",
  ]) {
    assert.ok(
      page.includes(token)
    )
  }
})

test("C8.4D-A3C3D1 renders the pre-write workflow", () => {
  const block = securityBlock()

  for (const token of [
    "Étape suivante — validation pre-write",
    "Lancer validation pre-write",
    "Preuve anti-replay consommée",
    "Ticket pre-write",
    "Execution ID",
    "replay_consumed = true",
    "prewrite_validated = true",
    "confirmation_ready = true",
    "production_authorized = false",
    "ad_write_authorized = false",
  ]) {
    assert.ok(
      block.includes(token)
    )
  }
})

test("C8.4D-A3C3D1 keeps ACL execution absent after pre-write", () => {
  const intentStart = page.indexOf(
    "function buildAclDelegationProductionIntent("
  )

  const intentEnd = page.indexOf(
    "function assertAclNonAuthorizingResponse(",
    intentStart
  )

  assert.ok(intentStart >= 0)
  assert.ok(intentEnd > intentStart)

  const intentBlock = page.slice(
    intentStart,
    intentEnd
  )

  assert.ok(
    intentBlock.includes(
      'action: "apply_acl_delegation"'
    )
  )

  const block = securityBlock()

  assert.equal(
    block.includes(
      "Appliquer la délégation"
    ),
    false
  )

  assert.equal(
    page.includes(
      "/api/admin/agent/mode"
    ),
    false
  )
})

test("C8.4D-A3C3D2 wires the dormant human confirmation", () => {
  assert.ok(
    page.includes(
      "/api/ad-admin/acl-delegation/production-confirmation"
    )
  )

  assert.ok(
    page.includes(
      "confirmAclDelegationProduction"
    )
  )

  assert.match(
    page,
    /claim_id:\s*claimId/
  )

  assert.match(
    page,
    /ticket_id:\s*ticketId/
  )

  assert.match(
    page,
    /execution_id:\s*executionId/
  )
})

test("C8.4D-A3C3D2 requires exact DN and phrase", () => {
  const block = securityBlock()

  for (const token of [
    "DN exact attendu",
    "Phrase exacte attendue",
    "Recopiez exactement le DN",
    "Recopiez exactement la phrase",
    "Valider la confirmation finale",
  ]) {
    assert.ok(
      block.includes(token)
    )
  }

  assert.match(
    page,
    /typedDn !== expectedDn/
  )

  assert.match(
    page,
    /typedPhrase !== expectedPhrase/
  )
})

test("C8.4D-A3C3D2 requires Simulation before final confirmation", () => {
  const start = page.indexOf(
    "async function confirmAclDelegationProduction("
  )

  const end = page.indexOf(
    "async function runAdAdminJob(",
    start
  )

  assert.ok(start >= 0)
  assert.ok(end > start)

  const block = page.slice(
    start,
    end
  )

  const modeRead = block.indexOf(
    "await loadAdAgentMode()"
  )

  const simulationGuard = block.indexOf(
    '!== "simulation"',
    modeRead
  )

  const confirmationRoute = block.indexOf(
    "/api/ad-admin/acl-delegation/production-confirmation",
    simulationGuard
  )

  assert.ok(modeRead >= 0)
  assert.ok(simulationGuard > modeRead)
  assert.ok(confirmationRoute > simulationGuard)
})

test("C8.4D-A3C3D2 validates a strictly non-authorizing confirmation", () => {
  assert.ok(
    page.includes(
      "assertAclNonAuthorizingResponse("
    )
  )

  assert.ok(
    page.includes(
      "production_confirmation_dormant"
    )
  )

  assert.ok(
    page.includes(
      '!== "prewrite_validated"'
    )
  )
})

test("C8.4D-A3C3D2 renders dormant confirmation proof only", () => {
  const block = securityBlock()

  for (const token of [
    "Confirmation humaine finale",
    "Confirmation Production enregistrée",
    "Preuve dormante uniquement",
    "confirmation_validated = true",
    "confirmation_consumed = true",
    "production_authorized = false",
    "ad_write_authorized = false",
    "write_performed = false",
  ]) {
    assert.ok(
      block.includes(token)
    )
  }

  assert.equal(
    block.includes(
      "Appliquer la délégation"
    ),
    false
  )
})

test("C8.4D-A3C3D2 never changes agent mode automatically", () => {
  assert.equal(
    page.includes(
      "/api/admin/agent/mode"
    ),
    false
  )

  assert.equal(
    page.includes(
      "updateAgentMode("
    ),
    false
  )
})
