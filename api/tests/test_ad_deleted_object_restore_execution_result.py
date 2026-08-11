from __future__ import annotations

import importlib.util
import json

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.services.ad_deleted_object_restore_execution_transport as m
import main as api_main


HELPER_PATH = Path(__file__).with_name(
    "test_ad_deleted_object_restore_execution_transport.py"
)

SPEC = importlib.util.spec_from_file_location(
    "c95_a5e2_transport_helpers",
    HELPER_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "unable to load A5E2 transport helpers"
    )

helper = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    helper
)

SECRET = helper.SECRET


def _processing(
    monkeypatch,
    tmp_path,
    now,
):
    envelope = helper._envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = tmp_path / "transport.json"

    ticket = helper._queue(
        envelope,
        registry,
        now=now + timedelta(seconds=6),
    )

    claim = (
        m.claim_ad_deleted_object_restore_execution_for_agent(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            agent_name="SRV-DC01",
            signing_secret=SECRET,
            current_mode="Simulation",
            now=now + timedelta(seconds=7),
        )
    )

    return (
        envelope,
        registry,
        ticket,
        claim,
    )


def _success_result(
    envelope,
):
    return {
        "contract_version":
            "c9.5a5e3-v1",

        "action":
            "restore_deleted_object_execute",

        "global_mode":
            "Simulation",

        "envelope_id":
            envelope.envelope_id,

        "execution_consumption_id":
            envelope.execution_consumption_id,

        "execution_ticket_id":
            envelope.execution_ticket_id,

        "object_guid":
            envelope.object_guid,

        "effective_new_name":
            envelope.effective_new_name,

        "effective_target_path":
            envelope.effective_target_path,

        "signature_verified":
            True,

        "fresh_deleted_object_verified":
            True,

        "fresh_target_verified":
            True,

        "target_collision":
            False,

        "controlled_restore_runtime_authorized":
            True,

        "restore_performed":
            True,

        "write_performed":
            True,

        "post_restore_object_guid_verified":
            True,

        "post_restore_target_present":
            True,

        "post_restore_deleted_object_absent":
            True,

        "production_authorized":
            False,
    }


def _failure_result(
    envelope,
    *,
    signature_verified=True,
    write_performed=False,
):
    return {
        "contract_version":
            "c9.5a5e3-v1",

        "action":
            "restore_deleted_object_execute",

        "global_mode":
            "Simulation",

        "envelope_id":
            envelope.envelope_id,

        "execution_consumption_id":
            envelope.execution_consumption_id,

        "execution_ticket_id":
            envelope.execution_ticket_id,

        "object_guid":
            envelope.object_guid,

        "effective_new_name":
            envelope.effective_new_name,

        "effective_target_path":
            envelope.effective_target_path,

        "signature_verified":
            signature_verified,

        "restore_performed":
            write_performed,

        "write_performed":
            write_performed,

        "production_authorized":
            False,
    }


