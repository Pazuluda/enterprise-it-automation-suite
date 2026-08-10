from __future__ import annotations

import dataclasses
import hashlib
import json
import os

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.services.ad_deleted_object_restore_ticket import (
    AD_DELETED_OBJECT_RESTORE_TICKET_CONTRACT_VERSION,
    AD_DELETED_OBJECT_RESTORE_TICKET_TTL_SECONDS,
    AdDeletedObjectRestoreTicket,
)
from app.services.ad_deleted_object_restore_ticket_persistence import (
    AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION,
    AdDeletedObjectRestoreTicketPersistenceError,
    assert_ad_deleted_object_restore_ticket_persistence_invariants,
    persist_ad_deleted_object_restore_ticket,
)


def _sha(payload: dict) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _ticket(now: datetime) -> AdDeletedObjectRestoreTicket:
    source_live = now - timedelta(seconds=20)
    fresh_live = now - timedelta(seconds=5)

    payload = {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_TICKET_CONTRACT_VERSION,

        "ticket_id":
            str(uuid4()),

        "state":
            "restore_ticket_dormant",

        "status":
            "dormant",

        "source_simulation_job_id":
            str(uuid4()),

        "source_inventory_job_id":
            str(uuid4()),

        "source_live_job_id":
            str(uuid4()),

        "source_live_completed_at":
            source_live.isoformat(),

        "fresh_live_job_id":
            str(uuid4()),

        "fresh_live_sha256":
            "a" * 64,

        "fresh_live_completed_at":
            fresh_live.isoformat(),

        "object_guid":
            str(uuid4()),

        "object_class":
            "group",

        "class_policy":
            "standard_controlled",

        "effective_new_name":
            "GG_C95_RECYCLE_TEST",

        "effective_target_path":
            "OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL",

        "issued_at":
            now.isoformat(),

        "expires_at":
            (
                now
                + timedelta(
                    seconds=AD_DELETED_OBJECT_RESTORE_TICKET_TTL_SECONDS
                )
            ).isoformat(),

        "one_shot_required":
            True,

        "replay_consumed":
            False,

        "persistence_enabled":
            False,

        "route_enabled":
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

        "write_performed":
            False,
    }

    return AdDeletedObjectRestoreTicket(
        ticket_digest=_sha(payload),
        **payload,
    )


def test_persist_restore_ticket_is_dormant_and_0600(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _ticket(now)

    storage = (
        tmp_path
        / "restore-ticket-registry.json"
    )

    record = persist_ad_deleted_object_restore_ticket(
        ticket,
        storage_file=storage,
        now=now + timedelta(seconds=1),
    )

    assert (
        record.contract_version
        == AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION
    )
    assert record.ticket_contract_version == ticket.contract_version
    assert record.ticket_id == ticket.ticket_id
    assert record.ticket_digest == ticket.ticket_digest
    assert record.state == "restore_ticket_dormant"
    assert record.status == "dormant"
    assert record.one_shot_required is True
    assert record.replay_consumed is False
    assert record.persistence_enabled is True
    assert record.route_enabled is False
    assert record.job_creation_authorized is False
    assert record.claim_authorized is False
    assert record.runtime_authorized is False
    assert record.production_authorized is False
    assert record.restore_authorized is False
    assert record.restore_whatif_authorized is False
    assert record.write_performed is False

    assert storage.exists()
    assert (storage.stat().st_mode & 0o777) == 0o600

    payload = json.loads(
        storage.read_text(
            encoding="utf-8"
        )
    )

    assert payload["contract_version"] == (
        AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_CONTRACT_VERSION
    )
    assert len(payload["records"]) == 1

    assert_ad_deleted_object_restore_ticket_persistence_invariants(
        record
    )


def test_persistence_preserves_restore_identity_binding(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _ticket(now)

    record = persist_ad_deleted_object_restore_ticket(
        ticket,
        storage_file=tmp_path / "registry.json",
        now=now + timedelta(seconds=1),
    )

    assert (
        record.source_simulation_job_id
        == ticket.source_simulation_job_id
    )
    assert (
        record.source_inventory_job_id
        == ticket.source_inventory_job_id
    )
    assert record.source_live_job_id == ticket.source_live_job_id
    assert record.fresh_live_job_id == ticket.fresh_live_job_id
    assert record.fresh_live_sha256 == ticket.fresh_live_sha256
    assert record.object_guid == ticket.object_guid
    assert record.object_class == "group"
    assert record.class_policy == "standard_controlled"
    assert record.effective_new_name == "GG_C95_RECYCLE_TEST"
    assert record.effective_target_path == (
        "OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL"
    )


def test_duplicate_ticket_rejected(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _ticket(now)
    storage = tmp_path / "registry.json"

    persist_ad_deleted_object_restore_ticket(
        ticket,
        storage_file=storage,
        now=now + timedelta(seconds=1),
    )

    with pytest.raises(
        AdDeletedObjectRestoreTicketPersistenceError,
        match="already persisted",
    ):
        persist_ad_deleted_object_restore_ticket(
            ticket,
            storage_file=storage,
            now=now + timedelta(seconds=2),
        )


def test_expired_ticket_rejected(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _ticket(now)

    with pytest.raises(
        AdDeletedObjectRestoreTicketPersistenceError,
        match="expired restore ticket",
    ):
        persist_ad_deleted_object_restore_ticket(
            ticket,
            storage_file=tmp_path / "registry.json",
            now=(
                now
                + timedelta(
                    seconds=AD_DELETED_OBJECT_RESTORE_TICKET_TTL_SECONDS
                )
            ),
        )


def test_relative_storage_path_rejected():
    now = datetime.now(timezone.utc)
    ticket = _ticket(now)

    with pytest.raises(
        AdDeletedObjectRestoreTicketPersistenceError,
        match="absolute",
    ):
        persist_ad_deleted_object_restore_ticket(
            ticket,
            storage_file=Path("relative-registry.json"),
            now=now + timedelta(seconds=1),
        )


def test_symlink_storage_path_rejected(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _ticket(now)

    target = tmp_path / "real.json"
    target.write_text(
        "{}",
        encoding="utf-8",
    )

    link = tmp_path / "registry.json"
    link.symlink_to(target)

    with pytest.raises(
        AdDeletedObjectRestoreTicketPersistenceError,
        match="symlink",
    ):
        persist_ad_deleted_object_restore_ticket(
            ticket,
            storage_file=link,
            now=now + timedelta(seconds=1),
        )


def test_persisted_record_rejects_unsafe_flag(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _ticket(now)

    record = persist_ad_deleted_object_restore_ticket(
        ticket,
        storage_file=tmp_path / "registry.json",
        now=now + timedelta(seconds=1),
    )

    unsafe = dataclasses.replace(
        record,
        restore_authorized=True,
    )

    with pytest.raises(
        AdDeletedObjectRestoreTicketPersistenceError,
        match="unsafe persisted restore ticket flag",
    ):
        assert_ad_deleted_object_restore_ticket_persistence_invariants(
            unsafe
        )


def test_persistence_source_contains_no_restore_cmdlet():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_ticket_persistence.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = "Restore" + "-ADObject"
    assert forbidden not in source

    assert (
        "AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_RESTORE_AUTHORIZED = False"
        in source
    )
    assert (
        "AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_RESTORE_WHATIF_AUTHORIZED = False"
        in source
    )
    assert (
        "AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_PRODUCTION_AUTHORIZED = False"
        in source
    )
