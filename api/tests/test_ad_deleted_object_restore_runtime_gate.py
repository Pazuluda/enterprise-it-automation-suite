from __future__ import annotations

import importlib.util

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.services.ad_deleted_object_restore_runtime_gate as gate


HELPER_PATH = Path(__file__).with_name(
    "test_ad_deleted_object_restore_authorization_consumption.py"
)

SPEC = importlib.util.spec_from_file_location(
    "c95_a4d3_test_helpers",
    HELPER_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "unable to load A4D3 test helpers"
    )

helper = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    helper
)


def _actor(record):
    return {
        "subject": record.actor_subject,
        "username": record.actor_username,
        "issuer": record.actor_issuer,
        "azp": record.actor_azp,
    }


def _source(
    monkeypatch,
    tmp_path,
    now,
):
    _, _, record = helper._consume(
        monkeypatch,
        tmp_path,
        now,
    )

    return record


def _build(
    monkeypatch,
    tmp_path,
    now,
    *,
    source=None,
    actor=None,
    mode="Simulation",
    gate_now=None,
):
    record = (
        source
        if source is not None
        else _source(
            monkeypatch,
            tmp_path,
            now,
        )
    )

    return gate.build_ad_deleted_object_restore_runtime_gate(
        record,
        server_actor=(
            actor
            if actor is not None
            else _actor(record)
        ),
        current_mode=mode,
        now=(
            gate_now
            if gate_now is not None
            else now + timedelta(seconds=2)
        ),
    )


def test_valid_gate_is_dormant_and_non_authorizing(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    source = _source(
        monkeypatch,
        tmp_path,
        now,
    )

    record = _build(
        monkeypatch,
        tmp_path,
        now,
        source=source,
    )

    assert record.contract_version == "c9.5a4e-v1"
    assert record.state == "restore_runtime_gate_dormant"
    assert record.status == "ready_dormant"

    assert (
        record.authorization_consumption_id
        == source.authorization_consumption_id
    )

    assert (
        record.authorization_consumption_record_digest
        == source.record_digest
    )

    assert record.authorization_id == source.authorization_id
    assert record.authorization_digest == source.authorization_digest
    assert record.preexecution_id == source.preexecution_id
    assert record.preexecution_digest == source.preexecution_digest

    assert record.object_guid == source.object_guid
    assert record.object_class == source.object_class
    assert record.class_policy == source.class_policy
    assert record.effective_new_name == source.effective_new_name
    assert record.effective_target_path == source.effective_target_path

    assert record.human_authorized is True
    assert record.revalidation_passed is True
    assert record.one_shot_consumption_verified is True
    assert record.source_consumption_verified is True

    for field in (
        "persistence_enabled",
        "route_enabled",
        "agent_endpoints_enabled",
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

    gate.assert_ad_deleted_object_restore_runtime_gate_invariants(
        record
    )


def test_production_mode_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    source = _source(
        monkeypatch,
        tmp_path,
        now,
    )

    with pytest.raises(
        gate.AdDeletedObjectRestoreRuntimeGateError,
        match="Simulation-only",
    ):
        _build(
            monkeypatch,
            tmp_path,
            now,
            source=source,
            mode="Production",
        )


def test_actor_mismatch_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    source = _source(
        monkeypatch,
        tmp_path,
        now,
    )

    actor = _actor(source)
    actor["subject"] = "different-subject"

    with pytest.raises(
        gate.AdDeletedObjectRestoreRuntimeGateConflict,
        match="actor mismatch",
    ):
        _build(
            monkeypatch,
            tmp_path,
            now,
            source=source,
            actor=actor,
        )


def test_unconsumed_source_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    source = _source(
        monkeypatch,
        tmp_path,
        now,
    )

    source = replace(
        source,
        authorization_consumed=False,
    )

    with pytest.raises(
        gate.AdDeletedObjectRestoreRuntimeGateError,
        match="authorization consumption marker",
    ):
        _build(
            monkeypatch,
            tmp_path,
            now,
            source=source,
        )


def test_unsafe_source_runtime_flag_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    source = _source(
        monkeypatch,
        tmp_path,
        now,
    )

    source = replace(
        source,
        runtime_authorized=True,
    )

    with pytest.raises(
        gate.AdDeletedObjectRestoreRuntimeGateError,
        match="unsafe authorization consumption flag",
    ):
        _build(
            monkeypatch,
            tmp_path,
            now,
            source=source,
        )


def test_expired_preexecution_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    source = _source(
        monkeypatch,
        tmp_path,
        now,
    )

    expires = datetime.fromisoformat(
        source.preexecution_expires_at.replace(
            "Z",
            "+00:00",
        )
    )

    with pytest.raises(
        gate.AdDeletedObjectRestoreRuntimeGateConflict,
        match="preexecution expired",
    ):
        _build(
            monkeypatch,
            tmp_path,
            now,
            source=source,
            gate_now=expires,
        )


def test_normal_gate_ttl_is_exactly_30_seconds(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    record = _build(
        monkeypatch,
        tmp_path,
        now,
    )

    issued = datetime.fromisoformat(
        record.issued_at.replace(
            "Z",
            "+00:00",
        )
    )

    expires = datetime.fromisoformat(
        record.expires_at.replace(
            "Z",
            "+00:00",
        )
    )

    assert (
        expires - issued
        == timedelta(seconds=30)
    )


def test_gate_ttl_is_clamped_to_source_expiration(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    source = _source(
        monkeypatch,
        tmp_path,
        now,
    )

    preexecution_expiration = datetime.fromisoformat(
        source.preexecution_expires_at.replace(
            "Z",
            "+00:00",
        )
    )

    gate_now = (
        preexecution_expiration
        - timedelta(seconds=5)
    )

    record = _build(
        monkeypatch,
        tmp_path,
        now,
        source=source,
        gate_now=gate_now,
    )

    issued = datetime.fromisoformat(
        record.issued_at.replace(
            "Z",
            "+00:00",
        )
    )

    expires = datetime.fromisoformat(
        record.expires_at.replace(
            "Z",
            "+00:00",
        )
    )

    assert expires == preexecution_expiration
    assert expires - issued == timedelta(seconds=5)


def test_tampered_runtime_gate_digest_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    record = _build(
        monkeypatch,
        tmp_path,
        now,
    )

    tampered = replace(
        record,
        effective_new_name=(
            record.effective_new_name
            + "-tampered"
        ),
    )

    with pytest.raises(
        gate.AdDeletedObjectRestoreRuntimeGateError,
        match="digest mismatch",
    ):
        gate.assert_ad_deleted_object_restore_runtime_gate_invariants(
            tampered
        )


def test_service_has_no_route_worker_or_restore_primitive():
    service_path = Path(
        "api/app/services/"
        "ad_deleted_object_restore_runtime_gate.py"
    )

    service = service_path.read_text(
        encoding="utf-8"
    )

    main = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    windows = Path(
        "agent-windows/modules/EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8"
    )

    assert "Restore-ADObject" not in service
    assert "Enable-ADOptionalFeature" not in service

    assert (
        "ad_deleted_object_restore_runtime_gate"
        not in main
    )

    assert (
        "build_ad_deleted_object_restore_runtime_gate"
        not in main
    )

    assert (
        "ad_deleted_object_restore_runtime_gate"
        not in windows
    )
