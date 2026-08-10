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

from app.services.ad_recycle_bin_activation_authorization_persistence import (
    AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,
    AdRecycleBinActivationAuthorizationPersistence,
    AdRecycleBinActivationAuthorizationPersistenceError,
    assert_ad_recycle_bin_activation_authorization_persistence_invariants,
)

from app.services.ad_recycle_bin_activation_preexecution import (
    AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_CONTRACT_VERSION,
    AdRecycleBinActivationPreexecution,
    AdRecycleBinActivationPreexecutionError,
    assert_ad_recycle_bin_activation_preexecution_invariants,
)


AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION = (
    "c9.4a2e-a3-v1"
)

AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_REGISTRY_MAX_RECORDS = 4096

AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_PERSISTENCE_ENABLED = True
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_ROUTE_ENABLED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_JOB_CREATION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_RUNTIME_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_PRODUCTION_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_ACTIVATION_AUTHORIZED = True
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_RESTORE_AUTHORIZED = False
AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_WRITE_PERFORMED = False


class AdRecycleBinActivationAuthorizationConsumptionError(
    ValueError
):
    pass


class AdRecycleBinActivationAuthorizationConsumptionConflict(
    AdRecycleBinActivationAuthorizationConsumptionError
):
    pass


@dataclass(frozen=True)
class AdRecycleBinActivationAuthorizationConsumption:
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
    ticket_consumption_id: str
    ticket_consumption_record_digest: str

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
        raise AdRecycleBinActivationAuthorizationConsumptionError(
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
        raise AdRecycleBinActivationAuthorizationConsumptionError(
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
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            f"{field} is invalid"
        ) from exc

    if parsed.tzinfo is None:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
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
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            f"{field} must be a string"
        )

    cleaned = value.strip()

    if not cleaned:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            f"{field} is required"
        )

    if len(cleaned) > max_length:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
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
        raise AdRecycleBinActivationAuthorizationConsumptionError(
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
        raise AdRecycleBinActivationAuthorizationConsumptionError(
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


def _record_digest_payload(
    record: AdRecycleBinActivationAuthorizationConsumption,
) -> dict[str, Any]:
    payload = asdict(
        record
    )

    payload.pop(
        "record_digest"
    )

    return payload


def _extract_actor(
    server_actor: Mapping[str, Any],
) -> dict[str, str]:
    if not isinstance(
        server_actor,
        Mapping,
    ):
        raise AdRecycleBinActivationAuthorizationConsumptionError(
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
        raise AdRecycleBinActivationAuthorizationConsumptionConflict(
            "OIDC issuer mismatch"
        )

    if (
        OIDC_ALLOWED_AZP
        and actor["azp"] not in OIDC_ALLOWED_AZP
    ):
        raise AdRecycleBinActivationAuthorizationConsumptionConflict(
            "OIDC azp is not allowed"
        )

    return actor


def _assert_safe_path(
    path: Path,
) -> None:
    if not path.is_absolute():
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption registry path must be absolute"
        )

    if path.is_symlink():
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption registry path must not be a symlink"
        )

    current = path.parent

    while True:
        if current.is_symlink():
            raise AdRecycleBinActivationAuthorizationConsumptionError(
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
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "unable to open authorization consumption registry lock"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdRecycleBinActivationAuthorizationConsumptionError(
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


def assert_ad_recycle_bin_activation_authorization_consumption_invariants(
    record: AdRecycleBinActivationAuthorizationConsumption,
) -> None:
    if (
        record.contract_version
        != AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption contract version mismatch"
        )

    if (
        record.authorization_persistence_contract_version
        != AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization persistence contract version mismatch"
        )

    if (
        record.preexecution_contract_version
        != AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "preexecution contract version mismatch"
        )

    for field in (
        "authorization_consumption_id",
        "authorization_id",
        "preexecution_id",
        "ticket_id",
        "ticket_consumption_id",
        "source_intent_id",
    ):
        _required_uuid(
            getattr(
                record,
                field,
            ),
            field=field,
        )

    for field in (
        "record_digest",
        "authorization_digest",
        "authorization_record_digest",
        "preexecution_digest",
        "ticket_digest",
        "ticket_consumption_record_digest",
        "source_intent_digest",
        "authorization_evidence_sha256",
        "fresh_evidence_sha256",
    ):
        _required_sha256(
            getattr(
                record,
                field,
            ),
            field=field,
        )

    if record.state != "activation_authorization_consumed":
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption state is invalid"
        )

    if record.status != "consumed":
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption status is invalid"
        )

    if record.human_authorized is not True:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "human authorization marker must remain true"
        )

    if record.revalidation_passed is not True:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "preexecution revalidation marker must remain true"
        )

    if record.authorization_consumed is not True:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption marker must be true"
        )

    if record.one_shot_consumption is not True:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption must remain one-shot"
        )

    if record.persistence_enabled is not True:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption persistence marker must be true"
        )

    if record.activation_authorized is not True:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
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
            raise AdRecycleBinActivationAuthorizationConsumptionError(
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
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization expiration is invalid"
        )

    if preexecution_expires_at <= preexecution_issued_at:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "preexecution expiration is invalid"
        )

    if consumed_at < preexecution_issued_at:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumed before preexecution issue time"
        )

    if consumed_at >= preexecution_expires_at:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumed after preexecution expiration"
        )

    if consumed_at >= authorization_expires_at:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumed after authorization expiration"
        )

    expected = _canonical_sha256(
        _record_digest_payload(
            record
        )
    )

    if record.record_digest != expected:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption record digest mismatch"
        )


