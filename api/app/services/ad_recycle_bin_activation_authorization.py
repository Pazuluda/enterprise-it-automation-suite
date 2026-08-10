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

from app.services.ad_recycle_bin_activation_ticket_consumption import (
    AdRecycleBinActivationTicketConsumption,
    AdRecycleBinActivationTicketConsumptionError,
    assert_ad_recycle_bin_activation_ticket_consumption_invariants,
)

from app.services.ad_recycle_bin_activation_ticket_persistence import (
    AdRecycleBinActivationTicketPersistence,
    AdRecycleBinActivationTicketPersistenceError,
    assert_ad_recycle_bin_activation_ticket_persistence_invariants,
)


AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONTRACT_VERSION = (
    "c9.4a2d-v1"
)

AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_TTL_SECONDS = 60
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_FUTURE_SKEW_SECONDS = 30

AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_ENABLED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_ROUTE_ENABLED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_JOB_CREATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_RUNTIME_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PRODUCTION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_ACTIVATION_AUTHORIZED = True
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_RESTORE_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_WRITE_PERFORMED = False


class AdRecycleBinActivationAuthorizationError(
    ValueError
):
    pass


class AdRecycleBinActivationAuthorizationConflict(
    AdRecycleBinActivationAuthorizationError
):
    pass


@dataclass(frozen=True)
class AdRecycleBinActivationAuthorization:
    contract_version: str
    authorization_id: str
    authorization_digest: str

    state: str
    status: str

    ticket_id: str
    ticket_digest: str
    consumption_id: str
    consumption_record_digest: str

    source_intent_id: str
    source_intent_digest: str

    fresh_evidence_job_id: str
    fresh_evidence_sha256: str

    forest_name: str
    root_domain: str
    forest_mode: str

    actor_subject: str
    actor_username: str
    actor_issuer: str
    actor_azp: str

    acknowledge_forest_wide: bool
    acknowledge_irreversible: bool
    acknowledge_no_restore: bool
    authorization_reason: str

    issued_at: str
    expires_at: str

    one_shot_required: bool
    authorization_consumed: bool

    human_authorized: bool
    persistence_enabled: bool
    route_enabled: bool
    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    activation_authorized: bool
    restore_authorized: bool
    write_performed: bool


_ALLOWED_PAYLOAD_KEYS = {
    "ticket_id",
    "ticket_digest",
    "consumption_id",
    "forest_name",
    "acknowledge_forest_wide",
    "acknowledge_irreversible",
    "acknowledge_no_restore",
    "authorization_reason",
}


def _normalize_now(
    now: datetime | None,
) -> datetime:
    current = (
        datetime.now(timezone.utc)
        if now is None
        else now
    )

    if current.tzinfo is None:
        raise AdRecycleBinActivationAuthorizationError(
            "now must be timezone-aware"
        )

    return current.astimezone(
        timezone.utc
    )


