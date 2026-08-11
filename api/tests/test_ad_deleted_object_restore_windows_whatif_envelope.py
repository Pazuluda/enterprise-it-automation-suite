from __future__ import annotations

import importlib.util
import re

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.services.ad_deleted_object_restore_windows_whatif_envelope as m


HELPER_PATH = Path(__file__).with_name(
    "test_ad_deleted_object_restore_execution_ticket.py"
)

SPEC = importlib.util.spec_from_file_location(
    "c95_a5b_test_helpers",
    HELPER_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(
        "unable to load A5B test helpers"
    )

helper = importlib.util.module_from_spec(
    SPEC
)

SPEC.loader.exec_module(
    helper
)


SECRET = "not_a_secret_c95_whatif_fixture_00000000"


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


def _envelope(
    monkeypatch,
    tmp_path,
    now,
    *,
    ticket=None,
    secret=SECRET,
    mode="Simulation",
    envelope_now=None,
):
    source = (
        ticket
        if ticket is not None
        else _ticket(
            monkeypatch,
            tmp_path,
            now,
        )
    )

    return m.build_ad_deleted_object_restore_windows_whatif_envelope(
        source,
        signing_secret=secret,
        current_mode=mode,
        now=(
            envelope_now
            if envelope_now is not None
            else now + timedelta(seconds=4)
        ),
    )


def test_signed_whatif_envelope_is_strict_and_nonwriting(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    ticket = _ticket(
        monkeypatch,
        tmp_path,
        now,
    )

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
        ticket=ticket,
    )

    assert envelope.contract_version == "c9.5a5c-v1"
    assert envelope.operation == "restore_deleted_object_whatif"
    assert envelope.signature_algorithm == "hmac-sha256"

    assert envelope.execution_ticket_id == ticket.execution_ticket_id
    assert envelope.execution_ticket_digest == ticket.execution_ticket_digest
    assert envelope.object_guid == ticket.object_guid.lower()
    assert envelope.effective_new_name == ticket.effective_new_name
    assert envelope.effective_target_path == ticket.effective_target_path

    assert envelope.one_shot_required is True
    assert envelope.source_ticket_consumed is False

    assert envelope.runtime_authorized is False
    assert envelope.production_authorized is False
    assert envelope.execution_authorized is False
    assert envelope.write_performed is False

    assert envelope.restore_cmdlet_authorized is True
    assert envelope.restore_whatif_authorized is True

    assert len(envelope.signature) == 64

    m.assert_ad_deleted_object_restore_windows_whatif_envelope_invariants(
        envelope,
        signing_secret=SECRET,
    )


def test_wrong_signing_secret_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreWindowsWhatIfEnvelopeError,
        match="signature mismatch",
    ):
        m.assert_ad_deleted_object_restore_windows_whatif_envelope_invariants(
            envelope,
            signing_secret="different-unit-test-secret-value",
        )


def test_tampered_guid_breaks_signature(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    tampered = replace(
        envelope,
        object_guid="11111111-1111-4111-8111-111111111111",
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreWindowsWhatIfEnvelopeError,
        match="signature mismatch",
    ):
        m.assert_ad_deleted_object_restore_windows_whatif_envelope_invariants(
            tampered,
            signing_secret=SECRET,
        )


def test_production_global_mode_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    with pytest.raises(
        m.AdDeletedObjectRestoreWindowsWhatIfEnvelopeError,
        match="Simulation global mode",
    ):
        _envelope(
            monkeypatch,
            tmp_path,
            now,
            mode="Production",
        )


def test_expired_ticket_cannot_create_envelope(
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
        m.AdDeletedObjectRestoreWindowsWhatIfEnvelopeConflict,
        match="expired",
    ):
        _envelope(
            monkeypatch,
            tmp_path,
            now,
            ticket=ticket,
            envelope_now=expires,
        )


def test_whatif_envelope_ttl_is_at_most_15_seconds(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

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
    assert expires - issued <= timedelta(seconds=15)


def test_message_format_is_fixed_order_and_simple(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    message = (
        m.build_ad_deleted_object_restore_windows_whatif_message(
            envelope
        )
    )

    lines = message.splitlines()

    assert lines[0] == "contract_version=c9.5a5c-v1"
    assert lines[1].startswith("envelope_id=")
    assert lines[2] == "operation=restore_deleted_object_whatif"
    assert "one_shot_required=true" in lines
    assert "production_authorized=false" in lines
    assert "restore_whatif_authorized=true" in lines
    assert "execution_authorized=false" in lines
    assert "write_performed=false" in lines


def test_service_contains_no_secret_value_or_restore_primitive():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_windows_whatif_envelope.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "EITAS_API_KEY" not in source
    assert "dev-local-key-change-me" not in source
    assert re.search(
        r"(?mi)^\\s*Restore-ADObject(?:\\s|`)",
        source,
    ) is None
    assert "subprocess" not in source
    assert "powershell" not in source.lower()


def test_service_not_integrated_into_main_or_windows():
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
        "ad_deleted_object_restore_windows_whatif_envelope"
        not in main
    )

    assert (
        "function Invoke-EitasAdAdminDeletedObjectRestoreWhatIf {"
        in windows
    )

    marker = (
        "function Invoke-EitasAdAdminJob {"
    )

    start = windows.index(
        marker
    )

    end = windows.find(
        "\nfunction ",
        start + len(marker),
    )

    dispatcher = windows[
        start:
        end if end != -1 else None
    ]

    assert (
        "restore_deleted_object_whatif"
        not in dispatcher
    )

    assert (
        "Invoke-EitasAdAdminDeletedObjectRestoreWhatIf"
        not in dispatcher
    )


def test_wrong_capability_flag_is_rejected(
    monkeypatch,
    tmp_path,
):
    now = datetime.now(timezone.utc)

    envelope = _envelope(
        monkeypatch,
        tmp_path,
        now,
    )

    unsafe = replace(
        envelope,
        execution_authorized=True,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreWindowsWhatIfEnvelopeError,
        match="unsafe Windows WhatIf flag",
    ):
        m.assert_ad_deleted_object_restore_windows_whatif_envelope_invariants(
            unsafe
        )