def test_successful_restore_result_completes_atomically(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope, registry, ticket, claim = _processing(
        monkeypatch,
        tmp_path,
        now,
    )

    completion = (
        m.complete_ad_deleted_object_restore_execution(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            transport_execution_id=claim.transport_execution_id,
            agent_name="SRV-DC01",
            signing_secret=SECRET,
            current_mode="Simulation",
            success=True,
            result=_success_result(
                envelope
            ),
            now=now + timedelta(seconds=9),
        )
    )

    assert completion.state == "restore_execution_completed"
    assert completion.success is True
    assert completion.write_performed is True
    assert completion.production_authorized is False

    persisted = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    record = persisted["records"][0]

    assert record["state"] == "restore_execution_completed"
    assert record["success"] is True
    assert record["write_performed"] is True
    assert record["controlled_restore_runtime_authorized"] is False

    assert len(
        record["completion_digest"]
    ) == 64

    m._validate_registry(
        persisted
    )


def test_completed_transport_cannot_be_completed_twice(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope, registry, ticket, claim = _processing(
        monkeypatch,
        tmp_path,
        now,
    )

    kwargs = {
        "transport_registry_file":
            registry,

        "transport_ticket_id":
            ticket.transport_ticket_id,

        "transport_execution_id":
            claim.transport_execution_id,

        "agent_name":
            "SRV-DC01",

        "signing_secret":
            SECRET,

        "current_mode":
            "Simulation",

        "success":
            True,

        "result":
            _success_result(
                envelope
            ),
    }

    m.complete_ad_deleted_object_restore_execution(
        **kwargs,
        now=now + timedelta(seconds=9),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportConflict,
        match="not processing",
    ):
        m.complete_ad_deleted_object_restore_execution(
            **kwargs,
            now=now + timedelta(seconds=10),
        )


def test_wrong_execution_id_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope, registry, ticket, claim = _processing(
        monkeypatch,
        tmp_path,
        now,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportConflict,
        match="execution id mismatch",
    ):
        m.complete_ad_deleted_object_restore_execution(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            transport_execution_id=(
                "11111111-1111-4111-8111-111111111111"
            ),
            agent_name="SRV-DC01",
            signing_secret=SECRET,
            current_mode="Simulation",
            success=True,
            result=_success_result(
                envelope
            ),
            now=now + timedelta(seconds=9),
        )


def test_wrong_agent_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope, registry, ticket, claim = _processing(
        monkeypatch,
        tmp_path,
        now,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportConflict,
        match="another agent",
    ):
        m.complete_ad_deleted_object_restore_execution(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            transport_execution_id=claim.transport_execution_id,
            agent_name="OTHER-DC",
            signing_secret=SECRET,
            current_mode="Simulation",
            success=True,
            result=_success_result(
                envelope
            ),
            now=now + timedelta(seconds=9),
        )


def test_tampered_result_binding_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope, registry, ticket, claim = _processing(
        monkeypatch,
        tmp_path,
        now,
    )

    result = _success_result(
        envelope
    )

    result[
        "object_guid"
    ] = "11111111-1111-4111-8111-111111111111"

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportError,
        match="object_guid",
    ):
        m.complete_ad_deleted_object_restore_execution(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            transport_execution_id=claim.transport_execution_id,
            agent_name="SRV-DC01",
            signing_secret=SECRET,
            current_mode="Simulation",
            success=True,
            result=result,
            now=now + timedelta(seconds=9),
        )


def test_success_cannot_hide_missing_write(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope, registry, ticket, claim = _processing(
        monkeypatch,
        tmp_path,
        now,
    )

    result = _success_result(
        envelope
    )

    result[
        "restore_performed"
    ] = False

    result[
        "write_performed"
    ] = False

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportError,
        match="marker missing",
    ):
        m.complete_ad_deleted_object_restore_execution(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            transport_execution_id=claim.transport_execution_id,
            agent_name="SRV-DC01",
            signing_secret=SECRET,
            current_mode="Simulation",
            success=True,
            result=result,
            now=now + timedelta(seconds=9),
        )


def test_failure_before_write_is_recorded_without_write(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope, registry, ticket, claim = _processing(
        monkeypatch,
        tmp_path,
        now,
    )

    completion = (
        m.complete_ad_deleted_object_restore_execution(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            transport_execution_id=claim.transport_execution_id,
            agent_name="SRV-DC01",
            signing_secret=SECRET,
            current_mode="Simulation",
            success=False,
            result=_failure_result(
                envelope,
                signature_verified=False,
                write_performed=False,
            ),
            message="signature rejected",
            now=now + timedelta(seconds=9),
        )
    )

    assert completion.state == "restore_execution_failed"
    assert completion.success is False
    assert completion.write_performed is False


def test_failure_after_write_preserves_write_marker(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope, registry, ticket, claim = _processing(
        monkeypatch,
        tmp_path,
        now,
    )

    completion = (
        m.complete_ad_deleted_object_restore_execution(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            transport_execution_id=claim.transport_execution_id,
            agent_name="SRV-DC01",
            signing_secret=SECRET,
            current_mode="Simulation",
            success=False,
            result=_failure_result(
                envelope,
                write_performed=True,
            ),
            message="post restore verification failed",
            now=now + timedelta(seconds=9),
        )
    )

    assert completion.state == "restore_execution_failed"
    assert completion.success is False
    assert completion.write_performed is True

    persisted = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    assert (
        persisted["records"][0][
            "write_performed"
        ]
        is True
    )


def test_failure_requires_message(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope, registry, ticket, claim = _processing(
        monkeypatch,
        tmp_path,
        now,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportError,
        match="failure message",
    ):
        m.complete_ad_deleted_object_restore_execution(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            transport_execution_id=claim.transport_execution_id,
            agent_name="SRV-DC01",
            signing_secret=SECRET,
            current_mode="Simulation",
            success=False,
            result=_failure_result(
                envelope
            ),
            message="",
            now=now + timedelta(seconds=9),
        )


def test_result_route_is_strict_worker_only_and_restore_worker_requires_explicit_optin():
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

    assert (
        '"/api/agent/deleted-object-restore/execution/result/"'
        in main
    )

    result_index = main.index(
        '"/api/agent/deleted-object-restore/execution/result/"'
    )

    nearby = main[
        result_index:
        result_index + 1200
    ]

    assert "require_worker_api_key" in nearby

    assert (
        "function Process-EitasPendingDeletedObjectRestoreExecutions {"
        in windows
    )

    worker = Path(
        "agent-windows/Run-AdAdminWorker.ps1"
    ).read_text(
        encoding="utf-8"
    )

    # A5E3-R2D exposes the dedicated processor only inside
    # the candidate module. The worker entrypoint remains unwired.
    assert (
        "function Invoke-EitasAdAdminDeletedObjectRestoreExecute {"
        in windows
    )

    assert (
        "[switch]$EnableDeletedObjectRestoreExecution"
        in worker
    )

    assert (
        "if ($EnableDeletedObjectRestoreExecution) {"
        in worker
    )

    assert (
        worker.count(
            "Process-EitasPendingDeletedObjectRestoreExecutions"
        )
        == 1
    )

    assert (
        "$EnableDeletedObjectRestoreExecution = $true"
        not in worker
    )

    assert (
        "restore_deleted_object_execute"
        not in worker
    )


def test_result_route_uses_server_simulation_mode_and_secret(
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "API_KEY",
        SECRET,
    )

    monkeypatch.setattr(
        api_main,
        "_eitas_agent_mode_load_config",
        lambda: {
            "mode":
                "Simulation",
        },
    )

    captured = {}

    completion = SimpleNamespace(
        contract_version="c9.5a5e2-v1",
        state="restore_execution_completed",

        transport_ticket_id=(
            "11111111-1111-4111-8111-111111111111"
        ),

        transport_execution_id=(
            "22222222-2222-4222-8222-222222222222"
        ),

        envelope_id=(
            "33333333-3333-4333-8333-333333333333"
        ),

        execution_consumption_id=(
            "44444444-4444-4444-8444-444444444444"
        ),

        execution_ticket_id=(
            "55555555-5555-4555-8555-555555555555"
        ),

        completed_at="2026-08-11T07:00:09+00:00",
        completed_by="SRV-DC01",

        success=True,
        write_performed=True,

        completion_digest="a" * 64,

        controlled_restore_runtime_authorized=False,
        production_authorized=False,
    )

    def fake_complete(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return completion

    monkeypatch.setattr(
        api_main,
        "service_complete_ad_deleted_object_restore_execution",
        fake_complete,
    )

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs: None,
    )

    response = (
        api_main.complete_deleted_object_restore_execution_api(
            completion.transport_ticket_id,
            {
                "transport_execution_id":
                    completion.transport_execution_id,

                "agent_name":
                    "SRV-DC01",

                "success":
                    True,

                "result":
                    {
                        "dummy":
                            True,
                    },

                "message":
                    "",
            },
            worker=SimpleNamespace(),
        )
    )

    assert captured["current_mode"] == "Simulation"
    assert captured["signing_secret"] == SECRET
    assert captured["agent_name"] == "SRV-DC01"

    assert response["success"] is True
    assert response["write_performed"] is True

    assert (
        response["authorization"][
            "production_authorized"
        ]
        is False
    )
