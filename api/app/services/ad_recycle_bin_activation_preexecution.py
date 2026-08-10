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

from app.services.ad_recycle_bin_activation_authorization_persistence import (
    AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,
    AdRecycleBinActivationAuthorizationPersistence,
    AdRecycleBinActivationAuthorizationPersistenceError,
    assert_ad_recycle_bin_activation_authorization_persistence_invariants,
)


AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_CONTRACT_VERSION = (
    "c9.4a2e-v1"
)

AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_TTL_SECONDS = 45
AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_EVIDENCE_MAX_AGE_SECONDS = 45
AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_FUTURE_SKEW_SECONDS = 30

AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_PERSISTENCE_ENABLED = False
AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_ROUTE_ENABLED = False
AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_JOB_CREATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_RUNTIME_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_PRODUCTION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_ACTIVATION_AUTHORIZED = True
AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_RESTORE_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_WRITE_PERFORMED = False


class AdRecycleBinActivationPreexecutionError(
    ValueError
):
    pass


class AdRecycleBinActivationPreexecutionConflict(
    AdRecycleBinActivationPreexecutionError
):
    pass


@dataclass(frozen=True)
class AdRecycleBinActivationPreexecution:
    contract_version: str
    preexecution_id: str
    preexecution_digest: str

    state: str
    status: str

    authorization_persistence_contract_version: str
    authorization_id: str
    authorization_digest: str
    authorization_record_digest: str

    ticket_id: str
    ticket_digest: str
    consumption_id: str
    consumption_record_digest: str

    source_intent_id: str
    source_intent_digest: str

    authorization_evidence_job_id: str
    authorization_evidence_sha256: str

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

    human_authorized: bool
    revalidation_passed: bool
    authorization_consumption_required: bool
    authorization_consumed: bool

    persistence_enabled: bool
    route_enabled: bool
    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    activation_authorized: bool
    restore_authorized: bool
    write_performed: bool


def _normalize_now(
    now: datetime | None,
) -> datetime:
    current = (
        datetime.now(timezone.utc)
        if now is None
        else now
    )

    if current.tzinfo is None:
        raise AdRecycleBinActivationPreexecutionError(
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
        raise AdRecycleBinActivationPreexecutionError(
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
        raise AdRecycleBinActivationPreexecutionError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdRecycleBinActivationPreexecutionError(
            f"{field} must be timezone-aware"
        )

    return parsed.astimezone(
        timezone.utc
    )


def _required_string(
    value: Any,
    *,
    field: str,
    max_length: int = 512,
) -> str:
    if not isinstance(value, str):
        raise AdRecycleBinActivationPreexecutionError(
            f"{field} must be a string"
        )

    cleaned = value.strip()

    if not cleaned:
        raise AdRecycleBinActivationPreexecutionError(
            f"{field} is required"
        )

    if len(cleaned) > max_length:
        raise AdRecycleBinActivationPreexecutionError(
            f"{field} exceeds {max_length} characters"
        )

    return cleaned


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
        raise AdRecycleBinActivationPreexecutionError(
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
        raise AdRecycleBinActivationPreexecutionError(
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


def _preexecution_digest_payload(
    record: AdRecycleBinActivationPreexecution,
) -> dict[str, Any]:
    payload = asdict(
        record
    )

    payload.pop(
        "preexecution_digest"
    )

    return payload


def _extract_actor(
    server_actor: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(
        server_actor,
        Mapping,
    ):
        raise AdRecycleBinActivationPreexecutionError(
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
        raise AdRecycleBinActivationPreexecutionConflict(
            "OIDC issuer mismatch"
        )

    if (
        OIDC_ALLOWED_AZP
        and actor["azp"] not in OIDC_ALLOWED_AZP
    ):
        raise AdRecycleBinActivationPreexecutionConflict(
            "OIDC azp is not allowed"
        )

    return actor


def _fresh_evidence_payload(
    evidence_job: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        evidence_job,
        Mapping,
    ):
        raise AdRecycleBinActivationPreexecutionError(
            "fresh evidence job is invalid"
        )

    if evidence_job.get("type") != "ad_explorer":
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence job type mismatch"
        )

    if (
        evidence_job.get("action")
        != "get_recycle_bin_activation_evidence"
    ):
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence action mismatch"
        )

    if evidence_job.get("status") != "completed":
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence job is not completed"
        )

    if evidence_job.get("success") is not True:
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence job failed"
        )

    result = evidence_job.get("result")

    if not isinstance(
        result,
        Mapping,
    ):
        raise AdRecycleBinActivationPreexecutionError(
            "fresh evidence result is invalid"
        )

    if (
        result.get("action")
        != "get_recycle_bin_activation_evidence"
    ):
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence result action mismatch"
        )

    if result.get("read_only") is not True:
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence is not read-only"
        )

    for field in (
        "activation_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "write_performed",
    ):
        if result.get(field) is not False:
            raise AdRecycleBinActivationPreexecutionConflict(
                f"unsafe fresh evidence flag: {field}"
            )

    if result.get("recycle_bin_enabled") is not False:
        raise AdRecycleBinActivationPreexecutionConflict(
            "Recycle Bin is already enabled"
        )

    if result.get("recycle_bin_enabled_scope_count") != 0:
        raise AdRecycleBinActivationPreexecutionConflict(
            "Recycle Bin enabled scope count is not zero"
        )

    controller_count = result.get(
        "domain_controller_count"
    )

    if (
        not isinstance(
            controller_count,
            int,
        )
        or isinstance(
            controller_count,
            bool,
        )
        or controller_count < 1
    ):
        raise AdRecycleBinActivationPreexecutionConflict(
            "domain controller count is invalid"
        )

    if result.get("replication_query_succeeded") is not True:
        raise AdRecycleBinActivationPreexecutionConflict(
            "replication query failed"
        )

    if (
        result.get("replication_partner_query_succeeded")
        is not True
    ):
        raise AdRecycleBinActivationPreexecutionConflict(
            "replication partner query failed"
        )

    if result.get("replication_failure_count") != 0:
        raise AdRecycleBinActivationPreexecutionConflict(
            "replication failures detected"
        )

    if result.get("replication_ready") is not True:
        raise AdRecycleBinActivationPreexecutionConflict(
            "replication is not ready"
        )

    payload = dict(
        result
    )

    return payload


