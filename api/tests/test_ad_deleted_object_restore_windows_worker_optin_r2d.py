from pathlib import Path


WORKER = Path(
    "agent-windows/Run-AdAdminWorker.ps1"
)

MODULE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
)


def test_restore_worker_wiring_requires_explicit_switch():
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


def test_restore_switch_is_not_enabled_by_default():
    worker = WORKER.read_text(
        encoding="utf-8"
    )

    assert (
        "$EnableDeletedObjectRestoreExecution = $true"
        not in worker
    )

    assert (
        "[switch]$EnableDeletedObjectRestoreExecution = $true"
        not in worker
    )


def test_worker_never_contains_restore_action_or_primitive():
    worker = WORKER.read_text(
        encoding="utf-8"
    )

    assert (
        "restore_deleted_object_execute"
        not in worker
    )

    assert "Restore-ADObject" not in worker


def test_dedicated_processor_remains_in_module():
    module = MODULE.read_text(
        encoding="utf-8"
    )

    assert (
        "function Process-EitasPendingDeletedObjectRestoreExecutions {"
        in module
    )


def test_generic_dispatcher_remains_unconnected():
    module = MODULE.read_text(
        encoding="utf-8"
    )

    start = module.index(
        "function Invoke-EitasAdAdminJob {"
    )

    end = module.index(
        "function Process-EitasPendingDeletedObjectRestoreExecutions {"
    )

    dispatcher = module[
        start:end
    ]

    assert (
        "restore_deleted_object_execute"
        not in dispatcher
    )

    assert "Restore-ADObject" not in dispatcher
