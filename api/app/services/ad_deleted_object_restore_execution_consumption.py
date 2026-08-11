from __future__ import annotations

import fcntl
import json
import os
import stat

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID, uuid4

from app.services.ad_deleted_object_restore_authorization_consumption import (
    _canonical_sha256,
    _extract_actor,
    _normalize_now,
    _parse_timestamp,
    _required_sha256,
    _required_string,
    _required_uuid,
)
from app.services.ad_deleted_object_restore_execution_ticket import (
    AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CONTRACT_VERSION,
    AdDeletedObjectRestoreExecutionTicket,
    AdDeletedObjectRestoreExecutionTicketError,
    assert_ad_deleted_object_restore_execution_ticket_invariants,
)


AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_CONTRACT_VERSION = (
    "c9.5a5d-v1"
)

AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_REGISTRY_MAX_RECORDS = (
    2048
)

AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_PERSISTENCE_ENABLED = True

AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_AGENT_ENDPOINT_ENABLED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_CLAIM_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_PRODUCTION_AUTHORIZED = False

# A consumption record proves one-shot use.
# It does not itself authorize the AD write.
AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_RESTORE_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_RESTORE_WHATIF_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_EXECUTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_WRITE_PERFORMED = False


class AdDeletedObjectRestoreExecutionConsumptionError(
    ValueError
):
    pass


class AdDeletedObjectRestoreExecutionConsumptionConflict(
    AdDeletedObjectRestoreExecutionConsumptionError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreExecutionConsumption:
    contract_version: str
    execution_consumption_id: str
    record_digest: str

    state: str
    status: str

    execution_ticket_contract_version: str
    execution_ticket_id: str
    execution_ticket_digest: str

    runtime_gate_id: str
    runtime_gate_digest: str

    authorization_consumption_id: str
    authorization_consumption_record_digest: str

    authorization_id: str
    authorization_digest: str

    preexecution_id: str
    preexecution_digest: str

    object_guid: str
    object_class: str
    class_policy: str
    effective_new_name: str
    effective_target_path: str

    actor_subject: str
    actor_username: str
    actor_issuer: str
    actor_azp: str

    confirmation_sha256: str

    execution_ticket_issued_at: str
    execution_ticket_expires_at: str
    consumed_at: str

    human_authorized: bool
    revalidation_passed: bool

    execution_ticket_consumed: bool
    one_shot_consumption: bool

    persistence_enabled: bool
    route_enabled: bool
    agent_endpoint_enabled: bool
    job_creation_authorized: bool
    claim_authorized: bool
    runtime_authorized: bool
    production_authorized: bool

    restore_authorized: bool
    restore_whatif_authorized: bool
    execution_authorized: bool
    write_performed: bool


def _assert_safe_path(
    path: Path,
) -> None:
    if not path.is_absolute():
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption registry path must be absolute"
        )

    if path.is_symlink():
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption registry path must not be a symlink"
        )


def _open_flags(
    base: int,
) -> int:
    flags = base

    for name in (
        "O_CLOEXEC",
        "O_NOFOLLOW",
    ):
        flags |= getattr(
            os,
            name,
            0,
        )

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

    try:
        fd = os.open(
            lock_file,
            _open_flags(
                os.O_RDWR | os.O_CREAT
            ),
            0o600,
        )
    except OSError as exc:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "unable to open execution consumption registry lock"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdDeletedObjectRestoreExecutionConsumptionError(
                "execution consumption registry lock is not a regular file"
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


def _record_digest_payload(
    record: AdDeletedObjectRestoreExecutionConsumption,
) -> dict[str, Any]:
    payload = asdict(
        record
    )

    payload.pop(
        "record_digest"
    )

    return payload


def assert_ad_deleted_object_restore_execution_consumption_invariants(
    record: AdDeletedObjectRestoreExecutionConsumption,
) -> None:
    if (
        record.contract_version
        != AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption contract mismatch"
        )

    if (
        record.execution_ticket_contract_version
        != AD_DELETED_OBJECT_RESTORE_EXECUTION_TICKET_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution ticket contract mismatch"
        )

    for field in (
        "execution_consumption_id",
        "execution_ticket_id",
        "runtime_gate_id",
        "authorization_consumption_id",
        "authorization_id",
        "preexecution_id",
        "object_guid",
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
        "execution_ticket_digest",
        "runtime_gate_digest",
        "authorization_consumption_record_digest",
        "authorization_digest",
        "preexecution_digest",
        "confirmation_sha256",
    ):
        _required_sha256(
            getattr(
                record,
                field,
            ),
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
            getattr(
                record,
                field,
            ),
            field=field,
        )

    if record.state != "restore_execution_ticket_consumed_dormant":
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption state invalid"
        )

    if record.status != "consumed":
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption status invalid"
        )

    if record.human_authorized is not True:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "human authorization marker missing"
        )

    if record.revalidation_passed is not True:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "revalidation marker missing"
        )

    if record.execution_ticket_consumed is not True:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution ticket consumption marker missing"
        )

    if record.one_shot_consumption is not True:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "one-shot execution consumption marker missing"
        )

    if record.persistence_enabled is not True:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption persistence must be enabled"
        )

    for field in (
        "route_enabled",
        "agent_endpoint_enabled",
        "job_creation_authorized",
        "claim_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "restore_whatif_authorized",
        "execution_authorized",
        "write_performed",
    ):
        if getattr(
            record,
            field,
        ) is not False:
            raise AdDeletedObjectRestoreExecutionConsumptionError(
                f"unsafe execution consumption flag: {field}"
            )

    issued_at = _parse_timestamp(
        record.execution_ticket_issued_at,
        field="execution_ticket_issued_at",
    )

    expires_at = _parse_timestamp(
        record.execution_ticket_expires_at,
        field="execution_ticket_expires_at",
    )

    consumed_at = _parse_timestamp(
        record.consumed_at,
        field="consumed_at",
    )

    if consumed_at < issued_at:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution ticket consumed before issue time"
        )

    if consumed_at >= expires_at:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "expired execution ticket cannot be consumed"
        )

    expected = _canonical_sha256(
        _record_digest_payload(
            record
        )
    )

    if record.record_digest != expected:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption digest mismatch"
        )


