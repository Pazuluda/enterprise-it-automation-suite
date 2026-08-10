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

from app.services.ad_deleted_object_restore_authorization_persistence import (
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,
    AdDeletedObjectRestoreAuthorizationPersistence,
    AdDeletedObjectRestoreAuthorizationPersistenceError,
    assert_ad_deleted_object_restore_authorization_persistence_invariants,
)

from app.services.ad_deleted_object_restore_preexecution import (
    AD_DELETED_OBJECT_RESTORE_PREEXECUTION_CONTRACT_VERSION,
    AdDeletedObjectRestorePreexecution,
    AdDeletedObjectRestorePreexecutionError,
    assert_ad_deleted_object_restore_preexecution_invariants,
)


AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION = (
    "c9.5a4d3-v1"
)

AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_REGISTRY_MAX_RECORDS = 4096

AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_PERSISTENCE_ENABLED = True
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_CLAIM_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_PRODUCTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_RESTORE_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_RESTORE_WHATIF_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_EXECUTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_WRITE_PERFORMED = False


class AdDeletedObjectRestoreAuthorizationConsumptionError(
    ValueError
):
    pass


class AdDeletedObjectRestoreAuthorizationConsumptionConflict(
    AdDeletedObjectRestoreAuthorizationConsumptionError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreAuthorizationConsumption:
    contract_version: str
    authorization_consumption_id: str
    record_digest: str

    state: str
    status: str

    authorization_persistence_contract_version: str
    authorization_id: str
    authorization_digest: str
    authorization_record_digest: str

    preexecution_contract_version: str
    preexecution_id: str
    preexecution_digest: str

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
    preexecution_issued_at: str
    preexecution_expires_at: str
    consumed_at: str

    human_authorized: bool
    revalidation_passed: bool
    authorization_consumed: bool
    one_shot_consumption: bool

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



def _normalize_now(
    now: datetime | None,
) -> datetime:
    current = (
        datetime.now(timezone.utc)
        if now is None
        else now
    )

    if current.tzinfo is None:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
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
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
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
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
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
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            f"{field} must be a string"
        )

    cleaned = value.strip()

    if not cleaned:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            f"{field} is required"
        )

    if len(cleaned) > max_length:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
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
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
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
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
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


def _extract_actor(
    server_actor: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(
        server_actor,
        Mapping,
    ):
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
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
        raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
            "OIDC issuer mismatch"
        )

    if (
        OIDC_ALLOWED_AZP
        and actor["azp"] not in OIDC_ALLOWED_AZP
    ):
        raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
            "OIDC azp is not allowed"
        )

    return actor


def _assert_safe_path(
    path: Path,
) -> None:
    if not path.is_absolute():
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption registry path must be absolute"
        )

    if path.is_symlink():
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption registry path must not be a symlink"
        )

    current = path.parent

    while True:
        if current.is_symlink():
            raise AdDeletedObjectRestoreAuthorizationConsumptionError(
                "authorization consumption registry parent must not be a symlink"
            )

        if current == current.parent:
            break

        current = current.parent


