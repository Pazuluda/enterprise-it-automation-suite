from __future__ import annotations

import dataclasses
import hashlib
import json

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.services.ad_deleted_object_restore_ticket import (
    AD_DELETED_OBJECT_RESTORE_TICKET_CONTRACT_VERSION,
    AD_DELETED_OBJECT_RESTORE_TICKET_TTL_SECONDS,
    AdDeletedObjectRestoreTicket,
)
from app.services.ad_deleted_object_restore_ticket_consumption import (
    AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CONTRACT_VERSION,
    AdDeletedObjectRestoreTicketConsumptionConflict,
    AdDeletedObjectRestoreTicketConsumptionError,
    assert_ad_deleted_object_restore_ticket_consumption_invariants,
    consume_ad_deleted_object_restore_ticket,
)
from app.services.ad_deleted_object_restore_ticket_persistence import (
    AdDeletedObjectRestoreTicketPersistence,
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
            (now - timedelta(seconds=20)).isoformat(),
        "fresh_live_job_id":
            str(uuid4()),
        "fresh_live_sha256":
            "a" * 64,
        "fresh_live_completed_at":
            (now - timedelta(seconds=5)).isoformat(),
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


def _persisted(
    tmp_path: Path,
    now: datetime,
) -> AdDeletedObjectRestoreTicketPersistence:
    return persist_ad_deleted_object_restore_ticket(
        _ticket(now),
        storage_file=tmp_path / "ticket-registry.json",
        now=now + timedelta(seconds=1),
    )


def test_consumption_is_one_shot_non_authorizing_and_0600(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _persisted(tmp_path, now)
    registry = tmp_path / "consumption-registry.json"

    record = consume_ad_deleted_object_restore_ticket(
        ticket,
        consumption_registry_file=registry,
        current_mode="Simulation",
        now=now + timedelta(seconds=2),
    )

    assert (
        record.contract_version
        == AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_CONTRACT_VERSION
    )
    assert record.state == "restore_ticket_consumed"
    assert record.consumed is True
    assert record.ticket_id == ticket.ticket_id
    assert record.ticket_digest == ticket.ticket_digest
    assert record.job_creation_authorized is False
    assert record.claim_authorized is False
    assert record.runtime_authorized is False
    assert record.production_authorized is False
    assert record.restore_authorized is False
    assert record.restore_whatif_authorized is False
    assert record.write_performed is False
    assert (registry.stat().st_mode & 0o777) == 0o600

    assert_ad_deleted_object_restore_ticket_consumption_invariants(
        record
    )


def test_consumption_preserves_restore_identity_binding(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _persisted(tmp_path, now)

    record = consume_ad_deleted_object_restore_ticket(
        ticket,
        consumption_registry_file=tmp_path / "consumption.json",
        current_mode="Simulation",
        now=now + timedelta(seconds=2),
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
    assert record.object_class == ticket.object_class
    assert record.class_policy == "standard_controlled"
    assert record.effective_new_name == ticket.effective_new_name
    assert record.effective_target_path == ticket.effective_target_path


def test_same_ticket_cannot_be_consumed_twice(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _persisted(tmp_path, now)
    registry = tmp_path / "consumption.json"

    consume_ad_deleted_object_restore_ticket(
        ticket,
        consumption_registry_file=registry,
        current_mode="Simulation",
        now=now + timedelta(seconds=2),
    )

    with pytest.raises(
        AdDeletedObjectRestoreTicketConsumptionConflict,
        match="already consumed",
    ):
        consume_ad_deleted_object_restore_ticket(
            ticket,
            consumption_registry_file=registry,
            current_mode="Simulation",
            now=now + timedelta(seconds=3),
        )


def test_expired_ticket_cannot_be_consumed(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _persisted(tmp_path, now)

    with pytest.raises(
        AdDeletedObjectRestoreTicketConsumptionConflict,
        match="expired restore ticket",
    ):
        consume_ad_deleted_object_restore_ticket(
            ticket,
            consumption_registry_file=tmp_path / "consumption.json",
            current_mode="Simulation",
            now=(
                now
                + timedelta(
                    seconds=AD_DELETED_OBJECT_RESTORE_TICKET_TTL_SECONDS
                )
            ),
        )


def test_consumption_is_simulation_only(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _persisted(tmp_path, now)

    with pytest.raises(
        AdDeletedObjectRestoreTicketConsumptionError,
        match="Simulation-only",
    ):
        consume_ad_deleted_object_restore_ticket(
            ticket,
            consumption_registry_file=tmp_path / "consumption.json",
            current_mode="Production",
            now=now + timedelta(seconds=2),
        )


def test_relative_consumption_registry_rejected(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _persisted(tmp_path, now)

    with pytest.raises(
        AdDeletedObjectRestoreTicketConsumptionError,
        match="absolute",
    ):
        consume_ad_deleted_object_restore_ticket(
            ticket,
            consumption_registry_file=Path("relative-consumption.json"),
            current_mode="Simulation",
            now=now + timedelta(seconds=2),
        )


def test_symlink_consumption_registry_rejected(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _persisted(tmp_path, now)

    target = tmp_path / "real-consumption.json"
    target.write_text(
        "{}",
        encoding="utf-8",
    )

    link = tmp_path / "consumption.json"
    link.symlink_to(target)

    with pytest.raises(
        AdDeletedObjectRestoreTicketConsumptionError,
        match="symlink",
    ):
        consume_ad_deleted_object_restore_ticket(
            ticket,
            consumption_registry_file=link,
            current_mode="Simulation",
            now=now + timedelta(seconds=2),
        )


def test_consumption_record_rejects_unsafe_restore_flag(
    tmp_path: Path,
):
    now = datetime.now(timezone.utc)
    ticket = _persisted(tmp_path, now)

    record = consume_ad_deleted_object_restore_ticket(
        ticket,
        consumption_registry_file=tmp_path / "consumption.json",
        current_mode="Simulation",
        now=now + timedelta(seconds=2),
    )

    unsafe = dataclasses.replace(
        record,
        restore_authorized=True,
    )

    with pytest.raises(
        AdDeletedObjectRestoreTicketConsumptionError,
        match="unsafe restore ticket consumption flag",
    ):
        assert_ad_deleted_object_restore_ticket_consumption_invariants(
            unsafe
        )


def test_consumption_source_contains_no_restore_cmdlet():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_ticket_consumption.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = "Restore" + "-ADObject"
    assert forbidden not in source

    assert (
        "AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_RESTORE_AUTHORIZED = False"
        in source
    )
    assert (
        "AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_RESTORE_WHATIF_AUTHORIZED = False"
        in source
    )