def _empty_registry() -> dict[str, Any]:
    return {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_CONTRACT_VERSION,
        "records": [],
    }


def _validate_registry(
    data: Any,
) -> dict[str, Any]:
    if not isinstance(
        data,
        dict,
    ):
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption registry is invalid"
        )

    if (
        data.get("contract_version")
        != AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption registry contract mismatch"
        )

    records = data.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption registry records are invalid"
        )

    if (
        len(records)
        > AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_REGISTRY_MAX_RECORDS
    ):
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption registry is full"
        )

    unique_fields = {
        "execution_consumption_id": set(),
        "execution_ticket_id": set(),
        "execution_ticket_digest": set(),
        "runtime_gate_id": set(),
        "runtime_gate_digest": set(),
        "authorization_consumption_id": set(),
        "authorization_id": set(),
        "preexecution_id": set(),
    }

    for item in records:
        if not isinstance(
            item,
            dict,
        ):
            raise AdDeletedObjectRestoreExecutionConsumptionError(
                "execution consumption registry record is invalid"
            )

        try:
            record = (
                AdDeletedObjectRestoreExecutionConsumption(
                    **item
                )
            )
        except TypeError as exc:
            raise AdDeletedObjectRestoreExecutionConsumptionError(
                "execution consumption registry record schema invalid"
            ) from exc

        assert_ad_deleted_object_restore_execution_consumption_invariants(
            record
        )

        for field, values in unique_fields.items():
            value = getattr(
                record,
                field,
            )

            if value in values:
                raise AdDeletedObjectRestoreExecutionConsumptionError(
                    f"duplicate {field} in execution consumption registry"
                )

            values.add(
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
        return _empty_registry()

    try:
        fd = os.open(
            registry_file,
            _open_flags(
                os.O_RDONLY
            ),
        )
    except OSError as exc:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "unable to open execution consumption registry"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdDeletedObjectRestoreExecutionConsumptionError(
                "execution consumption registry is not a regular file"
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
                raise AdDeletedObjectRestoreExecutionConsumptionError(
                    "execution consumption registry JSON is invalid"
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
    registry: dict[str, Any],
) -> None:
    _validate_registry(
        registry
    )

    temporary = registry_file.with_name(
        "."
        + registry_file.name
        + "."
        + str(
            os.getpid()
        )
        + "."
        + str(
            uuid4()
        )
        + ".tmp"
    )

    _assert_safe_path(
        temporary
    )

    flags = _open_flags(
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
    )

    fd = -1

    try:
        fd = os.open(
            temporary,
            flags,
            0o600,
        )

        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdDeletedObjectRestoreExecutionConsumptionError(
                "temporary execution consumption registry is not regular"
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

            handle.write(
                "\n"
            )

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            registry_file,
        )

        try:
            directory_fd = os.open(
                str(
                    registry_file.parent
                ),
                os.O_DIRECTORY,
            )

            try:
                os.fsync(
                    directory_fd
                )
            finally:
                os.close(
                    directory_fd
                )
        except OSError:
            pass
    finally:
        if fd >= 0:
            os.close(
                fd
            )

        if temporary.exists():
            temporary.unlink(
                missing_ok=True
            )


def consume_ad_deleted_object_restore_execution_ticket(
    execution_ticket: AdDeletedObjectRestoreExecutionTicket,
    *,
    consumption_registry_file: Path,
    server_actor: Mapping[str, Any],
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreExecutionConsumption:
    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption requires Simulation global mode"
        )

    try:
        assert_ad_deleted_object_restore_execution_ticket_invariants(
            execution_ticket
        )
    except AdDeletedObjectRestoreExecutionTicketError as exc:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            str(
                exc
            )
        ) from exc

    if execution_ticket.consumed is not False:
        raise AdDeletedObjectRestoreExecutionConsumptionConflict(
            "execution ticket is already marked consumed"
        )

    if execution_ticket.one_shot_required is not True:
        raise AdDeletedObjectRestoreExecutionConsumptionConflict(
            "execution ticket is not one-shot"
        )

    if execution_ticket.human_authorized is not True:
        raise AdDeletedObjectRestoreExecutionConsumptionConflict(
            "human authorization marker missing"
        )

    if execution_ticket.revalidation_passed is not True:
        raise AdDeletedObjectRestoreExecutionConsumptionConflict(
            "execution ticket revalidation missing"
        )

    if execution_ticket.source_one_shot_verified is not True:
        raise AdDeletedObjectRestoreExecutionConsumptionConflict(
            "source one-shot verification missing"
        )

    for field in (
        "persistence_enabled",
        "route_enabled",
        "agent_endpoints_enabled",
        "job_creation_authorized",
        "claim_authorized",
        "runtime_authorized",
        "production_authorized",
        "write_performed",
    ):
        if getattr(
            execution_ticket,
            field,
        ) is not False:
            raise AdDeletedObjectRestoreExecutionConsumptionConflict(
                f"unsafe execution ticket flag: {field}"
            )

    for field in (
        "controlled_restore_authorized",
        "restore_cmdlet_authorized",
        "restore_whatif_authorized",
        "execution_authorized",
    ):
        if getattr(
            execution_ticket,
            field,
        ) is not True:
            raise AdDeletedObjectRestoreExecutionConsumptionConflict(
                f"execution ticket capability missing: {field}"
            )

    actor = _extract_actor(
        server_actor
    )

    for field, expected in (
        (
            "actor_subject",
            actor["subject"],
        ),
        (
            "actor_username",
            actor["username"],
        ),
        (
            "actor_issuer",
            actor["issuer"],
        ),
        (
            "actor_azp",
            actor["azp"],
        ),
    ):
        if getattr(
            execution_ticket,
            field,
        ) != expected:
            raise AdDeletedObjectRestoreExecutionConsumptionConflict(
                f"actor mismatch: {field}"
            )

    current = _normalize_now(
        now
    )

    issued_at = _parse_timestamp(
        execution_ticket.issued_at,
        field="execution_ticket.issued_at",
    )

    expires_at = _parse_timestamp(
        execution_ticket.expires_at,
        field="execution_ticket.expires_at",
    )

    if current < issued_at:
        raise AdDeletedObjectRestoreExecutionConsumptionConflict(
            "execution ticket cannot be consumed before issue time"
        )

    if current >= expires_at:
        raise AdDeletedObjectRestoreExecutionConsumptionConflict(
            "execution ticket expired before consumption"
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
            len(records)
            >= AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_REGISTRY_MAX_RECORDS
        ):
            raise AdDeletedObjectRestoreExecutionConsumptionError(
                "execution consumption registry is full"
            )

        duplicate_bindings = (
            (
                "execution ticket id",
                "execution_ticket_id",
                execution_ticket.execution_ticket_id,
            ),
            (
                "execution ticket digest",
                "execution_ticket_digest",
                execution_ticket.execution_ticket_digest,
            ),
            (
                "runtime gate id",
                "runtime_gate_id",
                execution_ticket.runtime_gate_id,
            ),
            (
                "runtime gate digest",
                "runtime_gate_digest",
                execution_ticket.runtime_gate_digest,
            ),
            (
                "authorization consumption id",
                "authorization_consumption_id",
                execution_ticket.authorization_consumption_id,
            ),
            (
                "authorization id",
                "authorization_id",
                execution_ticket.authorization_id,
            ),
            (
                "preexecution id",
                "preexecution_id",
                execution_ticket.preexecution_id,
            ),
        )

        for existing in records:
            for label, field, value in duplicate_bindings:
                if existing[field] == value:
                    raise AdDeletedObjectRestoreExecutionConsumptionConflict(
                        f"{label} already consumed"
                    )

        payload = {
            "contract_version":
                AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_CONTRACT_VERSION,

            "execution_consumption_id":
                str(
                    uuid4()
                ),

            "state":
                "restore_execution_ticket_consumed_dormant",

            "status":
                "consumed",

            "execution_ticket_contract_version":
                execution_ticket.contract_version,

            "execution_ticket_id":
                execution_ticket.execution_ticket_id,

            "execution_ticket_digest":
                execution_ticket.execution_ticket_digest,

            "runtime_gate_id":
                execution_ticket.runtime_gate_id,

            "runtime_gate_digest":
                execution_ticket.runtime_gate_digest,

            "authorization_consumption_id":
                execution_ticket.authorization_consumption_id,

            "authorization_consumption_record_digest":
                execution_ticket.authorization_consumption_record_digest,

            "authorization_id":
                execution_ticket.authorization_id,

            "authorization_digest":
                execution_ticket.authorization_digest,

            "preexecution_id":
                execution_ticket.preexecution_id,

            "preexecution_digest":
                execution_ticket.preexecution_digest,

            "object_guid":
                execution_ticket.object_guid.lower(),

            "object_class":
                execution_ticket.object_class,

            "class_policy":
                execution_ticket.class_policy,

            "effective_new_name":
                execution_ticket.effective_new_name,

            "effective_target_path":
                execution_ticket.effective_target_path,

            "actor_subject":
                execution_ticket.actor_subject,

            "actor_username":
                execution_ticket.actor_username,

            "actor_issuer":
                execution_ticket.actor_issuer,

            "actor_azp":
                execution_ticket.actor_azp,

            "confirmation_sha256":
                execution_ticket.confirmation_sha256,

            "execution_ticket_issued_at":
                execution_ticket.issued_at,

            "execution_ticket_expires_at":
                execution_ticket.expires_at,

            "consumed_at":
                current.isoformat(),

            "human_authorized":
                True,

            "revalidation_passed":
                True,

            "execution_ticket_consumed":
                True,

            "one_shot_consumption":
                True,

            "persistence_enabled":
                True,

            "route_enabled":
                False,

            "agent_endpoint_enabled":
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

            "execution_authorized":
                False,

            "write_performed":
                False,
        }

        record = (
            AdDeletedObjectRestoreExecutionConsumption(
                record_digest=(
                    _canonical_sha256(
                        payload
                    )
                ),
                **payload,
            )
        )

        assert_ad_deleted_object_restore_execution_consumption_invariants(
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


def get_ad_deleted_object_restore_execution_consumption(
    *,
    consumption_registry_file: Path,
    execution_consumption_id: str,
) -> AdDeletedObjectRestoreExecutionConsumption:
    raw_id = str(
        execution_consumption_id or ""
    ).strip()

    try:
        normalized_id = str(
            UUID(
                raw_id
            )
        )
    except (
        ValueError,
        AttributeError,
        TypeError,
    ) as exc:
        raise AdDeletedObjectRestoreExecutionConsumptionError(
            "execution consumption id invalid"
        ) from exc

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

    with _exclusive_registry_lock(
        consumption_registry_file
    ):
        registry = _load_registry(
            consumption_registry_file
        )

        matches = [
            item
            for item in registry[
                "records"
            ]
            if str(
                item.get(
                    "execution_consumption_id"
                )
                or ""
            ).lower()
            == normalized_id.lower()
        ]

        if not matches:
            raise AdDeletedObjectRestoreExecutionConsumptionError(
                "execution consumption record not found"
            )

        if len(
            matches
        ) != 1:
            raise AdDeletedObjectRestoreExecutionConsumptionError(
                "duplicate execution consumption id"
            )

        try:
            record = (
                AdDeletedObjectRestoreExecutionConsumption(
                    **matches[
                        0
                    ]
                )
            )
        except TypeError as exc:
            raise AdDeletedObjectRestoreExecutionConsumptionError(
                "execution consumption record schema invalid"
            ) from exc

        assert_ad_deleted_object_restore_execution_consumption_invariants(
            record
        )

        return record


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_CONTRACT_VERSION",
    "AdDeletedObjectRestoreExecutionConsumption",
    "AdDeletedObjectRestoreExecutionConsumptionConflict",
    "AdDeletedObjectRestoreExecutionConsumptionError",
    "assert_ad_deleted_object_restore_execution_consumption_invariants",
    "consume_ad_deleted_object_restore_execution_ticket",
    "get_ad_deleted_object_restore_execution_consumption",
]
