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

from app.services.ad_recycle_bin_activation_ticket import (
    AD_RECYCLE_BIN_ACTIVATION_TICKET_CONTRACT_VERSION,
    AdRecycleBinActivationTicket,
    AdRecycleBinActivationTicketError,
    assert_ad_recycle_bin_activation_ticket_invariants,
)

AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CONTRACT_VERSION = "c9.4a2b-v1"
AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_ENABLED = True
AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_JOB_CREATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CLAIM_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_RUNTIME_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_PRODUCTION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_ACTIVATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_RESTORE_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_WRITE_PERFORMED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_REGISTRY_MAX_RECORDS = 4096


class AdRecycleBinActivationTicketPersistenceError(ValueError):
    pass


@dataclass(frozen=True)
class AdRecycleBinActivationTicketPersistence:
    contract_version: str
    record_digest: str
    ticket_contract_version: str
    ticket_id: str
    ticket_digest: str
    state: str
    status: str
    source_intent_id: str
    source_intent_digest: str
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
    persisted_at: str
    one_shot_required: bool
    replay_consumed: bool
    persistence_enabled: bool
    job_creation_authorized: bool
    claim_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    activation_authorized: bool
    restore_authorized: bool
    write_performed: bool


def _normalize_now(now: datetime | None) -> datetime:
    current = datetime.now(timezone.utc) if now is None else now
    if current.tzinfo is None:
        raise AdRecycleBinActivationTicketPersistenceError("now must be timezone-aware")
    return current.astimezone(timezone.utc)