def _parse_timestamp(
    value: str,
    *,
    field: str,
) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AdRecycleBinActivationAuthorizationError(
            f"{field} is invalid"
        )

    try:
        parsed = datetime.fromisoformat(
            value.strip().replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise AdRecycleBinActivationAuthorizationError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdRecycleBinActivationAuthorizationError(
            f"{field} must be timezone-aware"
        )

    return parsed.astimezone(
        timezone.utc
    )


def _required_string(
    value: Any,
    *,
    field: str,
    min_length: int = 1,
    max_length: int = 512,
) -> str:
    if not isinstance(value, str):
        raise AdRecycleBinActivationAuthorizationError(
            f"{field} must be a string"
        )

    cleaned = value.strip()

    if len(cleaned) < min_length:
        raise AdRecycleBinActivationAuthorizationError(
            f"{field} is required"
        )

    if len(cleaned) > max_length:
        raise AdRecycleBinActivationAuthorizationError(
            f"{field} exceeds {max_length} characters"
        )

    return cleaned


def _required_true(
    value: Any,
    *,
    field: str,
) -> bool:
    if value is not True:
        raise AdRecycleBinActivationAuthorizationConflict(
            f"{field} must be true"
        )

    return True


def _required_uuid(
    value: Any,
    *,
    field: str,
) -> str:
    cleaned = _required_string(
        value,
        field=field,
        max_length=64,
    )

    try:
        UUID(cleaned)
    except ValueError as exc:
        raise AdRecycleBinActivationAuthorizationError(
            f"{field} is not a UUID"
        ) from exc

    return cleaned


def _required_sha256(
    value: Any,
    *,
    field: str,
) -> str:
    cleaned = _required_string(
        value,
        field=field,
        max_length=64,
    ).lower()

    if (
        len(cleaned) != 64
        or any(
            char not in "0123456789abcdef"
            for char in cleaned
        )
    ):
        raise AdRecycleBinActivationAuthorizationError(
            f"{field} is not a SHA-256 digest"
        )

    return cleaned


def _canonical_sha256(
    payload: dict[str, Any],
) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def _authorization_digest_payload(
    authorization: AdRecycleBinActivationAuthorization,
) -> dict[str, Any]:
    payload = asdict(
        authorization
    )

    payload.pop(
        "authorization_digest"
    )

    return payload


def _extract_actor(
    server_actor: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(
        server_actor,
        Mapping,
    ):
        raise AdRecycleBinActivationAuthorizationError(
            "server actor is invalid"
        )

    actor = {
        "subject":
            _required_string(
                server_actor.get("subject"),
                field="server_actor.subject",
                max_length=256,
            ),

        "username":
            _required_string(
                server_actor.get("username"),
                field="server_actor.username",
                max_length=128,
            ),

        "issuer":
            _required_string(
                server_actor.get("issuer"),
                field="server_actor.issuer",
            ),

        "azp":
            _required_string(
                server_actor.get("azp"),
                field="server_actor.azp",
                max_length=128,
            ),
    }

    if actor["issuer"] != OIDC_ISSUER:
        raise AdRecycleBinActivationAuthorizationConflict(
            "OIDC issuer mismatch"
        )

    if (
        OIDC_ALLOWED_AZP
        and actor["azp"] not in OIDC_ALLOWED_AZP
    ):
        raise AdRecycleBinActivationAuthorizationConflict(
            "OIDC azp is not allowed"
        )

    return actor


def assert_ad_recycle_bin_activation_authorization_invariants(
    authorization: AdRecycleBinActivationAuthorization,
) -> None:
    if (
        authorization.contract_version
        != AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationAuthorizationError(
            "authorization contract version mismatch"
        )

    _required_uuid(
        authorization.authorization_id,
        field="authorization_id",
    )

    _required_sha256(
        authorization.authorization_digest,
        field="authorization_digest",
    )

    _required_uuid(
        authorization.ticket_id,
        field="ticket_id",
    )

    _required_sha256(
        authorization.ticket_digest,
        field="ticket_digest",
    )

    _required_uuid(
        authorization.consumption_id,
        field="consumption_id",
    )

    _required_sha256(
        authorization.consumption_record_digest,
        field="consumption_record_digest",
    )

    if authorization.state != "activation_authorization_dormant":
        raise AdRecycleBinActivationAuthorizationError(
            "authorization state must remain dormant"
        )

    if authorization.status != "authorized":
        raise AdRecycleBinActivationAuthorizationError(
            "authorization status is invalid"
        )

    if authorization.one_shot_required is not True:
        raise AdRecycleBinActivationAuthorizationError(
            "authorization must remain one-shot"
        )

    if authorization.authorization_consumed is not False:
        raise AdRecycleBinActivationAuthorizationError(
            "authorization must remain unconsumed"
        )

    if authorization.human_authorized is not True:
        raise AdRecycleBinActivationAuthorizationError(
            "human authorization marker must be true"
        )

    if authorization.activation_authorized is not True:
        raise AdRecycleBinActivationAuthorizationError(
            "activation authorization marker must be true"
        )

    false_fields = (
        "persistence_enabled",
        "route_enabled",
        "job_creation_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "write_performed",
    )

    for field in false_fields:
        if getattr(
            authorization,
            field,
        ) is not False:
            raise AdRecycleBinActivationAuthorizationError(
                f"unsafe authorization flag: {field}"
            )

    _required_true(
        authorization.acknowledge_forest_wide,
        field="acknowledge_forest_wide",
    )

    _required_true(
        authorization.acknowledge_irreversible,
        field="acknowledge_irreversible",
    )

    _required_true(
        authorization.acknowledge_no_restore,
        field="acknowledge_no_restore",
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
        raise AdRecycleBinActivationAuthorizationError(
            "authorization expiration is invalid"
        )

    lifetime = int(
        (
            expires_at
            - issued_at
        ).total_seconds()
    )

    if lifetime > AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_TTL_SECONDS:
        raise AdRecycleBinActivationAuthorizationError(
            "authorization lifetime exceeds maximum TTL"
        )

    expected_digest = _canonical_sha256(
        _authorization_digest_payload(
            authorization
        )
    )

    if (
        authorization.authorization_digest
        != expected_digest
    ):
        raise AdRecycleBinActivationAuthorizationError(
            "authorization digest mismatch"
        )


def build_ad_recycle_bin_activation_authorization(
    ticket_record: AdRecycleBinActivationTicketPersistence,
    consumption_record: AdRecycleBinActivationTicketConsumption,
    *,
    server_actor: Mapping[str, Any],
    payload: Mapping[str, Any],
    current_mode: str,
    now: datetime | None = None,
) -> AdRecycleBinActivationAuthorization:
    if current_mode != "Simulation":
        raise AdRecycleBinActivationAuthorizationError(
            "activation authorization preparation is Simulation-only"
        )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise AdRecycleBinActivationAuthorizationError(
            "authorization payload is invalid"
        )

    unknown = (
        set(payload.keys())
        - _ALLOWED_PAYLOAD_KEYS
    )

    if unknown:
        raise AdRecycleBinActivationAuthorizationError(
            "authorization payload contains unknown fields"
        )

    try:
        assert_ad_recycle_bin_activation_ticket_persistence_invariants(
            ticket_record
        )
    except AdRecycleBinActivationTicketPersistenceError as exc:
        raise AdRecycleBinActivationAuthorizationError(
            str(exc)
        ) from exc

    try:
        assert_ad_recycle_bin_activation_ticket_consumption_invariants(
            consumption_record
        )
    except AdRecycleBinActivationTicketConsumptionError as exc:
        raise AdRecycleBinActivationAuthorizationError(
            str(exc)
        ) from exc

    if ticket_record.state != "activation_ticket_dormant":
        raise AdRecycleBinActivationAuthorizationConflict(
            "ticket is not dormant"
        )

    if ticket_record.status != "dormant":
        raise AdRecycleBinActivationAuthorizationConflict(
            "ticket status is not dormant"
        )

    if ticket_record.replay_consumed is not False:
        raise AdRecycleBinActivationAuthorizationConflict(
            "dormant ticket persistence is already replay-consumed"
        )

    if consumption_record.state != "activation_ticket_consumed":
        raise AdRecycleBinActivationAuthorizationConflict(
            "consumption state mismatch"
        )

    if consumption_record.consumed is not True:
        raise AdRecycleBinActivationAuthorizationConflict(
            "ticket has not been consumed"
        )

    bindings = {
        "ticket_id":
            (
                ticket_record.ticket_id,
                consumption_record.ticket_id,
            ),

        "ticket_digest":
            (
                ticket_record.ticket_digest,
                consumption_record.ticket_digest,
            ),

        "source_intent_id":
            (
                ticket_record.source_intent_id,
                consumption_record.source_intent_id,
            ),

        "source_intent_digest":
            (
                ticket_record.source_intent_digest,
                consumption_record.source_intent_digest,
            ),

        "fresh_evidence_job_id":
            (
                ticket_record.fresh_evidence_job_id,
                consumption_record.fresh_evidence_job_id,
            ),

        "fresh_evidence_sha256":
            (
                ticket_record.fresh_evidence_sha256,
                consumption_record.fresh_evidence_sha256,
            ),

        "forest_name":
            (
                ticket_record.forest_name,
                consumption_record.forest_name,
            ),

        "actor_subject":
            (
                ticket_record.actor_subject,
                consumption_record.actor_subject,
            ),

        "actor_username":
            (
                ticket_record.actor_username,
                consumption_record.actor_username,
            ),

        "actor_issuer":
            (
                ticket_record.actor_issuer,
                consumption_record.actor_issuer,
            ),

        "actor_azp":
            (
                ticket_record.actor_azp,
                consumption_record.actor_azp,
            ),
    }

    for field, pair in bindings.items():
        if pair[0] != pair[1]:
            raise AdRecycleBinActivationAuthorizationConflict(
                f"ticket/consumption mismatch: {field}"
            )

    actor = _extract_actor(
        server_actor
    )

    actor_bindings = {
        "actor_subject":
            actor["subject"],

        "actor_username":
            actor["username"],

        "actor_issuer":
            actor["issuer"],

        "actor_azp":
            actor["azp"],
    }

    for field, current_value in actor_bindings.items():
        if (
            getattr(
                ticket_record,
                field,
            )
            != current_value
        ):
            raise AdRecycleBinActivationAuthorizationConflict(
                f"actor mismatch: {field}"
            )

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

    supplied_forest = _required_string(
        payload.get("forest_name"),
        field="payload.forest_name",
        max_length=255,
    )

    if supplied_ticket_id != ticket_record.ticket_id:
        raise AdRecycleBinActivationAuthorizationConflict(
            "ticket id confirmation mismatch"
        )

    if supplied_ticket_digest != ticket_record.ticket_digest:
        raise AdRecycleBinActivationAuthorizationConflict(
            "ticket digest confirmation mismatch"
        )

    if supplied_consumption_id != consumption_record.consumption_id:
        raise AdRecycleBinActivationAuthorizationConflict(
            "consumption id confirmation mismatch"
        )

    if supplied_forest != ticket_record.forest_name:
        raise AdRecycleBinActivationAuthorizationConflict(
            "forest confirmation mismatch"
        )

    acknowledge_forest_wide = _required_true(
        payload.get("acknowledge_forest_wide"),
        field="acknowledge_forest_wide",
    )

    acknowledge_irreversible = _required_true(
        payload.get("acknowledge_irreversible"),
        field="acknowledge_irreversible",
    )

    acknowledge_no_restore = _required_true(
        payload.get("acknowledge_no_restore"),
        field="acknowledge_no_restore",
    )

    authorization_reason = _required_string(
        payload.get("authorization_reason"),
        field="authorization_reason",
        min_length=8,
        max_length=512,
    )

    current = _normalize_now(
        now
    )

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
        ticket_issued_at
        - current
        > timedelta(
            seconds=AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_FUTURE_SKEW_SECONDS
        )
    ):
        raise AdRecycleBinActivationAuthorizationConflict(
            "ticket issue time is too far in the future"
        )

    if current >= ticket_expires_at:
        raise AdRecycleBinActivationAuthorizationConflict(
            "ticket expired before authorization"
        )

    if (
        consumed_at
        - current
        > timedelta(
            seconds=AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_FUTURE_SKEW_SECONDS
        )
    ):
        raise AdRecycleBinActivationAuthorizationConflict(
            "consumption timestamp is too far in the future"
        )

    if consumed_at >= ticket_expires_at:
        raise AdRecycleBinActivationAuthorizationConflict(
            "ticket consumption occurred after expiration"
        )

    expires_at = min(
        current
        + timedelta(
            seconds=AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_TTL_SECONDS
        ),
        ticket_expires_at,
    )

    if expires_at <= current:
        raise AdRecycleBinActivationAuthorizationConflict(
            "authorization window is already closed"
        )

    payload_data = {
        "contract_version":
            AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONTRACT_VERSION,

        "authorization_id":
            str(uuid4()),

        "state":
            "activation_authorization_dormant",

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

        "source_intent_id":
            ticket_record.source_intent_id,

        "source_intent_digest":
            ticket_record.source_intent_digest,

        "fresh_evidence_job_id":
            ticket_record.fresh_evidence_job_id,

        "fresh_evidence_sha256":
            ticket_record.fresh_evidence_sha256,

        "forest_name":
            ticket_record.forest_name,

        "root_domain":
            ticket_record.root_domain,

        "forest_mode":
            ticket_record.forest_mode,

        "actor_subject":
            ticket_record.actor_subject,

        "actor_username":
            ticket_record.actor_username,

        "actor_issuer":
            ticket_record.actor_issuer,

        "actor_azp":
            ticket_record.actor_azp,

        "acknowledge_forest_wide":
            acknowledge_forest_wide,

        "acknowledge_irreversible":
            acknowledge_irreversible,

        "acknowledge_no_restore":
            acknowledge_no_restore,

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
            AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_ENABLED,

        "route_enabled":
            AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_ROUTE_ENABLED,

        "job_creation_authorized":
            AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_JOB_CREATION_AUTHORIZED,

        "runtime_authorized":
            AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_RUNTIME_AUTHORIZED,

        "production_authorized":
            AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PRODUCTION_AUTHORIZED,

        "activation_authorized":
            AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_ACTIVATION_AUTHORIZED,

        "restore_authorized":
            AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_RESTORE_AUTHORIZED,

        "write_performed":
            AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_WRITE_PERFORMED,
    }

    authorization_digest = _canonical_sha256(
        payload_data
    )

    authorization = AdRecycleBinActivationAuthorization(
        authorization_digest=authorization_digest,
        **payload_data,
    )

    assert_ad_recycle_bin_activation_authorization_invariants(
        authorization
    )

    return authorization


__all__ = [
    "AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONTRACT_VERSION",
    "AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_TTL_SECONDS",
    "AdRecycleBinActivationAuthorization",
    "AdRecycleBinActivationAuthorizationConflict",
    "AdRecycleBinActivationAuthorizationError",
    "assert_ad_recycle_bin_activation_authorization_invariants",
    "build_ad_recycle_bin_activation_authorization",
]
