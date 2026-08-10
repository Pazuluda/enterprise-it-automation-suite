from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any
import uuid

from app.services.ad_recycle_bin_activation_intent import (
    AdRecycleBinActivationIntent,
    AdRecycleBinActivationIntentError,
    assert_ad_recycle_bin_activation_intent_invariants,
)


AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION = (
    "c9.3a5c-v1"
)

AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_ENABLED = True


AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_JOB_CREATION_AUTHORIZED = (
    False
)

AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_RUNTIME_AUTHORIZED = (
    False
)

AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_PRODUCTION_AUTHORIZED = (
    False
)

AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_ACTIVATION_AUTHORIZED = (
    False
)

AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_RESTORE_AUTHORIZED = (
    False
)

AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_WRITE_PERFORMED = (
    False
)


class AdRecycleBinActivationIntentPersistenceError(
    ValueError
):
    pass


@dataclass(frozen=True)
class AdRecycleBinActivationIntentPersistence:
    contract_version: str
    intent_id: str
    intent_digest: str

    state: str
    status: str

    forest_name: str
    root_domain: str

    actor_subject: str
    actor_username: str
    actor_issuer: str
    actor_azp: str

    evidence_sha256: str
    evidence_created_at: str

    created_at: str
    persisted_at: str

    job_creation_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    activation_authorized: bool
    restore_authorized: bool
    write_performed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_now(
    now: datetime | None,
) -> datetime:
    value = (
        datetime.now(timezone.utc)
        if now is None
        else now
    )

    if value.tzinfo is None:
        raise AdRecycleBinActivationIntentPersistenceError(
            "now must be timezone-aware"
        )

    return value.astimezone(
        timezone.utc
    )


def _assert_safe_storage_path(
    storage_file: Path,
) -> None:
    if storage_file.exists() and storage_file.is_symlink():
        raise AdRecycleBinActivationIntentPersistenceError(
            "Activation intent storage must not be a symlink"
        )

    parent = storage_file.parent

    if parent.exists() and parent.is_symlink():
        raise AdRecycleBinActivationIntentPersistenceError(
            "Activation intent storage directory "
            "must not be a symlink"
        )


def _canonical_digest(
    *,
    intent_id: str,
    intent: AdRecycleBinActivationIntent,
    persisted_at: str,
) -> str:
    payload = {
        "intent_id":
            intent_id,

        "intent_contract_version":
            intent.contract_version,

        "forest_name":
            intent.forest_name,

        "root_domain":
            intent.root_domain,

        "forest_mode":
            intent.forest_mode,

        "evidence_sha256":
            intent.evidence_sha256,

        "evidence_created_at":
            intent.evidence_created_at,

        "actor_subject":
            intent.actor_subject,

        "actor_username":
            intent.actor_username,

        "actor_issuer":
            intent.actor_issuer,

        "actor_azp":
            intent.actor_azp,

        "created_at":
            intent.created_at,

        "persisted_at":
            persisted_at,

        "state":
            intent.state,
    }

    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        raw
    ).hexdigest()


