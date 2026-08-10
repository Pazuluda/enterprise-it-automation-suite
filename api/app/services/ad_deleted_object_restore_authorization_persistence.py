from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import tempfile

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from app.services.ad_deleted_object_restore_authorization import (
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION,
    AdDeletedObjectRestoreAuthorization,
    AdDeletedObjectRestoreAuthorizationError,
    assert_ad_deleted_object_restore_authorization_invariants,
)

AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION = "c9.5a4c3-v1"
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_ENABLED = True
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CLAIM_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_PRODUCTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_RESTORE_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_RESTORE_WHATIF_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_EXECUTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_WRITE_PERFORMED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_REGISTRY_MAX_RECORDS = 4096


class AdDeletedObjectRestoreAuthorizationPersistenceError(ValueError):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreAuthorizationPersistence:
    contract_version: str
    record_digest: str
    authorization_contract_version: str
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
    persisted_at: str
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


def _normalize_now(now: datetime | None) -> datetime:
    current = datetime.now(timezone.utc) if now is None else now
    if current.tzinfo is None:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "now must be timezone-aware"
        )
    return current.astimezone(timezone.utc)


def _parse_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            f"{field} is invalid"
        )
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            f"{field} is invalid"
        ) from exc
    if parsed.tzinfo is None:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            f"{field} must be timezone-aware"
        )
    return parsed.astimezone(timezone.utc)


def _assert_uuid(value: Any, *, field: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            f"{field} is not a UUID"
        ) from exc


def _assert_sha256(value: Any, *, field: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value.lower())
    ):
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            f"{field} is not a SHA-256 digest"
        )


def _canonical_sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _record_digest_payload(
    record: AdDeletedObjectRestoreAuthorizationPersistence,
) -> dict[str, Any]:
    payload = asdict(record)
    payload.pop("record_digest")
    return payload


def _source_authorization(
    record: AdDeletedObjectRestoreAuthorizationPersistence,
) -> AdDeletedObjectRestoreAuthorization:
    payload = asdict(record)
    for key in (
        "contract_version",
        "record_digest",
        "authorization_contract_version",
        "persisted_at",
    ):
        payload.pop(key)
    payload["contract_version"] = record.authorization_contract_version
    payload["persistence_enabled"] = False
    return AdDeletedObjectRestoreAuthorization(**payload)


def _assert_safe_path(path: Path) -> None:
    if not path.is_absolute():
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization registry path must be absolute"
        )
    if path.is_symlink():
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization registry path must not be a symlink"
        )
    current = path.parent
    while True:
        if current.is_symlink():
            raise AdDeletedObjectRestoreAuthorizationPersistenceError(
                "authorization registry parent must not be a symlink"
            )
        if current == current.parent:
            break
        current = current.parent


def _open_flags(base_flags: int) -> int:
    if hasattr(os, "O_NOFOLLOW"):
        return base_flags | os.O_NOFOLLOW
    return base_flags


@contextmanager
def _exclusive_registry_lock(registry_file: Path):
    lock_file = registry_file.with_name("." + registry_file.name + ".lock")
    _assert_safe_path(lock_file)
    fd = -1
    try:
        fd = os.open(lock_file, _open_flags(os.O_CREAT | os.O_RDWR), 0o600)
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    except OSError as exc:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "unable to lock authorization registry"
        ) from exc
    finally:
        if fd >= 0:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)


