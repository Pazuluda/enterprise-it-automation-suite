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

from app.services.ad_deleted_object_restore_ticket import (
    AD_DELETED_OBJECT_RESTORE_TICKET_CONTRACT_VERSION,
    AdDeletedObjectRestoreTicket,
    AdDeletedObjectRestoreTicketError,
    assert_ad_deleted_object_restore_ticket_invariants,
)


AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION = (
    "c9.5a4b2-v1"
)

AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_ENABLED = True
AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CLAIM_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_PRODUCTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_RESTORE_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_RESTORE_WHATIF_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_WRITE_PERFORMED = False

AD_DELETED_OBJECT_RESTORE_TICKET_REGISTRY_MAX_RECORDS = 4096


class AdDeletedObjectRestoreTicketPersistenceError(ValueError):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreTicketPersistence:
    contract_version: str
    record_digest: str

    ticket_contract_version: str
    ticket_id: str
    ticket_digest: str

    state: str
    status: str

    source_simulation_job_id: str
    source_inventory_job_id: str
    source_live_job_id: str
    source_live_completed_at: str

    fresh_live_job_id: str
    fresh_live_sha256: str
    fresh_live_completed_at: str

    object_guid: str
    object_class: str
    class_policy: str
    effective_new_name: str
    effective_target_path: str

    issued_at: str
    expires_at: str
    persisted_at: str

    one_shot_required: bool
    replay_consumed: bool

    persistence_enabled: bool
    route_enabled: bool
    job_creation_authorized: bool
    claim_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    restore_authorized: bool
    restore_whatif_authorized: bool
    write_performed: bool


def _normalize_now(now: datetime | None) -> datetime:
    current = (
        datetime.now(timezone.utc)
        if now is None
        else now
    )

    if current.tzinfo is None:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "now must be timezone-aware"
        )

    return current.astimezone(timezone.utc)


def _parse_timestamp(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AdDeletedObjectRestoreTicketPersistenceError(
            f"{field} is invalid"
        )

    try:
        parsed = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            f"{field} must be timezone-aware"
        )

    return parsed.astimezone(timezone.utc)


def _assert_uuid(value: Any, *, field: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise AdDeletedObjectRestoreTicketPersistenceError(
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
        raise AdDeletedObjectRestoreTicketPersistenceError(
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
    record: AdDeletedObjectRestoreTicketPersistence,
) -> dict[str, Any]:
    payload = asdict(record)
    payload.pop("record_digest")
    return payload


def _assert_safe_path(path: Path) -> None:
    if not path.is_absolute():
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "storage path must be absolute"
        )

    if path.is_symlink():
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "storage path must not be a symlink"
        )

    current = path.parent

    while True:
        if current.is_symlink():
            raise AdDeletedObjectRestoreTicketPersistenceError(
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
def _exclusive_lock(storage_file: Path):
    lock_file = storage_file.with_name(
        "." + storage_file.name + ".lock"
    )

    _assert_safe_path(lock_file)

    flags = _open_flags(
        os.O_CREAT | os.O_RDWR
    )

    try:
        fd = os.open(
            lock_file,
            flags,
            0o600,
        )
    except OSError as exc:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "unable to open restore ticket registry lock"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdDeletedObjectRestoreTicketPersistenceError(
                "restore ticket registry lock is not a regular file"
            )

        os.fchmod(
            fd,
            0o600,
        )

        fcntl.flock(
            fd,
            fcntl.LOCK_EX,
        )

        yield

    finally:
        try:
            fcntl.flock(
                fd,
                fcntl.LOCK_UN,
            )
        finally:
            os.close(fd)


def _empty_registry() -> dict[str, Any]:
    return {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION,

        "records":
            [],
    }


_RECORD_KEYS = {
    item.name
    for item in fields(
        AdDeletedObjectRestoreTicketPersistence
    )
}


def assert_ad_deleted_object_restore_ticket_persistence_invariants(
    record: AdDeletedObjectRestoreTicketPersistence,
) -> None:
    if not AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_ENABLED:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket persistence is disabled"
        )

    dangerous = (
        AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_ROUTE_ENABLED,
        AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_JOB_CREATION_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CLAIM_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_RUNTIME_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_PRODUCTION_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_RESTORE_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_RESTORE_WHATIF_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_WRITE_PERFORMED,
    )

    if any(dangerous):
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "dangerous restore ticket persistence capability enabled"
        )

    if (
        record.contract_version
        != AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket persistence contract mismatch"
        )

    if (
        record.ticket_contract_version
        != AD_DELETED_OBJECT_RESTORE_TICKET_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket contract mismatch"
        )

    _assert_uuid(
        record.ticket_id,
        field="ticket_id",
    )

    _assert_uuid(
        record.object_guid,
        field="object_guid",
    )

    for value, field in (
        (record.record_digest, "record_digest"),
        (record.ticket_digest, "ticket_digest"),
        (record.fresh_live_sha256, "fresh_live_sha256"),
    ):
        _assert_sha256(
            value,
            field=field,
        )

    for value, field in (
        (
            record.source_simulation_job_id,
            "source_simulation_job_id",
        ),
        (
            record.source_inventory_job_id,
            "source_inventory_job_id",
        ),
        (
            record.source_live_job_id,
            "source_live_job_id",
        ),
        (
            record.fresh_live_job_id,
            "fresh_live_job_id",
        ),
    ):
        _assert_uuid(
            value,
            field=field,
        )

    if (
        record.state != "restore_ticket_dormant"
        or record.status != "dormant"
    ):
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket persistence must remain dormant"
        )

    if record.one_shot_required is not True:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "persisted restore ticket must remain one-shot"
        )

    if record.replay_consumed is not False:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "dormant restore ticket cannot be replay-consumed"
        )

    if record.persistence_enabled is not True:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket persistence marker must be true"
        )

    for field in (
        "route_enabled",
        "job_creation_authorized",
        "claim_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "restore_whatif_authorized",
        "write_performed",
    ):
        if getattr(record, field) is not False:
            raise AdDeletedObjectRestoreTicketPersistenceError(
                f"unsafe persisted restore ticket flag: {field}"
            )

    issued_at = _parse_timestamp(
        record.issued_at,
        field="issued_at",
    )

    expires_at = _parse_timestamp(
        record.expires_at,
        field="expires_at",
    )

    persisted_at = _parse_timestamp(
        record.persisted_at,
        field="persisted_at",
    )

    source_live_completed_at = _parse_timestamp(
        record.source_live_completed_at,
        field="source_live_completed_at",
    )

    fresh_live_completed_at = _parse_timestamp(
        record.fresh_live_completed_at,
        field="fresh_live_completed_at",
    )

    if expires_at <= issued_at:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket expiration is invalid"
        )

    if persisted_at < issued_at:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket persisted before issue time"
        )

    if persisted_at >= expires_at:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "expired restore ticket cannot remain dormant"
        )

    if fresh_live_completed_at <= source_live_completed_at:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "fresh live binding is not newer than source live binding"
        )

    expected = _canonical_sha256(
        _record_digest_payload(
            record
        )
    )

    if record.record_digest != expected:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "persisted restore ticket record digest mismatch"
        )


