from __future__ import annotations

import hashlib
import json
import tempfile

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.core.security import OIDC_ALLOWED_AZP, OIDC_ISSUER
from app.services.ad_deleted_object_restore_authorization import (
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION,
    AdDeletedObjectRestoreAuthorization,
    assert_ad_deleted_object_restore_authorization_invariants,
)
from app.services.ad_deleted_object_restore_authorization_persistence import (
    AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_PERSISTENCE_CONTRACT_VERSION,
    AdDeletedObjectRestoreAuthorizationPersistence,
    assert_ad_deleted_object_restore_authorization_persistence_invariants,
    persist_ad_deleted_object_restore_authorization,
)
import app.services.ad_deleted_object_restore_preexecution as pre


AUTH_ID = "11111111-1111-4111-8111-111111111111"
TICKET_ID = "22222222-2222-4222-8222-222222222222"
CONSUMPTION_ID = "33333333-3333-4333-8333-333333333333"
SIM_ID = "44444444-4444-4444-8444-444444444444"
INVENTORY_ID = "55555555-5555-4555-8555-555555555555"
SOURCE_LIVE_ID = "66666666-6666-4666-8666-666666666666"
AUTH_FRESH_ID = "77777777-7777-4777-8777-777777777777"
FRESH_ID = "88888888-8888-4888-8888-888888888888"
GUID = "b1018519-8b6e-4788-81c8-3108a188e7b4"
NAME = "GG_C95_RECYCLE_TEST"
TARGET = "OU=test,OU=Users,OU=EITAS,DC=API,DC=LOCAL"


def _sha(payload):
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _azp():
    if isinstance(OIDC_ALLOWED_AZP, str):
        return OIDC_ALLOWED_AZP
    if OIDC_ALLOWED_AZP:
        return sorted(OIDC_ALLOWED_AZP)[0]
    return "eitas-portal"


def actor():
    return {
        "subject": "c9.5-preexecution-test-subject",
        "username": "c9.5-preexecution-test-user",
        "issuer": OIDC_ISSUER,
        "azp": _azp(),
    }


def authorization(now):
    payload = {
        "contract_version":
            AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONTRACT_VERSION,
        "authorization_id": AUTH_ID,
        "state": "restore_authorization_dormant",
        "status": "authorized",
        "ticket_id": TICKET_ID,
        "ticket_digest": "b" * 64,
        "consumption_id": CONSUMPTION_ID,
        "consumption_record_digest": "c" * 64,
        "source_simulation_job_id": SIM_ID,
        "source_inventory_job_id": INVENTORY_ID,
        "source_live_job_id": SOURCE_LIVE_ID,
        "fresh_live_job_id": AUTH_FRESH_ID,
        "fresh_live_sha256": "d" * 64,
        "object_guid": GUID,
        "object_class": "group",
        "class_policy": "standard_controlled",
        "effective_new_name": NAME,
        "effective_target_path": TARGET,
        "actor_subject": actor()["subject"],
        "actor_username": actor()["username"],
        "actor_issuer": actor()["issuer"],
        "actor_azp": actor()["azp"],
        "acknowledge_exact_object": True,
        "acknowledge_exact_target": True,
        "acknowledge_restore_write": True,
        "authorization_reason":
            "Validation humaine controlee de restauration EITAS.",
        "issued_at": (now - timedelta(seconds=10)).isoformat(),
        "expires_at": (now + timedelta(seconds=50)).isoformat(),
        "one_shot_required": True,
        "authorization_consumed": False,
        "human_authorized": True,
        "persistence_enabled": False,
        "route_enabled": False,
        "job_creation_authorized": False,
        "claim_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "restore_authorized": False,
        "restore_whatif_authorized": False,
        "execution_authorized": False,
        "write_performed": False,
    }

    source = AdDeletedObjectRestoreAuthorization(
        authorization_digest=_sha(payload),
        **payload,
    )

    assert_ad_deleted_object_restore_authorization_invariants(
        source
    )

    with tempfile.TemporaryDirectory(
        prefix="c95-a4d2-auth-"
    ) as directory:
        record = persist_ad_deleted_object_restore_authorization(
            source,
            registry_file=(
                Path(directory)
                / "restore-authorization-registry.json"
            ),
            now=now - timedelta(seconds=5),
        )

    assert_ad_deleted_object_restore_authorization_persistence_invariants(
        record
    )

    return record


