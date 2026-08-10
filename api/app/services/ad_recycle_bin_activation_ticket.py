from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from uuid import UUID, uuid4

from app.core.security import (
    OIDC_ALLOWED_AZP,
    OIDC_ISSUER,
)

from app.services.ad_recycle_bin_activation_intent_persistence import (
    AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,
)


AD_RECYCLE_BIN_ACTIVATION_TICKET_CONTRACT_VERSION = (
    "c9.4a2a-v1"
)

AD_RECYCLE_BIN_ACTIVATION_TICKET_ENABLED = True

AD_RECYCLE_BIN_ACTIVATION_TICKET_TTL_SECONDS = 120
AD_RECYCLE_BIN_ACTIVATION_TICKET_EVIDENCE_MAX_AGE_SECONDS = 120
AD_RECYCLE_BIN_ACTIVATION_TICKET_FUTURE_SKEW_SECONDS = 30

AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_ENABLED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_ROUTE_ENABLED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_JOB_CREATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_CLAIM_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_RUNTIME_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_PRODUCTION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_ACTIVATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_RESTORE_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_WRITE_PERFORMED = False


class AdRecycleBinActivationTicketError(ValueError):
    pass


@dataclass(frozen=True)
class AdRecycleBinActivationTicket:
    contract_version: str

    ticket_id: str
    ticket_digest: str

    state: str
    status: str

    source_intent_id: str
    source_intent_digest: str
    source_intent_contract_version: str

    source_evidence_sha256: str
    source_evidence_created_at: str

    fresh_evidence_job_id: str
    fresh_evidence_sha256: str
    fresh_evidence_created_at: str

    forest_name: str
    root_domain: str
    forest_mode: str

    actor_subject: str
    actor_username: str
    actor_issuer: str
    actor_azp: str

    issued_at: str
    expires_at: str

    one_shot_required: bool
    replay_consumed: bool

    persistence_enabled: bool
    route_enabled: bool
    job_creation_authorized: bool
    claim_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    activation_authorized: bool
    restore_authorized: bool
    write_performed: bool


def _required_string(
    value: Any,
    *,
    field: str,
    max_length: int = 512,
) -> str:
    if not isinstance(value, str):
        raise AdRecycleBinActivationTicketError(
            f"{field} must be a string"
        )

    cleaned = value.strip()

    if not cleaned:
        raise AdRecycleBinActivationTicketError(
            f"{field} is required"
        )

    if len(cleaned) > max_length:
        raise AdRecycleBinActivationTicketError(
            f"{field} exceeds {max_length} characters"
        )

    return cleaned


def _normalize_now(
    now: datetime | None,
) -> datetime:
    current = (
        datetime.now(timezone.utc)
        if now is None
        else now
    )

    if current.tzinfo is None:
        raise AdRecycleBinActivationTicketError(
            "now must be timezone-aware"
        )

    return current.astimezone(
        timezone.utc
    )


