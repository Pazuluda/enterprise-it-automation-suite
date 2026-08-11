from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Mapping
from uuid import uuid4

from app.services.ad_deleted_object_restore_authorization_consumption import (
    _canonical_sha256,
    _extract_actor,
    _normalize_now,
    _parse_timestamp,
    _required_sha256,
    _required_string,
    _required_uuid,
)
from app.services.ad_deleted_object_restore_runtime_gate import (
    AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_CONTRACT_VERSION,
    AdDeletedObjectRestoreRuntimeGate,
    AdDeletedObjectRestoreRuntimeGateError,
    assert_ad_deleted_object_restore_runtime_gate_invariants,
)


AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CONTRACT_VERSION = (
    "c9.5a5b-v1"
)

AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_TTL_SECONDS = 20

AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_PERSISTENCE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_AGENT_ENDPOINTS_ENABLED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CLAIM_AUTHORIZED = False

# Le runtime generique EITAS et Production restent fermes.
AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_PRODUCTION_AUTHORIZED = False

# Capacite A5 etroite : uniquement le restore controle lie au ticket.
AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CONTROLLED_RESTORE_AUTHORIZED = True
AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_RESTORE_CMDLET_AUTHORIZED = True
AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_RESTORE_WHATIF_AUTHORIZED = True
AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_EXECUTION_AUTHORIZED = True

AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_WRITE_PERFORMED = False


class AdDeletedObjectRestoreExecutionTicketError(
    ValueError
):
    pass


