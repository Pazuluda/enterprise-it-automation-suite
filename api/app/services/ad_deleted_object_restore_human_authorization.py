from __future__ import annotations

import fcntl
import json
import os
import stat

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Mapping
from uuid import UUID

from app.services.ad_deleted_object_restore_authorization import (
    AdDeletedObjectRestoreAuthorizationConflict,
    AdDeletedObjectRestoreAuthorizationError,
    build_ad_deleted_object_restore_authorization,
)
from app.services.ad_deleted_object_restore_authorization_persistence import (
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,
    AdDeletedObjectRestoreAuthorizationPersistence,
    AdDeletedObjectRestoreAuthorizationPersistenceError,
    assert_ad_deleted_object_restore_authorization_persistence_invariants,
    persist_ad_deleted_object_restore_authorization,
)
from app.services.ad_deleted_object_restore_ticket_consumption import (
    AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CONTRACT_VERSION,
    AdDeletedObjectRestoreTicketConsumption,
    AdDeletedObjectRestoreTicketConsumptionError,
    assert_ad_deleted_object_restore_ticket_consumption_invariants,
)
from app.services.ad_deleted_object_restore_ticket_persistence import (
    AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION,
    AdDeletedObjectRestoreTicketPersistence,
    AdDeletedObjectRestoreTicketPersistenceError,
    assert_ad_deleted_object_restore_ticket_persistence_invariants,
)


AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_CONTRACT_VERSION = (
    "c9.5r2e1d4e2-v1"
)

AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_ENABLED = True

AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_ROUTE_ENABLED = False

AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_RUNTIME_AUTHORIZED = False

AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_PRODUCTION_AUTHORIZED = False

AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_RESTORE_AUTHORIZED = False

AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_RESTORE_WHATIF_AUTHORIZED = (
    False
)

AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_EXECUTION_AUTHORIZED = False

AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_WRITE_PERFORMED = False


class AdDeletedObjectRestoreHumanAuthorizationError(
    ValueError
):
    pass


class AdDeletedObjectRestoreHumanAuthorizationConflict(
    AdDeletedObjectRestoreHumanAuthorizationError
):
    pass


class AdDeletedObjectRestoreHumanAuthorizationNotFound(
    AdDeletedObjectRestoreHumanAuthorizationError
):
    pass


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
    text = _clean(
        value
    )

    try:
        parsed = UUID(
            text
        )

    except Exception as exc:
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            f"{field} must be a UUID"
        ) from exc

    return str(
        parsed
    )


def _assert_absolute_path(
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
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            f"{field} must be absolute"
        )

    if path.is_symlink():
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            f"{field} must not be a symlink"
        )

    current = path.parent

    while True:
        if current.is_symlink():
            raise AdDeletedObjectRestoreHumanAuthorizationError(
                f"{field} parent must not be a symlink"
            )

        if (
            current.exists()
            and not current.is_dir()
        ):
            raise AdDeletedObjectRestoreHumanAuthorizationError(
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

def _load_registry_records(
    path: Path,
    *,
    field: str,
    expected_contract_version: str,
    required: bool,
) -> list[dict[str, Any]]:
    path = _assert_absolute_path(
        path,
        field=field,
    )

    if not path.exists():
        if required:
            raise AdDeletedObjectRestoreHumanAuthorizationNotFound(
                f"{field} not found"
            )

        return []

    fd = -1

    try:
        fd = os.open(
            path,
            _open_flags(
                os.O_RDONLY
            ),
        )

    except FileNotFoundError as exc:
        if required:
            raise AdDeletedObjectRestoreHumanAuthorizationNotFound(
                f"{field} not found"
            ) from exc

        return []

    except OSError as exc:
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            f"unable to open {field}"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(
                fd
            ).st_mode
        ):
            raise AdDeletedObjectRestoreHumanAuthorizationError(
                f"{field} must be a regular file"
            )

        with os.fdopen(
            fd,
            "r",
            encoding="utf-8",
        ) as handle:
            fd = -1

            try:
                payload = json.load(
                    handle
                )

            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
            ) as exc:
                raise AdDeletedObjectRestoreHumanAuthorizationError(
                    f"{field} contains invalid JSON"
                ) from exc

    finally:
        if fd >= 0:
            os.close(
                fd
            )

    if not isinstance(
        payload,
        dict,
    ):
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            f"{field} registry must be an object"
        )

    if (
        payload.get(
            "contract_version"
        )
        != expected_contract_version
    ):
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            f"{field} contract mismatch"
        )

    records = payload.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            f"{field} records are invalid"
        )

    if any(
        not isinstance(
            record,
            dict,
        )
        for record in records
    ):
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            f"{field} contains an invalid record"
        )

    return records

