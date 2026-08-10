from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.ad_deleted_object_restore_ticket import (
    AdDeletedObjectRestoreTicketError,
    assert_ad_deleted_object_restore_ticket_invariants,
    build_ad_deleted_object_restore_ticket,
)

GUID = "b1018519-8b6e-4788-81c8-3108a188e7b4"
SIM = "383fb0c5-03fb-4440-92c0-c188a889a420"
INV = "c1ed1625-db5a-4dd0-82f4-1c4e244f9770"
SRC_LIVE = "ccea9426-5de0-4267-89a1-211801fff7f6"
FRESH = "11111111-2222-4333-8444-555555555555"
NAME = "GG_C95_RECYCLE_TEST"
TARGET = "OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL"


def iso(v):
    return v.isoformat().replace("+00:00", "Z")


def source(now):
    p = {
        "contract_version": "c9.2b-v1",
        "persistence_contract_version": "c9.2b-a3b-v1",
        "mode": "Simulation",
        "policy_decision": "candidate_preflight",
        "class_policy": "standard_controlled",
        "manual_review_required": False,
        "preflight_passed": True,
        "simulation_candidate": True,
        "simulation_job_authorized": True,
        "simulation_job_persistence_authorized": True,
        "worker_claim_authorized": False,
        "worker_runtime_authorized": False,
        "production_authorized": False,
        "restore_cmdlet_authorized": False,
        "restore_whatif_authorized": False,
        "execution_authorized": False,
        "write_authorized": False,
        "restore_implemented": False,
        "restore_performed": False,
        "object_guid": GUID,
        "effective_new_name": NAME,
        "effective_target_path": TARGET,
        "object_class": "group",
        "source_inventory_job_id": INV,
        "live_job_id": SRC_LIVE,
        "live_job_completed_at": iso(now - timedelta(seconds=20)),
    }
    return {
        "id": SIM, "type": "ad_admin", "status": "prepared",
        "action": "simulate_deleted_object_restore", "payload": p,
        "claimed_at": None, "claimed_by": None, "result": None,
    }


def inventory(now):
    return {
        "id": INV, "type": "ad_explorer", "action": "get_deleted_objects",
        "status": "completed", "success": True,
        "completed_at": iso(now - timedelta(seconds=30)),
        "result": {
            "items": [{
                "object_guid": GUID, "object_class": "group",
                "is_deleted": True, "is_recycled": False,
                "last_known_parent": "CN=Users,DC=API,DC=LOCAL",
                "last_known_rdn": NAME,
            }],
            "recycle_bin": {"enabled": True},
        },
    }


def live(now):
    return {
        "id": FRESH, "type": "ad_explorer",
        "action": "revalidate_deleted_object_preflight",
        "status": "completed", "success": True,
        "completed_at": iso(now - timedelta(seconds=2)),
        "query": GUID,
        "filters": {"new_name": NAME, "target_path": TARGET},
        "result": {
            "action": "revalidate_deleted_object_preflight",
            "read_only": True, "live_revalidation_performed": True,
            "object_found": True, "object_guid": GUID,
            "object_class": "group", "is_deleted": True,
            "is_recycled": False, "recycle_bin_enabled": True,
            "requested_new_name": NAME, "requested_target_path": TARGET,
            "effective_new_name": NAME, "effective_target_path": TARGET,
            "last_known_parent": "CN=Users,DC=API,DC=LOCAL",
            "last_known_rdn": NAME, "parent_exists": True,
            "parent_deleted": False, "parent_recycled": False,
            "collision_probe_performed": True, "target_collision": False,
            "restore_job_created": False, "restore_implemented": False,
            "execution_authorized": False, "write_authorized": False,
        },
    }


def build(tmp_path: Path, now, src=None, fresh=None, mode="Simulation"):
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps([inventory(now), fresh or live(now)]), encoding="utf-8")
    return build_ad_deleted_object_restore_ticket(
        deleted_object_jobs_path=path,
        source_simulation_job=src or source(now),
        expected_simulation_job_id=SIM,
        fresh_live_job_id=FRESH,
        current_mode=mode,
        now=now,
    )


def test_builds_dormant_one_shot_ticket(tmp_path):
    now = datetime.now(timezone.utc)
    ticket = build(tmp_path, now)
    assert ticket.state == "restore_ticket_dormant"
    assert ticket.one_shot_required is True
    assert ticket.replay_consumed is False
    assert ticket.object_guid == GUID
    assert ticket.effective_target_path == TARGET
    assert ticket.restore_authorized is False
    assert ticket.restore_whatif_authorized is False
    assert ticket.runtime_authorized is False
    assert ticket.production_authorized is False
    assert ticket.write_performed is False
    assert len(ticket.ticket_digest) == 64


def test_production_rejected(tmp_path):
    now = datetime.now(timezone.utc)
    with pytest.raises(AdDeletedObjectRestoreTicketError, match="Simulation-only"):
        build(tmp_path, now, mode="Production")


def test_unsafe_source_rejected(tmp_path):
    now = datetime.now(timezone.utc)
    src = source(now)
    src["payload"]["restore_cmdlet_authorized"] = True
    with pytest.raises(AdDeletedObjectRestoreTicketError, match="unsafe source simulation flag"):
        build(tmp_path, now, src=src)


def test_fresh_live_must_be_newer(tmp_path):
    now = datetime.now(timezone.utc)
    fresh = live(now)
    fresh["completed_at"] = iso(now - timedelta(seconds=25))
    with pytest.raises(AdDeletedObjectRestoreTicketError, match="not newer"):
        build(tmp_path, now, fresh=fresh)


def test_collision_rejected(tmp_path):
    now = datetime.now(timezone.utc)
    fresh = live(now)
    fresh["result"]["target_collision"] = True
    with pytest.raises(AdDeletedObjectRestoreTicketError):
        build(tmp_path, now, fresh=fresh)


def test_digest_detects_mutation(tmp_path):
    now = datetime.now(timezone.utc)
    ticket = build(tmp_path, now)
    with pytest.raises(AdDeletedObjectRestoreTicketError, match="digest mismatch"):
        assert_ad_deleted_object_restore_ticket_invariants(
            replace(ticket, effective_new_name="OTHER")
        )
