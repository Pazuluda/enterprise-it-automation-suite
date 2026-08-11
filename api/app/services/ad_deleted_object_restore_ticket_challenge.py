from __future__ import annotations

import fcntl
import hashlib
import json
import os

from contextlib import contextmanager
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID
from uuid import uuid4

from app.services.ad_deleted_object_restore_ticket import (
    AdDeletedObjectRestoreTicketError,
    build_ad_deleted_object_restore_ticket,
)
from app.services.ad_deleted_object_restore_ticket_consumption import (
    AdDeletedObjectRestoreTicketConsumptionConflict,
    AdDeletedObjectRestoreTicketConsumptionError,
    consume_ad_deleted_object_restore_ticket,
)
from app.services.ad_deleted_object_restore_ticket_persistence import (
    AdDeletedObjectRestoreTicketPersistenceError,
    persist_ad_deleted_object_restore_ticket,
)


AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_CONTRACT_VERSION = (
    "c9.5r2e1d1-v1"
)

AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_ENABLED = True

AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_ROUTE_ENABLED = False

AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_RUNTIME_AUTHORIZED = False

AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_PRODUCTION_AUTHORIZED = False

AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_RESTORE_AUTHORIZED = False

AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_EXECUTION_AUTHORIZED = False

AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_WRITE_PERFORMED = False


class AdDeletedObjectRestoreTicketChallengeError(
    ValueError
):
    pass


class AdDeletedObjectRestoreTicketChallengeConflict(
    AdDeletedObjectRestoreTicketChallengeError
):
    pass


class AdDeletedObjectRestoreTicketChallengeNotFound(
    AdDeletedObjectRestoreTicketChallengeError
):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreTicketChallenge:
    contract_version: str
    challenge_id: str

    state: str

    ticket_persistence_contract_version: str
    ticket_id: str
    ticket_digest: str

    ticket_consumption_contract_version: str
    consumption_id: str
    consumption_record_digest: str

    source_simulation_job_id: str
    source_inventory_job_id: str
    source_live_job_id: str
    fresh_live_job_id: str
    fresh_live_sha256: str

    object_guid: str
    object_class: str
    class_policy: str

    effective_new_name: str
    effective_target_path: str

    created_at: str

    one_shot_required: bool

    human_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    restore_authorized: bool
    restore_whatif_authorized: bool
    execution_authorized: bool
    write_performed: bool

    challenge_digest: str


def _canonical_sha256(
    payload: dict[str, Any],
) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        raw
    ).hexdigest()


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
        raise AdDeletedObjectRestoreTicketChallengeError(
            f"{field} must be a UUID"
        ) from exc

    return str(
        parsed
    )


def _assert_sha256(
    value: Any,
    field: str,
) -> str:
    text = _clean(
        value
    ).lower()

    if (
        len(text) != 64
        or any(
            character
            not in "0123456789abcdef"
            for character in text
        )
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            f"{field} must be SHA-256"
        )

    return text


