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

from app.services.ad_recycle_bin_activation_authorization import (
    AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONTRACT_VERSION,
    AdRecycleBinActivationAuthorization,
    AdRecycleBinActivationAuthorizationError,
    assert_ad_recycle_bin_activation_authorization_invariants,
)


AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION = (
    "c9.4a2d-a3-v1"
)

AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_ENABLED = True

AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_ROUTE_ENABLED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_JOB_CREATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_RUNTIME_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_PRODUCTION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_ACTIVATION_AUTHORIZED = True
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_RESTORE_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_WRITE_PERFORMED = False

AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_REGISTRY_MAX_RECORDS = 4096


class AdRecycleBinActivationAuthorizationPersistenceError(
    ValueError
):
    pass


@dataclass(frozen=True)
class AdRecycleBinActivationAuthorizationPersistence:
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
    persisted_at: str

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


def _normalize_now(
    now: datetime | None,
) -> datetime:
    current = (
        datetime.now(timezone.utc)
        if now is None
        else now
    )

    if current.tzinfo is None:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
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
        raise AdRecycleBinActivationAuthorizationPersistenceError(
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
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            f"{field} must be timezone-aware"
        )

    return parsed.astimezone(
        timezone.utc
    )


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
        raise AdRecycleBinActivationAuthorizationPersistenceError(
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
        raise AdRecycleBinActivationAuthorizationPersistenceError(
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
    record: AdRecycleBinActivationAuthorizationPersistence,
) -> dict[str, Any]:
    payload = asdict(record)
    payload.pop("record_digest")
    return payload


def _assert_safe_path(
    path: Path,
) -> None:
    if not path.is_absolute():
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization registry path must be absolute"
        )

    if path.is_symlink():
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization registry path must not be a symlink"
        )

    current = path.parent

    while True:
        if current.is_symlink():
            raise AdRecycleBinActivationAuthorizationPersistenceError(
                "authorization registry parent must not be a symlink"
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
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "unable to open authorization registry lock"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdRecycleBinActivationAuthorizationPersistenceError(
                "authorization registry lock is not a regular file"
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


def assert_ad_recycle_bin_activation_authorization_persistence_invariants(
    record: AdRecycleBinActivationAuthorizationPersistence,
) -> None:
    if not AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_ENABLED:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization persistence is disabled"
        )

    if (
        record.contract_version
        != AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization persistence contract version mismatch"
        )

    if (
        record.authorization_contract_version
        != AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization contract version mismatch"
        )

    for field in (
        "authorization_id",
        "ticket_id",
        "consumption_id",
        "source_intent_id",
    ):
        _assert_uuid(
            getattr(record, field),
            field=field,
        )

    for field in (
        "record_digest",
        "authorization_digest",
        "ticket_digest",
        "consumption_record_digest",
        "source_intent_digest",
        "fresh_evidence_sha256",
    ):
        _assert_sha256(
            getattr(record, field),
            field=field,
        )

    if record.state != "activation_authorization_dormant":
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization persistence state must remain dormant"
        )

    if record.status != "authorized":
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization persistence status is invalid"
        )

    if record.one_shot_required is not True:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization must remain one-shot"
        )

    if record.authorization_consumed is not False:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "persisted authorization must remain unconsumed"
        )

    if record.human_authorized is not True:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "human authorization marker must remain true"
        )

    if record.persistence_enabled is not True:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization persistence marker must be true"
        )

    if record.activation_authorized is not True:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "human activation authorization marker must remain true"
        )

    false_fields = (
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
            raise AdRecycleBinActivationAuthorizationPersistenceError(
                f"unsafe persisted authorization flag: {field}"
            )

    if record.acknowledge_forest_wide is not True:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "forest-wide acknowledgement must remain true"
        )

    if record.acknowledge_irreversible is not True:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "irreversible acknowledgement must remain true"
        )

    if record.acknowledge_no_restore is not True:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "no-restore acknowledgement must remain true"
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

    if expires_at <= issued_at:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization expiration is invalid"
        )

    if persisted_at < issued_at:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization persisted before issue time"
        )

    if persisted_at >= expires_at:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "expired authorization cannot remain dormant"
        )

    expected_digest = _canonical_sha256(
        _record_digest_payload(
            record
        )
    )

    if record.record_digest != expected_digest:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization persistence record digest mismatch"
        )


_RECORD_KEYS = {
    item.name
    for item in fields(
        AdRecycleBinActivationAuthorizationPersistence
    )
}