def assert_ad_deleted_object_restore_authorization_persistence_invariants(
    record: AdDeletedObjectRestoreAuthorizationPersistence,
) -> None:
    if not AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_ENABLED:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization persistence is disabled"
        )
    if (
        record.contract_version
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization persistence contract version mismatch"
        )
    if (
        record.authorization_contract_version
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization contract version mismatch"
        )

    for field in (
        "authorization_id",
        "ticket_id",
        "consumption_id",
        "source_simulation_job_id",
        "source_inventory_job_id",
        "source_live_job_id",
        "fresh_live_job_id",
        "object_guid",
    ):
        _assert_uuid(getattr(record, field), field=field)

    for field in (
        "record_digest",
        "authorization_digest",
        "ticket_digest",
        "consumption_record_digest",
        "fresh_live_sha256",
    ):
        _assert_sha256(getattr(record, field), field=field)

    if record.one_shot_required is not True:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization must remain one-shot"
        )
    if record.authorization_consumed is not False:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "persisted authorization must remain unconsumed"
        )
    if record.human_authorized is not True:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "human authorization marker must remain true"
        )
    if record.persistence_enabled is not True:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization persistence marker must be true"
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
        if getattr(record, field) is not False:
            raise AdDeletedObjectRestoreAuthorizationPersistenceError(
                f"unsafe persisted authorization flag: {field}"
            )

    for field in (
        "acknowledge_exact_object",
        "acknowledge_exact_target",
        "acknowledge_restore_write",
    ):
        if getattr(record, field) is not True:
            raise AdDeletedObjectRestoreAuthorizationPersistenceError(
                f"authorization acknowledgement lost: {field}"
            )

    try:
        assert_ad_deleted_object_restore_authorization_invariants(
            _source_authorization(record)
        )
    except AdDeletedObjectRestoreAuthorizationError as exc:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(str(exc)) from exc

    issued_at = _parse_timestamp(record.issued_at, field="issued_at")
    expires_at = _parse_timestamp(record.expires_at, field="expires_at")
    persisted_at = _parse_timestamp(record.persisted_at, field="persisted_at")
    if expires_at <= issued_at:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization expiration is invalid"
        )
    if persisted_at < issued_at:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization persisted before issue time"
        )
    if persisted_at >= expires_at:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "expired authorization cannot remain dormant"
        )

    expected = _canonical_sha256(_record_digest_payload(record))
    if record.record_digest != expected:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization persistence record digest mismatch"
        )


_RECORD_KEYS = {
    item.name
    for item in fields(AdDeletedObjectRestoreAuthorizationPersistence)
}


def _empty_registry() -> dict[str, Any]:
    return {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,
        "records": [],
    }


def _validate_registry(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization registry is invalid"
        )
    if (
        data.get("contract_version")
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization registry contract version mismatch"
        )
    records = data.get("records")
    if not isinstance(records, list):
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization registry records are invalid"
        )
    if len(records) > AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_REGISTRY_MAX_RECORDS:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization registry is full"
        )

    seen_authorization_ids: set[str] = set()
    seen_authorization_digests: set[str] = set()
    seen_ticket_ids: set[str] = set()
    seen_ticket_digests: set[str] = set()
    seen_consumption_ids: set[str] = set()

    for raw in records:
        if not isinstance(raw, dict) or set(raw) != _RECORD_KEYS:
            raise AdDeletedObjectRestoreAuthorizationPersistenceError(
                "authorization registry record schema mismatch"
            )
        record = AdDeletedObjectRestoreAuthorizationPersistence(**raw)
        assert_ad_deleted_object_restore_authorization_persistence_invariants(
            record
        )
        checks = (
            (record.authorization_id, seen_authorization_ids, "authorization id"),
            (record.authorization_digest, seen_authorization_digests, "authorization digest"),
            (record.ticket_id, seen_ticket_ids, "ticket id"),
            (record.ticket_digest, seen_ticket_digests, "ticket digest"),
            (record.consumption_id, seen_consumption_ids, "consumption id"),
        )
        for value, seen, label in checks:
            if value in seen:
                raise AdDeletedObjectRestoreAuthorizationPersistenceError(
                    f"duplicate {label} in authorization registry"
                )
            seen.add(value)
    return data


def _load_registry(registry_file: Path) -> dict[str, Any]:
    if not registry_file.exists():
        return _empty_registry()
    _assert_safe_path(registry_file)
    try:
        fd = os.open(registry_file, _open_flags(os.O_RDONLY))
    except OSError as exc:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "unable to open authorization registry"
        ) from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise AdDeletedObjectRestoreAuthorizationPersistenceError(
                "authorization registry is not a regular file"
            )
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            fd = -1
            try:
                data = json.load(handle)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise AdDeletedObjectRestoreAuthorizationPersistenceError(
                    "authorization registry JSON is invalid"
                ) from exc
    finally:
        if fd >= 0:
            os.close(fd)
    return _validate_registry(data)


def _atomic_write_registry(registry_file: Path, registry: dict[str, Any]) -> None:
    _validate_registry(registry)
    parent = registry_file.parent
    _assert_safe_path(registry_file)
    fd = -1
    temporary = Path()
    try:
        fd, temporary_name = tempfile.mkstemp(
            prefix="." + registry_file.name + ".",
            suffix=".tmp",
            dir=str(parent),
        )
        temporary = Path(temporary_name)
        os.fchmod(fd, 0o600)
        raw = json.dumps(
            registry,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        os.write(fd, raw)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(temporary, registry_file)
        os.chmod(registry_file, 0o600)

        directory_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY
        directory_fd = os.open(parent, _open_flags(directory_flags))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "unable to atomically write authorization registry"
        ) from exc
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary and temporary.exists():
            temporary.unlink()