def _parse_timestamp(
    value: Any,
    *,
    field: str,
) -> datetime:
    raw = _required_string(
        value,
        field=field,
        max_length=128,
    )

    try:
        parsed = datetime.fromisoformat(
            raw.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise AdRecycleBinActivationTicketError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdRecycleBinActivationTicketError(
            f"{field} must be timezone-aware"
        )

    return parsed.astimezone(
        timezone.utc
    )


def _required_sha256(
    value: Any,
    *,
    field: str,
) -> str:
    raw = _required_string(
        value,
        field=field,
        max_length=64,
    ).lower()

    if not re.fullmatch(
        r"[0-9a-f]{64}",
        raw,
    ):
        raise AdRecycleBinActivationTicketError(
            f"{field} is not a SHA-256 digest"
        )

    return raw


def _required_uuid(
    value: Any,
    *,
    field: str,
) -> str:
    raw = _required_string(
        value,
        field=field,
        max_length=64,
    )

    try:
        parsed = UUID(raw)
    except ValueError as exc:
        raise AdRecycleBinActivationTicketError(
            f"{field} is not a UUID"
        ) from exc

    return str(parsed)


def _canonical_sha256(
    value: Mapping[str, Any],
) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


def _assert_false_flag(
    source: Mapping[str, Any],
    *,
    field: str,
) -> None:
    if source.get(field) is not False:
        raise AdRecycleBinActivationTicketError(
            f"unsafe authorization flag: {field}"
        )


def _assert_same_dns_name(
    left: str,
    right: str,
    *,
    field: str,
) -> None:
    if left.casefold() != right.casefold():
        raise AdRecycleBinActivationTicketError(
            f"{field} mismatch"
        )


def _ticket_digest_payload(
    ticket: AdRecycleBinActivationTicket,
) -> dict[str, Any]:
    payload = asdict(
        ticket
    )

    payload.pop(
        "ticket_digest"
    )

    return payload


def assert_ad_recycle_bin_activation_ticket_invariants(
    ticket: AdRecycleBinActivationTicket,
) -> None:
    if not AD_RECYCLE_BIN_ACTIVATION_TICKET_ENABLED:
        raise AdRecycleBinActivationTicketError(
            "activation ticket contract is disabled"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_ENABLED
        or AD_RECYCLE_BIN_ACTIVATION_TICKET_ROUTE_ENABLED
        or AD_RECYCLE_BIN_ACTIVATION_TICKET_JOB_CREATION_AUTHORIZED
        or AD_RECYCLE_BIN_ACTIVATION_TICKET_CLAIM_AUTHORIZED
        or AD_RECYCLE_BIN_ACTIVATION_TICKET_RUNTIME_AUTHORIZED
        or AD_RECYCLE_BIN_ACTIVATION_TICKET_PRODUCTION_AUTHORIZED
        or AD_RECYCLE_BIN_ACTIVATION_TICKET_ACTIVATION_AUTHORIZED
        or AD_RECYCLE_BIN_ACTIVATION_TICKET_RESTORE_AUTHORIZED
        or AD_RECYCLE_BIN_ACTIVATION_TICKET_WRITE_PERFORMED
    ):
        raise AdRecycleBinActivationTicketError(
            "dangerous activation ticket capability is enabled"
        )

    if (
        ticket.contract_version
        != AD_RECYCLE_BIN_ACTIVATION_TICKET_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationTicketError(
            "ticket contract version mismatch"
        )

    _required_uuid(
        ticket.ticket_id,
        field="ticket_id",
    )

    _required_sha256(
        ticket.ticket_digest,
        field="ticket_digest",
    )

    _required_uuid(
        ticket.source_intent_id,
        field="source_intent_id",
    )

    _required_sha256(
        ticket.source_intent_digest,
        field="source_intent_digest",
    )

    _required_sha256(
        ticket.source_evidence_sha256,
        field="source_evidence_sha256",
    )

    _required_sha256(
        ticket.fresh_evidence_sha256,
        field="fresh_evidence_sha256",
    )

    if ticket.state != "activation_ticket_dormant":
        raise AdRecycleBinActivationTicketError(
            "ticket state must remain dormant"
        )

    if ticket.status != "dormant":
        raise AdRecycleBinActivationTicketError(
            "ticket status must remain dormant"
        )

    if ticket.one_shot_required is not True:
        raise AdRecycleBinActivationTicketError(
            "one-shot requirement must remain enabled"
        )

    if ticket.replay_consumed is not False:
        raise AdRecycleBinActivationTicketError(
            "new dormant ticket cannot already be consumed"
        )

    false_fields = (
        "persistence_enabled",
        "route_enabled",
        "job_creation_authorized",
        "claim_authorized",
        "runtime_authorized",
        "production_authorized",
        "activation_authorized",
        "restore_authorized",
        "write_performed",
    )

    for field in false_fields:
        if getattr(
            ticket,
            field,
        ) is not False:
            raise AdRecycleBinActivationTicketError(
                f"unsafe ticket flag: {field}"
            )

    issued_at = _parse_timestamp(
        ticket.issued_at,
        field="issued_at",
    )

    expires_at = _parse_timestamp(
        ticket.expires_at,
        field="expires_at",
    )

    lifetime = (
        expires_at
        - issued_at
    ).total_seconds()

    if lifetime != AD_RECYCLE_BIN_ACTIVATION_TICKET_TTL_SECONDS:
        raise AdRecycleBinActivationTicketError(
            "ticket TTL mismatch"
        )

    expected_digest = _canonical_sha256(
        _ticket_digest_payload(
            ticket
        )
    )

    if ticket.ticket_digest != expected_digest:
        raise AdRecycleBinActivationTicketError(
            "ticket digest mismatch"
        )


def build_ad_recycle_bin_activation_ticket(
    *,
    source_intent_record: Mapping[str, Any],
    expected_intent_id: str,
    expected_intent_digest: str,
    evidence_job: Mapping[str, Any],
    expected_evidence_job_id: str,
    server_actor: Mapping[str, Any],
    confirmed_forest_name: str,
    current_mode: str,
    now: datetime | None = None,
) -> AdRecycleBinActivationTicket:
    if not AD_RECYCLE_BIN_ACTIVATION_TICKET_ENABLED:
        raise AdRecycleBinActivationTicketError(
            "activation ticket contract is disabled"
        )

    if current_mode != "Simulation":
        raise AdRecycleBinActivationTicketError(
            "activation ticket preparation is Simulation-only"
        )

    if not isinstance(
        source_intent_record,
        Mapping,
    ):
        raise AdRecycleBinActivationTicketError(
            "source intent record is invalid"
        )

    if not isinstance(
        evidence_job,
        Mapping,
    ):
        raise AdRecycleBinActivationTicketError(
            "fresh evidence job is invalid"
        )

    if not isinstance(
        server_actor,
        Mapping,
    ):
        raise AdRecycleBinActivationTicketError(
            "server actor is invalid"
        )

    current = _normalize_now(
        now
    )

    source_contract = _required_string(
        source_intent_record.get(
            "contract_version"
        ),
        field="source.contract_version",
        max_length=128,
    )

    if (
        source_contract
        != AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationTicketError(
            "source intent contract version mismatch"
        )

    if (
        source_intent_record.get("state")
        != "activation_intent_dormant"
    ):
        raise AdRecycleBinActivationTicketError(
            "source intent state is not dormant"
        )

    if (
        source_intent_record.get("status")
        != "dormant"
    ):
        raise AdRecycleBinActivationTicketError(
            "source intent status is not dormant"
        )

    for field in (
        "job_creation_authorized",
        "runtime_authorized",
        "production_authorized",
        "activation_authorized",
        "restore_authorized",
        "write_performed",
    ):
        _assert_false_flag(
            source_intent_record,
            field=field,
        )

    source_intent_id = _required_uuid(
        source_intent_record.get(
            "intent_id"
        ),
        field="source.intent_id",
    )

    supplied_intent_id = _required_uuid(
        expected_intent_id,
        field="expected_intent_id",
    )

    if source_intent_id != supplied_intent_id:
        raise AdRecycleBinActivationTicketError(
            "source intent id mismatch"
        )

    source_intent_digest = _required_sha256(
        source_intent_record.get(
            "intent_digest"
        ),
        field="source.intent_digest",
    )

    supplied_intent_digest = _required_sha256(
        expected_intent_digest,
        field="expected_intent_digest",
    )

    if source_intent_digest != supplied_intent_digest:
        raise AdRecycleBinActivationTicketError(
            "source intent digest mismatch"
        )

    source_forest = _required_string(
        source_intent_record.get(
            "forest_name"
        ),
        field="source.forest_name",
    )

    source_root = _required_string(
        source_intent_record.get(
            "root_domain"
        ),
        field="source.root_domain",
    )

    source_evidence_sha256 = _required_sha256(
        source_intent_record.get(
            "evidence_sha256"
        ),
        field="source.evidence_sha256",
    )

    source_evidence_created_at = _parse_timestamp(
        source_intent_record.get(
            "evidence_created_at"
        ),
        field="source.evidence_created_at",
    )

    actor_subject = _required_string(
        server_actor.get(
            "subject"
        ),
        field="server_actor.subject",
        max_length=256,
    )

    actor_username = _required_string(
        server_actor.get(
            "username"
        ),
        field="server_actor.username",
        max_length=128,
    )

    actor_issuer = _required_string(
        server_actor.get(
            "issuer"
        ),
        field="server_actor.issuer",
    )

    actor_azp = _required_string(
        server_actor.get(
            "azp"
        ),
        field="server_actor.azp",
        max_length=128,
    )

    if actor_issuer != OIDC_ISSUER:
        raise AdRecycleBinActivationTicketError(
            "OIDC issuer mismatch"
        )

    if (
        OIDC_ALLOWED_AZP
        and actor_azp not in OIDC_ALLOWED_AZP
    ):
        raise AdRecycleBinActivationTicketError(
            "OIDC azp is not allowed"
        )

    actor_bindings = {
        "actor_subject":
            actor_subject,

        "actor_username":
            actor_username,

        "actor_issuer":
            actor_issuer,

        "actor_azp":
            actor_azp,
    }

    for source_field, current_value in actor_bindings.items():
        source_value = _required_string(
            source_intent_record.get(
                source_field
            ),
            field=f"source.{source_field}",
        )

        if source_value != current_value:
            raise AdRecycleBinActivationTicketError(
                f"actor mismatch: {source_field}"
            )

    expected_job_id = _required_string(
        expected_evidence_job_id,
        field="expected_evidence_job_id",
        max_length=128,
    )

    job_id = _required_string(
        evidence_job.get(
            "id"
        ),
        field="evidence_job.id",
        max_length=128,
    )

    if job_id != expected_job_id:
        raise AdRecycleBinActivationTicketError(
            "fresh evidence job id mismatch"
        )

    if evidence_job.get("type") != "ad_explorer":
        raise AdRecycleBinActivationTicketError(
            "fresh evidence job type is invalid"
        )

    if (
        evidence_job.get("action")
        != "get_recycle_bin_activation_evidence"
    ):
        raise AdRecycleBinActivationTicketError(
            "fresh evidence action is invalid"
        )

    if evidence_job.get("status") != "completed":
        raise AdRecycleBinActivationTicketError(
            "fresh evidence job is not completed"
        )

    if evidence_job.get("success") is not True:
        raise AdRecycleBinActivationTicketError(
            "fresh evidence job did not succeed"
        )

    result = evidence_job.get(
        "result"
    )

    if not isinstance(
        result,
        Mapping,
    ):
        raise AdRecycleBinActivationTicketError(
            "fresh evidence result is invalid"
        )

    if (
        result.get("action")
        != "get_recycle_bin_activation_evidence"
    ):
        raise AdRecycleBinActivationTicketError(
            "fresh evidence result action is invalid"
        )

    if result.get("read_only") is not True:
        raise AdRecycleBinActivationTicketError(
            "fresh evidence is not read-only"
        )

    for field in (
        "activation_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "write_performed",
    ):
        _assert_false_flag(
            result,
            field=field,
        )

    if (
        result.get(
            "recycle_bin_enabled"
        )
        is not False
    ):
        raise AdRecycleBinActivationTicketError(
            "Recycle Bin is already enabled"
        )

    if (
        int(
            result.get(
                "recycle_bin_enabled_scope_count"
            )
            or 0
        )
        != 0
    ):
        raise AdRecycleBinActivationTicketError(
            "Recycle Bin enabled scope count is not zero"
        )

    if (
        int(
            result.get(
                "domain_controller_count"
            )
            or 0
        )
        < 1
    ):
        raise AdRecycleBinActivationTicketError(
            "no domain controller is present"
        )

    if (
        result.get(
            "replication_query_succeeded"
        )
        is not True
    ):
        raise AdRecycleBinActivationTicketError(
            "replication query failed"
        )

    if (
        result.get(
            "replication_partner_query_succeeded"
        )
        is not True
    ):
        raise AdRecycleBinActivationTicketError(
            "replication partner query failed"
        )

    if (
        int(
            result.get(
                "replication_failure_count"
            )
            or 0
        )
        != 0
    ):
        raise AdRecycleBinActivationTicketError(
            "replication failures are present"
        )

    if (
        result.get(
            "replication_ready"
        )
        is not True
    ):
        raise AdRecycleBinActivationTicketError(
            "replication is not ready"
        )

    evidence_forest = _required_string(
        result.get(
            "forest_name"
        ),
        field="evidence.forest_name",
    )

    evidence_root = _required_string(
        result.get(
            "root_domain"
        ),
        field="evidence.root_domain",
    )

    forest_mode = _required_string(
        result.get(
            "forest_mode"
        ),
        field="evidence.forest_mode",
        max_length=128,
    )

    confirmed_forest = _required_string(
        confirmed_forest_name,
        field="confirmed_forest_name",
    )

    _assert_same_dns_name(
        source_forest,
        evidence_forest,
        field="forest",
    )

    _assert_same_dns_name(
        source_root,
        evidence_root,
        field="root_domain",
    )

    _assert_same_dns_name(
        confirmed_forest,
        evidence_forest,
        field="confirmed_forest_name",
    )

    fresh_evidence_created_at = _parse_timestamp(
        result.get(
            "evidence_created_at"
        ),
        field="evidence.evidence_created_at",
    )

    if (
        fresh_evidence_created_at
        - current
    ).total_seconds() > (
        AD_RECYCLE_BIN_ACTIVATION_TICKET_FUTURE_SKEW_SECONDS
    ):
        raise AdRecycleBinActivationTicketError(
            "fresh evidence timestamp is in the future"
        )

    age_seconds = (
        current
        - fresh_evidence_created_at
    ).total_seconds()

    if age_seconds > (
        AD_RECYCLE_BIN_ACTIVATION_TICKET_EVIDENCE_MAX_AGE_SECONDS
    ):
        raise AdRecycleBinActivationTicketError(
            "fresh evidence is stale"
        )

    if (
        fresh_evidence_created_at
        <= source_evidence_created_at
    ):
        raise AdRecycleBinActivationTicketError(
            "fresh evidence is not newer than source evidence"
        )

    fresh_evidence_sha256 = _canonical_sha256(
        dict(result)
    )

    issued_at = current

    expires_at = (
        current
        + timedelta(
            seconds=(
                AD_RECYCLE_BIN_ACTIVATION_TICKET_TTL_SECONDS
            )
        )
    )

    ticket_payload = {
        "contract_version":
            AD_RECYCLE_BIN_ACTIVATION_TICKET_CONTRACT_VERSION,

        "ticket_id":
            str(uuid4()),

        "state":
            "activation_ticket_dormant",

        "status":
            "dormant",

        "source_intent_id":
            source_intent_id,

        "source_intent_digest":
            source_intent_digest,

        "source_intent_contract_version":
            source_contract,

        "source_evidence_sha256":
            source_evidence_sha256,

        "source_evidence_created_at":
            source_evidence_created_at.isoformat(),

        "fresh_evidence_job_id":
            job_id,

        "fresh_evidence_sha256":
            fresh_evidence_sha256,

        "fresh_evidence_created_at":
            fresh_evidence_created_at.isoformat(),

        "forest_name":
            evidence_forest,

        "root_domain":
            evidence_root,

        "forest_mode":
            forest_mode,

        "actor_subject":
            actor_subject,

        "actor_username":
            actor_username,

        "actor_issuer":
            actor_issuer,

        "actor_azp":
            actor_azp,

        "issued_at":
            issued_at.isoformat(),

        "expires_at":
            expires_at.isoformat(),

        "one_shot_required":
            True,

        "replay_consumed":
            False,

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

        "activation_authorized":
            False,

        "restore_authorized":
            False,

        "write_performed":
            False,
    }

    ticket_digest = _canonical_sha256(
        ticket_payload
    )

    ticket = AdRecycleBinActivationTicket(
        ticket_digest=ticket_digest,
        **ticket_payload,
    )

    assert_ad_recycle_bin_activation_ticket_invariants(
        ticket
    )

    return ticket


__all__ = [
    "AD_RECYCLE_BIN_ACTIVATION_TICKET_CONTRACT_VERSION",
    "AD_RECYCLE_BIN_ACTIVATION_TICKET_TTL_SECONDS",
    "AD_RECYCLE_BIN_ACTIVATION_TICKET_EVIDENCE_MAX_AGE_SECONDS",
    "AdRecycleBinActivationTicket",
    "AdRecycleBinActivationTicketError",
    "assert_ad_recycle_bin_activation_ticket_invariants",
    "build_ad_recycle_bin_activation_ticket",
]
