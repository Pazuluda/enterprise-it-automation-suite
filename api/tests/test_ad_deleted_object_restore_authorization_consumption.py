from __future__ import annotations

import hashlib
import importlib.util
import json

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.services.ad_deleted_object_restore_authorization_consumption as m


HELPER_PATH = Path(__file__).with_name(
    "test_ad_deleted_object_restore_preexecution.py"
)

SPEC = importlib.util.spec_from_file_location(
    "c95_a4d2_test_helpers",
    HELPER_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load A4D2 test helpers")

h = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h)


def _canonical(payload: dict) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _records(monkeypatch, now):
    authorization = h.authorization(now)

    preexecution, _ = h.build(
        monkeypatch,
        now,
        authorization_record=authorization,
    )

    return authorization, preexecution


def _consume(
    monkeypatch,
    tmp_path,
    now,
    *,
    mode="Simulation",
    server_actor=None,
    registry=None,
):
    authorization, preexecution = _records(
        monkeypatch,
        now,
    )

    record = m.consume_ad_deleted_object_restore_authorization(
        authorization,
        preexecution,
        consumption_registry_file=(
            registry
            or tmp_path / "restore-authorization-consumptions.json"
        ),
        server_actor=server_actor or h.actor(),
        current_mode=mode,
        now=now + timedelta(seconds=1),
    )

    return authorization, preexecution, record


def test_valid_consumption_is_one_shot_and_non_authorizing(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    authorization, preexecution, record = _consume(
        monkeypatch,
        tmp_path,
        now,
    )

    assert record.contract_version == "c9.5a4d3-v1"
    assert record.state == "restore_authorization_consumed_dormant"
    assert record.status == "consumed"

    assert record.authorization_id == authorization.authorization_id
    assert record.authorization_digest == authorization.authorization_digest
    assert record.authorization_record_digest == authorization.record_digest

    assert record.preexecution_id == preexecution.preexecution_id
    assert record.preexecution_digest == preexecution.preexecution_digest

    assert record.object_guid == authorization.object_guid
    assert record.object_class == authorization.object_class
    assert record.class_policy == authorization.class_policy
    assert record.effective_new_name == authorization.effective_new_name
    assert record.effective_target_path == authorization.effective_target_path

    assert record.human_authorized is True
    assert record.revalidation_passed is True
    assert record.authorization_consumed is True
    assert record.one_shot_consumption is True

    assert record.persistence_enabled is True

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
        assert getattr(record, field) is False

    m.assert_ad_deleted_object_restore_authorization_consumption_invariants(
        record
    )


def test_duplicate_consumption_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)
    registry = tmp_path / "consumptions.json"

    authorization, preexecution = _records(
        monkeypatch,
        now,
    )

    m.consume_ad_deleted_object_restore_authorization(
        authorization,
        preexecution,
        consumption_registry_file=registry,
        server_actor=h.actor(),
        current_mode="Simulation",
        now=now + timedelta(seconds=1),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreAuthorizationConsumptionConflict,
        match="already consumed",
    ):
        m.consume_ad_deleted_object_restore_authorization(
            authorization,
            preexecution,
            consumption_registry_file=registry,
            server_actor=h.actor(),
            current_mode="Simulation",
            now=now + timedelta(seconds=2),
        )


def test_registry_and_lock_are_0600(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)
    registry = tmp_path / "consumptions.json"

    _consume(
        monkeypatch,
        tmp_path,
        now,
        registry=registry,
    )

    lock = tmp_path / ".consumptions.json.lock"

    assert (registry.stat().st_mode & 0o777) == 0o600
    assert (lock.stat().st_mode & 0o777) == 0o600


def test_production_mode_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)
    authorization, preexecution = _records(
        monkeypatch,
        now,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreAuthorizationConsumptionError,
        match="Simulation-only",
    ):
        m.consume_ad_deleted_object_restore_authorization(
            authorization,
            preexecution,
            consumption_registry_file=tmp_path / "consumptions.json",
            server_actor=h.actor(),
            current_mode="Production",
            now=now + timedelta(seconds=1),
        )