def _validate_registry(
    data: Any,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization registry is invalid"
        )

    if (
        data.get("contract_version")
        != AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization registry contract version mismatch"
        )

    records = data.get("records")

    if not isinstance(records, list):
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization registry records are invalid"
        )

    if (
        len(records)
        > AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_REGISTRY_MAX_RECORDS
    ):
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization registry is full"
        )

    seen_authorization_ids = set()
    seen_authorization_digests = set()
    seen_ticket_ids = set()
    seen_ticket_digests = set()
    seen_consumption_ids = set()

    for raw in records:
        if not isinstance(raw, dict):
            raise AdRecycleBinActivationAuthorizationPersistenceError(
                "authorization registry record is invalid"
            )

        if set(raw.keys()) != _RECORD_KEYS:
            raise AdRecycleBinActivationAuthorizationPersistenceError(
                "authorization registry record schema mismatch"
            )

        record = AdRecycleBinActivationAuthorizationPersistence(
            **raw
        )

        assert_ad_recycle_bin_activation_authorization_persistence_invariants(
            record
        )

        unique_bindings = (
            (
                "authorization id",
                record.authorization_id,
                seen_authorization_ids,
            ),
            (
                "authorization digest",
                record.authorization_digest,
                seen_authorization_digests,
            ),
            (
                "ticket id",
                record.ticket_id,
                seen_ticket_ids,
            ),
            (
                "ticket digest",
                record.ticket_digest,
                seen_ticket_digests,
            ),
            (
                "consumption id",
                record.consumption_id,
                seen_consumption_ids,
            ),
        )

        for label, value, seen in unique_bindings:
            if value in seen:
                raise AdRecycleBinActivationAuthorizationPersistenceError(
                    f"duplicate {label} in authorization registry"
                )

            seen.add(
                value
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
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,

            "records":
                [],
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
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "unable to open authorization registry"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdRecycleBinActivationAuthorizationPersistenceError(
                "authorization registry is not a regular file"
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
                raise AdRecycleBinActivationAuthorizationPersistenceError(
                    "authorization registry JSON is invalid"
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


def persist_ad_recycle_bin_activation_authorization(
    authorization: AdRecycleBinActivationAuthorization,
    *,
    registry_file: Path,
    now: datetime | None = None,
) -> AdRecycleBinActivationAuthorizationPersistence:
    if not AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_ENABLED:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization persistence is disabled"
        )

    try:
        assert_ad_recycle_bin_activation_authorization_invariants(
            authorization
        )
    except AdRecycleBinActivationAuthorizationError as exc:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            str(exc)
        ) from exc

    current = _normalize_now(
        now
    )

    issued_at = _parse_timestamp(
        authorization.issued_at,
        field="authorization.issued_at",
    )

    expires_at = _parse_timestamp(
        authorization.expires_at,
        field="authorization.expires_at",
    )

    if current < issued_at:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "authorization cannot be persisted before issue time"
        )

    if current >= expires_at:
        raise AdRecycleBinActivationAuthorizationPersistenceError(
            "expired authorization cannot be persisted"
        )

    if not isinstance(
        registry_file,
        Path,
    ):
        registry_file = Path(
            registry_file
        )

    payload = {
        "contract_version":
            AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,

        "authorization_contract_version":
            authorization.contract_version,

        "authorization_id":
            authorization.authorization_id,

        "authorization_digest":
            authorization.authorization_digest,

        "state":
            "activation_authorization_dormant",

        "status":
            "authorized",

        "ticket_id":
            authorization.ticket_id,

        "ticket_digest":
            authorization.ticket_digest,

        "consumption_id":
            authorization.consumption_id,

        "consumption_record_digest":
            authorization.consumption_record_digest,

        "source_intent_id":
            authorization.source_intent_id,

        "source_intent_digest":
            authorization.source_intent_digest,

        "fresh_evidence_job_id":
            authorization.fresh_evidence_job_id,

        "fresh_evidence_sha256":
            authorization.fresh_evidence_sha256,

        "forest_name":
            authorization.forest_name,

        "root_domain":
            authorization.root_domain,

        "forest_mode":
            authorization.forest_mode,

        "actor_subject":
            authorization.actor_subject,

        "actor_username":
            authorization.actor_username,

        "actor_issuer":
            authorization.actor_issuer,

        "actor_azp":
            authorization.actor_azp,

        "acknowledge_forest_wide":
            authorization.acknowledge_forest_wide,

        "acknowledge_irreversible":
            authorization.acknowledge_irreversible,

        "acknowledge_no_restore":
            authorization.acknowledge_no_restore,

        "authorization_reason":
            authorization.authorization_reason,

        "issued_at":
            authorization.issued_at,

        "expires_at":
            authorization.expires_at,

        "persisted_at":
            current.isoformat(),

        "one_shot_required":
            True,

        "authorization_consumed":
            False,

        "human_authorized":
            True,

        "persistence_enabled":
            True,

        "route_enabled":
            False,

        "job_creation_authorized":
            False,

        "runtime_authorized":
            False,

        "production_authorized":
            False,

        "activation_authorized":
            True,

        "restore_authorized":
            False,

        "write_performed":
            False,
    }

    record_digest = _canonical_sha256(
        payload
    )

    record = AdRecycleBinActivationAuthorizationPersistence(
        record_digest=record_digest,
        **payload,
    )

    assert_ad_recycle_bin_activation_authorization_persistence_invariants(
        record
    )

    _assert_safe_path(
        registry_file
    )

    registry_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _assert_safe_path(
        registry_file
    )

    with _exclusive_registry_lock(
        registry_file
    ):
        registry = _load_registry(
            registry_file
        )

        records = registry["records"]

        if (
            len(records)
            >= AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_REGISTRY_MAX_RECORDS
        ):
            raise AdRecycleBinActivationAuthorizationPersistenceError(
                "authorization registry is full"
            )

        uniqueness = (
            (
                "authorization id",
                "authorization_id",
                record.authorization_id,
            ),
            (
                "authorization digest",
                "authorization_digest",
                record.authorization_digest,
            ),
            (
                "ticket id",
                "ticket_id",
                record.ticket_id,
            ),
            (
                "ticket digest",
                "ticket_digest",
                record.ticket_digest,
            ),
            (
                "consumption id",
                "consumption_id",
                record.consumption_id,
            ),
        )

        for existing in records:
            for label, field, value in uniqueness:
                if existing[field] == value:
                    raise AdRecycleBinActivationAuthorizationPersistenceError(
                        f"{label} already persisted"
                    )

        records.append(
            asdict(record)
        )

        _atomic_write_registry(
            registry_file,
            registry,
        )

    return record


__all__ = [
    "AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION",
    "AdRecycleBinActivationAuthorizationPersistence",
    "AdRecycleBinActivationAuthorizationPersistenceError",
    "assert_ad_recycle_bin_activation_authorization_persistence_invariants",
    "persist_ad_recycle_bin_activation_authorization",
]