def _open_flags(
    base_flags: int,
) -> int:
    flags = base_flags

    if hasattr(
        os,
        "O_NOFOLLOW",
    ):
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
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "unable to open authorization consumption registry lock"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdDeletedObjectRestoreAuthorizationConsumptionError(
                "authorization consumption registry lock is not a regular file"
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
            os.close(
                fd
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
        dir=str(
            parent
        ),
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

            handle.write(
                "\n"
            )

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

        if temporary.exists():
            temporary.unlink()


def _record_digest_payload(
    record: AdDeletedObjectRestoreAuthorizationConsumption,
) -> dict[str, Any]:
    payload = asdict(record)
    payload.pop("record_digest")
    return payload


def assert_ad_deleted_object_restore_authorization_consumption_invariants(
    record: AdDeletedObjectRestoreAuthorizationConsumption,
) -> None:
    if (
        record.contract_version
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption contract version mismatch"
        )

    if (
        record.authorization_persistence_contract_version
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization persistence contract version mismatch"
        )

    if (
        record.preexecution_contract_version
        != AD_DELETED_OBJECT_RESTORE_PREEXECUTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "preexecution contract version mismatch"
        )

    for field in (
        "authorization_consumption_id",
        "authorization_id",
        "preexecution_id",
        "ticket_id",
        "consumption_id",
        "source_simulation_job_id",
        "source_inventory_job_id",
        "source_live_job_id",
        "authorization_fresh_live_job_id",
        "fresh_live_job_id",
        "object_guid",
    ):
        _required_uuid(
            getattr(record, field),
            field=field,
        )

    for field in (
        "record_digest",
        "authorization_digest",
        "authorization_record_digest",
        "preexecution_digest",
        "ticket_digest",
        "consumption_record_digest",
        "authorization_fresh_live_sha256",
        "fresh_live_sha256",
    ):
        _required_sha256(
            getattr(record, field),
            field=field,
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

    if record.state != "restore_authorization_consumed_dormant":
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption state is invalid"
        )

    if record.status != "consumed":
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption status is invalid"
        )

    if record.human_authorized is not True:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "human authorization marker must remain true"
        )

    if record.revalidation_passed is not True:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "preexecution revalidation marker must remain true"
        )

    if record.authorization_consumed is not True:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption marker must be true"
        )

    if record.one_shot_consumption is not True:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption must remain one-shot"
        )

    if record.persistence_enabled is not True:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption persistence marker must be true"
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
            raise AdDeletedObjectRestoreAuthorizationConsumptionError(
                f"unsafe authorization consumption flag: {field}"
            )

    authorization_issued_at = _parse_timestamp(
        record.authorization_issued_at,
        field="authorization_issued_at",
    )
    authorization_expires_at = _parse_timestamp(
        record.authorization_expires_at,
        field="authorization_expires_at",
    )
    preexecution_issued_at = _parse_timestamp(
        record.preexecution_issued_at,
        field="preexecution_issued_at",
    )
    preexecution_expires_at = _parse_timestamp(
        record.preexecution_expires_at,
        field="preexecution_expires_at",
    )
    consumed_at = _parse_timestamp(
        record.consumed_at,
        field="consumed_at",
    )

    if authorization_expires_at <= authorization_issued_at:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization expiration is invalid"
        )

    if preexecution_expires_at <= preexecution_issued_at:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "preexecution expiration is invalid"
        )

    if consumed_at < preexecution_issued_at:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumed before preexecution issue time"
        )

    if consumed_at >= preexecution_expires_at:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumed after preexecution expiration"
        )

    if consumed_at >= authorization_expires_at:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumed after authorization expiration"
        )

    expected = _canonical_sha256(
        _record_digest_payload(record)
    )

    if record.record_digest != expected:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption record digest mismatch"
        )


_RECORD_KEYS = {
    item.name
    for item in fields(
        AdDeletedObjectRestoreAuthorizationConsumption
    )
}


def _validate_registry(
    data: Any,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption registry is invalid"
        )

    if (
        data.get("contract_version")
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption registry contract version mismatch"
        )

    records = data.get("records")

    if not isinstance(records, list):
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption registry records are invalid"
        )

    if (
        len(records)
        > AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_REGISTRY_MAX_RECORDS
    ):
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption registry is full"
        )

    unique_sets = {
        "authorization consumption id": set(),
        "authorization id": set(),
        "authorization digest": set(),
        "preexecution id": set(),
        "preexecution digest": set(),
    }

    for raw in records:
        if not isinstance(raw, dict):
            raise AdDeletedObjectRestoreAuthorizationConsumptionError(
                "authorization consumption registry record is invalid"
            )

        if set(raw.keys()) != _RECORD_KEYS:
            raise AdDeletedObjectRestoreAuthorizationConsumptionError(
                "authorization consumption registry record schema mismatch"
            )

        record = AdDeletedObjectRestoreAuthorizationConsumption(
            **raw
        )

        assert_ad_deleted_object_restore_authorization_consumption_invariants(
            record
        )

        pairs = (
            (
                "authorization consumption id",
                record.authorization_consumption_id,
            ),
            (
                "authorization id",
                record.authorization_id,
            ),
            (
                "authorization digest",
                record.authorization_digest,
            ),
            (
                "preexecution id",
                record.preexecution_id,
            ),
            (
                "preexecution digest",
                record.preexecution_digest,
            ),
        )

        for label, value in pairs:
            if value in unique_sets[label]:
                raise AdDeletedObjectRestoreAuthorizationConsumptionError(
                    f"duplicate {label} in authorization consumption registry"
                )

            unique_sets[label].add(value)

    return data


