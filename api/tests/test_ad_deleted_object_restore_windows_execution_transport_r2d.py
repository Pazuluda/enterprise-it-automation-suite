from pathlib import Path


MODULE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
)

WORKER = Path(
    "agent-windows/Run-AdAdminWorker.ps1"
)


def _source() -> str:
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

    depth = 0
    opened = False

    for index in range(
        start,
        len(source),
    ):
        char = source[index]

        if char == "{":
            depth += 1
            opened = True

        elif char == "}":
            depth -= 1

            if (
                opened
                and depth == 0
            ):
                return source[
                    start:index + 1
                ]

    raise AssertionError(
        f"function body not closed: {name}"
    )


def test_r2d_dedicated_transport_helpers_exist():
    source = _source()

    for name in (
        "Get-EitasPendingDeletedObjectRestoreExecutions",
        "Claim-EitasDeletedObjectRestoreExecution",
        "Send-EitasDeletedObjectRestoreExecutionResult",
        "Assert-EitasDeletedObjectRestoreExecutionTransportAuthorization",
        "Process-EitasPendingDeletedObjectRestoreExecutions",
    ):
        assert (
            f"function {name} {{"
            in source
        )


def test_r2d_transport_paths_are_exact():
    source = _source()

    get_body = _function_body(
        source,
        "Get-EitasPendingDeletedObjectRestoreExecutions",
    )

    claim_body = _function_body(
        source,
        "Claim-EitasDeletedObjectRestoreExecution",
    )

    result_body = _function_body(
        source,
        "Send-EitasDeletedObjectRestoreExecutionResult",
    )

    assert (
        "/api/agent/deleted-object-restore/"
        in get_body
    )
    assert "execution/pending" in get_body

    assert (
        "/api/agent/deleted-object-restore/"
        in claim_body
    )
    assert "execution/claim/" in claim_body

    assert (
        "/api/agent/deleted-object-restore/"
        in result_body
    )
    assert "execution/result/" in result_body


def test_r2d_processor_enforces_transport_contracts():
    body = _function_body(
        _source(),
        "Process-EitasPendingDeletedObjectRestoreExecutions",
    )

    assert '"Simulation"' in body
    assert '"c9.5a5e2-v1"' in body
    assert '"restore_execution_pending"' in body
    assert '"c9.5a5e2-claim-v1"' in body
    assert '"restore_execution_processing"' in body
    assert '"c9.5a5e3-v1"' in body
    assert '"restore_deleted_object_execute"' in body


def test_r2d_processor_revalidates_binding_fields():
    body = _function_body(
        _source(),
        "Process-EitasPendingDeletedObjectRestoreExecutions",
    )

    for field in (
        "transport_ticket_id",
        "transport_execution_id",
        "envelope_id",
        "execution_consumption_id",
        "execution_ticket_id",
        "payload_digest",
    ):
        assert field in body


def test_r2d_authorization_remains_fail_closed():
    body = _function_body(
        _source(),
        "Assert-EitasDeletedObjectRestoreExecutionTransportAuthorization",
    )

    assert (
        "controlled_restore_runtime_authorized"
        in body
    )
    assert "production_authorized" in body
    assert "write_performed" in body

    assert (
        "$ProductionAuthorized -ne $false"
        in body
    )
    assert (
        "$WritePerformed -ne $false"
        in body
    )


def test_r2d_only_dedicated_processor_reaches_real_handler():
    source = _source()

    processor = _function_body(
        source,
        "Process-EitasPendingDeletedObjectRestoreExecutions",
    )

    dispatcher = _function_body(
        source,
        "Invoke-EitasAdAdminJob",
    )

    assert (
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute"
        in processor
    )

    assert (
        "restore_deleted_object_execute"
        not in dispatcher
    )

    assert (
        "Restore-ADObject"
        not in dispatcher
    )


def test_r2d_processor_has_no_restore_primitive_itself():
    processor = _function_body(
        _source(),
        "Process-EitasPendingDeletedObjectRestoreExecutions",
    )

    assert "Restore-ADObject" not in processor


def test_r2d_worker_requires_explicit_restore_optin():
    worker = WORKER.read_text(
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
