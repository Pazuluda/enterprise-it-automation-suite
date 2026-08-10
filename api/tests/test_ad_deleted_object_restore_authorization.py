from __future__ import annotations

import dataclasses
import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.ad_deleted_object_restore_authorization as m


def _actor() -> dict[str, str]:
    allowed = m.OIDC_ALLOWED_AZP
    if isinstance(allowed, (set, frozenset, list, tuple)):
        azp = next(iter(allowed), "eitas-portal")
    else:
        azp = str(allowed or "eitas-portal")
    return {
        "subject": "c9.5-a4c2-test-subject",
        "username": "c9.5-a4c2-test-user",
        "issuer": m.OIDC_ISSUER,
        "azp": azp,
    }


def _records(now: datetime):
    ids = [str(uuid4()) for _ in range(7)]
    ticket = SimpleNamespace(
        contract_version="c9.5a4b2-v1",
        record_digest="1" * 64,
        ticket_contract_version="c9.5a4b-v1",
        ticket_id=ids[0],
        ticket_digest="2" * 64,
        state="restore_ticket_dormant",
        status="dormant",
        source_simulation_job_id=ids[1],
        source_inventory_job_id=ids[2],
        source_live_job_id=ids[3],
        source_live_completed_at=(now - timedelta(seconds=30)).isoformat(),
        fresh_live_job_id=ids[4],
        fresh_live_sha256="3" * 64,
        fresh_live_completed_at=(now - timedelta(seconds=10)).isoformat(),
        object_guid=ids[5],
        object_class="group",
        class_policy="standard_controlled",
        effective_new_name="GG_C95_RECYCLE_TEST",
        effective_target_path="OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL",
        issued_at=(now - timedelta(seconds=5)).isoformat(),
        expires_at=(now + timedelta(seconds=115)).isoformat(),
        persisted_at=(now - timedelta(seconds=4)).isoformat(),
        one_shot_required=True,
        replay_consumed=False,
        persistence_enabled=True,
        route_enabled=False,
        job_creation_authorized=False,
        claim_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        restore_authorized=False,
        restore_whatif_authorized=False,
        write_performed=False,
    )
    consumption = SimpleNamespace(
        contract_version="c9.5a4b3-v1",
        record_digest="4" * 64,
        consumption_id=ids[6],
        state="restore_ticket_consumed",
        consumed=True,
        ticket_persistence_contract_version=ticket.contract_version,
        ticket_id=ticket.ticket_id,
        ticket_digest=ticket.ticket_digest,
        source_simulation_job_id=ticket.source_simulation_job_id,
        source_inventory_job_id=ticket.source_inventory_job_id,
        source_live_job_id=ticket.source_live_job_id,
        fresh_live_job_id=ticket.fresh_live_job_id,
        fresh_live_sha256=ticket.fresh_live_sha256,
        object_guid=ticket.object_guid,
        object_class=ticket.object_class,
        class_policy=ticket.class_policy,
        effective_new_name=ticket.effective_new_name,
        effective_target_path=ticket.effective_target_path,
        issued_at=ticket.issued_at,
        expires_at=ticket.expires_at,
        consumed_at=(now - timedelta(seconds=1)).isoformat(),
        job_creation_authorized=False,
        claim_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        restore_authorized=False,
        restore_whatif_authorized=False,
        write_performed=False,
    )
    return ticket, consumption


def _payload(ticket, consumption) -> dict:
    return {
        "ticket_id": ticket.ticket_id,
        "ticket_digest": ticket.ticket_digest,
        "consumption_id": consumption.consumption_id,
        "object_guid": ticket.object_guid,
        "effective_new_name": ticket.effective_new_name,
        "effective_target_path": ticket.effective_target_path,
        "acknowledge_exact_object": True,
        "acknowledge_exact_target": True,
        "acknowledge_restore_write": True,
        "authorization_reason": "Validation humaine contrôlée C9.5 A4C2.",
    }


def _disable_upstream_invariant_checks(monkeypatch):
    monkeypatch.setattr(
        m,
        "assert_ad_deleted_object_restore_ticket_persistence_invariants",
        lambda record: None,
    )
    monkeypatch.setattr(
        m,
        "assert_ad_deleted_object_restore_ticket_consumption_invariants",
        lambda record: None,
    )


def test_contract_and_ttl_are_locked():
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION == "c9.5a4c-v1"
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_TTL_SECONDS == 60