def _assert_absolute_path(
    path: Path,
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
        raise AdDeletedObjectRestoreTicketChallengeError(
            f"{field} must be absolute"
        )

    if (
        path.exists()
        and path.is_symlink()
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            f"{field} must not be a symlink"
        )

    return path


def _load_json(
    path: Path,
    *,
    field: str,
) -> Any:
    path = _assert_absolute_path(
        path,
        field,
    )

    if not path.exists():
        raise AdDeletedObjectRestoreTicketChallengeNotFound(
            f"{field} not found"
        )

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        raise AdDeletedObjectRestoreTicketChallengeError(
            f"{field} contains invalid JSON"
        ) from exc


def _registry_records(
    path: Path,
    *,
    field: str,
) -> list[dict[str, Any]]:
    path = _assert_absolute_path(
        path,
        field,
    )

    if not path.exists():
        return []

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        raise AdDeletedObjectRestoreTicketChallengeError(
            f"{field} contains invalid JSON"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            f"{field} registry must be an object"
        )

    records = payload.get(
        "records"
    )

    if not isinstance(
        records,
        list,
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            f"{field} registry records are invalid"
        )

    if any(
        not isinstance(
            record,
            dict,
        )
        for record in records
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            f"{field} registry contains invalid record"
        )

    return records


def _find_source_simulation_job(
    ad_admin_jobs_file: Path,
    *,
    simulation_job_id: str,
) -> dict[str, Any]:
    data = _load_json(
        ad_admin_jobs_file,
        field="ad_admin_jobs_file",
    )

    if not isinstance(
        data,
        list,
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            "AD Admin job storage must contain a JSON list"
        )

    matches = [
        job
        for job in data
        if (
            isinstance(
                job,
                dict,
            )
            and _clean(
                job.get("id")
            )
            == simulation_job_id
        )
    ]

    if not matches:
        raise AdDeletedObjectRestoreTicketChallengeNotFound(
            "source Simulation job not found"
        )

    if len(matches) != 1:
        raise AdDeletedObjectRestoreTicketChallengeConflict(
            "source Simulation job is not unique"
        )

    source = matches[0]

    if (
        source.get("type")
        != "ad_admin"
        or source.get("action")
        != "simulate_deleted_object_restore"
        or source.get("status")
        != "prepared"
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            "source Simulation job is not a prepared restore Simulation"
        )

    if (
        source.get("claimed_at")
        is not None
        or source.get("claimed_by")
        is not None
        or source.get("result")
        is not None
    ):
        raise AdDeletedObjectRestoreTicketChallengeConflict(
            "source Simulation job is no longer dormant"
        )

    return source


def _assert_simulation_not_reused(
    *,
    simulation_job_id: str,
    ticket_registry_file: Path,
    ticket_consumption_registry_file: Path,
) -> None:
    for field, registry in (
        (
            "ticket_registry_file",
            ticket_registry_file,
        ),
        (
            "ticket_consumption_registry_file",
            ticket_consumption_registry_file,
        ),
    ):
        for record in _registry_records(
            registry,
            field=field,
        ):
            if (
                _clean(
                    record.get(
                        "source_simulation_job_id"
                    )
                )
                == simulation_job_id
            ):
                raise AdDeletedObjectRestoreTicketChallengeConflict(
                    "source Simulation job already used "
                    "for a restore ticket challenge"
                )


@contextmanager
def _exclusive_challenge_lock(
    ticket_registry_file: Path,
):
    ticket_registry_file = (
        _assert_absolute_path(
            ticket_registry_file,
            "ticket_registry_file",
        )
    )

    parent = ticket_registry_file.parent

    parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_file = (
        parent
        / ".ad-deleted-object-restore-ticket-challenge.lock"
    )

    if (
        lock_file.exists()
        and lock_file.is_symlink()
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            "ticket challenge lock must not be a symlink"
        )

    flags = (
        os.O_CREAT
        | os.O_RDWR
    )

    if hasattr(
        os,
        "O_NOFOLLOW",
    ):
        flags |= os.O_NOFOLLOW

    try:
        fd = os.open(
            lock_file,
            flags,
            0o600,
        )
    except OSError as exc:
        raise AdDeletedObjectRestoreTicketChallengeError(
            "unable to open ticket challenge lock"
        ) from exc

    try:
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


def assert_ad_deleted_object_restore_ticket_challenge_invariants(
    challenge: AdDeletedObjectRestoreTicketChallenge,
) -> None:
    if not (
        AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_ENABLED
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            "ticket challenge contract disabled"
        )

    if (
        challenge.contract_version
        != AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_CONTRACT_VERSION
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            "ticket challenge contract mismatch"
        )

    if (
        challenge.state
        != "restore_ticket_challenge_ready"
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            "ticket challenge state invalid"
        )

    for field in (
        "challenge_id",
        "ticket_id",
        "consumption_id",
        "source_simulation_job_id",
        "source_inventory_job_id",
        "source_live_job_id",
        "fresh_live_job_id",
        "object_guid",
    ):
        _uuid(
            getattr(
                challenge,
                field,
            ),
            field,
        )

    for field in (
        "ticket_digest",
        "consumption_record_digest",
        "fresh_live_sha256",
    ):
        _assert_sha256(
            getattr(
                challenge,
                field,
            ),
            field,
        )

    for field in (
        "object_class",
        "class_policy",
        "effective_new_name",
        "effective_target_path",
        "created_at",
    ):
        if not _clean(
            getattr(
                challenge,
                field,
            )
        ):
            raise AdDeletedObjectRestoreTicketChallengeError(
                f"{field} is required"
            )

    if (
        challenge.one_shot_required
        is not True
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            "ticket challenge must remain one-shot"
        )

    for field in (
        "human_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "restore_whatif_authorized",
        "execution_authorized",
        "write_performed",
    ):
        if (
            getattr(
                challenge,
                field,
            )
            is not False
        ):
            raise AdDeletedObjectRestoreTicketChallengeError(
                f"unsafe ticket challenge flag: {field}"
            )

    payload = asdict(
        challenge
    )

    digest = payload.pop(
        "challenge_digest"
    )

    expected = _canonical_sha256(
        payload
    )

    if digest != expected:
        raise AdDeletedObjectRestoreTicketChallengeError(
            "ticket challenge digest mismatch"
        )


def build_ad_deleted_object_restore_ticket_challenge(
    *,
    ad_admin_jobs_file: Path,
    deleted_object_jobs_file: Path,
    ticket_registry_file: Path,
    ticket_consumption_registry_file: Path,
    simulation_job_id: str,
    fresh_live_job_id: str,
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreTicketChallenge:
    if not (
        AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_ENABLED
    ):
        raise AdDeletedObjectRestoreTicketChallengeError(
            "ticket challenge contract disabled"
        )

    if current_mode != "Simulation":
        raise AdDeletedObjectRestoreTicketChallengeError(
            "ticket challenge preparation is Simulation-only"
        )

    simulation_id = _uuid(
        simulation_job_id,
        "simulation_job_id",
    )

    fresh_id = _uuid(
        fresh_live_job_id,
        "fresh_live_job_id",
    )

    ad_admin_jobs_file = _assert_absolute_path(
        ad_admin_jobs_file,
        "ad_admin_jobs_file",
    )

    deleted_object_jobs_file = _assert_absolute_path(
        deleted_object_jobs_file,
        "deleted_object_jobs_file",
    )

    ticket_registry_file = _assert_absolute_path(
        ticket_registry_file,
        "ticket_registry_file",
    )

    ticket_consumption_registry_file = (
        _assert_absolute_path(
            ticket_consumption_registry_file,
            "ticket_consumption_registry_file",
        )
    )

    source_simulation_job = (
        _find_source_simulation_job(
            ad_admin_jobs_file,
            simulation_job_id=simulation_id,
        )
    )

    try:
        with _exclusive_challenge_lock(
            ticket_registry_file
        ):
            _assert_simulation_not_reused(
                simulation_job_id=simulation_id,
                ticket_registry_file=(
                    ticket_registry_file
                ),
                ticket_consumption_registry_file=(
                    ticket_consumption_registry_file
                ),
            )

            ticket = (
                build_ad_deleted_object_restore_ticket(
                    deleted_object_jobs_path=(
                        deleted_object_jobs_file
                    ),
                    source_simulation_job=(
                        source_simulation_job
                    ),
                    expected_simulation_job_id=(
                        simulation_id
                    ),
                    fresh_live_job_id=(
                        fresh_id
                    ),
                    current_mode=current_mode,
                    now=now,
                )
            )

            ticket_record = (
                persist_ad_deleted_object_restore_ticket(
                    ticket,
                    storage_file=(
                        ticket_registry_file
                    ),
                    now=now,
                )
            )

            consumption_record = (
                consume_ad_deleted_object_restore_ticket(
                    ticket_record,
                    consumption_registry_file=(
                        ticket_consumption_registry_file
                    ),
                    current_mode=current_mode,
                    now=now,
                )
            )

    except AdDeletedObjectRestoreTicketConsumptionConflict as exc:
        raise AdDeletedObjectRestoreTicketChallengeConflict(
            str(exc)
        ) from exc

    except (
        AdDeletedObjectRestoreTicketError,
        AdDeletedObjectRestoreTicketPersistenceError,
        AdDeletedObjectRestoreTicketConsumptionError,
    ) as exc:
        raise AdDeletedObjectRestoreTicketChallengeError(
            str(exc)
        ) from exc

    bindings = (
        "source_simulation_job_id",
        "source_inventory_job_id",
        "source_live_job_id",
        "fresh_live_job_id",
        "fresh_live_sha256",
        "object_guid",
        "object_class",
        "class_policy",
        "effective_new_name",
        "effective_target_path",
    )

    for field in bindings:
        if (
            getattr(
                ticket_record,
                field,
            )
            != getattr(
                consumption_record,
                field,
            )
        ):
            raise AdDeletedObjectRestoreTicketChallengeError(
                f"ticket challenge binding mismatch: {field}"
            )

    payload = {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_CONTRACT_VERSION,

        "challenge_id":
            str(
                uuid4()
            ),

        "state":
            "restore_ticket_challenge_ready",

        "ticket_persistence_contract_version":
            ticket_record.contract_version,

        "ticket_id":
            ticket_record.ticket_id,

        "ticket_digest":
            ticket_record.ticket_digest,

        "ticket_consumption_contract_version":
            consumption_record.contract_version,

        "consumption_id":
            consumption_record.consumption_id,

        "consumption_record_digest":
            consumption_record.record_digest,

        "source_simulation_job_id":
            consumption_record.source_simulation_job_id,

        "source_inventory_job_id":
            consumption_record.source_inventory_job_id,

        "source_live_job_id":
            consumption_record.source_live_job_id,

        "fresh_live_job_id":
            consumption_record.fresh_live_job_id,

        "fresh_live_sha256":
            consumption_record.fresh_live_sha256,

        "object_guid":
            consumption_record.object_guid,

        "object_class":
            consumption_record.object_class,

        "class_policy":
            consumption_record.class_policy,

        "effective_new_name":
            consumption_record.effective_new_name,

        "effective_target_path":
            consumption_record.effective_target_path,

        "created_at":
            consumption_record.consumed_at,

        "one_shot_required":
            True,

        "human_authorized":
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

    challenge = (
        AdDeletedObjectRestoreTicketChallenge(
            challenge_digest=(
                _canonical_sha256(
                    payload
                )
            ),
            **payload,
        )
    )

    assert_ad_deleted_object_restore_ticket_challenge_invariants(
        challenge
    )

    return challenge


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_CONTRACT_VERSION",
    "AdDeletedObjectRestoreTicketChallenge",
    "AdDeletedObjectRestoreTicketChallengeConflict",
    "AdDeletedObjectRestoreTicketChallengeError",
    "AdDeletedObjectRestoreTicketChallengeNotFound",
    "assert_ad_deleted_object_restore_ticket_challenge_invariants",
    "build_ad_deleted_object_restore_ticket_challenge",
]
