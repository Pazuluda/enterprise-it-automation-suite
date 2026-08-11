from __future__ import annotations

import importlib.util
import json
import multiprocessing

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.services.ad_deleted_object_restore_execution_consumption as m
import app.services.ad_deleted_object_restore_execution_ticket as ticket_module


HELPER_PATH = Path(__file__).with_name(
    "test_ad_deleted_object_restore_execution_ticket.py"
)

SPEC = importlib.util.spec_from_file_location(
    "c95_a5b_helpers",
    HELPER_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "unable to load A5B helpers"
    )

helper = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    helper
)


def _actor(
    ticket,
):
    return {
        "subject": ticket.actor_subject,
        "username": ticket.actor_username,
        "issuer": ticket.actor_issuer,
        "azp": ticket.actor_azp,
    }


def _ticket(
    monkeypatch,
    tmp_path,
    now,
):
    return helper._build_ticket(
        monkeypatch,
        tmp_path,
        now,
    )


def _consume(
    ticket,
    registry,
    *,
    actor=None,
    mode="Simulation",
    now=None,
):
    return m.consume_ad_deleted_object_restore_execution_ticket(
        ticket,
        consumption_registry_file=registry,
        server_actor=(
            actor
            if actor is not None
            else _actor(ticket)
        ),
        current_mode=mode,
        now=(
            now
            if now is not None
            else datetime.now(timezone.utc)
        ),
    )


def test_valid_execution_ticket_is_atomically_consumed(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = (
        tmp_path
        / "execution-consumption.json"
    )

    record = _consume(
        ticket,
        registry,
        now=now + timedelta(seconds=4),
    )

    assert record.contract_version == "c9.5a5d-v1"
    assert record.state == "restore_execution_ticket_consumed_dormant"
    assert record.status == "consumed"

    assert record.execution_ticket_id == ticket.execution_ticket_id
    assert record.execution_ticket_digest == ticket.execution_ticket_digest

    assert record.runtime_gate_id == ticket.runtime_gate_id
    assert record.authorization_id == ticket.authorization_id
    assert record.preexecution_id == ticket.preexecution_id

    assert record.object_guid == ticket.object_guid.lower()
    assert record.effective_new_name == ticket.effective_new_name
    assert record.effective_target_path == ticket.effective_target_path

    assert record.execution_ticket_consumed is True
    assert record.one_shot_consumption is True
    assert record.persistence_enabled is True

    assert record.route_enabled is False
    assert record.agent_endpoint_enabled is False
    assert record.runtime_authorized is False
    assert record.production_authorized is False
    assert record.restore_authorized is False
    assert record.execution_authorized is False
    assert record.write_performed is False

    assert registry.is_file()

    persisted = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    assert persisted["contract_version"] == "c9.5a5d-v1"
    assert len(persisted["records"]) == 1


def test_same_execution_ticket_replay_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = tmp_path / "registry.json"

    _consume(
        ticket,
        registry,
        now=now + timedelta(seconds=4),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionConsumptionConflict,
        match="already consumed",
    ):
        _consume(
            ticket,
            registry,
            now=now + timedelta(seconds=5),
        )


def test_second_ticket_from_same_runtime_gate_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    runtime_gate = helper._runtime_gate(
        monkeypatch,
        tmp_path,
        now,
    )

    actor = helper._actor(
        runtime_gate
    )

    confirmation = (
        ticket_module.expected_ad_deleted_object_restore_confirmation(
            runtime_gate
        )
    )

    first = (
        ticket_module.build_ad_deleted_object_restore_execution_ticket(
            runtime_gate,
            server_actor=actor,
            current_mode="Simulation",
            confirmation_text=confirmation,
            now=now + timedelta(seconds=3),
        )
    )

    second = (
        ticket_module.build_ad_deleted_object_restore_execution_ticket(
            runtime_gate,
            server_actor=actor,
            current_mode="Simulation",
            confirmation_text=confirmation,
            now=now + timedelta(seconds=4),
        )
    )

    assert first.execution_ticket_id != second.execution_ticket_id

    registry = tmp_path / "registry.json"

    _consume(
        first,
        registry,
        now=now + timedelta(seconds=5),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionConsumptionConflict,
        match="runtime gate id already consumed",
    ):
        _consume(
            second,
            registry,
            now=now + timedelta(seconds=6),
        )


def test_actor_mismatch_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    actor = _actor(
        ticket
    )

    actor["subject"] = "different-subject"

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionConsumptionConflict,
        match="actor mismatch",
    ):
        _consume(
            ticket,
            tmp_path / "registry.json",
            actor=actor,
            now=now + timedelta(seconds=4),
        )


def test_production_global_mode_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionConsumptionError,
        match="Simulation global mode",
    ):
        _consume(
            ticket,
            tmp_path / "registry.json",
            mode="Production",
            now=now + timedelta(seconds=4),
        )


