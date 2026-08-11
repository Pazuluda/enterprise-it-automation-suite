from __future__ import annotations

import importlib.util
import json
import multiprocessing

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.services.ad_deleted_object_restore_execution_transport as m
import app.services.ad_deleted_object_restore_windows_execution_envelope as envelope_module


HELPER_PATH = Path(__file__).with_name(
    "test_ad_deleted_object_restore_windows_execution_envelope.py"
)

SPEC = importlib.util.spec_from_file_location(
    "c95_a5e_envelope_helpers",
    HELPER_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "unable to load A5E envelope helpers"
    )

helper = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    helper
)


SECRET = helper.SECRET


def _envelope(
    monkeypatch,
    tmp_path,
    now,
    *,
    source=None,
    envelope_now=None,
):
    return helper._envelope(
        monkeypatch,
        tmp_path,
        now,
        source=source,
        envelope_now=(
            envelope_now
            if envelope_now is not None
            else now + timedelta(seconds=5)
        ),
    )


def _queue(
    envelope,
    registry,
    *,
    now,
    mode="Simulation",
):
    return m.queue_ad_deleted_object_restore_execution(
        envelope,
        transport_registry_file=registry,
        signing_secret=SECRET,
        current_mode=mode,
        now=now,
    )


def test_valid_signed_envelope_is_queued_without_runtime_authorization(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = (
        tmp_path
        / "transport.json"
    )

    ticket = _queue(
        envelope,
        registry,
        now=now + timedelta(seconds=6),
    )

    assert ticket.contract_version == "c9.5a5e2-v1"
    assert ticket.state == "restore_execution_pending"

    assert ticket.envelope_id == envelope.envelope_id

    assert (
        ticket.execution_consumption_id
        == envelope.execution_consumption_id
    )

    assert ticket.execution_ticket_id == envelope.execution_ticket_id
    assert ticket.object_guid == envelope.object_guid.lower()

    assert ticket.controlled_restore_runtime_authorized is False
    assert ticket.production_authorized is False
    assert ticket.write_performed is False

    persisted = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    assert len(
        persisted["records"]
    ) == 1

    assert (
        persisted["records"][0]["payload_digest"]
        == ticket.payload_digest
    )


def test_same_envelope_cannot_be_queued_twice(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = tmp_path / "transport.json"

    _queue(
        envelope,
        registry,
        now=now + timedelta(seconds=6),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportConflict,
        match="already queued",
    ):
        _queue(
            envelope,
            registry,
            now=now + timedelta(seconds=7),
        )


def test_second_envelope_from_same_consumption_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    source = helper._source(
        monkeypatch,
        tmp_path,
        now,
    )

    first = _envelope(
        monkeypatch,
        tmp_path,
        now,
        source=source,
        envelope_now=now + timedelta(seconds=5),
    )

    second = _envelope(
        monkeypatch,
        tmp_path,
        now,
        source=source,
        envelope_now=now + timedelta(seconds=6),
    )

    assert first.envelope_id != second.envelope_id

    registry = tmp_path / "transport.json"

    _queue(
        first,
        registry,
        now=now + timedelta(seconds=6),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportConflict,
        match="execution consumption id already queued",
    ):
        _queue(
            second,
            registry,
            now=now + timedelta(seconds=7),
        )


def test_pending_list_exposes_metadata_but_not_signed_payload(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = tmp_path / "transport.json"

    _queue(
        envelope,
        registry,
        now=now + timedelta(seconds=6),
    )

    pending = (
        m.list_pending_ad_deleted_object_restore_executions(
            transport_registry_file=registry,
            now=now + timedelta(seconds=7),
        )
    )

    assert pending["count"] == 1

    ticket = pending["tickets"][0]

    assert "payload" not in ticket
    assert "signature" not in ticket

    assert ticket["state"] == "restore_execution_pending"
    assert ticket["controlled_restore_runtime_authorized"] is False
    assert ticket["production_authorized"] is False
    assert ticket["write_performed"] is False


def test_valid_agent_claim_is_atomic_and_returns_signed_payload(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = tmp_path / "transport.json"

    ticket = _queue(
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

    assert claim.contract_version == "c9.5a5e2-claim-v1"
    assert claim.state == "restore_execution_processing"

    assert claim.transport_ticket_id == ticket.transport_ticket_id
    assert claim.envelope_id == envelope.envelope_id

    assert claim.payload["signature"] == envelope.signature

    assert claim.controlled_restore_runtime_authorized is True
    assert claim.production_authorized is False
    assert claim.write_performed is False

    persisted = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    record = persisted["records"][0]

    assert record["state"] == "restore_execution_processing"
    assert record["claimed_by"] == "SRV-DC01"
    assert record["controlled_restore_runtime_authorized"] is True
    assert record["production_authorized"] is False
    assert record["write_performed"] is False


def test_second_claim_of_same_transport_ticket_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = tmp_path / "transport.json"

    ticket = _queue(
        envelope,
        registry,
        now=now + timedelta(seconds=6),
    )

    m.claim_ad_deleted_object_restore_execution_for_agent(
        transport_registry_file=registry,
        transport_ticket_id=ticket.transport_ticket_id,
        agent_name="SRV-DC01",
        signing_secret=SECRET,
        current_mode="Simulation",
        now=now + timedelta(seconds=7),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportConflict,
        match="not pending",
    ):
        m.claim_ad_deleted_object_restore_execution_for_agent(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            agent_name="SRV-DC01",
            signing_secret=SECRET,
            current_mode="Simulation",
            now=now + timedelta(seconds=8),
        )


def _concurrent_claim_worker(
    registry_text,
    ticket_id,
    now_text,
    start_event,
    result_queue,
):
    try:
        start_event.wait(
            timeout=10
        )

        claim = (
            m.claim_ad_deleted_object_restore_execution_for_agent(
                transport_registry_file=Path(
                    registry_text
                ),
                transport_ticket_id=ticket_id,
                agent_name="SRV-DC01",
                signing_secret=SECRET,
                current_mode="Simulation",
                now=datetime.fromisoformat(
                    now_text
                ),
            )
        )

        result_queue.put(
            (
                "success",
                claim.transport_execution_id,
            )
        )
    except m.AdDeletedObjectRestoreExecutionTransportConflict as exc:
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


def test_two_concurrent_claims_allow_exactly_one_winner(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = tmp_path / "transport.json"

    ticket = _queue(
        envelope,
        registry,
        now=now + timedelta(seconds=6),
    )

    context = multiprocessing.get_context(
        "fork"
    )

    start_event = context.Event()
    result_queue = context.Queue()

    claim_now = (
        now + timedelta(seconds=7)
    ).isoformat()

    processes = [
        context.Process(
            target=_concurrent_claim_worker,
            args=(
                str(
                    registry
                ),
                ticket.transport_ticket_id,
                claim_now,
                start_event,
                result_queue,
            ),
        )
        for _ in range(
            2
        )
    ]

    for process in processes:
        process.start()

    start_event.set()

    results = [
        result_queue.get(
            timeout=10
        ),
        result_queue.get(
            timeout=10
        ),
    ]

    for process in processes:
        process.join(
            timeout=10
        )

        if process.is_alive():
            process.terminate()
            process.join(
                timeout=5
            )

            raise AssertionError(
                "concurrent claim worker did not terminate"
            )

        assert process.exitcode == 0

    statuses = sorted(
        item[0]
        for item in results
    )

    assert statuses == [
        "conflict",
        "success",
    ]

    persisted = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    validated = m._validate_registry(
        persisted
    )

    assert len(
        validated["records"]
    ) == 1

    record = validated["records"][0]

    assert record["state"] == "restore_execution_processing"
    assert record["controlled_restore_runtime_authorized"] is True
    assert record["production_authorized"] is False
    assert record["write_performed"] is False


def test_expired_transport_ticket_cannot_be_claimed(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = tmp_path / "transport.json"

    ticket = _queue(
        envelope,
        registry,
        now=now + timedelta(seconds=6),
    )

    expires = datetime.fromisoformat(
        ticket.expires_at.replace(
            "Z",
            "+00:00",
        )
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportConflict,
        match="expired",
    ):
        m.claim_ad_deleted_object_restore_execution_for_agent(
            transport_registry_file=registry,
            transport_ticket_id=ticket.transport_ticket_id,
            agent_name="SRV-DC01",
            signing_secret=SECRET,
            current_mode="Simulation",
            now=expires,
        )


def test_global_production_mode_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportError,
        match="Simulation global mode",
    ):
        _queue(
            envelope,
            tmp_path / "transport.json",
            now=now + timedelta(seconds=6),
            mode="Production",
        )


def test_tampered_signed_envelope_is_rejected_before_queue(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    tampered = replace(
        envelope,
        effective_new_name=(
            envelope.effective_new_name
            + "-tampered"
        ),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportError,
        match="signature mismatch",
    ):
        _queue(
            tampered,
            tmp_path / "transport.json",
            now=now + timedelta(seconds=6),
        )


def test_symlink_transport_registry_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    target = tmp_path / "target.json"

    target.write_text(
        json.dumps(
            {
                "contract_version": "c9.5a5e2-v1",
                "records": [],
            }
        ),
        encoding="utf-8",
    )

    registry = tmp_path / "transport.json"

    registry.symlink_to(
        target
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportError,
        match="symlink",
    ):
        _queue(
            envelope,
            registry,
            now=now + timedelta(seconds=6),
        )


def test_corrupt_transport_registry_fails_closed(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    registry = tmp_path / "transport.json"

    registry.write_text(
        "{broken-json",
        encoding="utf-8",
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreExecutionTransportError,
        match="JSON is invalid",
    ):
        _queue(
            envelope,
            registry,
            now=now + timedelta(seconds=6),
        )


def test_transport_remains_completely_disconnected_and_write_free():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_execution_transport.py"
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
    assert "subprocess" not in source
    assert "powershell" not in source.lower()

    # R4B intentionally connects only queue, pending and
    # atomic claim. Completion and Windows execution remain
    # disconnected until the later A5E stages.
    assert (
        "service_queue_ad_deleted_object_restore_execution"
        in main
    )

    assert (
        '"/api/ad-admin/deleted-object-restore/execution/queue"'
        in main
    )

    assert (
        '"/api/agent/deleted-object-restore/execution/pending"'
        in main
    )

    assert (
        '"/api/agent/deleted-object-restore/execution/claim/"'
        in main
    )

    assert (
        "/api/agent/deleted-object-restore/execution/result/"
        in main
    )

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
