from __future__ import annotations

import importlib.util

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.services.ad_deleted_object_restore_windows_execution_envelope as m


HELPER_PATH = Path(__file__).with_name(
    "test_ad_deleted_object_restore_execution_consumption.py"
)

SPEC = importlib.util.spec_from_file_location(
    "c95_a5d_helpers",
    HELPER_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "unable to load A5D helpers"
    )

helper = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    helper
)


SECRET = "not_a_secret_c95_execute_fixture_0000000"


def _source(
    monkeypatch,
    tmp_path,
    now,
):
    execution_ticket = helper._ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    return helper._consume(
        execution_ticket,
        tmp_path / "source-consumption.json",
        now=now + timedelta(seconds=4),
    )


def _actor(
    source,
):
    return {
        "subject": source.actor_subject,
        "username": source.actor_username,
        "issuer": source.actor_issuer,
        "azp": source.actor_azp,
    }


def _envelope(
    monkeypatch,
    tmp_path,
    now,
    *,
    source=None,
    actor=None,
    secret=SECRET,
    mode="Simulation",
    confirmation=None,
    envelope_now=None,
):
    resolved = (
        source
        if source is not None
        else _source(
            monkeypatch,
            tmp_path,
            now,
        )
    )

    expected = (
        m.expected_ad_deleted_object_restore_execution_confirmation(
            resolved
        )
    )

    return (
        m.build_ad_deleted_object_restore_windows_execution_envelope(
            resolved,
            server_actor=(
                actor
                if actor is not None
                else _actor(
                    resolved
                )
            ),
            signing_secret=secret,
            current_mode=mode,
            confirmation_text=(
                expected
                if confirmation is None
                else confirmation
            ),
            now=(
                envelope_now
                if envelope_now is not None
                else now + timedelta(seconds=5)
            ),
        )
    )


def test_valid_execution_envelope_is_signed_and_narrow(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    source = _source(
        monkeypatch,
        tmp_path,
        now,
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
        source=source,
    )

    assert envelope.contract_version == "c9.5a5e-v1"

    assert (
        envelope.operation
        == "restore_deleted_object_execute"
    )

    assert envelope.signature_algorithm == "hmac-sha256"

    assert (
        envelope.execution_consumption_id
        == source.execution_consumption_id
    )

    assert (
        envelope.execution_consumption_record_digest
        == source.record_digest
    )

    assert envelope.execution_ticket_id == source.execution_ticket_id
    assert envelope.object_guid == source.object_guid.lower()
    assert envelope.effective_new_name == source.effective_new_name
    assert envelope.effective_target_path == source.effective_target_path

    assert envelope.source_consumption_verified is True
    assert envelope.source_one_shot_consumed is True
    assert envelope.human_authorized is True
    assert envelope.revalidation_passed is True

    assert envelope.route_enabled is False
    assert envelope.agent_endpoint_enabled is False
    assert envelope.generic_job_enabled is False
    assert envelope.claim_enabled is False

    assert envelope.runtime_authorized is False
    assert envelope.production_authorized is False

    assert envelope.controlled_restore_authorized is True
    assert envelope.restore_cmdlet_authorized is True
    assert envelope.execution_authorized is True

    assert envelope.write_performed is False

    assert len(
        envelope.signature
    ) == 64

    m.assert_ad_deleted_object_restore_windows_execution_envelope_invariants(
        envelope,
        signing_secret=SECRET,
    )


def test_wrong_signing_secret_is_rejected(
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
        m.AdDeletedObjectRestoreWindowsExecutionEnvelopeError,
        match="signature mismatch",
    ):
        m.assert_ad_deleted_object_restore_windows_execution_envelope_invariants(
            envelope,
            signing_secret="different-unit-test-secret-value",
        )


def test_tampered_target_breaks_signature(
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
        effective_target_path=(
            envelope.effective_target_path
            + ",OU=INVALID"
        ),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreWindowsExecutionEnvelopeError,
        match="signature mismatch",
    ):
        m.assert_ad_deleted_object_restore_windows_execution_envelope_invariants(
            tampered,
            signing_secret=SECRET,
        )


def test_actor_mismatch_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    source = _source(
        monkeypatch,
        tmp_path,
        now,
    )

    actor = _actor(
        source
    )

    actor["subject"] = "different-subject"

    with pytest.raises(
        m.AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict,
        match="actor mismatch",
    ):
        _envelope(
            monkeypatch,
            tmp_path,
            now,
            source=source,
            actor=actor,
        )


def test_wrong_confirmation_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict,
        match="confirmation mismatch",
    ):
        _envelope(
            monkeypatch,
            tmp_path,
            now,
            confirmation="RESTORE SOMETHING ELSE",
        )


def test_production_global_mode_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreWindowsExecutionEnvelopeError,
        match="Simulation global mode",
    ):
        _envelope(
            monkeypatch,
            tmp_path,
            now,
            mode="Production",
        )


def test_expired_source_ticket_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    source = _source(
        monkeypatch,
        tmp_path,
        now,
    )

    expires = datetime.fromisoformat(
        source.execution_ticket_expires_at.replace(
            "Z",
            "+00:00",
        )
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreWindowsExecutionEnvelopeConflict,
        match="expired",
    ):
        _envelope(
            monkeypatch,
            tmp_path,
            now,
            source=source,
            envelope_now=expires,
        )


def test_execution_envelope_ttl_is_at_most_10_seconds(
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

    issued = datetime.fromisoformat(
        envelope.issued_at.replace(
            "Z",
            "+00:00",
        )
    )

    expires = datetime.fromisoformat(
        envelope.expires_at.replace(
            "Z",
            "+00:00",
        )
    )

    assert expires > issued

    assert (
        expires - issued
        <= timedelta(seconds=10)
    )


def test_message_has_fixed_order_and_separate_execution_domain(
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

    message = (
        m.build_ad_deleted_object_restore_windows_execution_message(
            envelope
        )
    )

    lines = message.splitlines()

    assert lines[0] == "contract_version=c9.5a5e-v1"
    assert lines[1].startswith("envelope_id=")

    assert (
        lines[2]
        == "operation=restore_deleted_object_execute"
    )

    assert (
        "source_one_shot_consumed=true"
        in lines
    )

    assert (
        "production_authorized=false"
        in lines
    )

    assert (
        "controlled_restore_authorized=true"
        in lines
    )

    assert (
        "execution_authorized=true"
        in lines
    )

    assert (
        "write_performed=false"
        in lines
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_KEY_CONTEXT
        == "EITAS-C9.5-A5-WINDOWS-EXECUTE-V1"
    )


def test_execution_envelope_is_still_completely_dormant():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_windows_execution_envelope.py"
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

    assert "EITAS_API_KEY" not in source
    assert "dev-local-key-change-me" not in source

    assert "Restore-ADObject" not in source
    assert "subprocess" not in source
    assert "powershell" not in source.lower()

    # R4B intentionally binds envelope creation to the
    # authenticated human queue route. Windows execution is
    # still disconnected at this stage.
    assert (
        "service_build_ad_deleted_object_restore_windows_execution_envelope"
        in main
    )

    assert (
        "/api/agent/deleted-object-restore/execution/result/"
        in main
    )

    assert (
        "restore_deleted_object_execute"
        not in main
    )

    # A5E3-R2D intentionally contains the real execution
    # handler and the dedicated processor in the candidate module.
    # The worker entrypoint must still remain unwired.
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
