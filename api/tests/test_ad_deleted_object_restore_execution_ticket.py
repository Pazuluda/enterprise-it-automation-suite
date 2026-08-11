from __future__ import annotations

import importlib.util

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.services.ad_deleted_object_restore_execution_ticket as ticket


HELPER_PATH = Path(__file__).with_name(
    "test_ad_deleted_object_restore_runtime_gate.py"
)

SPEC = importlib.util.spec_from_file_location(
    "c95_a4e_test_helpers",
    HELPER_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "unable to load A4E runtime gate test helpers"
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


def _runtime_gate(
    monkeypatch,
    tmp_path,
    now,
):
    return helper._build(
        monkeypatch,
        tmp_path,
        now,
    )


def _build_ticket(
    monkeypatch,
    tmp_path,
    now,
    *,
    runtime_gate=None,
    actor=None,
    mode="Simulation",
    confirmation=None,
    ticket_now=None,
):
    source = (
        runtime_gate
        if runtime_gate is not None
        else _runtime_gate(
            monkeypatch,
            tmp_path,
            now,
        )
    )

    expected_confirmation = (
        ticket.expected_ad_deleted_object_restore_confirmation(
            source
        )
    )

    return ticket.build_ad_deleted_object_restore_execution_ticket(
        source,
        server_actor=(
            actor
            if actor is not None
            else _actor(source)
        ),
        current_mode=mode,
        confirmation_text=(
            expected_confirmation
            if confirmation is None
            else confirmation
        ),
        now=(
            ticket_now
            if ticket_now is not None
            else now + timedelta(seconds=3)
        ),
    )


def test_valid_ticket_is_exact_one_shot_and_controlled(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    runtime_gate = _runtime_gate(
        monkeypatch,
        tmp_path,
        now,
    )

    record = _build_ticket(
        monkeypatch,
        tmp_path,
        now,
        runtime_gate=runtime_gate,
    )

    assert record.contract_version == "c9.5a5b-v1"
    assert record.state == "restore_execution_ticket_dormant"
    assert record.status == "authorized_one_shot_dormant"

    assert record.runtime_gate_id == runtime_gate.runtime_gate_id
    assert record.runtime_gate_digest == runtime_gate.runtime_gate_digest

    assert (
        record.authorization_consumption_id
        == runtime_gate.authorization_consumption_id
    )

    assert record.authorization_id == runtime_gate.authorization_id
    assert record.preexecution_id == runtime_gate.preexecution_id

    assert record.object_guid == runtime_gate.object_guid
    assert record.object_class == runtime_gate.object_class
    assert record.class_policy == runtime_gate.class_policy

    assert (
        record.effective_new_name
        == runtime_gate.effective_new_name
    )

    assert (
        record.effective_target_path
        == runtime_gate.effective_target_path
    )

    assert record.human_authorized is True
    assert record.revalidation_passed is True
    assert record.source_one_shot_verified is True
    assert record.one_shot_required is True
    assert record.consumed is False

    assert record.persistence_enabled is False
    assert record.route_enabled is False
    assert record.agent_endpoints_enabled is False
    assert record.job_creation_authorized is False
    assert record.claim_authorized is False
    assert record.runtime_authorized is False
    assert record.production_authorized is False

    assert record.controlled_restore_authorized is True
    assert record.restore_cmdlet_authorized is True
    assert record.restore_whatif_authorized is True
    assert record.execution_authorized is True

    assert record.write_performed is False

    ticket.assert_ad_deleted_object_restore_execution_ticket_invariants(
        record
    )


def test_exact_confirmation_is_required(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    runtime_gate = _runtime_gate(
        monkeypatch,
        tmp_path,
        now,
    )

    expected = (
        ticket.expected_ad_deleted_object_restore_confirmation(
            runtime_gate
        )
    )

    assert runtime_gate.object_guid in expected
    assert runtime_gate.effective_new_name in expected
    assert runtime_gate.effective_target_path in expected

    with pytest.raises(
        ticket.AdDeletedObjectRestoreExecutionTicketConflict,
        match="confirmation mismatch",
    ):
        _build_ticket(
            monkeypatch,
            tmp_path,
            now,
            runtime_gate=runtime_gate,
            confirmation=expected + " ",
        )


def test_production_global_mode_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    runtime_gate = _runtime_gate(
        monkeypatch,
        tmp_path,
        now,
    )

    with pytest.raises(
        ticket.AdDeletedObjectRestoreExecutionTicketError,
        match="Simulation global mode",
    ):
        _build_ticket(
            monkeypatch,
            tmp_path,
            now,
            runtime_gate=runtime_gate,
            mode="Production",
        )


def test_actor_mismatch_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    runtime_gate = _runtime_gate(
        monkeypatch,
        tmp_path,
        now,
    )

    actor = _actor(
        runtime_gate
    )

    actor["subject"] = "different-subject"

    with pytest.raises(
        ticket.AdDeletedObjectRestoreExecutionTicketConflict,
        match="actor mismatch",
    ):
        _build_ticket(
            monkeypatch,
            tmp_path,
            now,
            runtime_gate=runtime_gate,
            actor=actor,
        )


def test_expired_runtime_gate_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    runtime_gate = _runtime_gate(
        monkeypatch,
        tmp_path,
        now,
    )

    expires = datetime.fromisoformat(
        runtime_gate.expires_at.replace(
            "Z",
            "+00:00",
        )
    )

    with pytest.raises(
        ticket.AdDeletedObjectRestoreExecutionTicketConflict,
        match="runtime gate expired",
    ):
        _build_ticket(
            monkeypatch,
            tmp_path,
            now,
            runtime_gate=runtime_gate,
            ticket_now=expires,
        )


def test_ticket_ttl_is_20_seconds(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    record = _build_ticket(
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
        == timedelta(seconds=20)
    )


def test_ticket_ttl_is_clamped_to_runtime_gate(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    runtime_gate = _runtime_gate(
        monkeypatch,
        tmp_path,
        now,
    )

    source_expiration = datetime.fromisoformat(
        runtime_gate.expires_at.replace(
            "Z",
            "+00:00",
        )
    )

    ticket_now = (
        source_expiration
        - timedelta(seconds=5)
    )

    record = _build_ticket(
        monkeypatch,
        tmp_path,
        now,
        runtime_gate=runtime_gate,
        ticket_now=ticket_now,
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

    assert expires == source_expiration
    assert expires - issued == timedelta(seconds=5)


def test_tampered_ticket_digest_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    record = _build_ticket(
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
        ticket.AdDeletedObjectRestoreExecutionTicketError,
        match="digest mismatch",
    ):
        ticket.assert_ad_deleted_object_restore_execution_ticket_invariants(
            tampered
        )


def test_unsafe_global_runtime_flag_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    record = _build_ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    unsafe = replace(
        record,
        runtime_authorized=True,
    )

    with pytest.raises(
        ticket.AdDeletedObjectRestoreExecutionTicketError,
        match="unsafe execution ticket flag",
    ):
        ticket.assert_ad_deleted_object_restore_execution_ticket_invariants(
            unsafe
        )


def test_service_has_capability_but_no_transport_or_restore_primitive():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_execution_ticket.py"
    ).read_text(
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

    assert "Restore-ADObject" not in source
    assert "service_create_ad_admin_job" not in source
    assert "claim_ad_admin_job" not in source
    assert "subprocess" not in source
    assert "powershell" not in source.lower()

    assert (
        "ad_deleted_object_restore_execution_ticket"
        not in main
    )

    assert (
        "build_ad_deleted_object_restore_execution_ticket"
        not in main
    )

    assert (
        "ad_deleted_object_restore_execution_ticket"
        not in windows
    )