def test_actor_mismatch_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)
    authorization, preexecution = _records(
        monkeypatch,
        now,
    )

    actor = h.actor()
    actor["subject"] = "different-subject"

    with pytest.raises(
        m.AdDeletedObjectRestoreAuthorizationConsumptionConflict,
        match="actor mismatch",
    ):
        m.consume_ad_deleted_object_restore_authorization(
            authorization,
            preexecution,
            consumption_registry_file=tmp_path / "consumptions.json",
            server_actor=actor,
            current_mode="Simulation",
            now=now + timedelta(seconds=1),
        )


def test_preexecution_binding_mismatch_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)
    authorization, preexecution = _records(
        monkeypatch,
        now,
    )

    changed = replace(
        preexecution,
        effective_target_path="OU=Other,DC=API,DC=LOCAL",
    )

    payload = asdict(changed)
    payload.pop("preexecution_digest")

    changed = replace(
        changed,
        preexecution_digest=_canonical(payload),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreAuthorizationConsumptionConflict,
        match="effective_target_path",
    ):
        m.consume_ad_deleted_object_restore_authorization(
            authorization,
            changed,
            consumption_registry_file=tmp_path / "consumptions.json",
            server_actor=h.actor(),
            current_mode="Simulation",
            now=now + timedelta(seconds=1),
        )


def test_expired_preexecution_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)
    authorization, preexecution = _records(
        monkeypatch,
        now,
    )

    expires = datetime.fromisoformat(
        preexecution.expires_at.replace("Z", "+00:00")
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreAuthorizationConsumptionConflict,
        match="preexecution expired",
    ):
        m.consume_ad_deleted_object_restore_authorization(
            authorization,
            preexecution,
            consumption_registry_file=tmp_path / "consumptions.json",
            server_actor=h.actor(),
            current_mode="Simulation",
            now=expires,
        )


def test_registry_symlink_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)
    authorization, preexecution = _records(
        monkeypatch,
        now,
    )

    target = tmp_path / "real.json"
    target.write_text("{}", encoding="utf-8")

    registry = tmp_path / "consumptions.json"
    registry.symlink_to(target)

    with pytest.raises(
        m.AdDeletedObjectRestoreAuthorizationConsumptionError,
        match="must not be a symlink",
    ):
        m.consume_ad_deleted_object_restore_authorization(
            authorization,
            preexecution,
            consumption_registry_file=registry,
            server_actor=h.actor(),
            current_mode="Simulation",
            now=now + timedelta(seconds=1),
        )


def test_tampered_registry_record_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)
    registry = tmp_path / "consumptions.json"

    authorization, preexecution, _ = _consume(
        monkeypatch,
        tmp_path,
        now,
        registry=registry,
    )

    data = json.loads(
        registry.read_text(encoding="utf-8")
    )

    data["records"][0]["effective_target_path"] = (
        "OU=Tampered,DC=API,DC=LOCAL"
    )

    registry.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreAuthorizationConsumptionError,
        match="record digest mismatch",
    ):
        m.consume_ad_deleted_object_restore_authorization(
            authorization,
            preexecution,
            consumption_registry_file=registry,
            server_actor=h.actor(),
            current_mode="Simulation",
            now=now + timedelta(seconds=2),
        )


def test_persisted_record_contains_no_execution_rights(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)
    registry = tmp_path / "consumptions.json"

    _consume(
        monkeypatch,
        tmp_path,
        now,
        registry=registry,
    )

    raw = registry.read_text(encoding="utf-8")

    assert '"authorization_consumed": true' in raw
    assert '"one_shot_consumption": true' in raw

    for forbidden in (
        '"route_enabled": true',
        '"job_creation_authorized": true',
        '"claim_authorized": true',
        '"runtime_authorized": true',
        '"production_authorized": true',
        '"restore_authorized": true',
        '"restore_whatif_authorized": true',
        '"execution_authorized": true',
        '"write_performed": true',
    ):
        assert forbidden not in raw


def test_service_has_no_ad_write_primitive_or_runtime_integration():
    service = Path(
        "api/app/services/"
        "ad_deleted_object_restore_authorization_consumption.py"
    ).read_text(encoding="utf-8")

    main = Path(
        "api/main.py"
    ).read_text(encoding="utf-8")

    assert "Restore-ADObject" not in service
    assert "Enable-ADOptionalFeature" not in service
    assert (
        "ad_deleted_object_restore_authorization_consumption"
        not in main
    )
