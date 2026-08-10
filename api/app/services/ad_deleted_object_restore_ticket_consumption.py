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
from uuid import UUID, uuid4

from app.services.ad_deleted_object_restore_ticket_persistence import (
    AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION,
    AdDeletedObjectRestoreTicketPersistence,
    AdDeletedObjectRestoreTicketPersistenceError,
    assert_ad_deleted_object_restore_ticket_persistence_invariants,
)


AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CONTRACT_VERSION = (
    "c9.5a4b3-v1"
)

AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_ENABLED = True
AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CLAIM_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_PRODUCTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_RESTORE_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_RESTORE_WHATIF_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_WRITE_PERFORMED = False

AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_REGISTRY_MAX_RECORDS = 4096


class AdDeletedObjectRestoreTicketConsumptionError(ValueError):
    pass


class AdDeletedObjectRestoreTicketConsumptionConflict(
    AdDeletedObjectRestoreTicketConsumptionError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreTicketConsumption:
    contract_version: str
    record_digest: str

    consumption_id: str
    state: str
    consumed: bool

    ticket_persistence_contract_version: str
    ticket_id: str
    ticket_digest: str

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

    issued_at: str
    expires_at: str
    consumed_at: str

    job_creation_authorized: bool
    claim_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    restore_authorized: bool
    restore_whatif_authorized: bool
    write_performed: bool


def _normalize_now(now: datetime | None) -> datetime:
    current = datetime.now(timezone.utc) if now is None else now

    if current.tzinfo is None:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "now must be timezone-aware"
        )

    return current.astimezone(timezone.utc)


def _parse_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AdDeletedObjectRestoreTicketConsumptionError(
            f"{field} is invalid"
        )

    try:
        parsed = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            f"{field} must be timezone-aware"
        )

    return parsed.astimezone(timezone.utc)


def _assert_uuid(value: Any, *, field: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            f"{field} is not a UUID"
        ) from exc


def _assert_sha256(value: Any, *, field: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(
            char not in "0123456789abcdef"
            for char in value.lower()
        )
    ):
        raise AdDeletedObjectRestoreTicketConsumptionError(
            f"{field} is not a SHA-256 digest"
        )


def _required_string(
    value: Any,
    *,
    field: str,
    max_length: int = 1024,
) -> str:
    if not isinstance(value, str):
        raise AdDeletedObjectRestoreTicketConsumptionError(
            f"{field} must be a string"
        )

    cleaned = value.strip()

    if not cleaned:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            f"{field} is required"
        )

    if len(cleaned) > max_length:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            f"{field} exceeds {max_length} characters"
        )

    return cleaned


def _canonical_sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def _record_digest_payload(
    record: AdDeletedObjectRestoreTicketConsumption,
) -> dict[str, Any]:
    payload = asdict(record)
    payload.pop("record_digest")
    return payload


def _assert_safe_path(path: Path) -> None:
    if not path.is_absolute():
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "storage path must be absolute"
        )

    if path.is_symlink():
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "storage path must not be a symlink"
        )

    current = path.parent

    while True:
        if current.is_symlink():
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "storage parent must not be a symlink"
            )

        if current == current.parent:
            break

        current = current.parent


def _open_flags(base_flags: int) -> int:
    flags = base_flags

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    return flags


@contextmanager
def _exclusive_registry_lock(storage_file: Path):
    lock_file = storage_file.with_name(
        "." + storage_file.name + ".lock"
    )

    _assert_safe_path(lock_file)

    try:
        fd = os.open(
            lock_file,
            _open_flags(os.O_CREAT | os.O_RDWR),
            0o600,
        )
    except OSError as exc:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "unable to open restore ticket consumption lock"
        ) from exc

    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "restore ticket consumption lock is not a regular file"
            )

        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _empty_registry() -> dict[str, Any]:
    return {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CONTRACT_VERSION,
        "records": [],
    }


