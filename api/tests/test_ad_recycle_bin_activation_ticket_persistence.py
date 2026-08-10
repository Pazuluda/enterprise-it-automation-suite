import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.security import OIDC_ALLOWED_AZP, OIDC_ISSUER
from app.services.ad_recycle_bin_activation_intent_persistence import AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION
from app.services.ad_recycle_bin_activation_ticket import build_ad_recycle_bin_activation_ticket
from app.services.ad_recycle_bin_activation_ticket_persistence import (
    AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CONTRACT_VERSION,
    AdRecycleBinActivationTicketPersistenceError,
    persist_ad_recycle_bin_activation_ticket,
)

NOW = datetime(2026, 8, 10, 16, 10, 0, tzinfo=timezone.utc)


def allowed_azp():
    if OIDC_ALLOWED_AZP:
        return sorted(OIDC_ALLOWED_AZP)[0]
    return "eitas-portal"


def actor():
    return {"subject": "subject-c94", "username": "admin-c94", "issuer": OIDC_ISSUER, "azp": allowed_azp()}


def source_record():
    current_actor = actor()
    return {
        "contract_version": AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,
        "intent_id": str(uuid4()),
        "intent_digest": "a" * 64,
        "state": "activation_intent_dormant",
        "status": "dormant",
        "forest_name": "API.LOCAL",
        "root_domain": "API.LOCAL",
        "actor_subject": current_actor["subject"],
        "actor_username": current_actor["username"],
        "actor_issuer": current_actor["issuer"],
        "actor_azp": current_actor["azp"],
        "evidence_sha256": "b" * 64,
        "evidence_created_at": (NOW - timedelta(seconds=30)).isoformat(),
        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "activation_authorized": False,
        "restore_authorized": False,
        "write_performed": False,
    }


def evidence_job():
    return {
        "id": "fresh-evidence-persistence",
        "type": "ad_explorer",
        "action": "get_recycle_bin_activation_evidence",
        "status": "completed",
        "success": True,
        "result": {
            "action": "get_recycle_bin_activation_evidence",
            "read_only": True,
            "forest_name": "API.LOCAL",
            "root_domain": "API.LOCAL",
            "forest_mode": "Windows2025Forest",
            "recycle_bin_enabled": False,
            "recycle_bin_enabled_scope_count": 0,
            "domain_controller_count": 1,
            "replication_query_succeeded": True,
            "replication_partner_query_succeeded": True,
            "replication_failure_count": 0,
            "replication_partner_count": 0,
            "replication_ready": True,
            "evidence_created_at": (NOW - timedelta(seconds=5)).isoformat(),
            "activation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "restore_authorized": False,
            "write_performed": False,
        },
    }


def make_ticket():
    source = source_record()
    return build_ad_recycle_bin_activation_ticket(
        source_intent_record=source,
        expected_intent_id=source["intent_id"],
        expected_intent_digest=source["intent_digest"],
        evidence_job=evidence_job(),
        expected_evidence_job_id="fresh-evidence-persistence",
        server_actor=actor(),
        confirmed_forest_name="API.LOCAL",
        current_mode="Simulation",
        now=NOW,
    )


def stat_mode(path):
    return os.stat(path).st_mode & 0o777


def test_ticket_is_persisted_dormant(tmp_path):
    storage = tmp_path / "tickets.json"
    record = persist_ad_recycle_bin_activation_ticket(make_ticket(), storage_file=storage, now=NOW + timedelta(seconds=1))
    assert record.state == "activation_ticket_dormant"
    assert record.status == "dormant"
    assert record.one_shot_required is True
    assert record.replay_consumed is False
    assert record.persistence_enabled is True
    assert record.claim_authorized is False
    assert record.runtime_authorized is False
    assert record.production_authorized is False
    assert record.activation_authorized is False
    assert record.restore_authorized is False
    assert record.write_performed is False
    assert len(record.record_digest) == 64
    data = json.loads(storage.read_text(encoding="utf-8"))
    assert data["contract_version"] == AD_RECYCLE_BIN_ACTIVATION_TICKET_PERSISTENCE_CONTRACT_VERSION
    assert len(data["records"]) == 1
    assert data["records"][0]["status"] == "dormant"


def test_storage_and_lock_are_mode_0600(tmp_path):
    storage = tmp_path / "tickets.json"
    persist_ad_recycle_bin_activation_ticket(make_ticket(), storage_file=storage, now=NOW + timedelta(seconds=1))
    lock = tmp_path / ".tickets.json.lock"
    assert stat_mode(storage) == 0o600
    assert stat_mode(lock) == 0o600


