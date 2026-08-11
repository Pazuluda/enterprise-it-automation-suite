from __future__ import annotations

import fcntl
import json
import os
import stat

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.services.ad_deleted_object_restore_authorization_consumption import (
    _canonical_sha256,
    _normalize_now,
    _parse_timestamp,
    _required_sha256,
    _required_string,
    _required_uuid,
)

from app.services.ad_deleted_object_restore_windows_execution_envelope import (
    AdDeletedObjectRestoreWindowsExecutionEnvelope,
    AdDeletedObjectRestoreWindowsExecutionEnvelopeError,
    assert_ad_deleted_object_restore_windows_execution_envelope_invariants,
)


AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_CONTRACT_VERSION = (
    "c9.5a5e2-v1"
)

AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_CLAIM_CONTRACT_VERSION = (
    "c9.5a5e2-claim-v1"
)

AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_MAX_RECORDS = 256

AD_DELETED_OBJECT_RESTORE_EXECUTION_RESULT_MAX_AGE_SECONDS = 60

AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_SERVICE_ENABLED = True

# R3 is backend-only and remains disconnected.
AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_AGENT_ENDPOINTS_ENABLED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_GENERIC_DISPATCH_ENABLED = False

# Global Production is never opened by this transport.
AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_PRODUCTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_WRITE_PERFORMED = False


class AdDeletedObjectRestoreExecutionTransportError(
    ValueError
):
    pass


class AdDeletedObjectRestoreExecutionTransportConflict(
    AdDeletedObjectRestoreExecutionTransportError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreExecutionTransportTicket:
    contract_version: str
    state: str

    transport_ticket_id: str

    envelope_id: str
    execution_consumption_id: str
    execution_ticket_id: str
    runtime_gate_id: str
    authorization_consumption_id: str
    authorization_id: str
    preexecution_id: str

    object_guid: str
    effective_new_name: str
    effective_target_path: str

    created_at: str
    expires_at: str

    payload_digest: str

    controlled_restore_runtime_authorized: bool
    production_authorized: bool
    write_performed: bool


@dataclass(frozen=True)
class AdDeletedObjectRestoreExecutionTransportClaim:
    contract_version: str
    state: str

    transport_ticket_id: str
    transport_execution_id: str

    envelope_id: str
    execution_consumption_id: str
    execution_ticket_id: str

    claimed_at: str
    claimed_by: str
    expires_at: str

    payload_digest: str
    payload: dict[str, Any]

    controlled_restore_runtime_authorized: bool
    production_authorized: bool
    write_performed: bool


@dataclass(frozen=True)
class AdDeletedObjectRestoreExecutionTransportCompletion:
    contract_version: str
    state: str

    transport_ticket_id: str
    transport_execution_id: str

    envelope_id: str
    execution_consumption_id: str
    execution_ticket_id: str

    completed_at: str
    completed_by: str

    success: bool
    write_performed: bool

    completion_digest: str

    controlled_restore_runtime_authorized: bool
    production_authorized: bool


def _assert_safe_path(
    path: Path,
) -> None:
    if not path.is_absolute():
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport registry path must be absolute"
        )

    if path.is_symlink():
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport registry path must not be a symlink"
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
        raise AdDeletedObjectRestoreExecutionTransportError(
            "unable to open transport registry lock"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport registry lock is not a regular file"
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


def _empty_registry() -> dict[str, Any]:
    return {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_CONTRACT_VERSION,
        "records": [],
    }


def _payload_digest(
    payload: dict[str, Any],
) -> str:
    return _canonical_sha256(
        payload
    )


def _envelope_from_payload(
    payload: Any,
) -> AdDeletedObjectRestoreWindowsExecutionEnvelope:
    if not isinstance(
        payload,
        dict,
    ):
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport payload is invalid"
        )

    try:
        envelope = (
            AdDeletedObjectRestoreWindowsExecutionEnvelope(
                **payload
            )
        )
    except TypeError as exc:
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport payload schema is invalid"
        ) from exc

    try:
        assert_ad_deleted_object_restore_windows_execution_envelope_invariants(
            envelope
        )
    except AdDeletedObjectRestoreWindowsExecutionEnvelopeError as exc:
        raise AdDeletedObjectRestoreExecutionTransportError(
            str(
                exc
            )
        ) from exc

    return envelope