def test_expired_execution_ticket_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    expires = datetime.fromisoformat(
        ticket.expires_at.replace(
            "Z",
            "+00:00",
        )
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionConsumptionConflict,
        match="expired",
    ):
        _consume(
            ticket,
            tmp_path / "registry.json",
            now=expires,
        )


def test_tampered_execution_ticket_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    tampered = replace(
        ticket,
        effective_new_name=(
            ticket.effective_new_name
            + "-tampered"
        ),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionConsumptionError,
        match="digest mismatch",
    ):
        _consume(
            tampered,
            tmp_path / "registry.json",
            now=now + timedelta(seconds=4),
        )


def test_relative_registry_path_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionConsumptionError,
        match="must be absolute",
    ):
        _consume(
            ticket,
            Path("relative-registry.json"),
            now=now + timedelta(seconds=4),
        )


def test_symlink_registry_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    target = tmp_path / "target.json"

    target.write_text(
        json.dumps(
            {
                "contract_version": "c9.5a5d-v1",
                "records": [],
            }
        ),
        encoding="utf-8",
    )

    registry = tmp_path / "registry.json"

    registry.symlink_to(
        target
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionConsumptionError,
        match="symlink",
    ):
        _consume(
            ticket,
            registry,
            now=now + timedelta(seconds=4),
        )


