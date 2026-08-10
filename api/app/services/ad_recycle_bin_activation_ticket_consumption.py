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
from typing import Any, Mapping
from uuid import UUID, uuid4

from app.core.security import (
    OIDC_ALLOWED_AZP,
    OIDC_ISSUER,
)

from app.services.ad_recycle_bin_activation_ticket_persistence import (
    AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CONTRACT_VERSION,
    AdRecycleBinActivationTicketPersistence,
    AdRecycleBinActivationTicketPersistenceError,
    assert_ad_recycle_bin_activation_ticket_persistence_invariants,
)


AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_CONTRACT_VERSION = (
    "c9.4a2c-v1"
)

AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_ENABLED = True

AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_JOB_CREATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_RUNTIME_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_PRODUCTION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_ACTIVATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_RESTORE_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_WRITE_PERFORMED = False

AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_REGISTRY_MAX_RECORDS = 4096


class AdRecycleBinActivationTicketConsumptionError(
    ValueError
):
    pass


class AdRecycleBinActivationTicketConsumptionConflict(
    AdRecycleBinActivationTicketConsumptionError
):
    pass


@dataclass(frozen=True)
class AdRecycleBinActivationTicketConsumption:
    contract_version: str
    record_digest: str

    consumption_id: str

    state: str
    consumed: bool

    ticket_persistence_contract_version: str
    ticket_id: str
    ticket_digest: str

    source_intent_id: str
    source_intent_digest: str

    fresh_evidence_job_id: str
    fresh_evidence_sha256: str

    forest_name: str

    actor_subject: str
    actor_username: str
    actor_issuer: str
    actor_azp: str

    issued_at: str
    expires_at: str
    consumed_at: str

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
        raise AdRecycleBinActivationTicketConsumptionError(
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
        raise AdRecycleBinActivationTicketConsumptionError(
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
        raise AdRecycleBinActivationTicketConsumptionError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdRecycleBinActivationTicketConsumptionError(
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
        raise AdRecycleBinActivationTicketConsumptionError(
            f"{field} must be a string"
        )

    cleaned = value.strip()

    if not cleaned:
        raise AdRecycleBinActivationTicketConsumptionError(
            f"{field} is required"
        )

    if len(cleaned) > max_length:
        raise AdRecycleBinActivationTicketConsumptionError(
            f"{field} exceeds {max_length} characters"
        )

    return cleaned


def _assert_uuid(
    value: str,
    *,
    field: str,
) -> None:
    try:
        UUID(value)
    except (
        TypeError,
        ValueError,
        AttributeError,
    ) as exc:
        raise AdRecycleBinActivationTicketConsumptionError(
            f"{field} is not a UUID"
        ) from exc


def _assert_sha256(
    value: str,
    *,
    field: str,
) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(
            char not in "0123456789abcdef"
            for char in value.lower()
        )
    ):
        raise AdRecycleBinActivationTicketConsumptionError(
            f"{field} is not a SHA-256 digest"
        )


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


def _record_digest_payload(
    record: AdRecycleBinActivationTicketConsumption,
) -> dict[str, Any]:
    payload = asdict(record)
    payload.pop("record_digest")
    return payload


def _assert_safe_path(
    path: Path,
) -> None:
    if not path.is_absolute():
        raise AdRecycleBinActivationTicketConsumptionError(
            "consumption registry path must be absolute"
        )

    if path.is_symlink():
        raise AdRecycleBinActivationTicketConsumptionError(
            "consumption registry path must not be a symlink"
        )

    current = path.parent

    while True:
        if current.is_symlink():
            raise AdRecycleBinActivationTicketConsumptionError(
                "consumption registry parent must not be a symlink"
            )

        if current == current.parent:
            break

        current = current.parent


def _open_flags(
    base_flags: int,
) -> int:
    flags = base_flags

    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    return flags


@contextmanager
def _exclusive_registry_lock(
    registry_file: Path,
):
    lock_file = registry_file.with_name(
        "." + registry_file.name + ".lock"
    )

    _assert_safe_path(
        lock_file
    )

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
        raise AdRecycleBinActivationTicketConsumptionError(
            "unable to open consumption registry lock"
        ) from exc

    try:
        mode = os.fstat(fd).st_mode

        if not stat.S_ISREG(mode):
            raise AdRecycleBinActivationTicketConsumptionError(
                "consumption registry lock is not a regular file"
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


def _assert_same_actor(
    ticket: AdRecycleBinActivationTicketPersistence,
    server_actor: Mapping[str, Any],
) -> None:
    if not isinstance(
        server_actor,
        Mapping,
    ):
        raise AdRecycleBinActivationTicketConsumptionError(
            "server actor is invalid"
        )

    subject = _required_string(
        server_actor.get("subject"),
        field="server_actor.subject",
        max_length=256,
    )

    username = _required_string(
        server_actor.get("username"),
        field="server_actor.username",
        max_length=128,
    )

    issuer = _required_string(
        server_actor.get("issuer"),
        field="server_actor.issuer",
    )

    azp = _required_string(
        server_actor.get("azp"),
        field="server_actor.azp",
        max_length=128,
    )

    if issuer != OIDC_ISSUER:
        raise AdRecycleBinActivationTicketConsumptionConflict(
            "OIDC issuer mismatch"
        )

    if (
        OIDC_ALLOWED_AZP
        and azp not in OIDC_ALLOWED_AZP
    ):
        raise AdRecycleBinActivationTicketConsumptionConflict(
            "OIDC azp is not allowed"
        )

    bindings = {
        "actor_subject": subject,
        "actor_username": username,
        "actor_issuer": issuer,
        "actor_azp": azp,
    }

    for field, current_value in bindings.items():
        if getattr(ticket, field) != current_value:
            raise AdRecycleBinActivationTicketConsumptionConflict(
                f"actor mismatch: {field}"
            )


def assert_ad_recycle_bin_activation_ticket_consumption_invariants(
    record: AdRecycleBinActivationTicketConsumption,
) -> None:
    if not AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_ENABLED:
        raise AdRecycleBinActivationTicketConsumptionError(
            "ticket consumption contract is disabled"
        )

    if any(
        (
            AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_JOB_CREATION_AUTHORIZED,
            AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_RUNTIME_AUTHORIZED,
            AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_PRODUCTION_AUTHORIZED,
            AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_ACTIVATION_AUTHORIZED,
            AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_RESTORE_AUTHORIZED,
            AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_WRITE_PERFORMED,
        )
    ):
        raise AdRecycleBinActivationTicketConsumptionError(
            "dangerous ticket consumption capability is enabled"
        )

    if (
        record.contract_version
        != AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationTicketConsumptionError(
            "consumption contract version mismatch"
        )

    if (
        record.ticket_persistence_contract_version
        != AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationTicketConsumptionError(
            "ticket persistence contract version mismatch"
        )

    _assert_uuid(
        record.consumption_id,
        field="consumption_id",
    )

    _assert_uuid(
        record.ticket_id,
        field="ticket_id",
    )

    _assert_uuid(
        record.source_intent_id,
        field="source_intent_id",
    )

    for field in (
        "record_digest",
        "ticket_digest",
        "source_intent_digest",
        "fresh_evidence_sha256",
    ):
        _assert_sha256(
            getattr(record, field),
            field=field,
        )

    if record.state != "activation_ticket_consumed":
        raise AdRecycleBinActivationTicketConsumptionError(
            "consumption state is invalid"
        )

    if record.consumed is not True:
        raise AdRecycleBinActivationTicketConsumptionError(
            "consumption marker must be true"
        )

    false_fields = (
        "job_creation_authorized",
        "runtime_authorized",
        "production_authorized",
        "activation_authorized",
        "restore_authorized",
        "write_performed",
    )

    for field in false_fields:
        if getattr(record, field) is not False:
            raise AdRecycleBinActivationTicketConsumptionError(
                f"unsafe consumption flag: {field}"
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
        raise AdRecycleBinActivationTicketConsumptionError(
            "ticket expiration is invalid"
        )

    if consumed_at < issued_at:
        raise AdRecycleBinActivationTicketConsumptionError(
            "ticket consumed before issue time"
        )

    if consumed_at >= expires_at:
        raise AdRecycleBinActivationTicketConsumptionError(
            "expired ticket cannot be consumed"
        )

    expected_digest = _canonical_sha256(
        _record_digest_payload(record)
    )

    if record.record_digest != expected_digest:
        raise AdRecycleBinActivationTicketConsumptionError(
            "consumption record digest mismatch"
        )


_RECORD_KEYS = {
    field.name
    for field in fields(
        AdRecycleBinActivationTicketConsumption
    )
}


def _validate_registry(
    data: Any,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AdRecycleBinActivationTicketConsumptionError(
            "consumption registry is invalid"
        )

    if (
        data.get("contract_version")
        != AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationTicketConsumptionError(
            "consumption registry contract version mismatch"
        )

    records = data.get("records")

    if not isinstance(records, list):
        raise AdRecycleBinActivationTicketConsumptionError(
            "consumption registry records are invalid"
        )

    if (
        len(records)
        > AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_REGISTRY_MAX_RECORDS
    ):
        raise AdRecycleBinActivationTicketConsumptionError(
            "consumption registry is full"
        )

    seen_consumption_ids = set()
    seen_ticket_ids = set()
    seen_ticket_digests = set()

    for raw in records:
        if not isinstance(raw, dict):
            raise AdRecycleBinActivationTicketConsumptionError(
                "consumption registry record is invalid"
            )

        if set(raw.keys()) != _RECORD_KEYS:
            raise AdRecycleBinActivationTicketConsumptionError(
                "consumption registry record schema mismatch"
            )

        record = AdRecycleBinActivationTicketConsumption(
            **raw
        )

        assert_ad_recycle_bin_activation_ticket_consumption_invariants(
            record
        )

        if record.consumption_id in seen_consumption_ids:
            raise AdRecycleBinActivationTicketConsumptionError(
                "duplicate consumption id in registry"
            )

        if record.ticket_id in seen_ticket_ids:
            raise AdRecycleBinActivationTicketConsumptionError(
                "duplicate ticket id in consumption registry"
            )

        if record.ticket_digest in seen_ticket_digests:
            raise AdRecycleBinActivationTicketConsumptionError(
                "duplicate ticket digest in consumption registry"
            )

        seen_consumption_ids.add(
            record.consumption_id
        )

        seen_ticket_ids.add(
            record.ticket_id
        )

        seen_ticket_digests.add(
            record.ticket_digest
        )

    return data


def _load_registry(
    registry_file: Path,
) -> dict[str, Any]:
    _assert_safe_path(
        registry_file
    )

    if not registry_file.exists():
        return {
            "contract_version":
                AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_CONTRACT_VERSION,
            "records": [],
        }

    flags = _open_flags(
        os.O_RDONLY
    )

    try:
        fd = os.open(
            registry_file,
            flags,
        )
    except OSError as exc:
        raise AdRecycleBinActivationTicketConsumptionError(
            "unable to open consumption registry"
        ) from exc

    try:
        mode = os.fstat(fd).st_mode

        if not stat.S_ISREG(mode):
            raise AdRecycleBinActivationTicketConsumptionError(
                "consumption registry is not a regular file"
            )

        with os.fdopen(
            fd,
            "r",
            encoding="utf-8",
        ) as handle:
            fd = -1

            try:
                data = json.load(
                    handle
                )
            except json.JSONDecodeError as exc:
                raise AdRecycleBinActivationTicketConsumptionError(
                    "consumption registry JSON is invalid"
                ) from exc

    finally:
        if fd >= 0:
            os.close(fd)

    return _validate_registry(
        data
    )


def _atomic_write_registry(
    registry_file: Path,
    data: dict[str, Any],
) -> None:
    _assert_safe_path(
        registry_file
    )

    parent = registry_file.parent

    parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _assert_safe_path(
        registry_file
    )

    fd, temporary_name = tempfile.mkstemp(
        prefix="." + registry_file.name + ".",
        suffix=".tmp",
        dir=str(parent),
    )

    temporary = Path(
        temporary_name
    )

    try:
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
                data,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )

            handle.write("\n")
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        _assert_safe_path(
            registry_file
        )

        os.replace(
            temporary,
            registry_file,
        )

        os.chmod(
            registry_file,
            0o600,
        )

        directory_flags = os.O_RDONLY

        if hasattr(os, "O_DIRECTORY"):
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
            os.close(fd)

        if temporary.exists():
            temporary.unlink()


def consume_ad_recycle_bin_activation_ticket(
    ticket_record: AdRecycleBinActivationTicketPersistence,
    *,
    consumption_registry_file: Path,
    server_actor: Mapping[str, Any],
    current_mode: str,
    now: datetime | None = None,
) -> AdRecycleBinActivationTicketConsumption:
    if not AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_ENABLED:
        raise AdRecycleBinActivationTicketConsumptionError(
            "ticket consumption contract is disabled"
        )

    if current_mode != "Simulation":
        raise AdRecycleBinActivationTicketConsumptionError(
            "ticket consumption is Simulation-only"
        )

    try:
        assert_ad_recycle_bin_activation_ticket_persistence_invariants(
            ticket_record
        )
    except AdRecycleBinActivationTicketPersistenceError as exc:
        raise AdRecycleBinActivationTicketConsumptionError(
            str(exc)
        ) from exc

    if ticket_record.state != "activation_ticket_dormant":
        raise AdRecycleBinActivationTicketConsumptionError(
            "ticket must be dormant before consumption"
        )

    if ticket_record.status != "dormant":
        raise AdRecycleBinActivationTicketConsumptionError(
            "ticket status must be dormant before consumption"
        )

    if ticket_record.one_shot_required is not True:
        raise AdRecycleBinActivationTicketConsumptionError(
            "ticket is not one-shot"
        )

    if ticket_record.replay_consumed is not False:
        raise AdRecycleBinActivationTicketConsumptionConflict(
            "ticket is already replay-consumed"
        )

    _assert_same_actor(
        ticket_record,
        server_actor,
    )

    current = _normalize_now(
        now
    )

    issued_at = _parse_timestamp(
        ticket_record.issued_at,
        field="ticket.issued_at",
    )

    expires_at = _parse_timestamp(
        ticket_record.expires_at,
        field="ticket.expires_at",
    )

    if current < issued_at:
        raise AdRecycleBinActivationTicketConsumptionError(
            "ticket cannot be consumed before issue time"
        )

    if current >= expires_at:
        raise AdRecycleBinActivationTicketConsumptionConflict(
            "expired ticket cannot be consumed"
        )

    if not isinstance(
        consumption_registry_file,
        Path,
    ):
        consumption_registry_file = Path(
            consumption_registry_file
        )

    _assert_safe_path(
        consumption_registry_file
    )

    consumption_registry_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _assert_safe_path(
        consumption_registry_file
    )

    with _exclusive_registry_lock(
        consumption_registry_file
    ):
        registry = _load_registry(
            consumption_registry_file
        )

        records = registry["records"]

        if (
            len(records)
            >= AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_REGISTRY_MAX_RECORDS
        ):
            raise AdRecycleBinActivationTicketConsumptionError(
                "consumption registry is full"
            )

        for existing in records:
            if existing["ticket_id"] == ticket_record.ticket_id:
                raise AdRecycleBinActivationTicketConsumptionConflict(
                    "ticket id is already consumed"
                )

            if existing["ticket_digest"] == ticket_record.ticket_digest:
                raise AdRecycleBinActivationTicketConsumptionConflict(
                    "ticket digest is already consumed"
                )

        # Recheck time only after acquiring the same lock used
        # for the replay decision and append.
        locked_now = _normalize_now(
            now
        )

        if locked_now < issued_at:
            raise AdRecycleBinActivationTicketConsumptionError(
                "ticket cannot be consumed before issue time"
            )

        if locked_now >= expires_at:
            raise AdRecycleBinActivationTicketConsumptionConflict(
                "expired ticket cannot be consumed"
            )

        payload = {
            "contract_version":
                AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_CONTRACT_VERSION,

            "consumption_id":
                str(uuid4()),

            "state":
                "activation_ticket_consumed",

            "consumed":
                True,

            "ticket_persistence_contract_version":
                ticket_record.contract_version,

            "ticket_id":
                ticket_record.ticket_id,

            "ticket_digest":
                ticket_record.ticket_digest,

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

            "actor_subject":
                ticket_record.actor_subject,

            "actor_username":
                ticket_record.actor_username,

            "actor_issuer":
                ticket_record.actor_issuer,

            "actor_azp":
                ticket_record.actor_azp,

            "issued_at":
                ticket_record.issued_at,

            "expires_at":
                ticket_record.expires_at,

            "consumed_at":
                locked_now.isoformat(),

            "job_creation_authorized":
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

        record_digest = _canonical_sha256(
            payload
        )

        record = AdRecycleBinActivationTicketConsumption(
            record_digest=record_digest,
            **payload,
        )

        assert_ad_recycle_bin_activation_ticket_consumption_invariants(
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
    "AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_CONTRACT_VERSION",
    "AdRecycleBinActivationTicketConsumption",
    "AdRecycleBinActivationTicketConsumptionConflict",
    "AdRecycleBinActivationTicketConsumptionError",
    "assert_ad_recycle_bin_activation_ticket_consumption_invariants",
    "consume_ad_recycle_bin_activation_ticket",
]