def _load_ticket_record(
    registry_file: Path,
    *,
    ticket_id: str,
) -> AdDeletedObjectRestoreTicketPersistence:
    records = _load_registry_records(
        registry_file,
        field="ticket_registry_file",
        expected_contract_version=(
            AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION
        ),
        required=True,
    )

    matches = [
        record
        for record in records
        if _clean(
            record.get(
                "ticket_id"
            )
        )
        == ticket_id
    ]

    if not matches:
        raise AdDeletedObjectRestoreHumanAuthorizationNotFound(
            "restore ticket not found"
        )

    if len(
        matches
    ) != 1:
        raise AdDeletedObjectRestoreHumanAuthorizationConflict(
            "restore ticket is not unique"
        )

    try:
        ticket = (
            AdDeletedObjectRestoreTicketPersistence(
                **matches[0]
            )
        )

        assert_ad_deleted_object_restore_ticket_persistence_invariants(
            ticket
        )

    except (
        TypeError,
        AdDeletedObjectRestoreTicketPersistenceError,
    ) as exc:
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            "restore ticket record is invalid"
        ) from exc

    return ticket


def _load_consumption_record(
    registry_file: Path,
    *,
    consumption_id: str,
) -> AdDeletedObjectRestoreTicketConsumption:
    records = _load_registry_records(
        registry_file,
        field="ticket_consumption_registry_file",
        expected_contract_version=(
            AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CONTRACT_VERSION
        ),
        required=True,
    )

    matches = [
        record
        for record in records
        if _clean(
            record.get(
                "consumption_id"
            )
        )
        == consumption_id
    ]

    if not matches:
        raise AdDeletedObjectRestoreHumanAuthorizationNotFound(
            "restore ticket consumption not found"
        )

    if len(
        matches
    ) != 1:
        raise AdDeletedObjectRestoreHumanAuthorizationConflict(
            "restore ticket consumption is not unique"
        )

    try:
        consumption = (
            AdDeletedObjectRestoreTicketConsumption(
                **matches[0]
            )
        )

        assert_ad_deleted_object_restore_ticket_consumption_invariants(
            consumption
        )

    except (
        TypeError,
        AdDeletedObjectRestoreTicketConsumptionError,
    ) as exc:
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            "restore ticket consumption record is invalid"
        ) from exc

    return consumption


def _load_authorization_records(
    registry_file: Path,
) -> list[AdDeletedObjectRestoreAuthorizationPersistence]:
    records = _load_registry_records(
        registry_file,
        field="authorization_registry_file",
        expected_contract_version=(
            AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION
        ),
        required=False,
    )

    result = []

    for raw_record in records:
        try:
            record = (
                AdDeletedObjectRestoreAuthorizationPersistence(
                    **raw_record
                )
            )

            assert_ad_deleted_object_restore_authorization_persistence_invariants(
                record
            )

        except (
            TypeError,
            AdDeletedObjectRestoreAuthorizationPersistenceError,
        ) as exc:
            raise AdDeletedObjectRestoreHumanAuthorizationError(
                "restore authorization registry contains "
                "an invalid record"
            ) from exc

        result.append(
            record
        )

    return result