def _load_registry(
    storage_file: Path,
) -> dict[str, Any]:
    if not storage_file.exists():
        return {
            "contract_version":
                AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,
            "records": [],
        }

    try:
        raw = storage_file.read_text(
            encoding="utf-8"
        )

        data = json.loads(
            raw
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise AdRecycleBinActivationIntentPersistenceError(
            "Unable to read activation intent storage"
        ) from exc

    if not isinstance(
        data,
        dict,
    ):
        raise AdRecycleBinActivationIntentPersistenceError(
            "Activation intent storage root is invalid"
        )

    records = data.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise AdRecycleBinActivationIntentPersistenceError(
            "Activation intent storage records are invalid"
        )

    return data


def _atomic_write_registry(
    storage_file: Path,
    registry: dict[str, Any],
) -> None:
    parent = storage_file.parent

    parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd = None
    temp_name = None

    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=(
                "."
                + storage_file.name
                + "."
            ),
            suffix=".tmp",
            dir=str(parent),
        )

        os.fchmod(
            fd,
            0o600,
        )

        serialized = (
            json.dumps(
                registry,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode(
            "utf-8"
        )

        with os.fdopen(
            fd,
            "wb",
            closefd=True,
        ) as handle:
            fd = None

            handle.write(
                serialized
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temp_name,
            storage_file,
        )

        temp_name = None

        os.chmod(
            storage_file,
            0o600,
        )

        dir_fd = os.open(
            parent,
            os.O_RDONLY,
        )

        try:
            os.fsync(
                dir_fd
            )
        finally:
            os.close(
                dir_fd
            )

    finally:
        if fd is not None:
            os.close(
                fd
            )

        if temp_name is not None:
            try:
                os.unlink(
                    temp_name
                )
            except FileNotFoundError:
                pass


def persist_ad_recycle_bin_activation_intent(
    intent: AdRecycleBinActivationIntent,
    *,
    storage_file: Path,
    now: datetime | None = None,
) -> AdRecycleBinActivationIntentPersistence:
    if (
        not AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_ENABLED
    ):
        raise AdRecycleBinActivationIntentPersistenceError(
            "Activation intent persistence is disabled"
        )

    try:
        assert_ad_recycle_bin_activation_intent_invariants(
            intent
        )
    except AdRecycleBinActivationIntentError as exc:
        raise AdRecycleBinActivationIntentPersistenceError(
            "Activation intent invariants failed"
        ) from exc

    _assert_safe_storage_path(
        storage_file
    )

    persisted_time = _normalize_now(
        now
    )

    persisted_at = persisted_time.isoformat()

    intent_id = str(
        uuid.uuid4()
    )

    digest = _canonical_digest(
        intent_id=intent_id,
        intent=intent,
        persisted_at=persisted_at,
    )

    record = {
        "contract_version":
            AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,

        "intent_id":
            intent_id,

        "intent_digest":
            digest,

        "state":
            "activation_intent_dormant",

        "status":
            "dormant",

        "forest_name":
            intent.forest_name,

        "root_domain":
            intent.root_domain,

        "forest_mode":
            intent.forest_mode,

        "actor_subject":
            intent.actor_subject,

        "actor_username":
            intent.actor_username,

        "actor_issuer":
            intent.actor_issuer,

        "actor_azp":
            intent.actor_azp,

        "evidence_sha256":
            intent.evidence_sha256,

        "evidence_created_at":
            intent.evidence_created_at,

        "acknowledge_forest_wide":
            intent.acknowledge_forest_wide,

        "acknowledge_irreversible":
            intent.acknowledge_irreversible,

        "acknowledge_no_restore":
            intent.acknowledge_no_restore,

        "requested_reason":
            intent.requested_reason,

        "created_at":
            intent.created_at,

        "persisted_at":
            persisted_at,

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

    lock_file = storage_file.with_name(
        storage_file.name + ".lock"
    )

    lock_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if lock_file.exists() and lock_file.is_symlink():
        raise AdRecycleBinActivationIntentPersistenceError(
            "Activation intent lock must not be a symlink"
        )

    lock_fd = os.open(
        lock_file,
        os.O_RDWR | os.O_CREAT,
        0o600,
    )

    try:
        os.fchmod(
            lock_fd,
            0o600,
        )

        with os.fdopen(
            lock_fd,
            "r+",
            closefd=True,
        ) as lock_handle:
            lock_fd = -1

            fcntl.flock(
                lock_handle.fileno(),
                fcntl.LOCK_EX,
            )

            _assert_safe_storage_path(
                storage_file
            )

            registry = _load_registry(
                storage_file
            )

            records = registry[
                "records"
            ]

            if any(
                existing.get(
                    "intent_digest"
                ) == digest
                for existing in records
                if isinstance(
                    existing,
                    dict,
                )
            ):
                raise AdRecycleBinActivationIntentPersistenceError(
                    "Duplicate activation intent digest"
                )

            records.append(
                record
            )

            registry[
                "contract_version"
            ] = (
                AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION
            )

            _atomic_write_registry(
                storage_file,
                registry,
            )

    finally:
        if lock_fd >= 0:
            os.close(
                lock_fd
            )

    return AdRecycleBinActivationIntentPersistence(
        contract_version=(
            AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION
        ),

        intent_id=intent_id,
        intent_digest=digest,

        state="activation_intent_dormant",
        status="dormant",

        forest_name=intent.forest_name,
        root_domain=intent.root_domain,

        actor_subject=intent.actor_subject,
        actor_username=intent.actor_username,
        actor_issuer=intent.actor_issuer,
        actor_azp=intent.actor_azp,

        evidence_sha256=intent.evidence_sha256,
        evidence_created_at=intent.evidence_created_at,

        created_at=intent.created_at,
        persisted_at=persisted_at,

        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        activation_authorized=False,
        restore_authorized=False,
        write_performed=False,
    )


def assert_ad_recycle_bin_activation_intent_persistence_invariants(
    record: AdRecycleBinActivationIntentPersistence,
) -> None:
    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_JOB_CREATION_AUTHORIZED
    ):
        raise AdRecycleBinActivationIntentPersistenceError(
            "C9.3 job creation must remain forbidden"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_RUNTIME_AUTHORIZED
    ):
        raise AdRecycleBinActivationIntentPersistenceError(
            "C9.3 runtime must remain forbidden"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_PRODUCTION_AUTHORIZED
    ):
        raise AdRecycleBinActivationIntentPersistenceError(
            "C9.3 Production must remain forbidden"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_ACTIVATION_AUTHORIZED
    ):
        raise AdRecycleBinActivationIntentPersistenceError(
            "C9.3 activation must remain forbidden"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_RESTORE_AUTHORIZED
    ):
        raise AdRecycleBinActivationIntentPersistenceError(
            "C9.3 restore must remain forbidden"
        )

    if (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_WRITE_PERFORMED
    ):
        raise AdRecycleBinActivationIntentPersistenceError(
            "C9.3 write_performed must remain false"
        )

    if record.status != "dormant":
        raise AdRecycleBinActivationIntentPersistenceError(
            "Activation intent must remain dormant"
        )

    if record.state != "activation_intent_dormant":
        raise AdRecycleBinActivationIntentPersistenceError(
            "Activation intent state is invalid"
        )

    unsafe_flags = (
        record.job_creation_authorized,
        record.runtime_authorized,
        record.production_authorized,
        record.activation_authorized,
        record.restore_authorized,
        record.write_performed,
    )

    if any(
        unsafe_flags
    ):
        raise AdRecycleBinActivationIntentPersistenceError(
            "Persisted activation intent contains "
            "an unsafe authorization flag"
        )


__all__ = [
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_ENABLED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_JOB_CREATION_AUTHORIZED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_RUNTIME_AUTHORIZED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_PRODUCTION_AUTHORIZED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_ACTIVATION_AUTHORIZED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_RESTORE_AUTHORIZED",
    "AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_WRITE_PERFORMED",
    "AdRecycleBinActivationIntentPersistence",
    "AdRecycleBinActivationIntentPersistenceError",
    "persist_ad_recycle_bin_activation_intent",
    "assert_ad_recycle_bin_activation_intent_persistence_invariants",
]