def _validate_record(
    record: Any,
) -> dict[str, Any]:
    if not isinstance(
        record,
        dict,
    ):
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport record is invalid"
        )

    if (
        record.get("contract_version")
        != AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport record contract mismatch"
        )

    state = str(
        record.get("state")
        or ""
    )

    if state not in {
        "restore_execution_pending",
        "restore_execution_processing",
        "restore_execution_completed",
        "restore_execution_failed",
    }:
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport record state invalid"
        )

    for field in (
        "transport_ticket_id",
        "envelope_id",
        "execution_consumption_id",
        "execution_ticket_id",
        "runtime_gate_id",
        "authorization_consumption_id",
        "authorization_id",
        "preexecution_id",
        "object_guid",
    ):
        _required_uuid(
            record.get(
                field
            ),
            field=field,
        )

    _required_sha256(
        record.get(
            "payload_digest"
        ),
        field="payload_digest",
    )

    for field in (
        "effective_new_name",
        "effective_target_path",
    ):
        _required_string(
            record.get(
                field
            ),
            field=field,
        )

    created_at = _parse_timestamp(
        record.get(
            "created_at"
        ),
        field="created_at",
    )

    expires_at = _parse_timestamp(
        record.get(
            "expires_at"
        ),
        field="expires_at",
    )

    if expires_at <= created_at:
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport record expiration invalid"
        )

    payload = record.get(
        "payload"
    )

    if (
        record.get("payload_digest")
        != _payload_digest(
            payload
        )
    ):
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport payload digest mismatch"
        )

    envelope = _envelope_from_payload(
        payload
    )

    exact = {
        "envelope_id":
            envelope.envelope_id,

        "execution_consumption_id":
            envelope.execution_consumption_id,

        "execution_ticket_id":
            envelope.execution_ticket_id,

        "runtime_gate_id":
            envelope.runtime_gate_id,

        "authorization_consumption_id":
            envelope.authorization_consumption_id,

        "authorization_id":
            envelope.authorization_id,

        "preexecution_id":
            envelope.preexecution_id,

        "object_guid":
            envelope.object_guid.lower(),

        "effective_new_name":
            envelope.effective_new_name,

        "effective_target_path":
            envelope.effective_target_path,

        "expires_at":
            envelope.expires_at,
    }

    for field, expected in exact.items():
        actual = record.get(
            field
        )

        if (
            field == "object_guid"
            and isinstance(
                actual,
                str,
            )
        ):
            actual = actual.lower()

        if actual != expected:
            raise AdDeletedObjectRestoreExecutionTransportError(
                f"transport/envelope binding mismatch: {field}"
            )

    if record.get(
        "production_authorized"
    ) is not False:
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport Production authorization forbidden"
        )

    runtime_flag = record.get(
        "controlled_restore_runtime_authorized"
    )

    if state == "restore_execution_pending":
        if record.get(
            "controlled_restore_runtime_authorized"
        ) is not False:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "pending transport cannot authorize runtime"
            )

        if record.get(
            "write_performed"
        ) is not False:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "pending transport cannot report write"
            )

        for field in (
            "transport_execution_id",
            "claimed_at",
            "claimed_by",
            "completed_at",
            "completed_by",
            "success",
            "completion_digest",
            "result_summary",
            "error_message",
        ):
            if field in record:
                raise AdDeletedObjectRestoreExecutionTransportError(
                    "pending transport contains execution fields"
                )

    if state == "restore_execution_processing":
        if record.get(
            "controlled_restore_runtime_authorized"
        ) is not True:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "processing transport runtime authorization missing"
            )

        if record.get(
            "write_performed"
        ) is not False:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "processing transport cannot report write"
            )

        _required_uuid(
            record.get(
                "transport_execution_id"
            ),
            field="transport_execution_id",
        )

        _required_string(
            record.get(
                "claimed_by"
            ),
            field="claimed_by",
        )

        claimed_at = _parse_timestamp(
            record.get(
                "claimed_at"
            ),
            field="claimed_at",
        )

        if claimed_at < created_at:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport claimed before creation"
            )

        if claimed_at >= expires_at:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport claimed after expiration"
            )

        for field in (
            "completed_at",
            "completed_by",
            "success",
            "completion_digest",
            "result_summary",
            "error_message",
        ):
            if field in record:
                raise AdDeletedObjectRestoreExecutionTransportError(
                    "processing transport contains completion fields"
                )

    if state in {
        "restore_execution_completed",
        "restore_execution_failed",
    }:
        if record.get(
            "controlled_restore_runtime_authorized"
        ) is not False:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "completed transport cannot retain runtime authorization"
            )

        _required_uuid(
            record.get(
                "transport_execution_id"
            ),
            field="transport_execution_id",
        )

        for field in (
            "claimed_by",
            "completed_by",
        ):
            _required_string(
                record.get(
                    field
                ),
                field=field,
            )

        claimed_at = _parse_timestamp(
            record.get(
                "claimed_at"
            ),
            field="claimed_at",
        )

        completed_at = _parse_timestamp(
            record.get(
                "completed_at"
            ),
            field="completed_at",
        )

        if claimed_at < created_at:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport claimed before creation"
            )

        if claimed_at >= expires_at:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport claimed after expiration"
            )

        if completed_at < claimed_at:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport completed before claim"
            )

        success = record.get(
            "success"
        )

        if success is not True and success is not False:
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport completion success must be boolean"
            )

        write_performed = record.get(
            "write_performed"
        )

        if (
            write_performed is not True
            and write_performed is not False
        ):
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport completion write marker must be boolean"
            )

        if not isinstance(
            record.get(
                "result_summary"
            ),
            dict,
        ):
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport completion result summary invalid"
            )

        _required_sha256(
            record.get(
                "completion_digest"
            ),
            field="completion_digest",
        )

        expected_completion_digest = _canonical_sha256(
            {
                "transport_ticket_id":
                    record["transport_ticket_id"],

                "transport_execution_id":
                    record["transport_execution_id"],

                "envelope_id":
                    record["envelope_id"],

                "execution_consumption_id":
                    record["execution_consumption_id"],

                "execution_ticket_id":
                    record["execution_ticket_id"],

                "object_guid":
                    record["object_guid"],

                "claimed_at":
                    record["claimed_at"],

                "claimed_by":
                    record["claimed_by"],

                "completed_at":
                    record["completed_at"],

                "completed_by":
                    record["completed_by"],

                "success":
                    success,

                "write_performed":
                    write_performed,

                "result_summary":
                    record["result_summary"],

                "error_message":
                    record.get(
                        "error_message"
                    ),
            }
        )

        if (
            record["completion_digest"]
            != expected_completion_digest
        ):
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport completion digest mismatch"
            )

        if state == "restore_execution_completed":
            if success is not True:
                raise AdDeletedObjectRestoreExecutionTransportError(
                    "completed transport success marker invalid"
                )

            if write_performed is not True:
                raise AdDeletedObjectRestoreExecutionTransportError(
                    "successful restore must report write"
                )

            if record.get(
                "error_message"
            ) is not None:
                raise AdDeletedObjectRestoreExecutionTransportError(
                    "successful restore cannot contain error message"
                )

        if state == "restore_execution_failed":
            if success is not False:
                raise AdDeletedObjectRestoreExecutionTransportError(
                    "failed transport success marker invalid"
                )

            _required_string(
                record.get(
                    "error_message"
                ),
                field="error_message",
            )

    return record