def _validate_registry(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket registry is invalid"
        )

    if (
        data.get("contract_version")
        != AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket registry contract mismatch"
        )

    records = data.get("records")

    if not isinstance(records, list):
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket registry records are invalid"
        )

    if len(records) > AD_DELETED_OBJECT_RESTORE_TICKET_REGISTRY_MAX_RECORDS:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket registry is full"
        )

    seen_ids: set[str] = set()
    seen_digests: set[str] = set()

    for raw in records:
        if not isinstance(raw, dict):
            raise AdDeletedObjectRestoreTicketPersistenceError(
                "restore ticket registry record invalid"
            )

        if set(raw) != _RECORD_KEYS:
            raise AdDeletedObjectRestoreTicketPersistenceError(
                "restore ticket registry record schema mismatch"
            )

        record = AdDeletedObjectRestoreTicketPersistence(
            **raw
        )

        assert_ad_deleted_object_restore_ticket_persistence_invariants(
            record
        )

        if record.ticket_id in seen_ids:
            raise AdDeletedObjectRestoreTicketPersistenceError(
                "duplicate restore ticket id in registry"
            )

        if record.ticket_digest in seen_digests:
            raise AdDeletedObjectRestoreTicketPersistenceError(
                "duplicate restore ticket digest in registry"
            )

        seen_ids.add(
            record.ticket_id
        )

        seen_digests.add(
            record.ticket_digest
        )

    return data