def safe_preflight(now, *, fresh_at=None):
    at = fresh_at or (now - timedelta(seconds=1))
    return {
        "read_only": True,
        "source_job_id": INVENTORY_ID,
        "source_completed_at": (now - timedelta(seconds=20)).isoformat(),
        "object_guid": GUID,
        "policy": {
            "decision": "candidate_preflight",
            "preflight_passed": True,
            "simulation_candidate": True,
            "manual_review_required": False,
            "object_class": "group",
            "class_policy": "standard_controlled",
            "effective_new_name": NAME,
            "effective_target_path": TARGET,
        },
        "live_revalidation_performed": True,
        "live_job_id": FRESH_ID,
        "live_job_completed_at": at.isoformat(),
        "restore_job_created": False,
        "restore_implemented": False,
        "execution_authorized": False,
        "write_authorized": False,
    }


def build(monkeypatch, now, **overrides):
    seen = {}

    preflight_result = overrides.pop(
        "preflight_result",
        None,
    )

    def fake(jobs_path, **kwargs):
        seen["jobs_path"] = jobs_path
        seen.update(kwargs)

        if preflight_result is not None:
            return preflight_result

        return safe_preflight(now)

    monkeypatch.setattr(
        pre,
        "preflight_deleted_object_restore",
        fake,
    )

    auth = overrides.pop(
        "authorization_record",
        authorization(now),
    )

    kwargs = {
        "jobs_path": Path("/tmp/c95-preexecution-jobs.json"),
        "fresh_live_job_id": FRESH_ID,
        "expected_authorization_id": AUTH_ID,
        "expected_authorization_digest": auth.authorization_digest,
        "expected_object_guid": GUID,
        "confirmed_new_name": NAME,
        "confirmed_target_path": TARGET,
        "server_actor": actor(),
        "current_mode": "Simulation",
        "now": now,
    }
    kwargs.update(overrides)

    return (
        pre.build_ad_deleted_object_restore_preexecution(
            auth,
            **kwargs,
        ),
        seen,
    )


def test_valid_preexecution_is_dormant_and_non_authorizing(monkeypatch):
    now = datetime.now(timezone.utc)
    record, _ = build(monkeypatch, now)

    assert record.contract_version == "c9.5a4d-v1"
    assert record.state == "restore_preexecution_ready_dormant"
    assert record.status == "ready"
    assert record.object_guid == GUID
    assert record.effective_new_name == NAME
    assert record.effective_target_path == TARGET
    assert record.human_authorized is True
    assert record.revalidation_passed is True
    assert record.authorization_consumption_required is True
    assert record.authorization_consumed is False

    assert record.persistence_enabled is False
    assert record.route_enabled is False
    assert record.job_creation_authorized is False
    assert record.claim_authorized is False
    assert record.runtime_authorized is False
    assert record.production_authorized is False
    assert record.restore_authorized is False
    assert record.restore_whatif_authorized is False
    assert record.execution_authorized is False
    assert record.write_performed is False

    pre.assert_ad_deleted_object_restore_preexecution_invariants(record)


def test_reuses_existing_read_only_preflight_with_45_second_ttl(monkeypatch):
    now = datetime.now(timezone.utc)
    _, seen = build(monkeypatch, now)

    assert seen["object_guid"] == GUID
    assert seen["requested_new_name"] == NAME
    assert seen["requested_target_path"] == TARGET
    assert seen["live_job_id"] == FRESH_ID
    assert seen["live_revalidation_max_age_seconds"] == 45


def test_preexecution_ttl_is_bounded_by_45_seconds(monkeypatch):
    now = datetime.now(timezone.utc)
    record, _ = build(monkeypatch, now)

    issued = datetime.fromisoformat(record.issued_at)
    expires = datetime.fromisoformat(record.expires_at)

    assert 0 < (expires - issued).total_seconds() <= 45


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("expected_authorization_id",
         "99999999-9999-4999-8999-999999999999",
         "authorization id mismatch"),
        ("expected_authorization_digest",
         "f" * 64,
         "authorization digest mismatch"),
        ("expected_object_guid",
         "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
         "object GUID mismatch"),
        ("confirmed_new_name",
         "GG_OTHER",
         "name confirmation mismatch"),
        ("confirmed_target_path",
         "OU=Other,DC=API,DC=LOCAL",
         "target confirmation mismatch"),
    ],
)
def test_exact_authorization_and_restore_bindings_are_required(
    monkeypatch,
    field,
    value,
    match,
):
    now = datetime.now(timezone.utc)

    with pytest.raises(
        pre.AdDeletedObjectRestorePreexecutionConflict,
        match=match,
    ):
        build(monkeypatch, now, **{field: value})