def _validate_registry(
    data: Any,
) -> dict[str, Any]:
    if not isinstance(
        data,
        dict,
    ):
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport registry is invalid"
        )

    if (
        data.get("contract_version")
        != AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport registry contract mismatch"
        )

    records = data.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport registry records are invalid"
        )

    if (
        len(records)
        > AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_MAX_RECORDS
    ):
        raise AdDeletedObjectRestoreExecutionTransportError(
            "transport registry is full"
        )

    unique_fields = {
        "transport_ticket_id": set(),
        "envelope_id": set(),
        "execution_consumption_id": set(),
        "execution_ticket_id": set(),
        "runtime_gate_id": set(),
        "authorization_consumption_id": set(),
        "authorization_id": set(),
        "preexecution_id": set(),
    }

    for record in records:
        _validate_record(
            record
        )

        for field, values in unique_fields.items():
            value = record[
                field
            ]

            if value in values:
                raise AdDeletedObjectRestoreExecutionTransportError(
                    f"duplicate {field} in transport registry"
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
        raise AdDeletedObjectRestoreExecutionTransportError(
            "unable to open transport registry"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport registry is not a regular file"
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
                raise AdDeletedObjectRestoreExecutionTransportError(
                    "transport registry JSON is invalid"
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

    fd = -1

    try:
        fd = os.open(
            temporary,
            _open_flags(
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
            ),
            0o600,
        )

        if not stat.S_ISREG(
            os.fstat(fd).st_mode
        ):
            raise AdDeletedObjectRestoreExecutionTransportError(
                "temporary transport registry is not regular"
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

        os.chmod(
            registry_file,
            0o600,
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


def _ticket_from_record(
    record: dict[str, Any],
) -> AdDeletedObjectRestoreExecutionTransportTicket:
    return AdDeletedObjectRestoreExecutionTransportTicket(
        contract_version=record["contract_version"],
        state=record["state"],

        transport_ticket_id=record["transport_ticket_id"],

        envelope_id=record["envelope_id"],
        execution_consumption_id=record["execution_consumption_id"],
        execution_ticket_id=record["execution_ticket_id"],
        runtime_gate_id=record["runtime_gate_id"],
        authorization_consumption_id=record["authorization_consumption_id"],
        authorization_id=record["authorization_id"],
        preexecution_id=record["preexecution_id"],

        object_guid=record["object_guid"],
        effective_new_name=record["effective_new_name"],
        effective_target_path=record["effective_target_path"],

        created_at=record["created_at"],
        expires_at=record["expires_at"],

        payload_digest=record["payload_digest"],

        controlled_restore_runtime_authorized=(
            record["controlled_restore_runtime_authorized"]
        ),

        production_authorized=record["production_authorized"],
        write_performed=record["write_performed"],
    )


def queue_ad_deleted_object_restore_execution(
    envelope: AdDeletedObjectRestoreWindowsExecutionEnvelope,
    *,
    transport_registry_file: Path,
    signing_secret: str,
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreExecutionTransportTicket:
    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreExecutionTransportError(
            "controlled restore transport requires Simulation global mode"
        )

    try:
        assert_ad_deleted_object_restore_windows_execution_envelope_invariants(
            envelope,
            signing_secret=signing_secret,
        )
    except AdDeletedObjectRestoreWindowsExecutionEnvelopeError as exc:
        raise AdDeletedObjectRestoreExecutionTransportError(
            str(
                exc
            )
        ) from exc

    current = _normalize_now(
        now
    )

    issued_at = _parse_timestamp(
        envelope.issued_at,
        field="envelope.issued_at",
    )

    expires_at = _parse_timestamp(
        envelope.expires_at,
        field="envelope.expires_at",
    )

    if current < issued_at:
        raise AdDeletedObjectRestoreExecutionTransportConflict(
            "execution envelope has not started"
        )

    if current >= expires_at:
        raise AdDeletedObjectRestoreExecutionTransportConflict(
            "execution envelope expired before queue"
        )

    if not isinstance(
        transport_registry_file,
        Path,
    ):
        transport_registry_file = Path(
            transport_registry_file
        )

    _assert_safe_path(
        transport_registry_file
    )

    transport_registry_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _assert_safe_path(
        transport_registry_file
    )

    payload = asdict(
        envelope
    )

    payload_digest = _payload_digest(
        payload
    )

    with _exclusive_registry_lock(
        transport_registry_file
    ):
        registry = _load_registry(
            transport_registry_file
        )

        records = registry[
            "records"
        ]

        if (
            len(records)
            >= AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_MAX_RECORDS
        ):
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport registry is full"
            )

        duplicate_bindings = (
            (
                "envelope id",
                "envelope_id",
                envelope.envelope_id,
            ),
            (
                "execution consumption id",
                "execution_consumption_id",
                envelope.execution_consumption_id,
            ),
            (
                "execution ticket id",
                "execution_ticket_id",
                envelope.execution_ticket_id,
            ),
            (
                "runtime gate id",
                "runtime_gate_id",
                envelope.runtime_gate_id,
            ),
            (
                "authorization consumption id",
                "authorization_consumption_id",
                envelope.authorization_consumption_id,
            ),
            (
                "authorization id",
                "authorization_id",
                envelope.authorization_id,
            ),
            (
                "preexecution id",
                "preexecution_id",
                envelope.preexecution_id,
            ),
        )

        for existing in records:
            for label, field, value in duplicate_bindings:
                if existing[field] == value:
                    raise AdDeletedObjectRestoreExecutionTransportConflict(
                        f"{label} already queued"
                    )

        record = {
            "contract_version":
                AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_CONTRACT_VERSION,

            "state":
                "restore_execution_pending",

            "transport_ticket_id":
                str(
                    uuid4()
                ),

            "envelope_id":
                envelope.envelope_id,

            "execution_consumption_id":
                envelope.execution_consumption_id,

            "execution_ticket_id":
                envelope.execution_ticket_id,

            "runtime_gate_id":
                envelope.runtime_gate_id,

            "authorization_consumption_id":
                envelope.authorization_consumption_id,

            "authorization_id":
                envelope.authorization_id,

            "preexecution_id":
                envelope.preexecution_id,

            "object_guid":
                envelope.object_guid.lower(),

            "effective_new_name":
                envelope.effective_new_name,

            "effective_target_path":
                envelope.effective_target_path,

            "created_at":
                current.isoformat(),

            "expires_at":
                envelope.expires_at,

            "payload_digest":
                payload_digest,

            "payload":
                payload,

            "controlled_restore_runtime_authorized":
                False,

            "production_authorized":
                False,

            "write_performed":
                False,
        }

        _validate_record(
            record
        )

        records.append(
            record
        )

        _atomic_write_registry(
            transport_registry_file,
            registry,
        )

    return _ticket_from_record(
        record
    )


def list_pending_ad_deleted_object_restore_executions(
    *,
    transport_registry_file: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = _normalize_now(
        now
    )

    if not isinstance(
        transport_registry_file,
        Path,
    ):
        transport_registry_file = Path(
            transport_registry_file
        )

    _assert_safe_path(
        transport_registry_file
    )

    with _exclusive_registry_lock(
        transport_registry_file
    ):
        registry = _load_registry(
            transport_registry_file
        )

        tickets = []

        for record in registry[
            "records"
        ]:
            if (
                record["state"]
                != "restore_execution_pending"
            ):
                continue

            expires_at = _parse_timestamp(
                record["expires_at"],
                field="expires_at",
            )

            if current >= expires_at:
                continue

            ticket = _ticket_from_record(
                record
            )

            tickets.append(
                asdict(
                    ticket
                )
            )

        tickets.sort(
            key=lambda item:
                item["created_at"]
        )

        return {
            "count":
                len(
                    tickets
                ),
            "tickets":
                tickets,
        }


def claim_ad_deleted_object_restore_execution_for_agent(
    *,
    transport_registry_file: Path,
    transport_ticket_id: str,
    agent_name: str,
    signing_secret: str,
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreExecutionTransportClaim:
    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreExecutionTransportError(
            "controlled restore claim requires Simulation global mode"
        )

    normalized_ticket_id = _required_string(
        transport_ticket_id,
        field="transport_ticket_id",
    )

    normalized_agent_name = _required_string(
        agent_name,
        field="agent_name",
    )

    current = _normalize_now(
        now
    )

    if not isinstance(
        transport_registry_file,
        Path,
    ):
        transport_registry_file = Path(
            transport_registry_file
        )

    _assert_safe_path(
        transport_registry_file
    )

    with _exclusive_registry_lock(
        transport_registry_file
    ):
        registry = _load_registry(
            transport_registry_file
        )

        matches = [
            record
            for record in registry[
                "records"
            ]
            if record[
                "transport_ticket_id"
            ]
            == normalized_ticket_id
        ]

        if len(matches) != 1:
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "transport ticket unavailable"
            )

        record = matches[
            0
        ]

        if (
            record["state"]
            != "restore_execution_pending"
        ):
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "transport ticket is not pending"
            )

        expires_at = _parse_timestamp(
            record["expires_at"],
            field="expires_at",
        )

        if current >= expires_at:
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "transport ticket expired before claim"
            )

        envelope = _envelope_from_payload(
            record[
                "payload"
            ]
        )

        try:
            assert_ad_deleted_object_restore_windows_execution_envelope_invariants(
                envelope,
                signing_secret=signing_secret,
            )
        except AdDeletedObjectRestoreWindowsExecutionEnvelopeError as exc:
            raise AdDeletedObjectRestoreExecutionTransportError(
                str(
                    exc
                )
            ) from exc

        envelope_issued_at = _parse_timestamp(
            envelope.issued_at,
            field="envelope.issued_at",
        )

        envelope_expires_at = _parse_timestamp(
            envelope.expires_at,
            field="envelope.expires_at",
        )

        if current < envelope_issued_at:
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "execution envelope has not started at claim"
            )

        if current >= envelope_expires_at:
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "execution envelope expired before claim"
            )

        transport_execution_id = str(
            uuid4()
        )

        claimed_at = current.isoformat()

        record[
            "state"
        ] = "restore_execution_processing"

        record[
            "transport_execution_id"
        ] = transport_execution_id

        record[
            "claimed_at"
        ] = claimed_at

        record[
            "claimed_by"
        ] = normalized_agent_name

        record[
            "controlled_restore_runtime_authorized"
        ] = True

        record[
            "production_authorized"
        ] = False

        record[
            "write_performed"
        ] = False

        _validate_record(
            record
        )

        _atomic_write_registry(
            transport_registry_file,
            registry,
        )

        payload_copy = json.loads(
            json.dumps(
                record[
                    "payload"
                ]
            )
        )

        return AdDeletedObjectRestoreExecutionTransportClaim(
            contract_version=(
                AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_CLAIM_CONTRACT_VERSION
            ),

            state="restore_execution_processing",

            transport_ticket_id=(
                record[
                    "transport_ticket_id"
                ]
            ),

            transport_execution_id=(
                transport_execution_id
            ),

            envelope_id=(
                record[
                    "envelope_id"
                ]
            ),

            execution_consumption_id=(
                record[
                    "execution_consumption_id"
                ]
            ),

            execution_ticket_id=(
                record[
                    "execution_ticket_id"
                ]
            ),

            claimed_at=claimed_at,
            claimed_by=normalized_agent_name,
            expires_at=record["expires_at"],

            payload_digest=(
                record[
                    "payload_digest"
                ]
            ),

            payload=payload_copy,

            controlled_restore_runtime_authorized=True,

            production_authorized=False,
            write_performed=False,
        )


def _validate_completion_result_bindings(
    *,
    record: dict[str, Any],
    result: dict[str, Any],
) -> AdDeletedObjectRestoreWindowsExecutionEnvelope:
    if not isinstance(
        result,
        dict,
    ):
        raise AdDeletedObjectRestoreExecutionTransportError(
            "restore execution result must be an object"
        )

    envelope = _envelope_from_payload(
        record[
            "payload"
        ]
    )

    exact = {
        "contract_version":
            "c9.5a5e3-v1",

        "action":
            "restore_deleted_object_execute",

        "global_mode":
            "Simulation",

        "envelope_id":
            envelope.envelope_id,

        "execution_consumption_id":
            envelope.execution_consumption_id,

        "execution_ticket_id":
            envelope.execution_ticket_id,

        "object_guid":
            envelope.object_guid.lower(),

        "effective_new_name":
            envelope.effective_new_name,

        "effective_target_path":
            envelope.effective_target_path,

        "production_authorized":
            False,
    }

    for field, expected in exact.items():
        actual = result.get(
            field
        )

        if (
            field == "object_guid"
            and isinstance(
                actual,
                str,
            )
        ):
            actual = actual.lower()

        if actual != expected:
            raise AdDeletedObjectRestoreExecutionTransportError(
                f"restore execution result mismatch: {field}"
            )

    for field in (
        "signature_verified",
        "restore_performed",
        "write_performed",
    ):
        if (
            result.get(
                field
            )
            is not True
            and result.get(
                field
            )
            is not False
        ):
            raise AdDeletedObjectRestoreExecutionTransportError(
                f"restore execution result boolean invalid: {field}"
            )

    if (
        result["restore_performed"]
        is not result["write_performed"]
    ):
        raise AdDeletedObjectRestoreExecutionTransportError(
            "restore/write result markers disagree"
        )

    return envelope


def _validate_success_result(
    *,
    record: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    _validate_completion_result_bindings(
        record=record,
        result=result,
    )

    required_true = (
        "signature_verified",
        "fresh_deleted_object_verified",
        "fresh_target_verified",
        "controlled_restore_runtime_authorized",
        "restore_performed",
        "write_performed",
        "post_restore_object_guid_verified",
        "post_restore_target_present",
        "post_restore_deleted_object_absent",
    )

    for field in required_true:
        if result.get(
            field
        ) is not True:
            raise AdDeletedObjectRestoreExecutionTransportError(
                f"successful restore marker missing: {field}"
            )

    if result.get(
        "target_collision"
    ) is not False:
        raise AdDeletedObjectRestoreExecutionTransportError(
            "successful restore collision marker invalid"
        )

    return {
        "contract_version":
            "c9.5a5e3-v1",

        "action":
            "restore_deleted_object_execute",

        "global_mode":
            "Simulation",

        "envelope_id":
            record["envelope_id"],

        "execution_consumption_id":
            record["execution_consumption_id"],

        "execution_ticket_id":
            record["execution_ticket_id"],

        "object_guid":
            record["object_guid"],

        "effective_new_name":
            record["effective_new_name"],

        "effective_target_path":
            record["effective_target_path"],

        "signature_verified":
            True,

        "fresh_deleted_object_verified":
            True,

        "fresh_target_verified":
            True,

        "target_collision":
            False,

        "controlled_restore_runtime_authorized":
            True,

        "restore_performed":
            True,

        "write_performed":
            True,

        "post_restore_object_guid_verified":
            True,

        "post_restore_target_present":
            True,

        "post_restore_deleted_object_absent":
            True,

        "production_authorized":
            False,
    }


def _validate_failure_result(
    *,
    record: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    _validate_completion_result_bindings(
        record=record,
        result=result,
    )

    return {
        "contract_version":
            "c9.5a5e3-v1",

        "action":
            "restore_deleted_object_execute",

        "global_mode":
            "Simulation",

        "envelope_id":
            record["envelope_id"],

        "execution_consumption_id":
            record["execution_consumption_id"],

        "execution_ticket_id":
            record["execution_ticket_id"],

        "object_guid":
            record["object_guid"],

        "effective_new_name":
            record["effective_new_name"],

        "effective_target_path":
            record["effective_target_path"],

        "signature_verified":
            result["signature_verified"],

        "restore_performed":
            result["restore_performed"],

        "write_performed":
            result["write_performed"],

        "production_authorized":
            False,
    }


def complete_ad_deleted_object_restore_execution(
    *,
    transport_registry_file: Path,
    transport_ticket_id: str,
    transport_execution_id: str,
    agent_name: str,
    signing_secret: str,
    current_mode: str,
    success: bool,
    result: dict[str, Any],
    message: str = "",
    now: datetime | None = None,
) -> AdDeletedObjectRestoreExecutionTransportCompletion:
    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreExecutionTransportError(
            "controlled restore completion requires Simulation global mode"
        )

    if success is not True and success is not False:
        raise AdDeletedObjectRestoreExecutionTransportError(
            "restore execution success must be boolean"
        )

    normalized_ticket_id = _required_string(
        transport_ticket_id,
        field="transport_ticket_id",
    )

    normalized_execution_id = _required_string(
        transport_execution_id,
        field="transport_execution_id",
    )

    normalized_agent_name = _required_string(
        agent_name,
        field="agent_name",
    )

    current = _normalize_now(
        now
    )

    if not isinstance(
        transport_registry_file,
        Path,
    ):
        transport_registry_file = Path(
            transport_registry_file
        )

    _assert_safe_path(
        transport_registry_file
    )

    with _exclusive_registry_lock(
        transport_registry_file
    ):
        registry = _load_registry(
            transport_registry_file
        )

        matches = [
            record
            for record in registry[
                "records"
            ]
            if record[
                "transport_ticket_id"
            ]
            == normalized_ticket_id
        ]

        if len(
            matches
        ) != 1:
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "transport ticket unavailable for completion"
            )

        record = matches[
            0
        ]

        if (
            record["state"]
            != "restore_execution_processing"
        ):
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "transport execution is not processing"
            )

        if (
            record.get(
                "controlled_restore_runtime_authorized"
            )
            is not True
        ):
            raise AdDeletedObjectRestoreExecutionTransportError(
                "transport runtime authorization missing"
            )

        if (
            record.get(
                "transport_execution_id"
            )
            != normalized_execution_id
        ):
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "transport execution id mismatch"
            )

        if (
            record.get(
                "claimed_by"
            )
            != normalized_agent_name
        ):
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "restore execution claimed by another agent"
            )

        envelope = _envelope_from_payload(
            record[
                "payload"
            ]
        )

        try:
            assert_ad_deleted_object_restore_windows_execution_envelope_invariants(
                envelope,
                signing_secret=signing_secret,
            )
        except AdDeletedObjectRestoreWindowsExecutionEnvelopeError as exc:
            raise AdDeletedObjectRestoreExecutionTransportError(
                str(
                    exc
                )
            ) from exc

        claimed_at = _parse_timestamp(
            record[
                "claimed_at"
            ],
            field="claimed_at",
        )

        if current < claimed_at:
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "restore completion predates claim"
            )

        if (
            current
            - claimed_at
            > timedelta(
                seconds=(
                    AD_DELETED_OBJECT_RESTORE_EXECUTION_RESULT_MAX_AGE_SECONDS
                )
            )
        ):
            raise AdDeletedObjectRestoreExecutionTransportConflict(
                "restore completion is too old"
            )

        error_message = str(
            message or ""
        ).strip()

        if success:
            result_summary = (
                _validate_success_result(
                    record=record,
                    result=result,
                )
            )

            write_performed = True

            record[
                "state"
            ] = "restore_execution_completed"

            record[
                "error_message"
            ] = None

        else:
            if not error_message:
                raise AdDeletedObjectRestoreExecutionTransportError(
                    "restore failure message required"
                )

            result_summary = (
                _validate_failure_result(
                    record=record,
                    result=result,
                )
            )

            write_performed = bool(
                result_summary[
                    "write_performed"
                ]
            )

            record[
                "state"
            ] = "restore_execution_failed"

            record[
                "error_message"
            ] = error_message[
                :1024
            ]

        completed_at = current.isoformat()

        record[
            "completed_at"
        ] = completed_at

        record[
            "completed_by"
        ] = normalized_agent_name

        record[
            "success"
        ] = success

        record[
            "result_summary"
        ] = result_summary

        record[
            "controlled_restore_runtime_authorized"
        ] = False

        record[
            "production_authorized"
        ] = False

        record[
            "write_performed"
        ] = write_performed

        record[
            "completion_digest"
        ] = _canonical_sha256(
            {
                "transport_ticket_id":
                    record["transport_ticket_id"],

                "transport_execution_id":
                    record["transport_execution_id"],

                "envelope_id":
                    record["envelope_id"],

                "execution_consumption_id":
                    record["execution_consumption_id"],

                "execution_ticket_id":
                    record["execution_ticket_id"],

                "object_guid":
                    record["object_guid"],

                "claimed_at":
                    record["claimed_at"],

                "claimed_by":
                    record["claimed_by"],

                "completed_at":
                    record["completed_at"],

                "completed_by":
                    record["completed_by"],

                "success":
                    record["success"],

                "write_performed":
                    record["write_performed"],

                "result_summary":
                    record["result_summary"],

                "error_message":
                    record.get(
                        "error_message"
                    ),
            }
        )

        _validate_record(
            record
        )

        _atomic_write_registry(
            transport_registry_file,
            registry,
        )

        return AdDeletedObjectRestoreExecutionTransportCompletion(
            contract_version=(
                AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_CONTRACT_VERSION
            ),

            state=record["state"],

            transport_ticket_id=(
                record[
                    "transport_ticket_id"
                ]
            ),

            transport_execution_id=(
                record[
                    "transport_execution_id"
                ]
            ),

            envelope_id=(
                record[
                    "envelope_id"
                ]
            ),

            execution_consumption_id=(
                record[
                    "execution_consumption_id"
                ]
            ),

            execution_ticket_id=(
                record[
                    "execution_ticket_id"
                ]
            ),

            completed_at=completed_at,
            completed_by=normalized_agent_name,

            success=success,
            write_performed=write_performed,

            completion_digest=(
                record[
                    "completion_digest"
                ]
            ),

            controlled_restore_runtime_authorized=False,
            production_authorized=False,
        )