def test_dangerous_capabilities_remain_disabled():
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_ENABLED is False
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_ROUTE_ENABLED is False
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_JOB_CREATION_AUTHORIZED is False
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CLAIM_AUTHORIZED is False
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_RUNTIME_AUTHORIZED is False
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PRODUCTION_AUTHORIZED is False
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_RESTORE_AUTHORIZED is False
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_RESTORE_WHATIF_AUTHORIZED is False
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_EXECUTION_AUTHORIZED is False
    assert m.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_WRITE_PERFORMED is False


def test_human_payload_surface_is_exact():
    assert m._ALLOWED_PAYLOAD_KEYS == {
        "ticket_id",
        "ticket_digest",
        "consumption_id",
        "object_guid",
        "effective_new_name",
        "effective_target_path",
        "acknowledge_exact_object",
        "acknowledge_exact_target",
        "acknowledge_restore_write",
        "authorization_reason",
    }


def test_authorization_dataclass_keeps_exact_restore_bindings():
    names = {field.name for field in dataclasses.fields(m.AdDeletedObjectRestoreAuthorization)}
    required = {
        "ticket_id",
        "ticket_digest",
        "consumption_id",
        "consumption_record_digest",
        "object_guid",
        "object_class",
        "class_policy",
        "effective_new_name",
        "effective_target_path",
        "actor_subject",
        "actor_username",
        "actor_issuer",
        "actor_azp",
        "human_authorized",
        "restore_authorized",
        "restore_whatif_authorized",
        "execution_authorized",
        "write_performed",
    }
    assert required <= names


def test_production_mode_is_rejected_before_authorization():
    with pytest.raises(m.AdDeletedObjectRestoreAuthorizationError):
        m.build_ad_deleted_object_restore_authorization(
            None,
            None,
            server_actor={},
            payload={},
            current_mode="Production",
        )


def test_non_mapping_payload_is_rejected():
    with pytest.raises(m.AdDeletedObjectRestoreAuthorizationError):
        m.build_ad_deleted_object_restore_authorization(
            None,
            None,
            server_actor={},
            payload=None,
            current_mode="Simulation",
        )


def test_unknown_payload_field_is_rejected():
    with pytest.raises(m.AdDeletedObjectRestoreAuthorizationError):
        m.build_ad_deleted_object_restore_authorization(
            None,
            None,
            server_actor={},
            payload={"unexpected": True},
            current_mode="Simulation",
        )


def test_human_authorization_build_is_still_non_authorizing(monkeypatch):
    _disable_upstream_invariant_checks(monkeypatch)
    now = datetime.now(timezone.utc)
    ticket, consumption = _records(now)
    authorization = m.build_ad_deleted_object_restore_authorization(
        ticket,
        consumption,
        server_actor=_actor(),
        payload=_payload(ticket, consumption),
        current_mode="Simulation",
        now=now,
    )
    assert authorization.human_authorized is True
    assert authorization.object_guid == ticket.object_guid
    assert authorization.effective_new_name == ticket.effective_new_name
    assert authorization.effective_target_path == ticket.effective_target_path
    assert authorization.one_shot_required is True
    assert authorization.authorization_consumed is False
    assert authorization.restore_authorized is False
    assert authorization.restore_whatif_authorized is False
    assert authorization.execution_authorized is False
    assert authorization.production_authorized is False
    assert authorization.write_performed is False
    m.assert_ad_deleted_object_restore_authorization_invariants(authorization)


def test_object_guid_confirmation_mismatch_is_rejected(monkeypatch):
    _disable_upstream_invariant_checks(monkeypatch)
    now = datetime.now(timezone.utc)
    ticket, consumption = _records(now)
    payload = _payload(ticket, consumption)
    payload["object_guid"] = str(uuid4())
    with pytest.raises(m.AdDeletedObjectRestoreAuthorizationError):
        m.build_ad_deleted_object_restore_authorization(
            ticket,
            consumption,
            server_actor=_actor(),
            payload=payload,
            current_mode="Simulation",
            now=now,
        )


def test_source_contains_no_restore_primitive():
    source = Path(
        "api/app/services/ad_deleted_object_restore_authorization.py"
    ).read_text(encoding="utf-8")
    forbidden = "Restore" + "-ADObject"
    assert forbidden not in source
    assert "AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_RESTORE_AUTHORIZED = False" in source
    assert "AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_EXECUTION_AUTHORIZED = False" in source