def _parse_timestamp(value: str, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AdRecycleBinActivationTicketPersistenceError(f"{field} is invalid")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdRecycleBinActivationTicketPersistenceError(f"{field} is invalid") from exc
    if parsed.tzinfo is None:
        raise AdRecycleBinActivationTicketPersistenceError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _assert_uuid(value: str, *, field: str) -> None:
    try:
        UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise AdRecycleBinActivationTicketPersistenceError(f"{field} is not a UUID") from exc


def _assert_sha256(value: str, *, field: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower()):
        raise AdRecycleBinActivationTicketPersistenceError(f"{field} is not a SHA-256 digest")


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _record_digest_payload(record: AdRecycleBinActivationTicketPersistence) -> dict[str, Any]:
    payload = asdict(record)
    payload.pop("record_digest")
    return payload


def _assert_safe_path(path: Path) -> None:
    if not path.is_absolute():
        raise AdRecycleBinActivationTicketPersistenceError("storage path must be absolute")
    if path.is_symlink():
        raise AdRecycleBinActivationTicketPersistenceError("storage path must not be a symlink")
    current = path.parent
    while True:
        if current.is_symlink():
            raise AdRecycleBinActivationTicketPersistenceError("storage parent must not be a symlink")
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
    lock_file = storage_file.with_name("." + storage_file.name + ".lock")
    _assert_safe_path(lock_file)
    flags = _open_flags(os.O_CREAT | os.O_RDWR)
    try:
        fd = os.open(lock_file, flags, 0o600)
    except OSError as exc:
        raise AdRecycleBinActivationTicketPersistenceError("unable to open ticket registry lock") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise AdRecycleBinActivationTicketPersistenceError("ticket registry lock is not a regular file")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def assert_ad_recycle_bin_activation_ticket_persistence_invariants(record: AdRecycleBinActivationTicketPersistence) -> None:
    if not AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_ENABLED:
        raise AdRecycleBinActivationTicketPersistenceError("ticket persistence is disabled")
    dangerous = (
        AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_JOB_CREATION_AUTHORIZED,
        AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CLAIM_AUTHORIZED,
        AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_RUNTIME_AUTHORIZED,
        AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_PRODUCTION_AUTHORIZED,
        AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_ACTIVATION_AUTHORIZED,
        AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_RESTORE_AUTHORIZED,
        AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_WRITE_PERFORMED,
    )
    if any(dangerous):
        raise AdRecycleBinActivationTicketPersistenceError("dangerous ticket persistence capability is enabled")
    if record.contract_version != AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CONTRACT_VERSION:
        raise AdRecycleBinActivationTicketPersistenceError("ticket persistence contract version mismatch")
    if record.ticket_contract_version != AD_RECYCLE_BIN_ACTIVATION_TICKET_CONTRACT_VERSION:
        raise AdRecycleBinActivationTicketPersistenceError("ticket contract version mismatch")
    _assert_uuid(record.ticket_id, field="ticket_id")
    _assert_uuid(record.source_intent_id, field="source_intent_id")
    for name in ("record_digest", "ticket_digest", "source_intent_digest", "source_evidence_sha256", "fresh_evidence_sha256"):
        _assert_sha256(getattr(record, name), field=name)
    if record.state != "activation_ticket_dormant":
        raise AdRecycleBinActivationTicketPersistenceError("ticket persistence state must remain dormant")
    if record.status != "dormant":
        raise AdRecycleBinActivationTicketPersistenceError("ticket persistence status must remain dormant")
    if record.one_shot_required is not True:
        raise AdRecycleBinActivationTicketPersistenceError("ticket must remain one-shot")
    if record.replay_consumed is not False:
        raise AdRecycleBinActivationTicketPersistenceError("dormant ticket must not be replay-consumed")
    if record.persistence_enabled is not True:
        raise AdRecycleBinActivationTicketPersistenceError("persistence marker must be true")
    for field in ("job_creation_authorized", "claim_authorized", "runtime_authorized", "production_authorized", "activation_authorized", "restore_authorized", "write_performed"):
        if getattr(record, field) is not False:
            raise AdRecycleBinActivationTicketPersistenceError(f"unsafe persisted ticket flag: {field}")
    issued_at = _parse_timestamp(record.issued_at, field="issued_at")
    expires_at = _parse_timestamp(record.expires_at, field="expires_at")
    persisted_at = _parse_timestamp(record.persisted_at, field="persisted_at")
    if expires_at <= issued_at:
        raise AdRecycleBinActivationTicketPersistenceError("ticket expiration is invalid")
    if persisted_at < issued_at:
        raise AdRecycleBinActivationTicketPersistenceError("ticket persisted before issue time")
    if persisted_at >= expires_at:
        raise AdRecycleBinActivationTicketPersistenceError("expired ticket cannot remain dormant")
    expected = _canonical_sha256(_record_digest_payload(record))
    if record.record_digest != expected:
        raise AdRecycleBinActivationTicketPersistenceError("persisted ticket record digest mismatch")


_RECORD_KEYS = {item.name for item in fields(AdRecycleBinActivationTicketPersistence)}


def _validate_registry(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AdRecycleBinActivationTicketPersistenceError("ticket registry is invalid")
    if data.get("contract_version") != AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CONTRACT_VERSION:
        raise AdRecycleBinActivationTicketPersistenceError("ticket registry contract version mismatch")
    records = data.get("records")
    if not isinstance(records, list):
        raise AdRecycleBinActivationTicketPersistenceError("ticket registry records are invalid")
    if len(records) > AD_RECYCLE_BIN_ACTIVATION_TICKET_REGISTRY_MAX_RECORDS:
        raise AdRecycleBinActivationTicketPersistenceError("ticket registry is full")
    seen_ids = set()
    seen_digests = set()
    for raw in records:
        if not isinstance(raw, dict):
            raise AdRecycleBinActivationTicketPersistenceError("ticket registry record is invalid")
        if set(raw.keys()) != _RECORD_KEYS:
            raise AdRecycleBinActivationTicketPersistenceError("ticket registry record schema mismatch")
        record = AdRecycleBinActivationTicketPersistence(**raw)
        assert_ad_recycle_bin_activation_ticket_persistence_invariants(record)
        if record.ticket_id in seen_ids:
            raise AdRecycleBinActivationTicketPersistenceError("duplicate ticket id in registry")
        if record.ticket_digest in seen_digests:
            raise AdRecycleBinActivationTicketPersistenceError("duplicate ticket digest in registry")
        seen_ids.add(record.ticket_id)
        seen_digests.add(record.ticket_digest)
    return data


def _load_registry(storage_file: Path) -> dict[str, Any]:
    _assert_safe_path(storage_file)
    if not storage_file.exists():
        return {"contract_version": AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CONTRACT_VERSION, "records": []}
    flags = _open_flags(os.O_RDONLY)
    try:
        fd = os.open(storage_file, flags)
    except OSError as exc:
        raise AdRecycleBinActivationTicketPersistenceError("unable to open ticket registry") from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise AdRecycleBinActivationTicketPersistenceError("ticket registry is not a regular file")
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            fd = -1
            try:
                data = json.load(handle)
            except json.JSONDecodeError as exc:
                raise AdRecycleBinActivationTicketPersistenceError("ticket registry JSON is invalid") from exc
    finally:
        if fd >= 0:
            os.close(fd)
    return _validate_registry(data)


def _atomic_write_registry(storage_file: Path, data: dict[str, Any]) -> None:
    _assert_safe_path(storage_file)
    parent = storage_file.parent
    parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(storage_file)
    fd, temporary_name = tempfile.mkstemp(prefix="." + storage_file.name + ".", suffix=".tmp", dir=str(parent))
    temporary = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        _assert_safe_path(storage_file)
        os.replace(temporary, storage_file)
        os.chmod(storage_file, 0o600)
        directory_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY
        directory_flags = _open_flags(directory_flags)
        directory_fd = os.open(parent, directory_flags)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary.exists():
            temporary.unlink()


def persist_ad_recycle_bin_activation_ticket(ticket: AdRecycleBinActivationTicket, *, storage_file: Path, now: datetime | None = None) -> AdRecycleBinActivationTicketPersistence:
    if not AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_ENABLED:
        raise AdRecycleBinActivationTicketPersistenceError("ticket persistence is disabled")
    if not isinstance(storage_file, Path):
        storage_file = Path(storage_file)
    try:
        assert_ad_recycle_bin_activation_ticket_invariants(ticket)
    except AdRecycleBinActivationTicketError as exc:
        raise AdRecycleBinActivationTicketPersistenceError(str(exc)) from exc
    current = _normalize_now(now)
    issued_at = _parse_timestamp(ticket.issued_at, field="ticket.issued_at")
    expires_at = _parse_timestamp(ticket.expires_at, field="ticket.expires_at")
    if current < issued_at:
        raise AdRecycleBinActivationTicketPersistenceError("ticket cannot be persisted before issue time")
    if current >= expires_at:
        raise AdRecycleBinActivationTicketPersistenceError("expired ticket cannot be persisted")
    payload = {
        "contract_version": AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CONTRACT_VERSION,
        "ticket_contract_version": ticket.contract_version,
        "ticket_id": ticket.ticket_id,
        "ticket_digest": ticket.ticket_digest,
        "state": "activation_ticket_dormant",
        "status": "dormant",
        "source_intent_id": ticket.source_intent_id,
        "source_intent_digest": ticket.source_intent_digest,
        "source_evidence_sha256": ticket.source_evidence_sha256,
        "source_evidence_created_at": ticket.source_evidence_created_at,
        "fresh_evidence_job_id": ticket.fresh_evidence_job_id,
        "fresh_evidence_sha256": ticket.fresh_evidence_sha256,
        "fresh_evidence_created_at": ticket.fresh_evidence_created_at,
        "forest_name": ticket.forest_name,
        "root_domain": ticket.root_domain,
        "forest_mode": ticket.forest_mode,
        "actor_subject": ticket.actor_subject,
        "actor_username": ticket.actor_username,
        "actor_issuer": ticket.actor_issuer,
        "actor_azp": ticket.actor_azp,
        "issued_at": ticket.issued_at,
        "expires_at": ticket.expires_at,
        "persisted_at": current.isoformat(),
        "one_shot_required": True,
        "replay_consumed": False,
        "persistence_enabled": True,
        "job_creation_authorized": False,
        "claim_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "activation_authorized": False,
        "restore_authorized": False,
        "write_performed": False,
    }
    record = AdRecycleBinActivationTicketPersistence(record_digest=_canonical_sha256(payload), **payload)
    assert_ad_recycle_bin_activation_ticket_persistence_invariants(record)
    _assert_safe_path(storage_file)
    storage_file.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(storage_file)
    with _exclusive_lock(storage_file):
        registry = _load_registry(storage_file)
        records = registry["records"]
        if len(records) >= AD_RECYCLE_BIN_ACTIVATION_TICKET_REGISTRY_MAX_RECORDS:
            raise AdRecycleBinActivationTicketPersistenceError("ticket registry is full")
        for existing in records:
            if existing["ticket_id"] == record.ticket_id:
                raise AdRecycleBinActivationTicketPersistenceError("ticket id already persisted")
            if existing["ticket_digest"] == record.ticket_digest:
                raise AdRecycleBinActivationTicketPersistenceError("ticket digest already persisted")
        records.append(asdict(record))
        _atomic_write_registry(storage_file, registry)
    return record


__all__ = [
    "AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CONTRACT_VERSION",
    "AdRecycleBinActivationTicketPersistence",
    "AdRecycleBinActivationTicketPersistenceError",
    "assert_ad_recycle_bin_activation_ticket_persistence_invariants",
    "persist_ad_recycle_bin_activation_ticket",
]