def assert_ad_deleted_object_restore_execution_transport_invariants() -> None:
    if not AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_SERVICE_ENABLED:
        raise RuntimeError(
            "A5E2 transport service must remain enabled for isolated tests"
        )

    if AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_ROUTE_ENABLED:
        raise RuntimeError(
            "A5E2 human route must remain disabled in R3"
        )

    if AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_AGENT_ENDPOINTS_ENABLED:
        raise RuntimeError(
            "A5E2 agent endpoints must remain disabled in R3"
        )

    if AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_GENERIC_DISPATCH_ENABLED:
        raise RuntimeError(
            "A5E2 generic dispatcher must remain disabled"
        )

    if AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_PRODUCTION_AUTHORIZED:
        raise RuntimeError(
            "A5E2 must not authorize global Production"
        )

    if AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_WRITE_PERFORMED:
        raise RuntimeError(
            "A5E2 transport must not perform AD writes"
        )


assert_ad_deleted_object_restore_execution_transport_invariants()


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_CONTRACT_VERSION",
    "AD_DELETED_OBJECT_RESTORE_EXECUTION_TRANSPORT_CLAIM_CONTRACT_VERSION",
    "AdDeletedObjectRestoreExecutionTransportClaim",
    "AdDeletedObjectRestoreExecutionTransportConflict",
    "AdDeletedObjectRestoreExecutionTransportError",
    "AdDeletedObjectRestoreExecutionTransportTicket",
    "claim_ad_deleted_object_restore_execution_for_agent",
    "complete_ad_deleted_object_restore_execution",
    "list_pending_ad_deleted_object_restore_executions",
    "queue_ad_deleted_object_restore_execution",
]