def _load_registry(
    registry_file: Path,
) -> dict[str, Any]:
    _assert_safe_path(registry_file)

    if not registry_file.exists():
        return {
            "contract_version":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION,
            "records": [],
        }

    flags = _open_flags(os.O_RDONLY)

    try:
        fd = os.open(
            registry_file,
            flags,
        )
    except OSError as exc:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "unable to open authorization consumption registry"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdDeletedObjectRestoreAuthorizationConsumptionError(
                "authorization consumption registry is not a regular file"
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
                raise AdDeletedObjectRestoreAuthorizationConsumptionError(
                    "authorization consumption registry JSON is invalid"
                ) from exc
    finally:
        if fd >= 0:
            os.close(fd)

    return _validate_registry(data)


def consume_ad_deleted_object_restore_authorization(
    authorization_record: AdDeletedObjectRestoreAuthorizationPersistence,
    preexecution_record: AdDeletedObjectRestorePreexecution,
    *,
    consumption_registry_file: Path,
    server_actor: Mapping[str, Any],
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreAuthorizationConsumption:
    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            "authorization consumption is Simulation-only"
        )

    try:
        assert_ad_deleted_object_restore_authorization_persistence_invariants(
            authorization_record
        )
    except AdDeletedObjectRestoreAuthorizationPersistenceError as exc:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            str(exc)
        ) from exc

    try:
        assert_ad_deleted_object_restore_preexecution_invariants(
            preexecution_record
        )
    except AdDeletedObjectRestorePreexecutionError as exc:
        raise AdDeletedObjectRestoreAuthorizationConsumptionError(
            str(exc)
        ) from exc

    if authorization_record.authorization_consumed is not False:
        raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
            "authorization is already marked consumed"
        )

    if preexecution_record.authorization_consumption_required is not True:
        raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
            "preexecution does not require authorization consumption"
        )

    if preexecution_record.authorization_consumed is not False:
        raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
            "preexecution authorization is already consumed"
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
            raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
                f"unsafe authorization flag: {field}"
            )

        if getattr(preexecution_record, field) is not False:
            raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
                f"unsafe preexecution flag: {field}"
            )

    exact_bindings = {
        "authorization_id": (
            authorization_record.authorization_id,
            preexecution_record.authorization_id,
        ),
        "authorization_digest": (
            authorization_record.authorization_digest,
            preexecution_record.authorization_digest,
        ),
        "authorization_record_digest": (
            authorization_record.record_digest,
            preexecution_record.authorization_record_digest,
        ),
        "ticket_id": (
            authorization_record.ticket_id,
            preexecution_record.ticket_id,
        ),
        "ticket_digest": (
            authorization_record.ticket_digest,
            preexecution_record.ticket_digest,
        ),
        "consumption_id": (
            authorization_record.consumption_id,
            preexecution_record.consumption_id,
        ),
        "consumption_record_digest": (
            authorization_record.consumption_record_digest,
            preexecution_record.consumption_record_digest,
        ),
        "source_simulation_job_id": (
            authorization_record.source_simulation_job_id,
            preexecution_record.source_simulation_job_id,
        ),
        "source_inventory_job_id": (
            authorization_record.source_inventory_job_id,
            preexecution_record.source_inventory_job_id,
        ),
        "source_live_job_id": (
            authorization_record.source_live_job_id,
            preexecution_record.source_live_job_id,
        ),
        "authorization_fresh_live_job_id": (
            authorization_record.fresh_live_job_id,
            preexecution_record.authorization_fresh_live_job_id,
        ),
        "authorization_fresh_live_sha256": (
            authorization_record.fresh_live_sha256,
            preexecution_record.authorization_fresh_live_sha256,
        ),
        "object_guid": (
            authorization_record.object_guid.lower(),
            preexecution_record.object_guid.lower(),
        ),
        "object_class": (
            authorization_record.object_class,
            preexecution_record.object_class,
        ),
        "class_policy": (
            authorization_record.class_policy,
            preexecution_record.class_policy,
        ),
        "effective_new_name": (
            authorization_record.effective_new_name,
            preexecution_record.effective_new_name,
        ),
        "effective_target_path": (
            authorization_record.effective_target_path,
            preexecution_record.effective_target_path,
        ),
        "actor_subject": (
            authorization_record.actor_subject,
            preexecution_record.actor_subject,
        ),
        "actor_username": (
            authorization_record.actor_username,
            preexecution_record.actor_username,
        ),
        "actor_issuer": (
            authorization_record.actor_issuer,
            preexecution_record.actor_issuer,
        ),
        "actor_azp": (
            authorization_record.actor_azp,
            preexecution_record.actor_azp,
        ),
    }

    for field, pair in exact_bindings.items():
        if pair[0] != pair[1]:
            raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
                f"authorization/preexecution mismatch: {field}"
            )

    actor = _extract_actor(server_actor)

    for field, value in (
        ("actor_subject", actor["subject"]),
        ("actor_username", actor["username"]),
        ("actor_issuer", actor["issuer"]),
        ("actor_azp", actor["azp"]),
    ):
        if getattr(authorization_record, field) != value:
            raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
                f"actor mismatch: {field}"
            )

    current = _normalize_now(now)

    authorization_expires_at = _parse_timestamp(
        authorization_record.expires_at,
        field="authorization.expires_at",
    )

    preexecution_issued_at = _parse_timestamp(
        preexecution_record.issued_at,
        field="preexecution.issued_at",
    )

    preexecution_expires_at = _parse_timestamp(
        preexecution_record.expires_at,
        field="preexecution.expires_at",
    )

    fresh_live_completed_at = _parse_timestamp(
        preexecution_record.fresh_live_completed_at,
        field="preexecution.fresh_live_completed_at",
    )

    if current < preexecution_issued_at:
        raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
            "authorization cannot be consumed before preexecution issue time"
        )

    if current >= preexecution_expires_at:
        raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
            "preexecution expired before authorization consumption"
        )

    if current >= authorization_expires_at:
        raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
            "authorization expired before consumption"
        )

    if fresh_live_completed_at > current:
        raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
            "fresh live timestamp is in the future"
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
            >= AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_REGISTRY_MAX_RECORDS
        ):
            raise AdDeletedObjectRestoreAuthorizationConsumptionError(
                "authorization consumption registry is full"
            )

        duplicate_bindings = (
            (
                "authorization id",
                "authorization_id",
                authorization_record.authorization_id,
            ),
            (
                "authorization digest",
                "authorization_digest",
                authorization_record.authorization_digest,
            ),
            (
                "preexecution id",
                "preexecution_id",
                preexecution_record.preexecution_id,
            ),
            (
                "preexecution digest",
                "preexecution_digest",
                preexecution_record.preexecution_digest,
            ),
        )

        for existing in records:
            for label, field, value in duplicate_bindings:
                if existing[field] == value:
                    raise AdDeletedObjectRestoreAuthorizationConsumptionConflict(
                        f"{label} already consumed"
                    )

        payload = {
            "contract_version":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION,

            "authorization_consumption_id":
                str(uuid4()),

            "state":
                "restore_authorization_consumed_dormant",

            "status":
                "consumed",

            "authorization_persistence_contract_version":
                authorization_record.contract_version,

            "authorization_id":
                authorization_record.authorization_id,

            "authorization_digest":
                authorization_record.authorization_digest,

            "authorization_record_digest":
                authorization_record.record_digest,

            "preexecution_contract_version":
                preexecution_record.contract_version,

            "preexecution_id":
                preexecution_record.preexecution_id,

            "preexecution_digest":
                preexecution_record.preexecution_digest,

            "ticket_id":
                authorization_record.ticket_id,

            "ticket_digest":
                authorization_record.ticket_digest,

            "consumption_id":
                authorization_record.consumption_id,

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

            "fresh_live_job_id":
                preexecution_record.fresh_live_job_id,

            "fresh_live_sha256":
                preexecution_record.fresh_live_sha256,

            "fresh_live_completed_at":
                preexecution_record.fresh_live_completed_at,

            "object_guid":
                authorization_record.object_guid,

            "object_class":
                authorization_record.object_class,

            "class_policy":
                authorization_record.class_policy,

            "effective_new_name":
                authorization_record.effective_new_name,

            "effective_target_path":
                authorization_record.effective_target_path,

            "actor_subject":
                authorization_record.actor_subject,

            "actor_username":
                authorization_record.actor_username,

            "actor_issuer":
                authorization_record.actor_issuer,

            "actor_azp":
                authorization_record.actor_azp,

            "authorization_issued_at":
                authorization_record.issued_at,

            "authorization_expires_at":
                authorization_record.expires_at,

            "preexecution_issued_at":
                preexecution_record.issued_at,

            "preexecution_expires_at":
                preexecution_record.expires_at,

            "consumed_at":
                current.isoformat(),

            "human_authorized":
                True,

            "revalidation_passed":
                True,

            "authorization_consumed":
                True,

            "one_shot_consumption":
                True,

            "persistence_enabled":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_PERSISTENCE_ENABLED,

            "route_enabled":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_ROUTE_ENABLED,

            "job_creation_authorized":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_JOB_CREATION_AUTHORIZED,

            "claim_authorized":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_CLAIM_AUTHORIZED,

            "runtime_authorized":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_RUNTIME_AUTHORIZED,

            "production_authorized":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_PRODUCTION_AUTHORIZED,

            "restore_authorized":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_RESTORE_AUTHORIZED,

            "restore_whatif_authorized":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_RESTORE_WHATIF_AUTHORIZED,

            "execution_authorized":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_EXECUTION_AUTHORIZED,

            "write_performed":
                AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_WRITE_PERFORMED,
        }

        record = AdDeletedObjectRestoreAuthorizationConsumption(
            record_digest=_canonical_sha256(payload),
            **payload,
        )

        assert_ad_deleted_object_restore_authorization_consumption_invariants(
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
    "AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION",
    "AdDeletedObjectRestoreAuthorizationConsumption",
    "AdDeletedObjectRestoreAuthorizationConsumptionConflict",
    "AdDeletedObjectRestoreAuthorizationConsumptionError",
    "assert_ad_deleted_object_restore_authorization_consumption_invariants",
    "consume_ad_deleted_object_restore_authorization",
]