def assert_ad_recycle_bin_activation_preexecution_invariants(
    record: AdRecycleBinActivationPreexecution,
) -> None:
    if (
        record.contract_version
        != AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationPreexecutionError(
            "preexecution contract version mismatch"
        )

    _required_uuid(
        record.preexecution_id,
        field="preexecution_id",
    )

    for field in (
        "preexecution_digest",
        "authorization_digest",
        "authorization_record_digest",
        "ticket_digest",
        "consumption_record_digest",
        "source_intent_digest",
        "authorization_evidence_sha256",
        "fresh_evidence_sha256",
    ):
        _required_sha256(
            getattr(record, field),
            field=field,
        )

    for field in (
        "authorization_id",
        "ticket_id",
        "consumption_id",
        "source_intent_id",
    ):
        _required_uuid(
            getattr(record, field),
            field=field,
        )

    if record.state != "activation_preexecution_ready_dormant":
        raise AdRecycleBinActivationPreexecutionError(
            "preexecution state must remain dormant"
        )

    if record.status != "ready":
        raise AdRecycleBinActivationPreexecutionError(
            "preexecution status is invalid"
        )

    if record.human_authorized is not True:
        raise AdRecycleBinActivationPreexecutionError(
            "human authorization marker must be true"
        )

    if record.revalidation_passed is not True:
        raise AdRecycleBinActivationPreexecutionError(
            "fresh revalidation marker must be true"
        )

    if record.authorization_consumption_required is not True:
        raise AdRecycleBinActivationPreexecutionError(
            "authorization consumption must remain required"
        )

    if record.authorization_consumed is not False:
        raise AdRecycleBinActivationPreexecutionError(
            "authorization must remain unconsumed"
        )

    if record.activation_authorized is not True:
        raise AdRecycleBinActivationPreexecutionError(
            "human activation authorization marker must remain true"
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
            record,
            field,
        ) is not False:
            raise AdRecycleBinActivationPreexecutionError(
                f"unsafe preexecution flag: {field}"
            )

    issued_at = _parse_timestamp(
        record.issued_at,
        field="issued_at",
    )

    expires_at = _parse_timestamp(
        record.expires_at,
        field="expires_at",
    )

    if expires_at <= issued_at:
        raise AdRecycleBinActivationPreexecutionError(
            "preexecution expiration is invalid"
        )

    lifetime = int(
        (
            expires_at
            - issued_at
        ).total_seconds()
    )

    if lifetime > AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_TTL_SECONDS:
        raise AdRecycleBinActivationPreexecutionError(
            "preexecution lifetime exceeds maximum TTL"
        )

    expected = _canonical_sha256(
        _preexecution_digest_payload(
            record
        )
    )

    if record.preexecution_digest != expected:
        raise AdRecycleBinActivationPreexecutionError(
            "preexecution digest mismatch"
        )


def build_ad_recycle_bin_activation_preexecution(
    authorization_record: AdRecycleBinActivationAuthorizationPersistence,
    *,
    fresh_evidence_job: Mapping[str, Any],
    expected_authorization_id: str,
    expected_authorization_digest: str,
    server_actor: Mapping[str, Any],
    confirmed_forest_name: str,
    current_mode: str,
    now: datetime | None = None,
) -> AdRecycleBinActivationPreexecution:
    if current_mode != "Simulation":
        raise AdRecycleBinActivationPreexecutionError(
            "preexecution preparation is Simulation-only"
        )

    try:
        assert_ad_recycle_bin_activation_authorization_persistence_invariants(
            authorization_record
        )
    except AdRecycleBinActivationAuthorizationPersistenceError as exc:
        raise AdRecycleBinActivationPreexecutionError(
            str(exc)
        ) from exc

    if (
        authorization_record.contract_version
        != AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationPreexecutionConflict(
            "authorization persistence contract mismatch"
        )

    if authorization_record.state != "activation_authorization_dormant":
        raise AdRecycleBinActivationPreexecutionConflict(
            "authorization is not dormant"
        )

    if authorization_record.status != "authorized":
        raise AdRecycleBinActivationPreexecutionConflict(
            "authorization status mismatch"
        )

    if authorization_record.human_authorized is not True:
        raise AdRecycleBinActivationPreexecutionConflict(
            "human authorization is missing"
        )

    if authorization_record.activation_authorized is not True:
        raise AdRecycleBinActivationPreexecutionConflict(
            "activation authorization is missing"
        )

    if authorization_record.authorization_consumed is not False:
        raise AdRecycleBinActivationPreexecutionConflict(
            "authorization is already consumed"
        )

    for field in (
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "write_performed",
    ):
        if getattr(
            authorization_record,
            field,
        ) is not False:
            raise AdRecycleBinActivationPreexecutionConflict(
                f"unsafe authorization flag: {field}"
            )

    supplied_authorization_id = _required_uuid(
        expected_authorization_id,
        field="expected_authorization_id",
    )

    supplied_authorization_digest = _required_sha256(
        expected_authorization_digest,
        field="expected_authorization_digest",
    )

    if supplied_authorization_id != authorization_record.authorization_id:
        raise AdRecycleBinActivationPreexecutionConflict(
            "authorization id mismatch"
        )

    if supplied_authorization_digest != authorization_record.authorization_digest:
        raise AdRecycleBinActivationPreexecutionConflict(
            "authorization digest mismatch"
        )

    actor = _extract_actor(
        server_actor
    )

    actor_bindings = {
        "actor_subject": actor["subject"],
        "actor_username": actor["username"],
        "actor_issuer": actor["issuer"],
        "actor_azp": actor["azp"],
    }

    for field, value in actor_bindings.items():
        if getattr(
            authorization_record,
            field,
        ) != value:
            raise AdRecycleBinActivationPreexecutionConflict(
                f"actor mismatch: {field}"
            )

    confirmed_forest = _required_string(
        confirmed_forest_name,
        field="confirmed_forest_name",
        max_length=255,
    )

    if confirmed_forest != authorization_record.forest_name:
        raise AdRecycleBinActivationPreexecutionConflict(
            "forest confirmation mismatch"
        )

    evidence = _fresh_evidence_payload(
        fresh_evidence_job
    )

    fresh_job_id = _required_string(
        fresh_evidence_job.get("id"),
        field="fresh_evidence_job.id",
        max_length=128,
    )

    fresh_forest = _required_string(
        evidence.get("forest_name"),
        field="fresh_evidence.forest_name",
        max_length=255,
    )

    fresh_root = _required_string(
        evidence.get("root_domain"),
        field="fresh_evidence.root_domain",
        max_length=255,
    )

    fresh_mode = _required_string(
        evidence.get("forest_mode"),
        field="fresh_evidence.forest_mode",
        max_length=128,
    )

    if fresh_forest != authorization_record.forest_name:
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence forest mismatch"
        )

    if fresh_root != authorization_record.root_domain:
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence root domain mismatch"
        )

    if fresh_mode != authorization_record.forest_mode:
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence forest mode mismatch"
        )

    current = _normalize_now(
        now
    )

    authorization_issued_at = _parse_timestamp(
        authorization_record.issued_at,
        field="authorization.issued_at",
    )

    authorization_expires_at = _parse_timestamp(
        authorization_record.expires_at,
        field="authorization.expires_at",
    )

    authorization_persisted_at = _parse_timestamp(
        authorization_record.persisted_at,
        field="authorization.persisted_at",
    )

    if current >= authorization_expires_at:
        raise AdRecycleBinActivationPreexecutionConflict(
            "authorization expired before preexecution"
        )

    evidence_created_at = _parse_timestamp(
        evidence.get("evidence_created_at"),
        field="fresh_evidence.evidence_created_at",
    )

    if (
        evidence_created_at
        - current
        > timedelta(
            seconds=AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_FUTURE_SKEW_SECONDS
        )
    ):
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence timestamp is too far in the future"
        )

    evidence_age = (
        current
        - evidence_created_at
    ).total_seconds()

    if evidence_age < 0:
        evidence_age = 0

    if evidence_age > AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_EVIDENCE_MAX_AGE_SECONDS:
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence is stale"
        )

    if evidence_created_at <= authorization_persisted_at:
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence must be newer than persisted authorization"
        )

    if evidence_created_at <= authorization_issued_at:
        raise AdRecycleBinActivationPreexecutionConflict(
            "fresh evidence must be newer than authorization issue time"
        )

    fresh_evidence_sha256 = _canonical_sha256(
        dict(
            evidence
        )
    )

    expires_at = min(
        current
        + timedelta(
            seconds=AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_TTL_SECONDS
        ),
        authorization_expires_at,
    )

    if expires_at <= current:
        raise AdRecycleBinActivationPreexecutionConflict(
            "preexecution window is already closed"
        )

    payload = {
        "contract_version":
            AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_CONTRACT_VERSION,

        "preexecution_id":
            str(uuid4()),

        "state":
            "activation_preexecution_ready_dormant",

        "status":
            "ready",

        "authorization_persistence_contract_version":
            authorization_record.contract_version,

        "authorization_id":
            authorization_record.authorization_id,

        "authorization_digest":
            authorization_record.authorization_digest,

        "authorization_record_digest":
            authorization_record.record_digest,

        "ticket_id":
            authorization_record.ticket_id,

        "ticket_digest":
            authorization_record.ticket_digest,

        "consumption_id":
            authorization_record.consumption_id,

        "consumption_record_digest":
            authorization_record.consumption_record_digest,

        "source_intent_id":
            authorization_record.source_intent_id,

        "source_intent_digest":
            authorization_record.source_intent_digest,

        "authorization_evidence_job_id":
            authorization_record.fresh_evidence_job_id,

        "authorization_evidence_sha256":
            authorization_record.fresh_evidence_sha256,

        "fresh_evidence_job_id":
            fresh_job_id,

        "fresh_evidence_sha256":
            fresh_evidence_sha256,

        "fresh_evidence_created_at":
            evidence_created_at.isoformat(),

        "forest_name":
            authorization_record.forest_name,

        "root_domain":
            authorization_record.root_domain,

        "forest_mode":
            authorization_record.forest_mode,

        "actor_subject":
            authorization_record.actor_subject,

        "actor_username":
            authorization_record.actor_username,

        "actor_issuer":
            authorization_record.actor_issuer,

        "actor_azp":
            authorization_record.actor_azp,

        "issued_at":
            current.isoformat(),

        "expires_at":
            expires_at.isoformat(),

        "human_authorized":
            True,

        "revalidation_passed":
            True,

        "authorization_consumption_required":
            True,

        "authorization_consumed":
            False,

        "persistence_enabled":
            AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_PERSISTENCE_ENABLED,

        "route_enabled":
            AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_ROUTE_ENABLED,

        "job_creation_authorized":
            AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_JOB_CREATION_AUTHORIZED,

        "runtime_authorized":
            AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_RUNTIME_AUTHORIZED,

        "production_authorized":
            AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_PRODUCTION_AUTHORIZED,

        "activation_authorized":
            AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_ACTIVATION_AUTHORIZED,

        "restore_authorized":
            AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_RESTORE_AUTHORIZED,

        "write_performed":
            AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_WRITE_PERFORMED,
    }

    preexecution_digest = _canonical_sha256(
        payload
    )

    record = AdRecycleBinActivationPreexecution(
        preexecution_digest=preexecution_digest,
        **payload,
    )

    assert_ad_recycle_bin_activation_preexecution_invariants(
        record
    )

    return record


__all__ = [
    "AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_CONTRACT_VERSION",
    "AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_TTL_SECONDS",
    "AdRecycleBinActivationPreexecution",
    "AdRecycleBinActivationPreexecutionConflict",
    "AdRecycleBinActivationPreexecutionError",
    "assert_ad_recycle_bin_activation_preexecution_invariants",
    "build_ad_recycle_bin_activation_preexecution",
]