def test_duplicate_ticket_is_rejected(tmp_path):
    storage = tmp_path / "tickets.json"
    ticket = make_ticket()
    persist_ad_recycle_bin_activation_ticket(ticket, storage_file=storage, now=NOW + timedelta(seconds=1))
    with pytest.raises(AdRecycleBinActivationTicketPersistenceError, match="already persisted"):
        persist_ad_recycle_bin_activation_ticket(ticket, storage_file=storage, now=NOW + timedelta(seconds=2))


def test_expired_ticket_is_rejected(tmp_path):
    storage = tmp_path / "tickets.json"
    ticket = make_ticket()
    expires = datetime.fromisoformat(ticket.expires_at)
    with pytest.raises(AdRecycleBinActivationTicketPersistenceError, match="expired ticket"):
        persist_ad_recycle_bin_activation_ticket(ticket, storage_file=storage, now=expires)


def test_existing_storage_symlink_is_rejected(tmp_path):
    target = tmp_path / "target.json"
    target.write_text('{"safe":true}', encoding="utf-8")
    storage = tmp_path / "tickets.json"
    storage.symlink_to(target)
    with pytest.raises(AdRecycleBinActivationTicketPersistenceError, match="must not be a symlink"):
        persist_ad_recycle_bin_activation_ticket(make_ticket(), storage_file=storage, now=NOW + timedelta(seconds=1))


def test_dangling_storage_symlink_is_rejected(tmp_path):
    storage = tmp_path / "tickets.json"
    storage.symlink_to(tmp_path / "missing-target.json")
    assert storage.exists() is False
    assert storage.is_symlink() is True
    with pytest.raises(AdRecycleBinActivationTicketPersistenceError, match="must not be a symlink"):
        persist_ad_recycle_bin_activation_ticket(make_ticket(), storage_file=storage, now=NOW + timedelta(seconds=1))


def test_symlink_lock_is_rejected(tmp_path):
    storage = tmp_path / "tickets.json"
    lock = tmp_path / ".tickets.json.lock"
    target = tmp_path / "lock-target"
    target.write_text("", encoding="utf-8")
    lock.symlink_to(target)
    with pytest.raises(AdRecycleBinActivationTicketPersistenceError, match="must not be a symlink"):
        persist_ad_recycle_bin_activation_ticket(make_ticket(), storage_file=storage, now=NOW + timedelta(seconds=1))


def test_wrong_registry_version_is_rejected(tmp_path):
    storage = tmp_path / "tickets.json"
    storage.write_text(json.dumps({"contract_version": "wrong-version", "records": []}), encoding="utf-8")
    with pytest.raises(AdRecycleBinActivationTicketPersistenceError, match="registry contract version mismatch"):
        persist_ad_recycle_bin_activation_ticket(make_ticket(), storage_file=storage, now=NOW + timedelta(seconds=1))


def test_tampered_record_digest_is_rejected(tmp_path):
    storage = tmp_path / "tickets.json"
    persist_ad_recycle_bin_activation_ticket(make_ticket(), storage_file=storage, now=NOW + timedelta(seconds=1))
    data = json.loads(storage.read_text(encoding="utf-8"))
    data["records"][0]["forest_name"] = "OTHER.LOCAL"
    storage.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(AdRecycleBinActivationTicketPersistenceError, match="record digest mismatch"):
        persist_ad_recycle_bin_activation_ticket(make_ticket(), storage_file=storage, now=NOW + timedelta(seconds=2))


def test_registry_never_contains_pending(tmp_path):
    storage = tmp_path / "tickets.json"
    persist_ad_recycle_bin_activation_ticket(make_ticket(), storage_file=storage, now=NOW + timedelta(seconds=1))
    raw = storage.read_text(encoding="utf-8")
    assert '"status": "pending"' not in raw
    assert '"status": "dormant"' in raw


def test_service_is_not_runtime_integrated():
    main = Path("api/main.py").read_text(encoding="utf-8")
    admin = Path("api/app/services/ad_admin.py").read_text(encoding="utf-8")
    windows = Path("agent-windows/modules/EitasAdAdmin.ps1").read_text(encoding="utf-8", errors="replace")
    assert "ad_recycle_bin_activation_ticket_persistence" not in main
    assert "activate_recycle_bin" not in admin
    assert "activate_recycle_bin" not in windows
    assert "Enable-ADOptionalFeature" not in windows
    assert "Restore-ADObject" not in windows