class AdDeletedObjectRestoreExecutionTicketConflict(
    AdDeletedObjectRestoreExecutionTicketError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreExecutionTicket:
    contract_version: str
    execution_ticket_id: str
    execution_ticket_digest: str

    state: str
    status: str

    runtime_gate_contract_version: str
    runtime_gate_id: str
    runtime_gate_digest: str

    authorization_consumption_id: str
    authorization_consumption_record_digest: str

    authorization_id: str
    authorization_digest: str

    preexecution_id: str
    preexecution_digest: str

    object_guid: str
    object_class: str
    class_policy: str
    effective_new_name: str
    effective_target_path: str

    actor_subject: str
    actor_username: str
    actor_issuer: str
    actor_azp: str

    confirmation_sha256: str

    source_runtime_gate_expires_at: str
    issued_at: str
    expires_at: str

    human_authorized: bool
    revalidation_passed: bool
    source_one_shot_verified: bool

    one_shot_required: bool
    consumed: bool

    persistence_enabled: bool
    route_enabled: bool
    agent_endpoints_enabled: bool
    job_creation_authorized: bool
    claim_authorized: bool

    runtime_authorized: bool
    production_authorized: bool

    controlled_restore_authorized: bool
    restore_cmdlet_authorized: bool
    restore_whatif_authorized: bool
    execution_authorized: bool

    write_performed: bool


def expected_ad_deleted_object_restore_confirmation(
    runtime_gate: AdDeletedObjectRestoreRuntimeGate,
) -> str:
    return (
        "RESTORE "
        + runtime_gate.object_guid
        + " AS "
        + runtime_gate.effective_new_name
        + " TO "
        + runtime_gate.effective_target_path
    )


def _ticket_digest_payload(
    record: AdDeletedObjectRestoreExecutionTicket,
) -> dict[str, Any]:
    payload = asdict(
        record
    )

    payload.pop(
        "execution_ticket_digest"
    )

    return payload


def assert_ad_deleted_object_restore_execution_ticket_invariants(
    record: AdDeletedObjectRestoreExecutionTicket,
) -> None:
    if (
        record.contract_version
        != AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreExecutionTicketError(
            "restore execution ticket contract mismatch"
        )

    if (
        record.runtime_gate_contract_version
        != AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreExecutionTicketError(
            "runtime gate contract mismatch"
        )

    for field in (
        "execution_ticket_id",
        "runtime_gate_id",
        "authorization_consumption_id",
        "authorization_id",
        "preexecution_id",
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
        "execution_ticket_digest",
        "runtime_gate_digest",
        "authorization_consumption_record_digest",
        "authorization_digest",
        "preexecution_digest",
        "confirmation_sha256",
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

    if record.state != "restore_execution_ticket_dormant":
        raise AdDeletedObjectRestoreExecutionTicketError(
            "restore execution ticket state invalid"
        )

    if record.status != "authorized_one_shot_dormant":
        raise AdDeletedObjectRestoreExecutionTicketError(
            "restore execution ticket status invalid"
        )

    if record.human_authorized is not True:
        raise AdDeletedObjectRestoreExecutionTicketError(
            "human authorization is required"
        )

    if record.revalidation_passed is not True:
        raise AdDeletedObjectRestoreExecutionTicketError(
            "revalidation marker is required"
        )

    if record.source_one_shot_verified is not True:
        raise AdDeletedObjectRestoreExecutionTicketError(
            "source one-shot marker is required"
        )

    if record.one_shot_required is not True:
        raise AdDeletedObjectRestoreExecutionTicketError(
            "execution ticket must remain one-shot"
        )

    if record.consumed is not False:
        raise AdDeletedObjectRestoreExecutionTicketError(
            "new execution ticket must be unconsumed"
        )

    for field in (
        "persistence_enabled",
        "route_enabled",
        "agent_endpoints_enabled",
        "job_creation_authorized",
        "claim_authorized",
        "runtime_authorized",
        "production_authorized",
        "write_performed",
    ):
        if getattr(
            record,
            field,
        ) is not False:
            raise AdDeletedObjectRestoreExecutionTicketError(
                f"unsafe execution ticket flag: {field}"
            )

    for field in (
        "controlled_restore_authorized",
        "restore_cmdlet_authorized",
        "restore_whatif_authorized",
        "execution_authorized",
    ):
        if getattr(
            record,
            field,
        ) is not True:
            raise AdDeletedObjectRestoreExecutionTicketError(
                f"required controlled restore capability absent: {field}"
            )

    issued_at = _parse_timestamp(
        record.issued_at,
        field="issued_at",
    )

    expires_at = _parse_timestamp(
        record.expires_at,
        field="expires_at",
    )

    runtime_gate_expires_at = _parse_timestamp(
        record.source_runtime_gate_expires_at,
        field="source_runtime_gate_expires_at",
    )

    if expires_at <= issued_at:
        raise AdDeletedObjectRestoreExecutionTicketError(
            "execution ticket expiration invalid"
        )

    if (
        expires_at - issued_at
        > timedelta(
            seconds=(
                AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_TTL_SECONDS
            )
        )
    ):
        raise AdDeletedObjectRestoreExecutionTicketError(
            "execution ticket TTL exceeds maximum"
        )

    if expires_at > runtime_gate_expires_at:
        raise AdDeletedObjectRestoreExecutionTicketError(
            "execution ticket exceeds runtime gate expiration"
        )

    expected_digest = _canonical_sha256(
        _ticket_digest_payload(
            record
        )
    )

    if record.execution_ticket_digest != expected_digest:
        raise AdDeletedObjectRestoreExecutionTicketError(
            "execution ticket digest mismatch"
        )


def build_ad_deleted_object_restore_execution_ticket(
    runtime_gate: AdDeletedObjectRestoreRuntimeGate,
    *,
    server_actor: Mapping[str, Any],
    current_mode: str,
    confirmation_text: str,
    now=None,
) -> AdDeletedObjectRestoreExecutionTicket:
    # L'agent global reste en Simulation.
    # A5 est une capacite write isolee, pas une ouverture Production.
    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreExecutionTicketError(
            "controlled restore ticket requires Simulation global mode"
        )

    try:
        assert_ad_deleted_object_restore_runtime_gate_invariants(
            runtime_gate
        )
    except AdDeletedObjectRestoreRuntimeGateError as exc:
        raise AdDeletedObjectRestoreExecutionTicketError(
            str(
                exc
            )
        ) from exc

    if runtime_gate.human_authorized is not True:
        raise AdDeletedObjectRestoreExecutionTicketConflict(
            "runtime gate human authorization missing"
        )

    if runtime_gate.revalidation_passed is not True:
        raise AdDeletedObjectRestoreExecutionTicketConflict(
            "runtime gate revalidation missing"
        )

    if runtime_gate.one_shot_consumption_verified is not True:
        raise AdDeletedObjectRestoreExecutionTicketConflict(
            "runtime gate one-shot proof missing"
        )

    if runtime_gate.source_consumption_verified is not True:
        raise AdDeletedObjectRestoreExecutionTicketConflict(
            "runtime gate source consumption proof missing"
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
        if getattr(
            runtime_gate,
            field,
        ) != expected:
            raise AdDeletedObjectRestoreExecutionTicketConflict(
                f"actor mismatch: {field}"
            )

    current = _normalize_now(
        now
    )

    runtime_gate_issued_at = _parse_timestamp(
        runtime_gate.issued_at,
        field="runtime_gate.issued_at",
    )

    runtime_gate_expires_at = _parse_timestamp(
        runtime_gate.expires_at,
        field="runtime_gate.expires_at",
    )

    if current < runtime_gate_issued_at:
        raise AdDeletedObjectRestoreExecutionTicketConflict(
            "execution ticket predates runtime gate"
        )

    if current >= runtime_gate_expires_at:
        raise AdDeletedObjectRestoreExecutionTicketConflict(
            "runtime gate expired before execution ticket creation"
        )

    expected_confirmation = (
        expected_ad_deleted_object_restore_confirmation(
            runtime_gate
        )
    )

    if confirmation_text != expected_confirmation:
        raise AdDeletedObjectRestoreExecutionTicketConflict(
            "controlled restore confirmation mismatch"
        )

    confirmation_sha256 = _canonical_sha256(
        {
            "confirmation_text":
                confirmation_text,
        }
    )

    expires_at = min(
        current
        + timedelta(
            seconds=(
                AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_TTL_SECONDS
            )
        ),
        runtime_gate_expires_at,
    )

    if expires_at <= current:
        raise AdDeletedObjectRestoreExecutionTicketConflict(
            "execution ticket has no valid lifetime"
        )

    payload = {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CONTRACT_VERSION,

        "execution_ticket_id":
            str(
                uuid4()
            ),

        "state":
            "restore_execution_ticket_dormant",

        "status":
            "authorized_one_shot_dormant",

        "runtime_gate_contract_version":
            runtime_gate.contract_version,

        "runtime_gate_id":
            runtime_gate.runtime_gate_id,

        "runtime_gate_digest":
            runtime_gate.runtime_gate_digest,

        "authorization_consumption_id":
            runtime_gate.authorization_consumption_id,

        "authorization_consumption_record_digest":
            runtime_gate.authorization_consumption_record_digest,

        "authorization_id":
            runtime_gate.authorization_id,

        "authorization_digest":
            runtime_gate.authorization_digest,

        "preexecution_id":
            runtime_gate.preexecution_id,

        "preexecution_digest":
            runtime_gate.preexecution_digest,

        "object_guid":
            runtime_gate.object_guid,

        "object_class":
            runtime_gate.object_class,

        "class_policy":
            runtime_gate.class_policy,

        "effective_new_name":
            runtime_gate.effective_new_name,

        "effective_target_path":
            runtime_gate.effective_target_path,

        "actor_subject":
            runtime_gate.actor_subject,

        "actor_username":
            runtime_gate.actor_username,

        "actor_issuer":
            runtime_gate.actor_issuer,

        "actor_azp":
            runtime_gate.actor_azp,

        "confirmation_sha256":
            confirmation_sha256,

        "source_runtime_gate_expires_at":
            runtime_gate.expires_at,

        "issued_at":
            current.isoformat(),

        "expires_at":
            expires_at.isoformat(),

        "human_authorized":
            True,

        "revalidation_passed":
            True,

        "source_one_shot_verified":
            True,

        "one_shot_required":
            True,

        "consumed":
            False,

        "persistence_enabled":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_PERSISTENCE_ENABLED,

        "route_enabled":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_ROUTE_ENABLED,

        "agent_endpoints_enabled":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_AGENT_ENDPOINTS_ENABLED,

        "job_creation_authorized":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_JOB_CREATION_AUTHORIZED,

        "claim_authorized":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CLAIM_AUTHORIZED,

        "runtime_authorized":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_RUNTIME_AUTHORIZED,

        "production_authorized":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_PRODUCTION_AUTHORIZED,

        "controlled_restore_authorized":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CONTROLLED_RESTORE_AUTHORIZED,

        "restore_cmdlet_authorized":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_RESTORE_CMDLET_AUTHORIZED,

        "restore_whatif_authorized":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_RESTORE_WHATIF_AUTHORIZED,

        "execution_authorized":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_EXECUTION_AUTHORIZED,

        "write_performed":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_WRITE_PERFORMED,
    }

    digest = _canonical_sha256(
        payload
    )

    record = AdDeletedObjectRestoreExecutionTicket(
        execution_ticket_digest=digest,
        **payload,
    )

    assert_ad_deleted_object_restore_execution_ticket_invariants(
        record
    )

    return record


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CONTRACT_VERSION",
    "AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_TTL_SECONDS",
    "AdDeletedObjectRestoreExecutionTicket",
    "AdDeletedObjectRestoreExecutionTicketConflict",
    "AdDeletedObjectRestoreExecutionTicketError",
    "assert_ad_deleted_object_restore_execution_ticket_invariants",
    "build_ad_deleted_object_restore_execution_ticket",
    "expected_ad_deleted_object_restore_confirmation",
]