@contextmanager
def _exclusive_human_authorization_lock(
    authorization_registry_file: Path,
):
    authorization_registry_file = (
        _assert_absolute_path(
            authorization_registry_file,
            field="authorization_registry_file",
        )
    )

    parent = (
        authorization_registry_file.parent
    )

    if (
        not parent.exists()
        or not parent.is_dir()
    ):
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            "human authorization registry parent must already exist"
        )

    _assert_absolute_path(
        parent,
        field="human_authorization_registry_parent",
    )

    lock_file = (
        parent
        / ".ad-deleted-object-restore-human-authorization.lock"
    )

    _assert_absolute_path(
        lock_file,
        field="human_authorization_lock",
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
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            "unable to open human authorization lock"
        ) from exc

    try:
        if not stat.S_ISREG(
            os.fstat(
                fd
            ).st_mode
        ):
            raise AdDeletedObjectRestoreHumanAuthorizationError(
                "human authorization lock is not a regular file"
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

def _assert_authorization_not_reused(
    authorization_registry_file: Path,
    *,
    ticket: AdDeletedObjectRestoreTicketPersistence,
    consumption: AdDeletedObjectRestoreTicketConsumption,
) -> None:
    records = _load_authorization_records(
        authorization_registry_file
    )

    for record in records:
        if (
            record.ticket_id
            == ticket.ticket_id
            or record.consumption_id
            == consumption.consumption_id
            or record.source_simulation_job_id
            == ticket.source_simulation_job_id
        ):
            raise AdDeletedObjectRestoreHumanAuthorizationConflict(
                "restore ticket chain already has "
                "a human authorization"
            )


def _assert_persisted_binding(
    record: AdDeletedObjectRestoreAuthorizationPersistence,
    *,
    ticket: AdDeletedObjectRestoreTicketPersistence,
    consumption: AdDeletedObjectRestoreTicketConsumption,
) -> None:
    expected = {
        "ticket_id":
            ticket.ticket_id,

        "ticket_digest":
            ticket.ticket_digest,

        "consumption_id":
            consumption.consumption_id,

        "consumption_record_digest":
            consumption.record_digest,

        "source_simulation_job_id":
            ticket.source_simulation_job_id,

        "source_inventory_job_id":
            ticket.source_inventory_job_id,

        "source_live_job_id":
            ticket.source_live_job_id,

        "fresh_live_job_id":
            ticket.fresh_live_job_id,

        "fresh_live_sha256":
            ticket.fresh_live_sha256,

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
    }

    for field, value in (
        expected.items()
    ):
        if (
            getattr(
                record,
                field,
            )
            != value
        ):
            raise AdDeletedObjectRestoreHumanAuthorizationError(
                f"persisted authorization binding mismatch: {field}"
            )

    if (
        record.one_shot_required
        is not True
        or record.authorization_consumed
        is not False
        or record.human_authorized
        is not True
    ):
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            "persisted human authorization state is invalid"
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
        if (
            getattr(
                record,
                field,
            )
            is not False
        ):
            raise AdDeletedObjectRestoreHumanAuthorizationError(
                f"unsafe persisted authorization flag: {field}"
            )


def build_and_persist_ad_deleted_object_restore_human_authorization(
    *,
    ticket_registry_file: Path,
    ticket_consumption_registry_file: Path,
    authorization_registry_file: Path,
    server_actor: Mapping[str, Any],
    payload: Mapping[str, Any],
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreAuthorizationPersistence:
    if not (
        AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_ENABLED
    ):
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            "human authorization bridge disabled"
        )

    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            "human authorization bridge is Simulation-only"
        )

    if not isinstance(
        payload,
        Mapping,
    ):
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            "human authorization payload is invalid"
        )

    ticket_id = _uuid(
        payload.get(
            "ticket_id"
        ),
        field="payload.ticket_id",
    )

    consumption_id = _uuid(
        payload.get(
            "consumption_id"
        ),
        field="payload.consumption_id",
    )

    ticket_registry_file = (
        _assert_absolute_path(
            ticket_registry_file,
            field="ticket_registry_file",
        )
    )

    ticket_consumption_registry_file = (
        _assert_absolute_path(
            ticket_consumption_registry_file,
            field="ticket_consumption_registry_file",
        )
    )

    authorization_registry_file = (
        _assert_absolute_path(
            authorization_registry_file,
            field="authorization_registry_file",
        )
    )

    ticket = _load_ticket_record(
        ticket_registry_file,
        ticket_id=ticket_id,
    )

    consumption = _load_consumption_record(
        ticket_consumption_registry_file,
        consumption_id=consumption_id,
    )

    if (
        ticket.ticket_id
        != consumption.ticket_id
    ):
        raise AdDeletedObjectRestoreHumanAuthorizationConflict(
            "ticket/consumption ticket id mismatch"
        )

    if (
        ticket.ticket_digest
        != consumption.ticket_digest
    ):
        raise AdDeletedObjectRestoreHumanAuthorizationConflict(
            "ticket/consumption digest mismatch"
        )

    try:
        with _exclusive_human_authorization_lock(
            authorization_registry_file
        ):
            _assert_authorization_not_reused(
                authorization_registry_file,
                ticket=ticket,
                consumption=consumption,
            )

            authorization = (
                build_ad_deleted_object_restore_authorization(
                    ticket,
                    consumption,
                    server_actor=server_actor,
                    payload=payload,
                    current_mode=current_mode,
                    now=now,
                )
            )

            record = (
                persist_ad_deleted_object_restore_authorization(
                    authorization,
                    registry_file=(
                        authorization_registry_file
                    ),
                    now=now,
                )
            )

    except AdDeletedObjectRestoreAuthorizationConflict as exc:
        raise AdDeletedObjectRestoreHumanAuthorizationConflict(
            str(exc)
        ) from exc

    except (
        AdDeletedObjectRestoreAuthorizationError,
        AdDeletedObjectRestoreAuthorizationPersistenceError,
    ) as exc:
        raise AdDeletedObjectRestoreHumanAuthorizationError(
            str(exc)
        ) from exc

    assert_ad_deleted_object_restore_authorization_persistence_invariants(
        record
    )

    _assert_persisted_binding(
        record,
        ticket=ticket,
        consumption=consumption,
    )

    return record


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_CONTRACT_VERSION",
    "AdDeletedObjectRestoreHumanAuthorizationConflict",
    "AdDeletedObjectRestoreHumanAuthorizationError",
    "AdDeletedObjectRestoreHumanAuthorizationNotFound",
    "build_and_persist_ad_deleted_object_restore_human_authorization",
]