def test_corrupt_registry_fails_closed(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = tmp_path / "registry.json"

    registry.write_text(
        "{broken-json",
        encoding="utf-8",
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionConsumptionError,
        match="JSON is invalid",
    ):
        _consume(
            ticket,
            registry,
            now=now + timedelta(seconds=4),
        )


def test_consumption_record_digest_detects_tampering(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    record = _consume(
        ticket,
        tmp_path / "registry.json",
        now=now + timedelta(seconds=4),
    )

    tampered = replace(
        record,
        effective_target_path=(
            record.effective_target_path
            + ",OU=INVALID"
        ),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionConsumptionError,
        match="digest mismatch",
    ):
        m.assert_ad_deleted_object_restore_execution_consumption_invariants(
            tampered
        )


def test_service_is_dormant_and_has_no_ad_transport_or_write_primitive():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_execution_consumption.py"
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

    # R4B intentionally imports only the read-only lookup
    # into main.py. The mutating consumption primitive itself
    # must never be callable from an API route.
    assert (
        "service_get_ad_deleted_object_restore_execution_consumption"
        in main
    )

    assert (
        "consume_ad_deleted_object_restore_execution_ticket("
        not in main
    )

    assert (
        "/api/agent/deleted-object-restore/execution/result/"
        in main
    )

    assert "Restore-ADObject" not in source
    assert "subprocess" not in source
    assert "powershell" not in source.lower()

    # A5E3-R2D intentionally contains both the real handler
    # and its dedicated transport processor in the candidate module.
    # The Windows worker entrypoint must still remain unwired.
    assert (
        "function Invoke-EitasAdAdminDeletedObjectRestoreExecute {"
        in windows
    )

    assert (
        "function Process-EitasPendingDeletedObjectRestoreExecutions {"
        in windows
    )

    worker = Path(
        "agent-windows/Run-AdAdminWorker.ps1"
    ).read_text(
        encoding="utf-8"
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
def _concurrent_consume_worker(
    execution_ticket,
    registry_text,
    actor,
    now_text,
    ready_queue,
    start_event,
    result_queue,
):
    registry = Path(
        registry_text
    )

    current = datetime.fromisoformat(
        now_text
    )

    ready_queue.put(
        "ready"
    )

    if not start_event.wait(
        timeout=10
    ):
        result_queue.put(
            (
                "error",
                "start timeout",
            )
        )
        return

    try:
        record = (
            m.consume_ad_deleted_object_restore_execution_ticket(
                execution_ticket,
                consumption_registry_file=registry,
                server_actor=actor,
                current_mode="Simulation",
                now=current,
            )
        )

        result_queue.put(
            (
                "success",
                record.execution_consumption_id,
            )
        )
    except m.AdDeletedObjectRestoreExecutionConsumptionConflict as exc:
        result_queue.put(
            (
                "conflict",
                str(
                    exc
                ),
            )
        )
    except Exception as exc:
        result_queue.put(
            (
                "error",
                repr(
                    exc
                ),
            )
        )


def _run_two_concurrent_consumptions(
    first_ticket,
    second_ticket,
    registry,
    *,
    now,
):
    context = multiprocessing.get_context(
        "fork"
    )

    ready_queue = context.Queue()
    result_queue = context.Queue()
    start_event = context.Event()

    first_process = context.Process(
        target=_concurrent_consume_worker,
        args=(
            first_ticket,
            str(
                registry
            ),
            _actor(
                first_ticket
            ),
            now.isoformat(),
            ready_queue,
            start_event,
            result_queue,
        ),
    )

    second_process = context.Process(
        target=_concurrent_consume_worker,
        args=(
            second_ticket,
            str(
                registry
            ),
            _actor(
                second_ticket
            ),
            now.isoformat(),
            ready_queue,
            start_event,
            result_queue,
        ),
    )

    first_process.start()
    second_process.start()

    assert (
        ready_queue.get(
            timeout=10
        )
        == "ready"
    )

    assert (
        ready_queue.get(
            timeout=10
        )
        == "ready"
    )

    start_event.set()

    results = [
        result_queue.get(
            timeout=10
        ),
        result_queue.get(
            timeout=10
        ),
    ]

    first_process.join(
        timeout=10
    )

    second_process.join(
        timeout=10
    )

    if first_process.is_alive():
        first_process.terminate()
        first_process.join(
            timeout=5
        )

        raise AssertionError(
            "first concurrent consumer did not terminate"
        )

    if second_process.is_alive():
        second_process.terminate()
        second_process.join(
            timeout=5
        )

        raise AssertionError(
            "second concurrent consumer did not terminate"
        )

    assert first_process.exitcode == 0
    assert second_process.exitcode == 0

    return results


def _assert_single_valid_persisted_consumption(
    registry,
):
    persisted = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    validated = m._validate_registry(
        persisted
    )

    assert (
        validated["contract_version"]
        == "c9.5a5d-v1"
    )

    assert len(
        validated["records"]
    ) == 1

    leftovers = list(
        registry.parent.glob(
            ".*.tmp"
        )
    )

    assert leftovers == []

    return validated[
        "records"
    ][0]


def test_concurrent_same_ticket_allows_exactly_one_consumption(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    execution_ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = (
        tmp_path
        / "concurrent-same-ticket.json"
    )

    results = _run_two_concurrent_consumptions(
        execution_ticket,
        execution_ticket,
        registry,
        now=now + timedelta(
            seconds=5
        ),
    )

    statuses = sorted(
        item[0]
        for item in results
    )

    assert statuses == [
        "conflict",
        "success",
    ]

    conflicts = [
        value
        for status, value in results
        if status == "conflict"
    ]

    assert len(
        conflicts
    ) == 1

    assert (
        "already consumed"
        in conflicts[0]
    )

    persisted = (
        _assert_single_valid_persisted_consumption(
            registry
        )
    )

    assert (
        persisted["execution_ticket_id"]
        == execution_ticket.execution_ticket_id
    )

    assert (
        persisted["execution_ticket_digest"]
        == execution_ticket.execution_ticket_digest
    )

    assert (
        persisted["one_shot_consumption"]
        is True
    )

    assert (
        persisted["execution_ticket_consumed"]
        is True
    )


def test_concurrent_distinct_tickets_from_same_gate_allow_exactly_one(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    runtime_gate = helper._runtime_gate(
        monkeypatch,
        tmp_path,
        now,
    )

    actor = helper._actor(
        runtime_gate
    )

    confirmation = (
        ticket_module.expected_ad_deleted_object_restore_confirmation(
            runtime_gate
        )
    )

    first = (
        ticket_module.build_ad_deleted_object_restore_execution_ticket(
            runtime_gate,
            server_actor=actor,
            current_mode="Simulation",
            confirmation_text=confirmation,
            now=now + timedelta(
                seconds=3
            ),
        )
    )

    second = (
        ticket_module.build_ad_deleted_object_restore_execution_ticket(
            runtime_gate,
            server_actor=actor,
            current_mode="Simulation",
            confirmation_text=confirmation,
            now=now + timedelta(
                seconds=4
            ),
        )
    )

    assert (
        first.execution_ticket_id
        != second.execution_ticket_id
    )

    assert (
        first.execution_ticket_digest
        != second.execution_ticket_digest
    )

    assert (
        first.runtime_gate_id
        == second.runtime_gate_id
    )

    registry = (
        tmp_path
        / "concurrent-same-gate.json"
    )

    results = _run_two_concurrent_consumptions(
        first,
        second,
        registry,
        now=now + timedelta(
            seconds=6
        ),
    )

    statuses = sorted(
        item[0]
        for item in results
    )

    assert statuses == [
        "conflict",
        "success",
    ]

    conflicts = [
        value
        for status, value in results
        if status == "conflict"
    ]

    assert len(
        conflicts
    ) == 1

    assert (
        "runtime gate"
        in conflicts[0]
        or
        "authorization"
        in conflicts[0]
        or
        "preexecution"
        in conflicts[0]
    )

    persisted = (
        _assert_single_valid_persisted_consumption(
            registry
        )
    )

    assert (
        persisted["runtime_gate_id"]
        == runtime_gate.runtime_gate_id
    )

    assert (
        persisted["execution_ticket_id"]
        in {
            first.execution_ticket_id,
            second.execution_ticket_id,
        }
    )

    assert (
        persisted["one_shot_consumption"]
        is True
    )
