from __future__ import annotations

import hashlib
import json

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

from app.core.security import (
    OIDC_ALLOWED_AZP,
    OIDC_ISSUER,
)

from app.services.ad_deleted_object_restore_ticket_consumption import (
    AdDeletedObjectRestoreTicketConsumption,
    AdDeletedObjectRestoreTicketConsumptionError,
    assert_ad_deleted_object_restore_ticket_consumption_invariants,
)

from app.services.ad_deleted_object_restore_ticket_persistence import (
    AdDeletedObjectRestoreTicketPersistence,
    AdDeletedObjectRestoreTicketPersistenceError,
    assert_ad_deleted_object_restore_ticket_persistence_invariants,
)


AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION = "c9.5a4c-v1"
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_TTL_SECONDS = 60
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_FUTURE_SKEW_SECONDS = 30

AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CLAIM_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PRODUCTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_RESTORE_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_RESTORE_WHATIF_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_EXECUTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_WRITE_PERFORMED = False


class AdDeletedObjectRestoreAuthorizationError(ValueError):
    pass


class AdDeletedObjectRestoreAuthorizationConflict(
    AdDeletedObjectRestoreAuthorizationError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreAuthorization:
    contract_version: str
    authorization_id: str
    authorization_digest: str

    state: str
    status: str

    ticket_id: str
    ticket_digest: str
    consumption_id: str
    consumption_record_digest: str

    source_simulation_job_id: str
    source_inventory_job_id: str
    source_live_job_id: str
    fresh_live_job_id: str
    fresh_live_sha256: str

    object_guid: str
    object_class: str
    class_policy: str
    effective_new_name: str
    effective_target_path: str

    actor_subject: str
    actor_username: str
    actor_issuer: str
    actor_azp: str

    acknowledge_exact_object: bool
    acknowledge_exact_target: bool
    acknowledge_restore_write: bool
    authorization_reason: str

    issued_at: str
    expires_at: str

    one_shot_required: bool
    authorization_consumed: bool
    human_authorized: bool

    persistence_enabled: bool
    route_enabled: bool
    job_creation_authorized: bool
    claim_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    restore_authorized: bool
    restore_whatif_authorized: bool
    execution_authorized: bool
    write_performed: bool


_ALLOWED_PAYLOAD_KEYS = {
    "ticket_id",
    "ticket_digest",
    "consumption_id",
    "object_guid",
    "effective_new_name",
    "effective_target_path",
    "acknowledge_exact_object",
    "acknowledge_exact_target",
    "acknowledge_restore_write",
    "authorization_reason",
}


def _normalize_now(now: datetime | None) -> datetime:
    current = datetime.now(timezone.utc) if now is None else now

    if current.tzinfo is None:
        raise AdDeletedObjectRestoreAuthorizationError(
            "now must be timezone-aware"
        )

    return current.astimezone(timezone.utc)


def _parse_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AdDeletedObjectRestoreAuthorizationError(
            f"{field} is invalid"
        )

    try:
        parsed = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise AdDeletedObjectRestoreAuthorizationError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdDeletedObjectRestoreAuthorizationError(
            f"{field} must be timezone-aware"
        )

    return parsed.astimezone(timezone.utc)


def _required_string(
    value: Any,
    *,
    field: str,
    min_length: int = 1,
    max_length: int = 512,
) -> str:
    if not isinstance(value, str):
        raise AdDeletedObjectRestoreAuthorizationError(
            f"{field} must be a string"
        )

    cleaned = value.strip()

    if len(cleaned) < min_length:
        raise AdDeletedObjectRestoreAuthorizationError(
            f"{field} is required"
        )

    if len(cleaned) > max_length:
        raise AdDeletedObjectRestoreAuthorizationError(
            f"{field} exceeds {max_length} characters"
        )

    return cleaned


def _required_true(value: Any, *, field: str) -> bool:
    if value is not True:
        raise AdDeletedObjectRestoreAuthorizationConflict(
            f"{field} must be true"
        )

    return True


def _required_uuid(value: Any, *, field: str) -> str:
    raw = _required_string(
        value,
        field=field,
        max_length=64,
    )

    try:
        return str(UUID(raw))
    except (TypeError, ValueError, AttributeError) as exc:
        raise AdDeletedObjectRestoreAuthorizationError(
            f"{field} is not a UUID"
        ) from exc


def _required_sha256(value: Any, *, field: str) -> str:
    raw = _required_string(
        value,
        field=field,
        max_length=64,
    ).lower()

    if (
        len(raw) != 64
        or any(char not in "0123456789abcdef" for char in raw)
    ):
        raise AdDeletedObjectRestoreAuthorizationError(
            f"{field} is not a SHA-256 digest"
        )

    return raw


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _authorization_digest_payload(
    authorization: AdDeletedObjectRestoreAuthorization,
) -> dict[str, Any]:
    payload = asdict(authorization)
    payload.pop("authorization_digest")
    return payload


def _extract_actor(
    server_actor: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(server_actor, Mapping):
        raise AdDeletedObjectRestoreAuthorizationError(
            "server actor is invalid"
        )

    actor = {
        "subject": _required_string(
            server_actor.get("subject"),
            field="server_actor.subject",
            max_length=256,
        ),
        "username": _required_string(
            server_actor.get("username"),
            field="server_actor.username",
            max_length=128,
        ),
        "issuer": _required_string(
            server_actor.get("issuer"),
            field="server_actor.issuer",
        ),
        "azp": _required_string(
            server_actor.get("azp"),
            field="server_actor.azp",
            max_length=128,
        ),
    }

    if actor["issuer"] != OIDC_ISSUER:
        raise AdDeletedObjectRestoreAuthorizationConflict(
            "OIDC issuer mismatch"
        )

    if OIDC_ALLOWED_AZP and actor["azp"] not in OIDC_ALLOWED_AZP:
        raise AdDeletedObjectRestoreAuthorizationConflict(
            "OIDC azp is not allowed"
        )

    return actor


def _global_gate() -> None:
    if any((
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_ENABLED,
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_ROUTE_ENABLED,
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_JOB_CREATION_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CLAIM_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_RUNTIME_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PRODUCTION_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_RESTORE_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_RESTORE_WHATIF_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_EXECUTION_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_WRITE_PERFORMED,
    )):
        raise AdDeletedObjectRestoreAuthorizationError(
            "dangerous restore authorization capability enabled"
        )


def assert_ad_deleted_object_restore_authorization_invariants(
    authorization: AdDeletedObjectRestoreAuthorization,
) -> None:
    _global_gate()

    if (
        authorization.contract_version
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreAuthorizationError(
            "restore authorization contract mismatch"
        )

    _required_uuid(
        authorization.authorization_id,
        field="authorization_id",
    )
    _required_uuid(
        authorization.ticket_id,
        field="ticket_id",
    )
    _required_uuid(
        authorization.consumption_id,
        field="consumption_id",
    )
    _required_uuid(
        authorization.object_guid,
        field="object_guid",
    )

    for value, field in (
        (authorization.authorization_digest, "authorization_digest"),
        (authorization.ticket_digest, "ticket_digest"),
        (
            authorization.consumption_record_digest,
            "consumption_record_digest",
        ),
        (authorization.fresh_live_sha256, "fresh_live_sha256"),
    ):
        _required_sha256(value, field=field)

    if (
        authorization.state != "restore_authorization_dormant"
        or authorization.status != "authorized"
    ):
        raise AdDeletedObjectRestoreAuthorizationError(
            "restore authorization must remain dormant"
        )

    if authorization.one_shot_required is not True:
        raise AdDeletedObjectRestoreAuthorizationError(
            "restore authorization must remain one-shot"
        )

    if authorization.authorization_consumed is not False:
        raise AdDeletedObjectRestoreAuthorizationError(
            "restore authorization must remain unconsumed"
        )

    if authorization.human_authorized is not True:
        raise AdDeletedObjectRestoreAuthorizationError(
            "human authorization marker must be true"
        )

    for field in (
        "persistence_enabled",
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
        if getattr(authorization, field) is not False:
            raise AdDeletedObjectRestoreAuthorizationError(
                f"unsafe restore authorization flag: {field}"
            )

    _required_true(
        authorization.acknowledge_exact_object,
        field="acknowledge_exact_object",
    )
    _required_true(
        authorization.acknowledge_exact_target,
        field="acknowledge_exact_target",
    )
    _required_true(
        authorization.acknowledge_restore_write,
        field="acknowledge_restore_write",
    )

    _required_string(
        authorization.authorization_reason,
        field="authorization_reason",
        min_length=8,
        max_length=512,
    )

    issued_at = _parse_timestamp(
        authorization.issued_at,
        field="issued_at",
    )
    expires_at = _parse_timestamp(
        authorization.expires_at,
        field="expires_at",
    )

    if expires_at <= issued_at:
        raise AdDeletedObjectRestoreAuthorizationError(
            "restore authorization expiration is invalid"
        )

    lifetime = int((expires_at - issued_at).total_seconds())

    if lifetime > AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_TTL_SECONDS:
        raise AdDeletedObjectRestoreAuthorizationError(
            "restore authorization lifetime exceeds maximum TTL"
        )

    expected = _canonical_sha256(
        _authorization_digest_payload(authorization)
    )

    if authorization.authorization_digest != expected:
        raise AdDeletedObjectRestoreAuthorizationError(
            "restore authorization digest mismatch"
        )


def build_ad_deleted_object_restore_authorization(
    ticket_record: AdDeletedObjectRestoreTicketPersistence,
    consumption_record: AdDeletedObjectRestoreTicketConsumption,
    *,
    server_actor: Mapping[str, Any],
    payload: Mapping[str, Any],
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreAuthorization:
    _global_gate()

    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreAuthorizationError(
            "restore authorization preparation is Simulation-only"
        )

    if not isinstance(payload, Mapping):
        raise AdDeletedObjectRestoreAuthorizationError(
            "restore authorization payload is invalid"
        )

    unknown = set(payload) - _ALLOWED_PAYLOAD_KEYS

    if unknown:
        raise AdDeletedObjectRestoreAuthorizationError(
            "restore authorization payload contains unknown fields"
        )

    try:
        assert_ad_deleted_object_restore_ticket_persistence_invariants(
            ticket_record
        )
    except AdDeletedObjectRestoreTicketPersistenceError as exc:
        raise AdDeletedObjectRestoreAuthorizationError(str(exc)) from exc

    try:
        assert_ad_deleted_object_restore_ticket_consumption_invariants(
            consumption_record
        )
    except AdDeletedObjectRestoreTicketConsumptionError as exc:
        raise AdDeletedObjectRestoreAuthorizationError(str(exc)) from exc

    if (
        ticket_record.state != "restore_ticket_dormant"
        or ticket_record.status != "dormant"
    ):
        raise AdDeletedObjectRestoreAuthorizationConflict(
            "restore ticket is not dormant"
        )

    if ticket_record.replay_consumed is not False:
        raise AdDeletedObjectRestoreAuthorizationConflict(
            "restore ticket is already replay-consumed"
        )

    if (
        consumption_record.state != "restore_ticket_consumed"
        or consumption_record.consumed is not True
    ):
        raise AdDeletedObjectRestoreAuthorizationConflict(
            "restore ticket has not been consumed"
        )

    bindings = (
        "ticket_id",
        "ticket_digest",
        "source_simulation_job_id",
        "source_inventory_job_id",
        "source_live_job_id",
        "fresh_live_job_id",
        "fresh_live_sha256",
        "object_guid",
        "object_class",
        "class_policy",
        "effective_new_name",
        "effective_target_path",
    )

    for field in bindings:
        if getattr(ticket_record, field) != getattr(consumption_record, field):
            raise AdDeletedObjectRestoreAuthorizationConflict(
                f"ticket/consumption mismatch: {field}"
            )

    actor = _extract_actor(server_actor)

    supplied_ticket_id = _required_uuid(
        payload.get("ticket_id"),
        field="payload.ticket_id",
    )
    supplied_ticket_digest = _required_sha256(
        payload.get("ticket_digest"),
        field="payload.ticket_digest",
    )
    supplied_consumption_id = _required_uuid(
        payload.get("consumption_id"),
        field="payload.consumption_id",
    )
    supplied_guid = _required_uuid(
        payload.get("object_guid"),
        field="payload.object_guid",
    )
    supplied_name = _required_string(
        payload.get("effective_new_name"),
        field="payload.effective_new_name",
        max_length=255,
    )
    supplied_target = _required_string(
        payload.get("effective_target_path"),
        field="payload.effective_target_path",
        max_length=1024,
    )

    confirmations = {
        "ticket id": (
            supplied_ticket_id,
            ticket_record.ticket_id,
        ),
        "ticket digest": (
            supplied_ticket_digest,
            ticket_record.ticket_digest,
        ),
        "consumption id": (
            supplied_consumption_id,
            consumption_record.consumption_id,
        ),
        "object guid": (
            supplied_guid,
            ticket_record.object_guid,
        ),
        "effective new name": (
            supplied_name,
            ticket_record.effective_new_name,
        ),
        "effective target path": (
            supplied_target,
            ticket_record.effective_target_path,
        ),
    }

    for field, pair in confirmations.items():
        if pair[0] != pair[1]:
            raise AdDeletedObjectRestoreAuthorizationConflict(
                f"{field} confirmation mismatch"
            )

    acknowledge_exact_object = _required_true(
        payload.get("acknowledge_exact_object"),
        field="acknowledge_exact_object",
    )
    acknowledge_exact_target = _required_true(
        payload.get("acknowledge_exact_target"),
        field="acknowledge_exact_target",
    )
    acknowledge_restore_write = _required_true(
        payload.get("acknowledge_restore_write"),
        field="acknowledge_restore_write",
    )
    authorization_reason = _required_string(
        payload.get("authorization_reason"),
        field="authorization_reason",
        min_length=8,
        max_length=512,
    )

    current = _normalize_now(now)
    ticket_issued_at = _parse_timestamp(
        ticket_record.issued_at,
        field="ticket.issued_at",
    )
    ticket_expires_at = _parse_timestamp(
        ticket_record.expires_at,
        field="ticket.expires_at",
    )
    consumed_at = _parse_timestamp(
        consumption_record.consumed_at,
        field="consumption.consumed_at",
    )

    if (
        ticket_issued_at - current
        > timedelta(
            seconds=AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_FUTURE_SKEW_SECONDS
        )
    ):
        raise AdDeletedObjectRestoreAuthorizationConflict(
            "restore ticket issue time is too far in the future"
        )

    if current >= ticket_expires_at:
        raise AdDeletedObjectRestoreAuthorizationConflict(
            "restore ticket expired before authorization"
        )

    if (
        consumed_at - current
        > timedelta(
            seconds=AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_FUTURE_SKEW_SECONDS
        )
    ):
        raise AdDeletedObjectRestoreAuthorizationConflict(
            "restore ticket consumption time is too far in the future"
        )

    if consumed_at >= ticket_expires_at:
        raise AdDeletedObjectRestoreAuthorizationConflict(
            "restore ticket consumption occurred after expiration"
        )

    expires_at = min(
        current
        + timedelta(
            seconds=AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_TTL_SECONDS
        ),
        ticket_expires_at,
    )

    if expires_at <= current:
        raise AdDeletedObjectRestoreAuthorizationConflict(
            "restore authorization window is already closed"
        )

    payload_data = {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION,
        "authorization_id":
            str(uuid4()),
        "state":
            "restore_authorization_dormant",
        "status":
            "authorized",
        "ticket_id":
            ticket_record.ticket_id,
        "ticket_digest":
            ticket_record.ticket_digest,
        "consumption_id":
            consumption_record.consumption_id,
        "consumption_record_digest":
            consumption_record.record_digest,
        "source_simulation_job_id":
            ticket_record.source_simulation_job_id,
        "source_inventory_job_id":
            ticket_record.source_inventory_job_id,
        "source_live_job_id":
            ticket_record.source_live_job_id,
        "fresh_live_job_id":
            ticket_record.fresh_live_job_id,
        "fresh_live_sha256":
            ticket_record.fresh_live_sha256,
        "object_guid":
            ticket_record.object_guid,
        "object_class":
            ticket_record.object_class,
        "class_policy":
            ticket_record.class_policy,
        "effective_new_name":
            ticket_record.effective_new_name,
        "effective_target_path":
            ticket_record.effective_target_path,
        "actor_subject":
            actor["subject"],
        "actor_username":
            actor["username"],
        "actor_issuer":
            actor["issuer"],
        "actor_azp":
            actor["azp"],
        "acknowledge_exact_object":
            acknowledge_exact_object,
        "acknowledge_exact_target":
            acknowledge_exact_target,
        "acknowledge_restore_write":
            acknowledge_restore_write,
        "authorization_reason":
            authorization_reason,
        "issued_at":
            current.isoformat(),
        "expires_at":
            expires_at.isoformat(),
        "one_shot_required":
            True,
        "authorization_consumed":
            False,
        "human_authorized":
            True,
        "persistence_enabled":
            False,
        "route_enabled":
            False,
        "job_creation_authorized":
            False,
        "claim_authorized":
            False,
        "runtime_authorized":
            False,
        "production_authorized":
            False,
        "restore_authorized":
            False,
        "restore_whatif_authorized":
            False,
        "execution_authorized":
            False,
        "write_performed":
            False,
    }

    authorization = AdDeletedObjectRestoreAuthorization(
        authorization_digest=_canonical_sha256(payload_data),
        **payload_data,
    )

    assert_ad_deleted_object_restore_authorization_invariants(
        authorization
    )

    return authorization


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION",
    "AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_TTL_SECONDS",
    "AdDeletedObjectRestoreAuthorization",
    "AdDeletedObjectRestoreAuthorizationConflict",
    "AdDeletedObjectRestoreAuthorizationError",
    "assert_ad_deleted_object_restore_authorization_invariants",
    "build_ad_deleted_object_restore_authorization",
]
