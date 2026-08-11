from pathlib import Path

import app.services.ad_deleted_object_restore_windows_execution_envelope as envelope_module


MODULE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
)


def _source():
    return MODULE.read_text(
        encoding="utf-8"
    )


def _function_body(
    source: str,
    name: str,
) -> str:
    marker = f"function {name} {{"

    start = source.index(
        marker
    )

    end = source.find(
        "\nfunction ",
        start + len(marker),
    )

    return source[
        start:
        end if end != -1 else None
    ]


def test_execute_signature_helpers_exist():
    source = _source()

    for name in (
        "Get-EitasC95RestoreExecuteMessage",
        "Get-EitasC95RestoreExecuteHmacSha256",
        "Test-EitasC95RestoreExecuteSignature",
    ):
        assert (
            f"function {name} {{"
            in source
        )


def test_execute_hmac_domain_is_separate_from_whatif():
    source = _source()

    body = _function_body(
        source,
        "Get-EitasC95RestoreExecuteHmacSha256",
    )

    assert (
        "EITAS-C9.5-A5-WINDOWS-EXECUTE-V1"
        in body
    )

    assert (
        "EITAS-C9.5-A5-WINDOWS-WHATIF-V1"
        not in body
    )


def test_execution_message_field_order_matches_python_contract():
    source = _source()

    body = _function_body(
        source,
        "Get-EitasC95RestoreExecuteMessage",
    )

    expected = [
        "contract_version",
        "envelope_id",
        "operation",
        "execution_consumption_contract_version",
        "execution_consumption_id",
        "execution_consumption_record_digest",
        "execution_ticket_id",
        "execution_ticket_digest",
        "runtime_gate_id",
        "runtime_gate_digest",
        "authorization_consumption_id",
        "authorization_consumption_record_digest",
        "authorization_id",
        "authorization_digest",
        "preexecution_id",
        "preexecution_digest",
        "object_guid",
        "object_class",
        "class_policy",
        "effective_new_name",
        "effective_target_path",
        "actor_subject",
        "actor_username",
        "actor_issuer",
        "actor_azp",
        "confirmation_sha256",
        "issued_at",
        "expires_at",
        "source_consumption_verified",
        "source_one_shot_consumed",
        "human_authorized",
        "revalidation_passed",
        "runtime_authorized",
        "production_authorized",
        "controlled_restore_authorized",
        "restore_cmdlet_authorized",
        "execution_authorized",
        "write_performed",
    ]

    positions = [
        body.index(
            f'"{field}"'
        )
        for field in expected
    ]

    assert positions == sorted(
        positions
    )


def test_python_execution_domain_matches_windows_domain():
    source = _source()

    assert (
        envelope_module.AD_DELETED_OBJECT_RESTORE_WINDOWS_EXECUTION_KEY_CONTEXT
        == "EITAS-C9.5-A5-WINDOWS-EXECUTE-V1"
    )

    assert (
        "EITAS-C9.5-A5-WINDOWS-EXECUTE-V1"
        in source
    )



def test_execution_helpers_keep_expected_restore_boundary():
    source = _source()

    primitives = [
        line
        for line in source.splitlines()
        if line.lstrip().startswith(
            "Restore-ADObject"
        )
    ]

    # R2B intentionally adds one dormant real
    # restore primitive beside the historical
    # WhatIf primitive.
    assert len(
        primitives
    ) == 2

    whatif_body = _function_body(
        source,
        "Invoke-EitasAdAdminDeletedObjectRestoreWhatIf",
    )

    execute_body = _function_body(
        source,
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute",
    )

    assert "Restore-ADObject" in whatif_body
    assert "-WhatIf" in whatif_body

    assert "Restore-ADObject" in execute_body
    assert "-WhatIf" not in execute_body


def test_execute_handler_and_dedicated_transport_exist_with_explicit_worker_optin():
    source = _source()

    # R2B intentionally introduces the dormant
    # candidate-only real execution handler.
    assert (
        "function Invoke-EitasAdAdminDeletedObjectRestoreExecute {"
        in source
    )

    # R2D introduces the dedicated transport in the candidate
    # module, while Run-AdAdminWorker.ps1 remains unable to call it.
    assert (
        "function Process-EitasPendingDeletedObjectRestoreExecutions {"
        in source
    )

    assert (
        "function Get-EitasPendingDeletedObjectRestoreExecutions {"
        in source
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

    dispatcher = _function_body(
        source,
        "Invoke-EitasAdAdminJob",
    )

    assert (
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute"
        not in dispatcher
    )

    assert (
        "restore_deleted_object_execute"
        not in dispatcher
    )

def test_generic_dispatcher_remains_unconnected():
    source = _source()

    body = _function_body(
        source,
        "Invoke-EitasAdAdminJob",
    )

    assert "Restore-ADObject" not in body

    assert (
        "restore_deleted_object_execute"
        not in body
    )