def assert_ad_deleted_object_restore_ticket_consumption_invariants(
    record: AdDeletedObjectRestoreTicketConsumption,
) -> None:
    if not AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_ENABLED:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumption contract is disabled"
        )

    dangerous = (
        AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_JOB_CREATION_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CLAIM_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_RUNTIME_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_PRODUCTION_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_RESTORE_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_RESTORE_WHATIF_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_WRITE_PERFORMED,
    )

    if any(dangerous):
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "dangerous restore ticket consumption capability is enabled"
        )

    if (
        record.contract_version
        != AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumption contract mismatch"
        )

    if (
        record.ticket_persistence_contract_version
        != AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket persistence contract mismatch"
        )

    for value, field in (
        (record.consumption_id, "consumption_id"),
        (record.ticket_id, "ticket_id"),
        (record.source_simulation_job_id, "source_simulation_job_id"),
        (record.source_inventory_job_id, "source_inventory_job_id"),
        (record.source_live_job_id, "source_live_job_id"),
        (record.fresh_live_job_id, "fresh_live_job_id"),
        (record.object_guid, "object_guid"),
    ):
        _assert_uuid(value, field=field)

    for value, field in (
        (record.record_digest, "record_digest"),
        (record.ticket_digest, "ticket_digest"),
        (record.fresh_live_sha256, "fresh_live_sha256"),
    ):
        _assert_sha256(value, field=field)

    if record.state != "restore_ticket_consumed":
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumption state is invalid"
        )

    if record.consumed is not True:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket must be marked consumed"
        )

    for field in (
        "job_creation_authorized",
        "claim_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "restore_whatif_authorized",
        "write_performed",
    ):
        if getattr(record, field) is not False:
            raise AdDeletedObjectRestoreTicketConsumptionError(
                f"unsafe restore ticket consumption flag: {field}"
            )

    if _required_string(
        record.class_policy,
        field="class_policy",
        max_length=128,
    ) != "standard_controlled":
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket class policy is invalid"
        )

    _required_string(
        record.object_class,
        field="object_class",
        max_length=128,
    )
    _required_string(
        record.effective_new_name,
        field="effective_new_name",
    )
    _required_string(
        record.effective_target_path,
        field="effective_target_path",
    )

    issued_at = _parse_timestamp(
        record.issued_at,
        field="issued_at",
    )
    expires_at = _parse_timestamp(
        record.expires_at,
        field="expires_at",
    )
    consumed_at = _parse_timestamp(
        record.consumed_at,
        field="consumed_at",
    )

    if expires_at <= issued_at:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket expiration is invalid"
        )

    if consumed_at < issued_at:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumed before issue time"
        )

    if consumed_at >= expires_at:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "expired restore ticket cannot be consumed"
        )

    expected = _canonical_sha256(
        _record_digest_payload(record)
    )

    if record.record_digest != expected:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumption record digest mismatch"
        )


_RECORD_KEYS = {
    item.name
    for item in fields(
        AdDeletedObjectRestoreTicketConsumption
    )
}


def _validate_registry(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumption registry is invalid"
        )

    if (
        data.get("contract_version")
        != AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumption registry contract mismatch"
        )

    records = data.get("records")

    if not isinstance(records, list):
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumption records are invalid"
        )

    if (
        len(records)
        > AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_REGISTRY_MAX_RECORDS
    ):
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumption registry is full"
        )

    seen_consumption_ids: set[str] = set()
    seen_ticket_ids: set[str] = set()
    seen_ticket_digests: set[str] = set()

    for raw in records:
        if not isinstance(raw, dict):
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "restore ticket consumption record is invalid"
            )

        if set(raw) != _RECORD_KEYS:
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "restore ticket consumption record schema mismatch"
            )

        record = AdDeletedObjectRestoreTicketConsumption(
            **raw
        )

        assert_ad_deleted_object_restore_ticket_consumption_invariants(
            record
        )

        if record.consumption_id in seen_consumption_ids:
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "duplicate restore ticket consumption id"
            )

        if record.ticket_id in seen_ticket_ids:
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "duplicate consumed restore ticket id"
            )

        if record.ticket_digest in seen_ticket_digests:
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "duplicate consumed restore ticket digest"
            )

        seen_consumption_ids.add(record.consumption_id)
        seen_ticket_ids.add(record.ticket_id)
        seen_ticket_digests.add(record.ticket_digest)

    return data


def _load_registry(storage_file: Path) -> dict[str, Any]:
    if not storage_file.exists():
        return _empty_registry()

    _assert_safe_path(storage_file)

    try:
        fd = os.open(
            storage_file,
            _open_flags(os.O_RDONLY),
        )
    except OSError as exc:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "unable to open restore ticket consumption registry"
        ) from exc

    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "restore ticket consumption registry is not a regular file"
            )

        with os.fdopen(
            fd,
            "r",
            encoding="utf-8",
        ) as handle:
            fd = -1
            try:
                data = json.load(handle)
            except json.JSONDecodeError as exc:
                raise AdDeletedObjectRestoreTicketConsumptionError(
                    "restore ticket consumption registry JSON is invalid"
                ) from exc
    finally:
        if fd >= 0:
            os.close(fd)

    return _validate_registry(data)


