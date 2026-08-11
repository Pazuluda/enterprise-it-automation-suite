from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat

from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Mapping
from uuid import UUID

from app.services.ad_deleted_object_restore_authorization_persistence import (
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,
    AdDeletedObjectRestoreAuthorizationPersistence,
    AdDeletedObjectRestoreAuthorizationPersistenceError,
    assert_ad_deleted_object_restore_authorization_persistence_invariants,
)
from app.services.ad_deleted_object_restore_preexecution import (
    AdDeletedObjectRestorePreexecutionConflict,
    AdDeletedObjectRestorePreexecutionError,
    build_ad_deleted_object_restore_preexecution,
)
from app.services.ad_deleted_object_restore_authorization_consumption import (
    AdDeletedObjectRestoreAuthorizationConsumptionConflict,
    AdDeletedObjectRestoreAuthorizationConsumptionError,
    consume_ad_deleted_object_restore_authorization,
)
from app.services.ad_deleted_object_restore_runtime_gate import (
    AdDeletedObjectRestoreRuntimeGateConflict,
    AdDeletedObjectRestoreRuntimeGateError,
    build_ad_deleted_object_restore_runtime_gate,
)
from app.services.ad_deleted_object_restore_execution_ticket import (
    AdDeletedObjectRestoreExecutionTicketConflict,
    AdDeletedObjectRestoreExecutionTicketError,
    build_ad_deleted_object_restore_execution_ticket,
    expected_ad_deleted_object_restore_confirmation,
)
from app.services.ad_deleted_object_restore_execution_consumption import (
    AdDeletedObjectRestoreExecutionConsumption,
    AdDeletedObjectRestoreExecutionConsumptionConflict,
    AdDeletedObjectRestoreExecutionConsumptionError,
    assert_ad_deleted_object_restore_execution_consumption_invariants,
    consume_ad_deleted_object_restore_execution_ticket,
)


AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_CONTRACT_VERSION = (
    "c9.5r2e1d4e3-v1"
)

AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_ENABLED = True

AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_AGENT_ENDPOINT_ENABLED = False

AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_PRODUCTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_RESTORE_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_EXECUTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_WRITE_PERFORMED = False


class AdDeletedObjectRestorePostAuthorizationError(
    ValueError
):
    pass


class AdDeletedObjectRestorePostAuthorizationConflict(
    AdDeletedObjectRestorePostAuthorizationError
):
    pass


class AdDeletedObjectRestorePostAuthorizationNotFound(
    AdDeletedObjectRestorePostAuthorizationError
):
    pass


@dataclass(
    frozen=True
)
class AdDeletedObjectRestorePostAuthorizationResult:
    contract_version: str

    state: str
    status: str

    authorization_id: str
    preexecution_id: str
    authorization_consumption_id: str
    runtime_gate_id: str
    execution_ticket_id: str
    execution_consumption_id: str

    object_guid: str
    object_class: str
    effective_new_name: str
    effective_target_path: str

    confirmation_text: str

    human_authorized: bool
    revalidation_passed: bool
    authorization_consumed: bool
    execution_ticket_consumed: bool

    runtime_authorized: bool
    production_authorized: bool
    restore_authorized: bool
    execution_authorized: bool
    write_performed: bool


_AUTHORIZATION_KEYS = {
    item.name
    for item in fields(
        AdDeletedObjectRestoreAuthorizationPersistence
    )
}


def _clean(
    value: Any,
) -> str:
    return str(
        value
        if value is not None
        else ""
    ).strip()


def _uuid(
    value: Any,
    *,
    field: str,
) -> str:
    raw = _clean(
        value
    )

    try:
        return str(
            UUID(
                raw
            )
        )

    except Exception as exc:
        raise AdDeletedObjectRestorePostAuthorizationError(
            f"{field} must be a UUID"
        ) from exc


def _sha256(
    value: Any,
    *,
    field: str,
) -> str:
    raw = _clean(
        value
    ).lower()

    if (
        len(
            raw
        )
        != 64
        or any(
            character
            not in "0123456789abcdef"
            for character in raw
        )
    ):
        raise AdDeletedObjectRestorePostAuthorizationError(
            f"{field} must be SHA-256"
        )

    return raw