_RECORD_KEYS = {
    item.name
    for item in fields(
        AdRecycleBinActivationAuthorizationConsumption
    )
}


def _validate_registry(
    data: Any,
) -> dict[str, Any]:
    if not isinstance(
        data,
        dict,
    ):
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption registry is invalid"
        )

    if (
        data.get(
            "contract_version"
        )
        != AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption registry contract version mismatch"
        )

    records = data.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption registry records are invalid"
        )

    if (
        len(
            records
        )
        > AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_REGISTRY_MAX_RECORDS
    ):
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption registry is full"
        )

    seen_consumption_ids = set()
    seen_authorization_ids = set()
    seen_authorization_digests = set()
    seen_preexecution_ids = set()
    seen_preexecution_digests = set()

    for raw in records:
        if not isinstance(
            raw,
            dict,
        ):
            raise AdRecycleBinActivationAuthorizationConsumptionError(
                "authorization consumption registry record is invalid"
            )

        if set(
            raw.keys()
        ) != _RECORD_KEYS:
            raise AdRecycleBinActivationAuthorizationConsumptionError(
                "authorization consumption registry record schema mismatch"
            )

        record = AdRecycleBinActivationAuthorizationConsumption(
            **raw
        )

        assert_ad_recycle_bin_activation_authorization_consumption_invariants(
            record
        )

        unique_bindings = (
            (
                "authorization consumption id",
                record.authorization_consumption_id,
                seen_consumption_ids,
            ),
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
                "preexecution id",
                record.preexecution_id,
                seen_preexecution_ids,
            ),
            (
                "preexecution digest",
                record.preexecution_digest,
                seen_preexecution_digests,
            ),
        )

        for label, value, seen in unique_bindings:
            if value in seen:
                raise AdRecycleBinActivationAuthorizationConsumptionError(
                    f"duplicate {label} in authorization consumption registry"
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
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION,

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
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "unable to open authorization consumption registry"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(
                fd
            ).st_mode
        ):
            raise AdRecycleBinActivationAuthorizationConsumptionError(
                "authorization consumption registry is not a regular file"
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
                raise AdRecycleBinActivationAuthorizationConsumptionError(
                    "authorization consumption registry JSON is invalid"
                ) from exc

    finally:
        if fd >= 0:
            os.close(
                fd
            )

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


def consume_ad_recycle_bin_activation_authorization(
    authorization_record: AdRecycleBinActivationAuthorizationPersistence,
    preexecution_record: AdRecycleBinActivationPreexecution,
    *,
    consumption_registry_file: Path,
    server_actor: Mapping[str, Any],
    current_mode: str,
    now: datetime | None = None,
) -> AdRecycleBinActivationAuthorizationConsumption:
    if current_mode != "Simulation":
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            "authorization consumption is Simulation-only"
        )

    try:
        assert_ad_recycle_bin_activation_authorization_persistence_invariants(
            authorization_record
        )
    except AdRecycleBinActivationAuthorizationPersistenceError as exc:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            str(
                exc
            )
        ) from exc

    try:
        assert_ad_recycle_bin_activation_preexecution_invariants(
            preexecution_record
        )
    except AdRecycleBinActivationPreexecutionError as exc:
        raise AdRecycleBinActivationAuthorizationConsumptionError(
            str(
                exc
            )
        ) from exc

    if authorization_record.authorization_consumed is not False:
        raise AdRecycleBinActivationAuthorizationConsumptionConflict(
            "authorization is already marked consumed"
        )

    if preexecution_record.authorization_consumption_required is not True:
        raise AdRecycleBinActivationAuthorizationConsumptionConflict(
            "preexecution does not require authorization consumption"
        )

    if preexecution_record.authorization_consumed is not False:
        raise AdRecycleBinActivationAuthorizationConsumptionConflict(
            "preexecution authorization is already consumed"
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
            raise AdRecycleBinActivationAuthorizationConsumptionConflict(
                f"unsafe authorization flag: {field}"
            )

        if getattr(
            preexecution_record,
            field,
        ) is not False:
            raise AdRecycleBinActivationAuthorizationConsumptionConflict(
                f"unsafe preexecution flag: {field}"
            )

    exact_bindings = {
        "authorization_id":
            (
                authorization_record.authorization_id,
                preexecution_record.authorization_id,
            ),

        "authorization_digest":
            (
                authorization_record.authorization_digest,
                preexecution_record.authorization_digest,
            ),

        "authorization_record_digest":
            (
                authorization_record.record_digest,
                preexecution_record.authorization_record_digest,
            ),

        "ticket_id":
            (
                authorization_record.ticket_id,
                preexecution_record.ticket_id,
            ),

        "ticket_digest":
            (
                authorization_record.ticket_digest,
                preexecution_record.ticket_digest,
            ),

        "ticket_consumption_id":
            (
                authorization_record.consumption_id,
                preexecution_record.consumption_id,
            ),

        "ticket_consumption_record_digest":
            (
                authorization_record.consumption_record_digest,
                preexecution_record.consumption_record_digest,
            ),

        "source_intent_id":
            (
                authorization_record.source_intent_id,
                preexecution_record.source_intent_id,
            ),

        "source_intent_digest":
            (
                authorization_record.source_intent_digest,
                preexecution_record.source_intent_digest,
            ),

        "forest_name":
            (
                authorization_record.forest_name,
                preexecution_record.forest_name,
            ),

        "root_domain":
            (
                authorization_record.root_domain,
                preexecution_record.root_domain,
            ),

        "forest_mode":
            (
                authorization_record.forest_mode,
                preexecution_record.forest_mode,
            ),

        "actor_subject":
            (
                authorization_record.actor_subject,
                preexecution_record.actor_subject,
            ),

        "actor_username":
            (
                authorization_record.actor_username,
                preexecution_record.actor_username,
            ),

        "actor_issuer":
            (
                authorization_record.actor_issuer,
                preexecution_record.actor_issuer,
            ),

        "actor_azp":
            (
                authorization_record.actor_azp,
                preexecution_record.actor_azp,
            ),
    }

    for field, pair in exact_bindings.items():
        if pair[0] != pair[1]:
            raise AdRecycleBinActivationAuthorizationConsumptionConflict(
                f"authorization/preexecution mismatch: {field}"
            )

    actor = _extract_actor(
        server_actor
    )

    actor_bindings = {
        "actor_subject":
            actor["subject"],

        "actor_username":
            actor["username"],

        "actor_issuer":
            actor["issuer"],

        "actor_azp":
            actor["azp"],
    }

    for field, value in actor_bindings.items():
        if getattr(
            authorization_record,
            field,
        ) != value:
            raise AdRecycleBinActivationAuthorizationConsumptionConflict(
                f"actor mismatch: {field}"
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

    preexecution_issued_at = _parse_timestamp(
        preexecution_record.issued_at,
        field="preexecution.issued_at",
    )

    preexecution_expires_at = _parse_timestamp(
        preexecution_record.expires_at,
        field="preexecution.expires_at",
    )

    fresh_evidence_created_at = _parse_timestamp(
        preexecution_record.fresh_evidence_created_at,
        field="preexecution.fresh_evidence_created_at",
    )

    if current < preexecution_issued_at:
        raise AdRecycleBinActivationAuthorizationConsumptionConflict(
            "authorization cannot be consumed before preexecution issue time"
        )

    if current >= preexecution_expires_at:
        raise AdRecycleBinActivationAuthorizationConsumptionConflict(
            "preexecution expired before authorization consumption"
        )

    if current >= authorization_expires_at:
        raise AdRecycleBinActivationAuthorizationConsumptionConflict(
            "authorization expired before consumption"
        )

    if fresh_evidence_created_at > current:
        raise AdRecycleBinActivationAuthorizationConsumptionConflict(
            "fresh evidence timestamp is in the future"
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

        records = registry[
            "records"
        ]

        if (
            len(
                records
            )
            >= AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_REGISTRY_MAX_RECORDS
        ):
            raise AdRecycleBinActivationAuthorizationConsumptionError(
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
                if existing[
                    field
                ] == value:
                    raise AdRecycleBinActivationAuthorizationConsumptionConflict(
                        f"{label} already consumed"
                    )

        payload = {
            "contract_version":
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION,

            "authorization_consumption_id":
                str(
                    uuid4()
                ),

            "state":
                "activation_authorization_consumed",

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

            "ticket_consumption_id":
                authorization_record.consumption_id,

            "ticket_consumption_record_digest":
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
                preexecution_record.fresh_evidence_job_id,

            "fresh_evidence_sha256":
                preexecution_record.fresh_evidence_sha256,

            "fresh_evidence_created_at":
                preexecution_record.fresh_evidence_created_at,

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
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_PERSISTENCE_ENABLED,

            "route_enabled":
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_ROUTE_ENABLED,

            "job_creation_authorized":
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_JOB_CREATION_AUTHORIZED,

            "runtime_authorized":
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_RUNTIME_AUTHORIZED,

            "production_authorized":
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_PRODUCTION_AUTHORIZED,

            "activation_authorized":
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_ACTIVATION_AUTHORIZED,

            "restore_authorized":
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_RESTORE_AUTHORIZED,

            "write_performed":
                AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_WRITE_PERFORMED,
        }

        record_digest = _canonical_sha256(
            payload
        )

        record = AdRecycleBinActivationAuthorizationConsumption(
            record_digest=record_digest,
            **payload,
        )

        assert_ad_recycle_bin_activation_authorization_consumption_invariants(
            record
        )

        records.append(
            asdict(
                record
            )
        )

        _atomic_write_registry(
            consumption_registry_file,
            registry,
        )

    return record


__all__ = [
    "AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_CONSUMPTION_CONTRACT_VERSION",
    "AdRecycleBinActivationAuthorizationConsumption",
    "AdRecycleBinActivationAuthorizationConsumptionConflict",
    "AdRecycleBinActivationAuthorizationConsumptionError",
    "assert_ad_recycle_bin_activation_authorization_consumption_invariants",
    "consume_ad_recycle_bin_activation_authorization",
]