def test_production_is_rejected(monkeypatch):
    now = datetime.now(timezone.utc)

    with pytest.raises(
        pre.AdDeletedObjectRestorePreexecutionError,
        match="Simulation-only",
    ):
        build(monkeypatch, now, current_mode="Production")


def test_actor_binding_is_required(monkeypatch):
    now = datetime.now(timezone.utc)
    wrong = actor()
    wrong["subject"] = "another-subject"

    with pytest.raises(
        pre.AdDeletedObjectRestorePreexecutionConflict,
        match="actor mismatch",
    ):
        build(monkeypatch, now, server_actor=wrong)


@pytest.mark.parametrize(
    "offset,match",
    [
        (-50, "stale"),
        (-6, "newer than persisted authorization"),
        (31, "too far in the future"),
    ],
)
def test_fresh_live_timestamp_is_fail_closed(
    monkeypatch,
    offset,
    match,
):
    now = datetime.now(timezone.utc)
    result = safe_preflight(
        now,
        fresh_at=now + timedelta(seconds=offset),
    )

    with pytest.raises(
        pre.AdDeletedObjectRestorePreexecutionConflict,
        match=match,
    ):
        build(
            monkeypatch,
            now,
            preflight_result=result,
        )


def test_unsafe_live_preflight_is_rejected(monkeypatch):
    now = datetime.now(timezone.utc)
    result = safe_preflight(now)
    result["execution_authorized"] = True

    with pytest.raises(
        pre.AdDeletedObjectRestorePreexecutionConflict,
        match="unsafe fresh preflight flag",
    ):
        build(
            monkeypatch,
            now,
            preflight_result=result,
        )


def test_invariants_reject_restore_authorization_mutation(monkeypatch):
    now = datetime.now(timezone.utc)
    record, _ = build(monkeypatch, now)
    unsafe = replace(record, restore_authorized=True)

    with pytest.raises(
        pre.AdDeletedObjectRestorePreexecutionError,
        match="unsafe preexecution flag",
    ):
        pre.assert_ad_deleted_object_restore_preexecution_invariants(
            unsafe
        )


def test_source_contains_no_restore_primitive_and_dangerous_constants_are_false():
    source = Path(
        "api/app/services/ad_deleted_object_restore_preexecution.py"
    ).read_text(encoding="utf-8")

    forbidden = "Restore-" + "ADObject"
    assert forbidden not in source
    assert ("Enable-" + "ADOptionalFeature") not in source

    assert pre.AD_DELETED_OBJECT_RESTORE_PREEXECUTION_PERSISTENCE_ENABLED is False
    assert pre.AD_DELETED_OBJECT_RESTORE_PREEXECUTION_ROUTE_ENABLED is False
    assert pre.AD_DELETED_OBJECT_RESTORE_PREEXECUTION_JOB_CREATION_AUTHORIZED is False
    assert pre.AD_DELETED_OBJECT_RESTORE_PREEXECUTION_CLAIM_AUTHORIZED is False
    assert pre.AD_DELETED_OBJECT_RESTORE_PREEXECUTION_RUNTIME_AUTHORIZED is False
    assert pre.AD_DELETED_OBJECT_RESTORE_PREEXECUTION_PRODUCTION_AUTHORIZED is False
    assert pre.AD_DELETED_OBJECT_RESTORE_PREEXECUTION_RESTORE_AUTHORIZED is False
    assert pre.AD_DELETED_OBJECT_RESTORE_PREEXECUTION_RESTORE_WHATIF_AUTHORIZED is False
    assert pre.AD_DELETED_OBJECT_RESTORE_PREEXECUTION_EXECUTION_AUTHORIZED is False
    assert pre.AD_DELETED_OBJECT_RESTORE_PREEXECUTION_WRITE_PERFORMED is False