def _load_registry(storage_file: Path) -> dict[str, Any]:
    if not storage_file.exists():
        return _empty_registry()

    _assert_safe_path(
        storage_file
    )

    try:
        flags = _open_flags(
            os.O_RDONLY
        )

        fd = os.open(
            storage_file,
            flags,
        )

    except OSError as exc:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "unable to open restore ticket registry"
        ) from exc

    try:
        info = os.fstat(fd)

        if not stat.S_ISREG(
            info.st_mode
        ):
            raise AdDeletedObjectRestoreTicketPersistenceError(
                "restore ticket registry is not a regular file"
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
                raise AdDeletedObjectRestoreTicketPersistenceError(
                    "restore ticket registry JSON is invalid"
                ) from exc

    finally:
        if fd >= 0:
            os.close(fd)

    return _validate_registry(
        data
    )


def _atomic_write_registry(
    storage_file: Path,
    registry: dict[str, Any],
) -> None:
    _validate_registry(
        registry
    )

    parent = storage_file.parent

    _assert_safe_path(
        storage_file
    )

    parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _assert_safe_path(
        storage_file
    )

    fd = -1

    try:
        fd, temporary_name = tempfile.mkstemp(
            prefix="." + storage_file.name + ".",
            suffix=".tmp",
            dir=parent,
            text=True,
        )

        temporary = Path(
            temporary_name
        )

        os.fchmod(
            fd,
            0o600,
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
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        _assert_safe_path(
            storage_file
        )

        os.replace(
            temporary,
            storage_file,
        )

        os.chmod(
            storage_file,
            0o600,
        )

        directory_flags = os.O_RDONLY

        if hasattr(
            os,
            "O_DIRECTORY",
        ):
            directory_flags |= os.O_DIRECTORY

        directory_flags = _open_flags(
            directory_flags
        )

        directory_fd = os.open(
            parent,
            directory_flags,
        )

        try:
            os.fsync(
                directory_fd
            )
        finally:
            os.close(
                directory_fd
            )

    finally:
        if fd >= 0:
            os.close(
                fd
            )

        temporary_value = locals().get(
            "temporary"
        )

        if (
            isinstance(
                temporary_value,
                Path,
            )
            and temporary_value.exists()
        ):
            temporary_value.unlink()


def persist_ad_deleted_object_restore_ticket(
    ticket: AdDeletedObjectRestoreTicket,
    *,
    storage_file: Path,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreTicketPersistence:
    if not AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_ENABLED:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket persistence is disabled"
        )

    if not isinstance(
        storage_file,
        Path,
    ):
        storage_file = Path(
            storage_file
        )

    try:
        assert_ad_deleted_object_restore_ticket_invariants(
            ticket
        )
    except AdDeletedObjectRestoreTicketError as exc:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            str(exc)
        ) from exc

    current = _normalize_now(
        now
    )

    issued_at = _parse_timestamp(
        ticket.issued_at,
        field="ticket.issued_at",
    )

    expires_at = _parse_timestamp(
        ticket.expires_at,
        field="ticket.expires_at",
    )

    if current < issued_at:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "restore ticket cannot be persisted before issue time"
        )

    if current >= expires_at:
        raise AdDeletedObjectRestoreTicketPersistenceError(
            "expired restore ticket cannot be persisted"
        )

    payload = {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION,

        "ticket_contract_version":
            ticket.contract_version,

        "ticket_id":
            ticket.ticket_id,

        "ticket_digest":
            ticket.ticket_digest,

        "state":
            "restore_ticket_dormant",

        "status":
            "dormant",

        "source_simulation_job_id":
            ticket.source_simulation_job_id,

        "source_inventory_job_id":
            ticket.source_inventory_job_id,

        "source_live_job_id":
            ticket.source_live_job_id,

        "source_live_completed_at":
            ticket.source_live_completed_at,

        "fresh_live_job_id":
            ticket.fresh_live_job_id,

        "fresh_live_sha256":
            ticket.fresh_live_sha256,

        "fresh_live_completed_at":
            ticket.fresh_live_completed_at,

        "object_guid":
            ticket.object_guid,

        "object_class":
            ticket.object_class,

        "class_policy":
            ticket.class_policy,

        "effective_new_name":
            ticket.effective_new_name,

        "effective_target_path":
            ticket.effective_target_path,

        "issued_at":
            ticket.issued_at,

        "expires_at":
            ticket.expires_at,

        "persisted_at":
            current.isoformat(),

        "one_shot_required":
            True,

        "replay_consumed":
            False,

        "persistence_enabled":
            True,

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

        "write_performed":
            False,
    }

    record = AdDeletedObjectRestoreTicketPersistence(
        record_digest=_canonical_sha256(
            payload
        ),
        **payload,
    )

    assert_ad_deleted_object_restore_ticket_persistence_invariants(
        record
    )

    _assert_safe_path(
        storage_file
    )

    storage_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _assert_safe_path(
        storage_file
    )

    with _exclusive_lock(
        storage_file
    ):
        registry = _load_registry(
            storage_file
        )

        records = registry["records"]

        if (
            len(records)
            >= AD_DELETED_OBJECT_RESTORE_TICKET_REGISTRY_MAX_RECORDS
        ):
            raise AdDeletedObjectRestoreTicketPersistenceError(
                "restore ticket registry is full"
            )

        for existing in records:
            if (
                existing["ticket_id"]
                == record.ticket_id
            ):
                raise AdDeletedObjectRestoreTicketPersistenceError(
                    "restore ticket id already persisted"
                )

            if (
                existing["ticket_digest"]
                == record.ticket_digest
            ):
                raise AdDeletedObjectRestoreTicketPersistenceError(
                    "restore ticket digest already persisted"
                )

        records.append(
            asdict(
                record
            )
        )

        _atomic_write_registry(
            storage_file,
            registry,
        )

    return record


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION",
    "AdDeletedObjectRestoreTicketPersistence",
    "AdDeletedObjectRestoreTicketPersistenceError",
    "assert_ad_deleted_object_restore_ticket_persistence_invariants",
    "persist_ad_deleted_object_restore_ticket",
]
