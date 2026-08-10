from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Mapping
from uuid import uuid4

from app.services.ad_deleted_object_restore_authorization_consumption import (
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION,
    AdDeletedObjectRestoreAuthorizationConsumption,
    AdDeletedObjectRestoreAuthorizationConsumptionError,
    _canonical_sha256,
    _extract_actor,
    _normalize_now,
    _parse_timestamp,
    _required_sha256,
    _required_string,
    _required_uuid,
    assert_ad_deleted_object_restore_authorization_consumption_invariants,
)


AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_CONTRACT_VERSION = "c9.5a4e-v1"
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_TTL_SECONDS = 30

AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_PERSISTENCE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_AGENT_ENDPOINTS_ENABLED = False
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_CLAIM_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_PRODUCTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_RESTORE_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_RESTORE_WHATIF_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_EXECUTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_WRITE_PERFORMED = False


class AdDeletedObjectRestoreRuntimeGateError(
    ValueError
):
    pass


class AdDeletedObjectRestoreRuntimeGateConflict(
    AdDeletedObjectRestoreRuntimeGateError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreRuntimeGate:
    contract_version: str
    runtime_gate_id: str
    runtime_gate_digest: str

    state: str
    status: str

    authorization_consumption_contract_version: str
    authorization_consumption_id: str
    authorization_consumption_record_digest: str

    authorization_id: str
    authorization_digest: str
    authorization_record_digest: str

    preexecution_id: str
    preexecution_digest: str

    ticket_id: str
    ticket_digest: str
    consumption_id: str
    consumption_record_digest: str

    source_simulation_job_id: str
    source_inventory_job_id: str
    source_live_job_id: str

    authorization_fresh_live_job_id: str
    authorization_fresh_live_sha256: str

    fresh_live_job_id: str
    fresh_live_sha256: str
    fresh_live_completed_at: str

    object_guid: str
    object_class: str
    class_policy: str
    effective_new_name: str
    effective_target_path: str

    actor_subject: str
    actor_username: str
    actor_issuer: str
    actor_azp: str

    authorization_expires_at: str
    preexecution_expires_at: str
    source_consumed_at: str

    issued_at: str
    expires_at: str

    human_authorized: bool
    revalidation_passed: bool
    one_shot_consumption_verified: bool
    source_consumption_verified: bool

    persistence_enabled: bool
    route_enabled: bool
    agent_endpoints_enabled: bool
    job_creation_authorized: bool
    claim_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    restore_authorized: bool
    restore_whatif_authorized: bool
    execution_authorized: bool
    write_performed: bool


def _runtime_gate_digest_payload(
    record: AdDeletedObjectRestoreRuntimeGate,
) -> dict[str, Any]:
    payload = asdict(
        record
    )

    payload.pop(
        "runtime_gate_digest"
    )

    return payload


def assert_ad_deleted_object_restore_runtime_gate_invariants(
    record: AdDeletedObjectRestoreRuntimeGate,
) -> None:
    if (
        record.contract_version
        != AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreRuntimeGateError(
            "restore runtime gate contract version mismatch"
        )

    if (
        record.authorization_consumption_contract_version
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreRuntimeGateError(
            "authorization consumption contract version mismatch"
        )

    for field in (
        "runtime_gate_id",
        "authorization_consumption_id",
        "authorization_id",
        "preexecution_id",
        "ticket_id",
        "consumption_id",
        "source_simulation_job_id",
        "source_inventory_job_id",
        "source_live_job_id",
        "authorization_fresh_live_job_id",
        "fresh_live_job_id",
        "object_guid",
    ):
        _required_uuid(
            getattr(
                record,
                field,
            ),
            field=field,
        )

    for field in (
        "runtime_gate_digest",
        "authorization_consumption_record_digest",
        "authorization_digest",
        "authorization_record_digest",
        "preexecution_digest",
        "ticket_digest",
        "consumption_record_digest",
        "authorization_fresh_live_sha256",
        "fresh_live_sha256",
    ):
        _required_sha256(
            getattr(
                record,
                field,
            ),
            field=field,
        )

    for field in (
        "object_class",
        "class_policy",
        "effective_new_name",
        "effective_target_path",
        "actor_subject",
        "actor_username",
        "actor_issuer",
        "actor_azp",
    ):
        _required_string(
            getattr(
                record,
                field,
            ),
            field=field,
        )

    if record.state != "restore_runtime_gate_dormant":
        raise AdDeletedObjectRestoreRuntimeGateError(
            "restore runtime gate state is invalid"
        )

    if record.status != "ready_dormant":
        raise AdDeletedObjectRestoreRuntimeGateError(
            "restore runtime gate status is invalid"
        )

    if record.human_authorized is not True:
        raise AdDeletedObjectRestoreRuntimeGateError(
            "human authorization marker must remain true"
        )

    if record.revalidation_passed is not True:
        raise AdDeletedObjectRestoreRuntimeGateError(
            "revalidation marker must remain true"
        )

    if record.one_shot_consumption_verified is not True:
        raise AdDeletedObjectRestoreRuntimeGateError(
            "one-shot consumption marker must remain true"
        )

    if record.source_consumption_verified is not True:
        raise AdDeletedObjectRestoreRuntimeGateError(
            "source consumption verification marker must remain true"
        )

    for field in (
        "persistence_enabled",
        "route_enabled",
        "agent_endpoints_enabled",
        "job_creation_authorized",
        "claim_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "restore_whatif_authorized",
        "execution_authorized",
        "write_performed",
    ):
        if getattr(
            record,
            field,
        ) is not False:
            raise AdDeletedObjectRestoreRuntimeGateError(
                f"unsafe restore runtime gate flag: {field}"
            )

    source_consumed_at = _parse_timestamp(
        record.source_consumed_at,
        field="source_consumed_at",
    )

    issued_at = _parse_timestamp(
        record.issued_at,
        field="issued_at",
    )

    expires_at = _parse_timestamp(
        record.expires_at,
        field="expires_at",
    )

    authorization_expires_at = _parse_timestamp(
        record.authorization_expires_at,
        field="authorization_expires_at",
    )

    preexecution_expires_at = _parse_timestamp(
        record.preexecution_expires_at,
        field="preexecution_expires_at",
    )

    fresh_live_completed_at = _parse_timestamp(
        record.fresh_live_completed_at,
        field="fresh_live_completed_at",
    )

    if issued_at < source_consumed_at:
        raise AdDeletedObjectRestoreRuntimeGateError(
            "restore runtime gate issued before source consumption"
        )

    if fresh_live_completed_at > issued_at:
        raise AdDeletedObjectRestoreRuntimeGateError(
            "fresh live evidence is newer than runtime gate issue time"
        )

    if expires_at <= issued_at:
        raise AdDeletedObjectRestoreRuntimeGateError(
            "restore runtime gate expiration is invalid"
        )

    if (
        expires_at - issued_at
        > timedelta(
            seconds=AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_TTL_SECONDS
        )
    ):
        raise AdDeletedObjectRestoreRuntimeGateError(
            "restore runtime gate TTL exceeds maximum"
        )

    if expires_at > authorization_expires_at:
        raise AdDeletedObjectRestoreRuntimeGateError(
            "restore runtime gate exceeds authorization expiration"
        )

    if expires_at > preexecution_expires_at:
        raise AdDeletedObjectRestoreRuntimeGateError(
            "restore runtime gate exceeds preexecution expiration"
        )

    expected = _canonical_sha256(
        _runtime_gate_digest_payload(
            record
        )
    )

    if record.runtime_gate_digest != expected:
        raise AdDeletedObjectRestoreRuntimeGateError(
            "restore runtime gate digest mismatch"
        )


def build_ad_deleted_object_restore_runtime_gate(
    authorization_consumption:
        AdDeletedObjectRestoreAuthorizationConsumption,
    *,
    server_actor: Mapping[str, Any],
    current_mode: str,
    now=None,
) -> AdDeletedObjectRestoreRuntimeGate:
    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreRuntimeGateError(
            "restore runtime gate is Simulation-only"
        )

    try:
        assert_ad_deleted_object_restore_authorization_consumption_invariants(
            authorization_consumption
        )
    except AdDeletedObjectRestoreAuthorizationConsumptionError as exc:
        raise AdDeletedObjectRestoreRuntimeGateError(
            str(
                exc
            )
        ) from exc

    if authorization_consumption.authorization_consumed is not True:
        raise AdDeletedObjectRestoreRuntimeGateConflict(
            "authorization consumption is not complete"
        )

    if authorization_consumption.one_shot_consumption is not True:
        raise AdDeletedObjectRestoreRuntimeGateConflict(
            "authorization consumption is not one-shot"
        )

    if authorization_consumption.human_authorized is not True:
        raise AdDeletedObjectRestoreRuntimeGateConflict(
            "human authorization marker is missing"
        )

    if authorization_consumption.revalidation_passed is not True:
        raise AdDeletedObjectRestoreRuntimeGateConflict(
            "revalidation marker is missing"
        )

    for field in (
        "route_enabled",
        "job_creation_authorized",
        "claim_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "restore_whatif_authorized",
        "execution_authorized",
        "write_performed",
    ):
        if getattr(
            authorization_consumption,
            field,
        ) is not False:
            raise AdDeletedObjectRestoreRuntimeGateConflict(
                f"unsafe source authorization consumption flag: {field}"
            )

    actor = _extract_actor(
        server_actor
    )

    for field, expected in (
        (
            "actor_subject",
            actor["subject"],
        ),
        (
            "actor_username",
            actor["username"],
        ),
        (
            "actor_issuer",
            actor["issuer"],
        ),
        (
            "actor_azp",
            actor["azp"],
        ),
    ):
        if (
            getattr(
                authorization_consumption,
                field,
            )
            != expected
        ):
            raise AdDeletedObjectRestoreRuntimeGateConflict(
                f"actor mismatch: {field}"
            )

    current = _normalize_now(
        now
    )

    source_consumed_at = _parse_timestamp(
        authorization_consumption.consumed_at,
        field="authorization_consumption.consumed_at",
    )

    authorization_expires_at = _parse_timestamp(
        authorization_consumption.authorization_expires_at,
        field="authorization_consumption.authorization_expires_at",
    )

    preexecution_expires_at = _parse_timestamp(
        authorization_consumption.preexecution_expires_at,
        field="authorization_consumption.preexecution_expires_at",
    )

    fresh_live_completed_at = _parse_timestamp(
        authorization_consumption.fresh_live_completed_at,
        field="authorization_consumption.fresh_live_completed_at",
    )

    if current < source_consumed_at:
        raise AdDeletedObjectRestoreRuntimeGateConflict(
            "runtime gate cannot precede authorization consumption"
        )

    if current >= authorization_expires_at:
        raise AdDeletedObjectRestoreRuntimeGateConflict(
            "authorization expired before runtime gate creation"
        )

    if current >= preexecution_expires_at:
        raise AdDeletedObjectRestoreRuntimeGateConflict(
            "preexecution expired before runtime gate creation"
        )

    if fresh_live_completed_at > current:
        raise AdDeletedObjectRestoreRuntimeGateConflict(
            "fresh live timestamp is in the future"
        )

    expires_at = min(
        current
        + timedelta(
            seconds=AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_TTL_SECONDS
        ),
        authorization_expires_at,
        preexecution_expires_at,
    )

    if expires_at <= current:
        raise AdDeletedObjectRestoreRuntimeGateConflict(
            "restore runtime gate has no valid lifetime"
        )

    payload = {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_CONTRACT_VERSION,

        "runtime_gate_id":
            str(
                uuid4()
            ),

        "state":
            "restore_runtime_gate_dormant",

        "status":
            "ready_dormant",

        "authorization_consumption_contract_version":
            authorization_consumption.contract_version,

        "authorization_consumption_id":
            authorization_consumption.authorization_consumption_id,

        "authorization_consumption_record_digest":
            authorization_consumption.record_digest,

        "authorization_id":
            authorization_consumption.authorization_id,

        "authorization_digest":
            authorization_consumption.authorization_digest,

        "authorization_record_digest":
            authorization_consumption.authorization_record_digest,

        "preexecution_id":
            authorization_consumption.preexecution_id,

        "preexecution_digest":
            authorization_consumption.preexecution_digest,

        "ticket_id":
            authorization_consumption.ticket_id,

        "ticket_digest":
            authorization_consumption.ticket_digest,

        "consumption_id":
            authorization_consumption.consumption_id,

        "consumption_record_digest":
            authorization_consumption.consumption_record_digest,

        "source_simulation_job_id":
            authorization_consumption.source_simulation_job_id,

        "source_inventory_job_id":
            authorization_consumption.source_inventory_job_id,

        "source_live_job_id":
            authorization_consumption.source_live_job_id,

        "authorization_fresh_live_job_id":
            authorization_consumption.authorization_fresh_live_job_id,

        "authorization_fresh_live_sha256":
            authorization_consumption.authorization_fresh_live_sha256,

        "fresh_live_job_id":
            authorization_consumption.fresh_live_job_id,

        "fresh_live_sha256":
            authorization_consumption.fresh_live_sha256,

        "fresh_live_completed_at":
            authorization_consumption.fresh_live_completed_at,

        "object_guid":
            authorization_consumption.object_guid,

        "object_class":
            authorization_consumption.object_class,

        "class_policy":
            authorization_consumption.class_policy,

        "effective_new_name":
            authorization_consumption.effective_new_name,

        "effective_target_path":
            authorization_consumption.effective_target_path,

        "actor_subject":
            authorization_consumption.actor_subject,

        "actor_username":
            authorization_consumption.actor_username,

        "actor_issuer":
            authorization_consumption.actor_issuer,

        "actor_azp":
            authorization_consumption.actor_azp,

        "authorization_expires_at":
            authorization_consumption.authorization_expires_at,

        "preexecution_expires_at":
            authorization_consumption.preexecution_expires_at,

        "source_consumed_at":
            authorization_consumption.consumed_at,

        "issued_at":
            current.isoformat(),

        "expires_at":
            expires_at.isoformat(),

        "human_authorized":
            True,

        "revalidation_passed":
            True,

        "one_shot_consumption_verified":
            True,

        "source_consumption_verified":
            True,

        "persistence_enabled":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_PERSISTENCE_ENABLED,

        "route_enabled":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_ROUTE_ENABLED,

        "agent_endpoints_enabled":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_AGENT_ENDPOINTS_ENABLED,

        "job_creation_authorized":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_JOB_CREATION_AUTHORIZED,

        "claim_authorized":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_CLAIM_AUTHORIZED,

        "runtime_authorized":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_RUNTIME_AUTHORIZED,

        "production_authorized":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_PRODUCTION_AUTHORIZED,

        "restore_authorized":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_RESTORE_AUTHORIZED,

        "restore_whatif_authorized":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_RESTORE_WHATIF_AUTHORIZED,

        "execution_authorized":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_EXECUTION_AUTHORIZED,

        "write_performed":
            AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_WRITE_PERFORMED,
    }

    digest = _canonical_sha256(
        payload
    )

    record = AdDeletedObjectRestoreRuntimeGate(
        runtime_gate_digest=digest,
        **payload,
    )

    assert_ad_deleted_object_restore_runtime_gate_invariants(
        record
    )

    return record


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_CONTRACT_VERSION",
    "AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_TTL_SECONDS",
    "AdDeletedObjectRestoreRuntimeGate",
    "AdDeletedObjectRestoreRuntimeGateConflict",
    "AdDeletedObjectRestoreRuntimeGateError",
    "assert_ad_deleted_object_restore_runtime_gate_invariants",
    "build_ad_deleted_object_restore_runtime_gate",
]