def _safe_absolute_path(
    path: Path,
    *,
    field: str,
) -> Path:
    if not isinstance(
        path,
        Path,
    ):
        path = Path(
            path
        )

    if not path.is_absolute():
        raise AdDeletedObjectRestorePostAuthorizationError(
            f"{field} must be absolute"
        )

    if path.is_symlink():
        raise AdDeletedObjectRestorePostAuthorizationError(
            f"{field} must not be a symlink"
        )

    current = path.parent

    while True:
        if current.is_symlink():
            raise AdDeletedObjectRestorePostAuthorizationError(
                f"{field} parent must not be a symlink"
            )

        if (
            current.exists()
            and not current.is_dir()
        ):
            raise AdDeletedObjectRestorePostAuthorizationError(
                f"{field} parent must be a directory"
            )

        if current == current.parent:
            break

        current = current.parent

    return path


def _open_flags(
    base_flags: int,
) -> int:
    flags = base_flags

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

def _load_authorization_record(
    registry_file: Path,
    *,
    authorization_id: str,
) -> AdDeletedObjectRestoreAuthorizationPersistence:
    registry_file = _safe_absolute_path(
        registry_file,
        field="authorization_registry_file",
    )

    if not registry_file.exists():
        raise AdDeletedObjectRestorePostAuthorizationNotFound(
            "restore authorization registry not found"
        )

    fd = -1

    try:
        fd = os.open(
            registry_file,
            _open_flags(
                os.O_RDONLY
            ),
        )

    except FileNotFoundError as exc:
        raise AdDeletedObjectRestorePostAuthorizationNotFound(
            "restore authorization registry not found"
        ) from exc

    except OSError as exc:
        raise AdDeletedObjectRestorePostAuthorizationError(
            "unable to open restore authorization registry"
        ) from exc

    try:
        info = os.fstat(
            fd
        )

        if not stat.S_ISREG(
            info.st_mode
        ):
            raise AdDeletedObjectRestorePostAuthorizationError(
                "restore authorization registry is not a regular file"
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

            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
            ) as exc:
                raise AdDeletedObjectRestorePostAuthorizationError(
                    "restore authorization registry JSON is invalid"
                ) from exc

    finally:
        if fd >= 0:
            os.close(
                fd
            )

    if not isinstance(
        data,
        dict,
    ):
        raise AdDeletedObjectRestorePostAuthorizationError(
            "restore authorization registry is invalid"
        )

    if (
        data.get(
            "contract_version"
        )
        != AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestorePostAuthorizationError(
            "restore authorization registry contract mismatch"
        )

    records = data.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise AdDeletedObjectRestorePostAuthorizationError(
            "restore authorization records are invalid"
        )

    matches = []

    for raw in records:
        if not isinstance(
            raw,
            dict,
        ):
            raise AdDeletedObjectRestorePostAuthorizationError(
                "restore authorization record is invalid"
            )

        if set(
            raw
        ) != _AUTHORIZATION_KEYS:
            raise AdDeletedObjectRestorePostAuthorizationError(
                "restore authorization record schema mismatch"
            )

        try:
            record = (
                AdDeletedObjectRestoreAuthorizationPersistence(
                    **raw
                )
            )

            assert_ad_deleted_object_restore_authorization_persistence_invariants(
                record
            )

        except (
            TypeError,
            AdDeletedObjectRestoreAuthorizationPersistenceError,
        ) as exc:
            raise AdDeletedObjectRestorePostAuthorizationError(
                "restore authorization record invariants failed"
            ) from exc

        if (
            record.authorization_id
            == authorization_id
        ):
            matches.append(
                record
            )

    if not matches:
        raise AdDeletedObjectRestorePostAuthorizationNotFound(
            "restore authorization not found"
        )

    if len(
        matches
    ) != 1:
        raise AdDeletedObjectRestorePostAuthorizationConflict(
            "restore authorization is not unique"
        )

    return matches[0]

@contextmanager
def _exclusive_post_authorization_lock(
    authorization_consumption_registry_file: Path,
):
    path = _safe_absolute_path(
        authorization_consumption_registry_file,
        field="authorization_consumption_registry_file",
    )

    parent = path.parent

    if (
        not parent.exists()
        or not parent.is_dir()
    ):
        raise AdDeletedObjectRestorePostAuthorizationError(
            "post-authorization registry parent must already exist"
        )

    _safe_absolute_path(
        parent,
        field="post_authorization_registry_parent",
    )

    lock_file = (
        parent
        / ".ad-deleted-object-restore-post-authorization.lock"
    )

    _safe_absolute_path(
        lock_file,
        field="post_authorization_lock",
    )

    try:
        fd = os.open(
            lock_file,
            _open_flags(
                os.O_CREAT
                | os.O_RDWR
            ),
            0o600,
        )

    except OSError as exc:
        raise AdDeletedObjectRestorePostAuthorizationError(
            "unable to open post-authorization lock"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(
                fd
            ).st_mode
        ):
            raise AdDeletedObjectRestorePostAuthorizationError(
                "post-authorization lock is not a regular file"
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

def _confirmation_sha256(
    confirmation_text: str,
) -> str:
    payload = {
        "confirmation_text":
            confirmation_text,
    }

    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        canonical
    ).hexdigest()


def _assert_final_consumption(
    consumption: AdDeletedObjectRestoreExecutionConsumption,
    *,
    authorization: AdDeletedObjectRestoreAuthorizationPersistence,
    confirmation_text: str,
) -> None:
    assert_ad_deleted_object_restore_execution_consumption_invariants(
        consumption
    )

    expected = {
        "authorization_id":
            authorization.authorization_id,

        "authorization_digest":
            authorization.authorization_digest,

        "object_guid":
            authorization.object_guid,

        "object_class":
            authorization.object_class,

        "effective_new_name":
            authorization.effective_new_name,

        "effective_target_path":
            authorization.effective_target_path,
    }

    for field, value in expected.items():
        actual = getattr(
            consumption,
            field,
        )

        if (
            field
            == "object_guid"
        ):
            matches = (
                actual.lower()
                == value.lower()
            )

        else:
            matches = (
                actual
                == value
            )

        if not matches:
            raise AdDeletedObjectRestorePostAuthorizationError(
                f"final execution consumption binding mismatch: {field}"
            )

    confirmation_sha256 = (
        _confirmation_sha256(
            confirmation_text
        )
    )

    if (
        consumption.confirmation_sha256
        != confirmation_sha256
    ):
        raise AdDeletedObjectRestorePostAuthorizationError(
            "final confirmation digest mismatch"
        )

    if (
        consumption.human_authorized
        is not True
        or consumption.revalidation_passed
        is not True
        or consumption.execution_ticket_consumed
        is not True
        or consumption.one_shot_consumption
        is not True
    ):
        raise AdDeletedObjectRestorePostAuthorizationError(
            "final execution consumption proof is incomplete"
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
        if (
            getattr(
                consumption,
                field,
            )
            is not False
        ):
            raise AdDeletedObjectRestorePostAuthorizationError(
                f"unsafe final execution consumption flag: {field}"
            )


def build_ad_deleted_object_restore_post_authorization_chain(
    *,
    authorization_registry_file: Path,
    authorization_consumption_registry_file: Path,
    execution_consumption_registry_file: Path,
    jobs_path: Path,
    authorization_id: str,
    authorization_digest: str,
    fresh_live_job_id: str,
    server_actor: Mapping[str, Any],
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestorePostAuthorizationResult:
    if not (
        AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_ENABLED
    ):
        raise AdDeletedObjectRestorePostAuthorizationError(
            "post-authorization bridge disabled"
        )

    if current_mode != "Simulation":
        raise AdDeletedObjectRestorePostAuthorizationError(
            "post-authorization bridge is Simulation-only"
        )

    normalized_authorization_id = _uuid(
        authorization_id,
        field="authorization_id",
    )

    normalized_authorization_digest = _sha256(
        authorization_digest,
        field="authorization_digest",
    )

    normalized_fresh_live_job_id = _uuid(
        fresh_live_job_id,
        field="fresh_live_job_id",
    )

    authorization_registry_file = _safe_absolute_path(
        authorization_registry_file,
        field="authorization_registry_file",
    )

    authorization_consumption_registry_file = _safe_absolute_path(
        authorization_consumption_registry_file,
        field="authorization_consumption_registry_file",
    )

    execution_consumption_registry_file = _safe_absolute_path(
        execution_consumption_registry_file,
        field="execution_consumption_registry_file",
    )

    jobs_path = _safe_absolute_path(
        jobs_path,
        field="jobs_path",
    )

    authorization = _load_authorization_record(
        authorization_registry_file,
        authorization_id=(
            normalized_authorization_id
        ),
    )

    if (
        authorization.authorization_digest
        != normalized_authorization_digest
    ):
        raise AdDeletedObjectRestorePostAuthorizationConflict(
            "authorization digest mismatch"
        )

    try:
        with _exclusive_post_authorization_lock(
            authorization_consumption_registry_file
        ):
            preexecution = (
                build_ad_deleted_object_restore_preexecution(
                    authorization,
                    jobs_path=jobs_path,
                    fresh_live_job_id=(
                        normalized_fresh_live_job_id
                    ),
                    expected_authorization_id=(
                        authorization.authorization_id
                    ),
                    expected_authorization_digest=(
                        authorization.authorization_digest
                    ),
                    expected_object_guid=(
                        authorization.object_guid
                    ),
                    confirmed_new_name=(
                        authorization.effective_new_name
                    ),
                    confirmed_target_path=(
                        authorization.effective_target_path
                    ),
                    server_actor=(
                        server_actor
                    ),
                    current_mode=(
                        current_mode
                    ),
                    now=now,
                )
            )

            authorization_consumption = (
                consume_ad_deleted_object_restore_authorization(
                    authorization,
                    preexecution,
                    consumption_registry_file=(
                        authorization_consumption_registry_file
                    ),
                    server_actor=(
                        server_actor
                    ),
                    current_mode=(
                        current_mode
                    ),
                    now=now,
                )
            )

            runtime_gate = (
                build_ad_deleted_object_restore_runtime_gate(
                    authorization_consumption,
                    server_actor=(
                        server_actor
                    ),
                    current_mode=(
                        current_mode
                    ),
                    now=now,
                )
            )

            confirmation_text = (
                expected_ad_deleted_object_restore_confirmation(
                    runtime_gate
                )
            )

            execution_ticket = (
                build_ad_deleted_object_restore_execution_ticket(
                    runtime_gate,
                    server_actor=(
                        server_actor
                    ),
                    current_mode=(
                        current_mode
                    ),
                    confirmation_text=(
                        confirmation_text
                    ),
                    now=now,
                )
            )

            execution_consumption = (
                consume_ad_deleted_object_restore_execution_ticket(
                    execution_ticket,
                    consumption_registry_file=(
                        execution_consumption_registry_file
                    ),
                    server_actor=(
                        server_actor
                    ),
                    current_mode=(
                        current_mode
                    ),
                    now=now,
                )
            )

    except (
        AdDeletedObjectRestorePreexecutionConflict,
        AdDeletedObjectRestoreAuthorizationConsumptionConflict,
        AdDeletedObjectRestoreRuntimeGateConflict,
        AdDeletedObjectRestoreExecutionTicketConflict,
        AdDeletedObjectRestoreExecutionConsumptionConflict,
    ) as exc:
        raise AdDeletedObjectRestorePostAuthorizationConflict(
            str(
                exc
            )
        ) from exc

    except (
        AdDeletedObjectRestorePreexecutionError,
        AdDeletedObjectRestoreAuthorizationConsumptionError,
        AdDeletedObjectRestoreRuntimeGateError,
        AdDeletedObjectRestoreExecutionTicketError,
        AdDeletedObjectRestoreExecutionConsumptionError,
    ) as exc:
        raise AdDeletedObjectRestorePostAuthorizationError(
            str(
                exc
            )
        ) from exc

    _assert_final_consumption(
        execution_consumption,
        authorization=authorization,
        confirmation_text=confirmation_text,
    )

    return AdDeletedObjectRestorePostAuthorizationResult(
        contract_version=(
            AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_CONTRACT_VERSION
        ),

        state=(
            "restore_post_authorization_ready_for_queue"
        ),

        status=(
            "ready_for_final_confirmation"
        ),

        authorization_id=(
            authorization.authorization_id
        ),

        preexecution_id=(
            preexecution.preexecution_id
        ),

        authorization_consumption_id=(
            authorization_consumption.authorization_consumption_id
        ),

        runtime_gate_id=(
            runtime_gate.runtime_gate_id
        ),

        execution_ticket_id=(
            execution_ticket.execution_ticket_id
        ),

        execution_consumption_id=(
            execution_consumption.execution_consumption_id
        ),

        object_guid=(
            authorization.object_guid
        ),

        object_class=(
            authorization.object_class
        ),

        effective_new_name=(
            authorization.effective_new_name
        ),

        effective_target_path=(
            authorization.effective_target_path
        ),

        confirmation_text=(
            confirmation_text
        ),

        human_authorized=True,
        revalidation_passed=True,
        authorization_consumed=True,
        execution_ticket_consumed=True,

        runtime_authorized=False,
        production_authorized=False,
        restore_authorized=False,
        execution_authorized=False,
        write_performed=False,
    )


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_CONTRACT_VERSION",
    "AdDeletedObjectRestorePostAuthorizationConflict",
    "AdDeletedObjectRestorePostAuthorizationError",
    "AdDeletedObjectRestorePostAuthorizationNotFound",
    "AdDeletedObjectRestorePostAuthorizationResult",
    "build_ad_deleted_object_restore_post_authorization_chain",
]