def _atomic_write_registry(
    storage_file: Path,
    registry: dict[str, Any],
) -> None:
    _validate_registry(registry)
    _assert_safe_path(storage_file)

    parent = storage_file.parent
    parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(storage_file)

    fd, temporary_name = tempfile.mkstemp(
        prefix="." + storage_file.name + ".",
        suffix=".tmp",
        dir=parent,
    )
    temporary = Path(temporary_name)

    try:
        os.fchmod(fd, 0o600)

        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "temporary consumption registry is not a regular file"
            )

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            fd = -1
            json.dump(
                registry,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        _assert_safe_path(storage_file)
        os.replace(temporary, storage_file)
        os.chmod(storage_file, 0o600)

        directory_flags = os.O_RDONLY

        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY

        directory_fd = os.open(
            parent,
            _open_flags(directory_flags),
        )

        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    finally:
        if fd >= 0:
            os.close(fd)

        if temporary.exists():
            temporary.unlink()


def consume_ad_deleted_object_restore_ticket(
    ticket_record: AdDeletedObjectRestoreTicketPersistence,
    *,
    consumption_registry_file: Path,
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreTicketConsumption:
    if not AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_ENABLED:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumption contract is disabled"
        )

    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket consumption is Simulation-only"
        )

    try:
        assert_ad_deleted_object_restore_ticket_persistence_invariants(
            ticket_record
        )
    except AdDeletedObjectRestoreTicketPersistenceError as exc:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            str(exc)
        ) from exc

    if ticket_record.state != "restore_ticket_dormant":
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket must be dormant before consumption"
        )

    if ticket_record.status != "dormant":
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket status must be dormant before consumption"
        )

    if ticket_record.one_shot_required is not True:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket is not one-shot"
        )

    if ticket_record.replay_consumed is not False:
        raise AdDeletedObjectRestoreTicketConsumptionConflict(
            "restore ticket is already replay-consumed"
        )

    current = _normalize_now(now)

    issued_at = _parse_timestamp(
        ticket_record.issued_at,
        field="ticket.issued_at",
    )
    expires_at = _parse_timestamp(
        ticket_record.expires_at,
        field="ticket.expires_at",
    )

    if current < issued_at:
        raise AdDeletedObjectRestoreTicketConsumptionError(
            "restore ticket cannot be consumed before issue time"
        )

    if current >= expires_at:
        raise AdDeletedObjectRestoreTicketConsumptionConflict(
            "expired restore ticket cannot be consumed"
        )

    if not isinstance(consumption_registry_file, Path):
        consumption_registry_file = Path(
            consumption_registry_file
        )

    _assert_safe_path(consumption_registry_file)
    consumption_registry_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    _assert_safe_path(consumption_registry_file)

    with _exclusive_registry_lock(
        consumption_registry_file
    ):
        registry = _load_registry(
            consumption_registry_file
        )
        records = registry["records"]

        if (
            len(records)
            >= AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_REGISTRY_MAX_RECORDS
        ):
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "restore ticket consumption registry is full"
            )

        for existing in records:
            if existing["ticket_id"] == ticket_record.ticket_id:
                raise AdDeletedObjectRestoreTicketConsumptionConflict(
                    "restore ticket id is already consumed"
                )

            if existing["ticket_digest"] == ticket_record.ticket_digest:
                raise AdDeletedObjectRestoreTicketConsumptionConflict(
                    "restore ticket digest is already consumed"
                )

        locked_now = _normalize_now(now)

        if locked_now < issued_at:
            raise AdDeletedObjectRestoreTicketConsumptionError(
                "restore ticket cannot be consumed before issue time"
            )

        if locked_now >= expires_at:
            raise AdDeletedObjectRestoreTicketConsumptionConflict(
                "expired restore ticket cannot be consumed"
            )

        payload = {
            "contract_version":
                AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CONTRACT_VERSION,
            "consumption_id":
                str(uuid4()),
            "state":
                "restore_ticket_consumed",
            "consumed":
                True,
            "ticket_persistence_contract_version":
                ticket_record.contract_version,
            "ticket_id":
                ticket_record.ticket_id,
            "ticket_digest":
                ticket_record.ticket_digest,
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
            "issued_at":
                ticket_record.issued_at,
            "expires_at":
                ticket_record.expires_at,
            "consumed_at":
                locked_now.isoformat(),
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
            "write_performed":
                False,
        }

        record = AdDeletedObjectRestoreTicketConsumption(
            record_digest=_canonical_sha256(payload),
            **payload,
        )

        assert_ad_deleted_object_restore_ticket_consumption_invariants(
            record
        )

        records.append(
            asdict(record)
        )

        _atomic_write_registry(
            consumption_registry_file,
            registry,
        )

    return record


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CONTRACT_VERSION",
    "AdDeletedObjectRestoreTicketConsumption",
    "AdDeletedObjectRestoreTicketConsumptionConflict",
    "AdDeletedObjectRestoreTicketConsumptionError",
    "assert_ad_deleted_object_restore_ticket_consumption_invariants",
    "consume_ad_deleted_object_restore_ticket",
]