def persist_ad_deleted_object_restore_authorization(
    authorization: AdDeletedObjectRestoreAuthorization,
    *,
    registry_file: Path,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreAuthorizationPersistence:
    if not AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_ENABLED:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization persistence is disabled"
        )
    try:
        assert_ad_deleted_object_restore_authorization_invariants(authorization)
    except AdDeletedObjectRestoreAuthorizationError as exc:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(str(exc)) from exc

    current = _normalize_now(now)
    issued_at = _parse_timestamp(
        authorization.issued_at,
        field="authorization.issued_at",
    )
    expires_at = _parse_timestamp(
        authorization.expires_at,
        field="authorization.expires_at",
    )
    if current < issued_at:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "authorization cannot be persisted before issue time"
        )
    if current >= expires_at:
        raise AdDeletedObjectRestoreAuthorizationPersistenceError(
            "expired authorization cannot be persisted"
        )

    if not isinstance(registry_file, Path):
        registry_file = Path(registry_file)

    payload = {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,
        "authorization_contract_version": authorization.contract_version,
        "authorization_id": authorization.authorization_id,
        "authorization_digest": authorization.authorization_digest,
        "state": authorization.state,
        "status": authorization.status,
        "ticket_id": authorization.ticket_id,
        "ticket_digest": authorization.ticket_digest,
        "consumption_id": authorization.consumption_id,
        "consumption_record_digest": authorization.consumption_record_digest,
        "source_simulation_job_id": authorization.source_simulation_job_id,
        "source_inventory_job_id": authorization.source_inventory_job_id,
        "source_live_job_id": authorization.source_live_job_id,
        "fresh_live_job_id": authorization.fresh_live_job_id,
        "fresh_live_sha256": authorization.fresh_live_sha256,
        "object_guid": authorization.object_guid,
        "object_class": authorization.object_class,
        "class_policy": authorization.class_policy,
        "effective_new_name": authorization.effective_new_name,
        "effective_target_path": authorization.effective_target_path,
        "actor_subject": authorization.actor_subject,
        "actor_username": authorization.actor_username,
        "actor_issuer": authorization.actor_issuer,
        "actor_azp": authorization.actor_azp,
        "acknowledge_exact_object": authorization.acknowledge_exact_object,
        "acknowledge_exact_target": authorization.acknowledge_exact_target,
        "acknowledge_restore_write": authorization.acknowledge_restore_write,
        "authorization_reason": authorization.authorization_reason,
        "issued_at": authorization.issued_at,
        "expires_at": authorization.expires_at,
        "persisted_at": current.isoformat(),
        "one_shot_required": True,
        "authorization_consumed": False,
        "human_authorized": True,
        "persistence_enabled": True,
        "route_enabled": False,
        "job_creation_authorized": False,
        "claim_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "restore_authorized": False,
        "restore_whatif_authorized": False,
        "execution_authorized": False,
        "write_performed": False,
    }
    record = AdDeletedObjectRestoreAuthorizationPersistence(
        record_digest=_canonical_sha256(payload),
        **payload,
    )
    assert_ad_deleted_object_restore_authorization_persistence_invariants(record)

    _assert_safe_path(registry_file)
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(registry_file)

    with _exclusive_registry_lock(registry_file):
        registry = _load_registry(registry_file)
        records = registry["records"]
        if len(records) >= AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_REGISTRY_MAX_RECORDS:
            raise AdDeletedObjectRestoreAuthorizationPersistenceError(
                "authorization registry is full"
            )
        for existing in records:
            duplicate = (
                existing["authorization_id"] == record.authorization_id
                or existing["authorization_digest"] == record.authorization_digest
                or existing["ticket_id"] == record.ticket_id
                or existing["ticket_digest"] == record.ticket_digest
                or existing["consumption_id"] == record.consumption_id
            )
            if duplicate:
                raise AdDeletedObjectRestoreAuthorizationPersistenceError(
                    "restore authorization already persisted"
                )
        records.append(asdict(record))
        _atomic_write_registry(registry_file, registry)
    return record


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION",
    "AdDeletedObjectRestoreAuthorizationPersistence",
    "AdDeletedObjectRestoreAuthorizationPersistenceError",
    "assert_ad_deleted_object_restore_authorization_persistence_invariants",
    "persist_ad_deleted_object_restore_authorization",
]
