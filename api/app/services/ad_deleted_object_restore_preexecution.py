from __future__ import annotations

import hashlib
import json

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID, uuid4

from app.core.security import OIDC_ALLOWED_AZP, OIDC_ISSUER
from app.services.ad_deleted_object_restore_authorization_persistence import (
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,
    AdDeletedObjectRestoreAuthorizationPersistence,
    AdDeletedObjectRestoreAuthorizationPersistenceError,
    assert_ad_deleted_object_restore_authorization_persistence_invariants,
)
from app.services.ad_deleted_object_restore_preflight import (
    preflight_deleted_object_restore,
)


AD_DELETED_OBJECT_RESTORE_PREEXECUTION_CONTRACT_VERSION = "c9.5a4d-v1"
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_TTL_SECONDS = 45
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_LIVE_MAX_AGE_SECONDS = 45
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_FUTURE_SKEW_SECONDS = 30

AD_DELETED_OBJECT_RESTORE_PREEXECUTION_PERSISTENCE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_CLAIM_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_PRODUCTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_RESTORE_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_RESTORE_WHATIF_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_EXECUTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_PREEXECUTION_WRITE_PERFORMED = False


class AdDeletedObjectRestorePreexecutionError(ValueError):
    pass


class AdDeletedObjectRestorePreexecutionConflict(
    AdDeletedObjectRestorePreexecutionError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestorePreexecution:
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

    authorization_issued_at: str
    authorization_expires_at: str
    authorization_persisted_at: str

    issued_at: str
    expires_at: str

    human_authorized: bool
    revalidation_passed: bool

    authorization_consumption_required: bool
    authorization_consumed: bool

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


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalize_now(now: datetime | None) -> datetime:
    current = datetime.now(timezone.utc) if now is None else now
    if current.tzinfo is None:
        raise AdDeletedObjectRestorePreexecutionError(
            "now must be timezone-aware"
        )
    return current.astimezone(timezone.utc)


def _parse_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AdDeletedObjectRestorePreexecutionError(
            f"{field} is invalid"
        )
    try:
        parsed = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise AdDeletedObjectRestorePreexecutionError(
            f"{field} is invalid"
        ) from exc
    if parsed.tzinfo is None:
        raise AdDeletedObjectRestorePreexecutionError(
            f"{field} must be timezone-aware"
        )
    return parsed.astimezone(timezone.utc)


def _required_string(
    value: Any,
    *,
    field: str,
    min_length: int = 1,
    max_length: int = 1024,
) -> str:
    if not isinstance(value, str):
        raise AdDeletedObjectRestorePreexecutionError(
            f"{field} must be a string"
        )
    cleaned = value.strip()
    if len(cleaned) < min_length:
        raise AdDeletedObjectRestorePreexecutionError(
            f"{field} is required"
        )
    if len(cleaned) > max_length:
        raise AdDeletedObjectRestorePreexecutionError(
            f"{field} exceeds {max_length} characters"
        )
    return cleaned


def _required_uuid(value: Any, *, field: str) -> str:
    cleaned = _required_string(
        value,
        field=field,
        max_length=64,
    )
    try:
        return str(UUID(cleaned))
    except (ValueError, AttributeError) as exc:
        raise AdDeletedObjectRestorePreexecutionError(
            f"{field} is not a UUID"
        ) from exc


def _required_sha256(value: Any, *, field: str) -> str:
    cleaned = _required_string(
        value,
        field=field,
        max_length=64,
    ).lower()
    if (
        len(cleaned) != 64
        or any(c not in "0123456789abcdef" for c in cleaned)
    ):
        raise AdDeletedObjectRestorePreexecutionError(
            f"{field} is not a SHA-256 digest"
        )
    return cleaned


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _digest_payload(
    record: AdDeletedObjectRestorePreexecution,
) -> dict[str, Any]:
    payload = asdict(record)
    payload.pop("preexecution_digest")
    return payload


def _extract_actor(
    server_actor: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(server_actor, Mapping):
        raise AdDeletedObjectRestorePreexecutionError(
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
        raise AdDeletedObjectRestorePreexecutionConflict(
            "OIDC issuer mismatch"
        )

    if OIDC_ALLOWED_AZP and actor["azp"] not in OIDC_ALLOWED_AZP:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "OIDC azp is not allowed"
        )

    return actor


def assert_ad_deleted_object_restore_preexecution_invariants(
    record: AdDeletedObjectRestorePreexecution,
) -> None:
    if (
        record.contract_version
        != AD_DELETED_OBJECT_RESTORE_PREEXECUTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestorePreexecutionError(
            "preexecution contract version mismatch"
        )

    if (
        record.authorization_persistence_contract_version
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestorePreexecutionError(
            "authorization persistence contract mismatch"
        )

    for field in (
        "preexecution_id",
        "authorization_id",
        "ticket_id",
        "consumption_id",
        "source_simulation_job_id",
        "source_inventory_job_id",
        "source_live_job_id",
        "authorization_fresh_live_job_id",
        "fresh_live_job_id",
        "object_guid",
    ):
        _required_uuid(getattr(record, field), field=field)

    for field in (
        "preexecution_digest",
        "authorization_digest",
        "authorization_record_digest",
        "ticket_digest",
        "consumption_record_digest",
        "authorization_fresh_live_sha256",
        "fresh_live_sha256",
    ):
        _required_sha256(getattr(record, field), field=field)

    if record.state != "restore_preexecution_ready_dormant":
        raise AdDeletedObjectRestorePreexecutionError(
            "preexecution state must remain dormant"
        )

    if record.status != "ready":
        raise AdDeletedObjectRestorePreexecutionError(
            "preexecution status is invalid"
        )

    if record.human_authorized is not True:
        raise AdDeletedObjectRestorePreexecutionError(
            "human authorization marker must remain true"
        )

    if record.revalidation_passed is not True:
        raise AdDeletedObjectRestorePreexecutionError(
            "fresh revalidation marker must remain true"
        )

    if record.authorization_consumption_required is not True:
        raise AdDeletedObjectRestorePreexecutionError(
            "authorization consumption must remain required"
        )

    if record.authorization_consumed is not False:
        raise AdDeletedObjectRestorePreexecutionError(
            "authorization must remain unconsumed"
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
        if getattr(record, field) is not False:
            raise AdDeletedObjectRestorePreexecutionError(
                f"unsafe preexecution flag: {field}"
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
            getattr(record, field),
            field=field,
        )

    issued_at = _parse_timestamp(record.issued_at, field="issued_at")
    expires_at = _parse_timestamp(record.expires_at, field="expires_at")
    auth_issued = _parse_timestamp(
        record.authorization_issued_at,
        field="authorization_issued_at",
    )
    auth_persisted = _parse_timestamp(
        record.authorization_persisted_at,
        field="authorization_persisted_at",
    )
    auth_expires = _parse_timestamp(
        record.authorization_expires_at,
        field="authorization_expires_at",
    )
    fresh_completed = _parse_timestamp(
        record.fresh_live_completed_at,
        field="fresh_live_completed_at",
    )

    if not (
        auth_issued <= auth_persisted < auth_expires
    ):
        raise AdDeletedObjectRestorePreexecutionError(
            "authorization timestamp chain is invalid"
        )

    if issued_at < auth_persisted:
        raise AdDeletedObjectRestorePreexecutionError(
            "preexecution issued before persisted authorization"
        )

    if fresh_completed <= auth_persisted:
        raise AdDeletedObjectRestorePreexecutionError(
            "fresh live evidence is not newer than persisted authorization"
        )

    if (
        issued_at - fresh_completed
    ).total_seconds() > AD_DELETED_OBJECT_RESTORE_PREEXECUTION_LIVE_MAX_AGE_SECONDS:
        raise AdDeletedObjectRestorePreexecutionError(
            "fresh live evidence exceeds maximum age"
        )

    if (
        fresh_completed - issued_at
    ).total_seconds() > AD_DELETED_OBJECT_RESTORE_PREEXECUTION_FUTURE_SKEW_SECONDS:
        raise AdDeletedObjectRestorePreexecutionError(
            "fresh live evidence is too far in the future"
        )

    if expires_at <= issued_at:
        raise AdDeletedObjectRestorePreexecutionError(
            "preexecution expiration is invalid"
        )

    if (
        expires_at - issued_at
    ).total_seconds() > AD_DELETED_OBJECT_RESTORE_PREEXECUTION_TTL_SECONDS:
        raise AdDeletedObjectRestorePreexecutionError(
            "preexecution lifetime exceeds maximum TTL"
        )

    if expires_at > auth_expires:
        raise AdDeletedObjectRestorePreexecutionError(
            "preexecution cannot outlive authorization"
        )

    expected = _canonical_sha256(_digest_payload(record))
    if record.preexecution_digest != expected:
        raise AdDeletedObjectRestorePreexecutionError(
            "preexecution digest mismatch"
        )


def build_ad_deleted_object_restore_preexecution(
    authorization_record: AdDeletedObjectRestoreAuthorizationPersistence,
    *,
    jobs_path: Path,
    fresh_live_job_id: str,
    expected_authorization_id: str,
    expected_authorization_digest: str,
    expected_object_guid: str,
    confirmed_new_name: str,
    confirmed_target_path: str,
    server_actor: Mapping[str, Any],
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestorePreexecution:
    if current_mode != "Simulation":
        raise AdDeletedObjectRestorePreexecutionError(
            "restore preexecution preparation is Simulation-only"
        )

    try:
        assert_ad_deleted_object_restore_authorization_persistence_invariants(
            authorization_record
        )
    except AdDeletedObjectRestoreAuthorizationPersistenceError as exc:
        raise AdDeletedObjectRestorePreexecutionError(
            str(exc)
        ) from exc

    if (
        authorization_record.contract_version
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestorePreexecutionConflict(
            "authorization persistence contract mismatch"
        )

    if authorization_record.state != "restore_authorization_dormant":
        raise AdDeletedObjectRestorePreexecutionConflict(
            "authorization is not dormant"
        )

    if authorization_record.status != "authorized":
        raise AdDeletedObjectRestorePreexecutionConflict(
            "authorization status mismatch"
        )

    if authorization_record.human_authorized is not True:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "human authorization is missing"
        )

    if authorization_record.authorization_consumed is not False:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "authorization is already consumed"
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
        if getattr(authorization_record, field) is not False:
            raise AdDeletedObjectRestorePreexecutionConflict(
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
    supplied_guid = _required_uuid(
        expected_object_guid,
        field="expected_object_guid",
    )
    supplied_name = _required_string(
        confirmed_new_name,
        field="confirmed_new_name",
        max_length=512,
    )
    supplied_target = _required_string(
        confirmed_target_path,
        field="confirmed_target_path",
        max_length=2048,
    )
    fresh_id = _required_uuid(
        fresh_live_job_id,
        field="fresh_live_job_id",
    )

    expected_pairs = (
        (
            supplied_authorization_id,
            authorization_record.authorization_id,
            "authorization id mismatch",
        ),
        (
            supplied_authorization_digest,
            authorization_record.authorization_digest,
            "authorization digest mismatch",
        ),
        (
            supplied_guid.lower(),
            authorization_record.object_guid.lower(),
            "object GUID mismatch",
        ),
        (
            supplied_name,
            authorization_record.effective_new_name,
            "restore name confirmation mismatch",
        ),
        (
            supplied_target,
            authorization_record.effective_target_path,
            "restore target confirmation mismatch",
        ),
    )
    for supplied, expected, message in expected_pairs:
        if supplied != expected:
            raise AdDeletedObjectRestorePreexecutionConflict(message)

    if fresh_id == authorization_record.fresh_live_job_id:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh live revalidation must be newer than authorization evidence"
        )

    actor = _extract_actor(server_actor)
    actor_bindings = {
        "actor_subject": actor["subject"],
        "actor_username": actor["username"],
        "actor_issuer": actor["issuer"],
        "actor_azp": actor["azp"],
    }
    for field, value in actor_bindings.items():
        if getattr(authorization_record, field) != value:
            raise AdDeletedObjectRestorePreexecutionConflict(
                f"actor mismatch: {field}"
            )

    current = _normalize_now(now)
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

    if current < authorization_issued_at:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "authorization issue time is in the future"
        )

    if current >= authorization_expires_at:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "authorization expired before preexecution"
        )

    try:
        preflight = preflight_deleted_object_restore(
            Path(jobs_path),
            object_guid=authorization_record.object_guid,
            requested_new_name=authorization_record.effective_new_name,
            requested_target_path=authorization_record.effective_target_path,
            live_job_id=fresh_id,
            live_revalidation_max_age_seconds=(
                AD_DELETED_OBJECT_RESTORE_PREEXECUTION_LIVE_MAX_AGE_SECONDS
            ),
        )
    except (OSError, ValueError) as exc:
        raise AdDeletedObjectRestorePreexecutionConflict(
            f"fresh live preflight rejected: {exc}"
        ) from exc

    if not isinstance(preflight, Mapping):
        raise AdDeletedObjectRestorePreexecutionError(
            "fresh preflight result is invalid"
        )

    if preflight.get("read_only") is not True:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh preflight is not read-only"
        )

    if preflight.get("live_revalidation_performed") is not True:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh live revalidation was not performed"
        )

    if _clean(preflight.get("live_job_id")) != fresh_id:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh live job binding mismatch"
        )

    for field in (
        "restore_job_created",
        "restore_implemented",
        "execution_authorized",
        "write_authorized",
    ):
        if preflight.get(field) is not False:
            raise AdDeletedObjectRestorePreexecutionConflict(
                f"unsafe fresh preflight flag: {field}"
            )

    policy = preflight.get("policy")
    if not isinstance(policy, Mapping):
        raise AdDeletedObjectRestorePreexecutionError(
            "fresh preflight policy is invalid"
        )

    if policy.get("decision") != "candidate_preflight":
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh preflight policy decision mismatch"
        )

    if policy.get("preflight_passed") is not True:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh preflight did not pass"
        )

    if policy.get("simulation_candidate") is not True:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh preflight is not a Simulation candidate"
        )

    manual_review = policy.get(
        "manual_review_required",
        policy.get("manual_review"),
    )
    if manual_review is not False:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh preflight requires manual review"
        )

    policy_bindings = (
        (
            _clean(policy.get("object_class")),
            authorization_record.object_class,
            "fresh preflight class mismatch",
        ),
        (
            _clean(policy.get("class_policy")),
            authorization_record.class_policy,
            "fresh preflight class policy mismatch",
        ),
        (
            _clean(policy.get("effective_new_name")),
            authorization_record.effective_new_name,
            "fresh preflight new name mismatch",
        ),
        (
            _clean(policy.get("effective_target_path")),
            authorization_record.effective_target_path,
            "fresh preflight target mismatch",
        ),
    )
    for observed, expected, message in policy_bindings:
        if observed != expected:
            raise AdDeletedObjectRestorePreexecutionConflict(message)

    if _clean(preflight.get("object_guid")).lower() != (
        authorization_record.object_guid.lower()
    ):
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh preflight object GUID mismatch"
        )

    fresh_completed_at = _parse_timestamp(
        preflight.get("live_job_completed_at"),
        field="fresh_live_completed_at",
    )

    if (
        fresh_completed_at - current
    ) > timedelta(
        seconds=AD_DELETED_OBJECT_RESTORE_PREEXECUTION_FUTURE_SKEW_SECONDS
    ):
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh live timestamp is too far in the future"
        )

    age_seconds = (current - fresh_completed_at).total_seconds()
    if age_seconds < 0:
        age_seconds = 0
    if age_seconds > AD_DELETED_OBJECT_RESTORE_PREEXECUTION_LIVE_MAX_AGE_SECONDS:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh live revalidation is stale"
        )

    if fresh_completed_at <= authorization_persisted_at:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh live revalidation must be newer than persisted authorization"
        )

    if fresh_completed_at <= authorization_issued_at:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "fresh live revalidation must be newer than authorization issue time"
        )

    fresh_sha256 = _canonical_sha256(preflight)

    expires_at = min(
        current + timedelta(
            seconds=AD_DELETED_OBJECT_RESTORE_PREEXECUTION_TTL_SECONDS
        ),
        authorization_expires_at,
    )
    if expires_at <= current:
        raise AdDeletedObjectRestorePreexecutionConflict(
            "preexecution window is already closed"
        )

    payload = {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_CONTRACT_VERSION,
        "preexecution_id": str(uuid4()),
        "state": "restore_preexecution_ready_dormant",
        "status": "ready",
        "authorization_persistence_contract_version":
            authorization_record.contract_version,
        "authorization_id": authorization_record.authorization_id,
        "authorization_digest": authorization_record.authorization_digest,
        "authorization_record_digest": authorization_record.record_digest,
        "ticket_id": authorization_record.ticket_id,
        "ticket_digest": authorization_record.ticket_digest,
        "consumption_id": authorization_record.consumption_id,
        "consumption_record_digest":
            authorization_record.consumption_record_digest,
        "source_simulation_job_id":
            authorization_record.source_simulation_job_id,
        "source_inventory_job_id":
            authorization_record.source_inventory_job_id,
        "source_live_job_id":
            authorization_record.source_live_job_id,
        "authorization_fresh_live_job_id":
            authorization_record.fresh_live_job_id,
        "authorization_fresh_live_sha256":
            authorization_record.fresh_live_sha256,
        "fresh_live_job_id": fresh_id,
        "fresh_live_sha256": fresh_sha256,
        "fresh_live_completed_at": fresh_completed_at.isoformat(),
        "object_guid": authorization_record.object_guid,
        "object_class": authorization_record.object_class,
        "class_policy": authorization_record.class_policy,
        "effective_new_name": authorization_record.effective_new_name,
        "effective_target_path": authorization_record.effective_target_path,
        "actor_subject": authorization_record.actor_subject,
        "actor_username": authorization_record.actor_username,
        "actor_issuer": authorization_record.actor_issuer,
        "actor_azp": authorization_record.actor_azp,
        "authorization_issued_at": authorization_record.issued_at,
        "authorization_expires_at": authorization_record.expires_at,
        "authorization_persisted_at": authorization_record.persisted_at,
        "issued_at": current.isoformat(),
        "expires_at": expires_at.isoformat(),
        "human_authorized": True,
        "revalidation_passed": True,
        "authorization_consumption_required": True,
        "authorization_consumed": False,
        "persistence_enabled":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_PERSISTENCE_ENABLED,
        "route_enabled":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_ROUTE_ENABLED,
        "job_creation_authorized":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_JOB_CREATION_AUTHORIZED,
        "claim_authorized":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_CLAIM_AUTHORIZED,
        "runtime_authorized":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_RUNTIME_AUTHORIZED,
        "production_authorized":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_PRODUCTION_AUTHORIZED,
        "restore_authorized":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_RESTORE_AUTHORIZED,
        "restore_whatif_authorized":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_RESTORE_WHATIF_AUTHORIZED,
        "execution_authorized":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_EXECUTION_AUTHORIZED,
        "write_performed":
            AD_DELETED_OBJECT_RESTORE_PREEXECUTION_WRITE_PERFORMED,
    }

    digest = _canonical_sha256(payload)
    record = AdDeletedObjectRestorePreexecution(
        preexecution_digest=digest,
        **payload,
    )
    assert_ad_deleted_object_restore_preexecution_invariants(record)
    return record


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_PREEXECUTION_CONTRACT_VERSION",
    "AD_DELETED_OBJECT_RESTORE_PREEXECUTION_TTL_SECONDS",
    "AD_DELETED_OBJECT_RESTORE_PREEXECUTION_LIVE_MAX_AGE_SECONDS",
    "AdDeletedObjectRestorePreexecution",
    "AdDeletedObjectRestorePreexecutionConflict",
    "AdDeletedObjectRestorePreexecutionError",
    "assert_ad_deleted_object_restore_preexecution_invariants",
    "build_ad_deleted_object_restore_preexecution",
]
