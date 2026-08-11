from pathlib import Path


MODULE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
)


def _source():
    return MODULE.read_text(
        encoding="utf-8"
    )


def _body(
    source,
    name,
):
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


def test_real_execute_handler_exists_but_is_not_generic_dispatch():
    source = _source()

    assert (
        "function Invoke-EitasAdAdminDeletedObjectRestoreExecute {"
        in source
    )

    dispatcher = _body(
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


def test_exactly_two_restore_primitives_exist():
    source = _source()

    primitives = [
        line
        for line in source.splitlines()
        if line.lstrip().startswith(
            "Restore-ADObject"
        )
    ]

    assert len(
        primitives
    ) == 2


def test_whatif_and_real_restore_are_isolated_in_separate_handlers():
    source = _source()

    whatif = _body(
        source,
        "Invoke-EitasAdAdminDeletedObjectRestoreWhatIf",
    )

    execute = _body(
        source,
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute",
    )

    assert "Restore-ADObject" in whatif
    assert "-WhatIf" in whatif

    assert "Restore-ADObject" in execute
    assert "-WhatIf" not in execute
    assert "-Confirm:$false" in execute


def test_execute_requires_simulation_and_execute_contract():
    execute = _body(
        _source(),
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute",
    )

    assert (
        '$Mode -ine "Simulation"'
        in execute
    )

    assert (
        '"c9.5a5e-v1"'
        in execute
    )

    assert (
        '"restore_deleted_object_execute"'
        in execute
    )

    assert (
        '"c9.5a5d-v1"'
        in execute
    )


def test_signature_is_checked_before_any_ad_lookup():
    execute = _body(
        _source(),
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute",
    )

    signature = execute.index(
        "Test-EitasC95RestoreExecuteSignature"
    )

    import_ad = execute.index(
        "Import-EitasActiveDirectoryModule"
    )

    fresh_lookup = execute.index(
        "$Fresh = Get-ADObject"
    )

    restore = execute.index(
        "Restore-ADObject"
    )

    assert signature < import_ad
    assert signature < fresh_lookup
    assert fresh_lookup < restore


def test_execute_enforces_short_ttl_and_narrow_capabilities():
    execute = _body(
        _source(),
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute",
    )

    assert "TTL exceeds 10 seconds" in execute

    for field in (
        "source_consumption_verified",
        "source_one_shot_consumed",
        "human_authorized",
        "revalidation_passed",
        "controlled_restore_authorized",
        "restore_cmdlet_authorized",
        "execution_authorized",
    ):
        assert (
            f'"{field}"'
            in execute
        )

    for field in (
        "runtime_authorized",
        "production_authorized",
        "write_performed",
    ):
        assert (
            f'"{field}"'
            in execute
        )


def test_restore_occurs_only_after_fresh_object_target_and_collision_checks():
    execute = _body(
        _source(),
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute",
    )

    fresh = execute.index(
        "$Fresh = Get-ADObject"
    )

    target = execute.index(
        "$TargetParent = Get-ADObject"
    )

    collision = execute.index(
        "$CollisionMatches = @("
    )

    restore = execute.index(
        "Restore-ADObject"
    )

    assert fresh < target
    assert target < collision
    assert collision < restore


def test_post_restore_verification_occurs_after_write():
    execute = _body(
        _source(),
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute",
    )

    restore = execute.index(
        "Restore-ADObject"
    )

    write_marker = execute.index(
        "$WritePerformed = $true"
    )

    post_object = execute.index(
        "$PostObject = Get-ADObject"
    )

    post_target = execute.index(
        "$PostTargetMatches = @("
    )

    assert restore < write_marker
    assert write_marker < post_object
    assert post_object < post_target


def test_success_result_matches_server_required_security_markers():
    execute = _body(
        _source(),
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute",
    )

    for field in (
        "signature_verified",
        "fresh_deleted_object_verified",
        "fresh_target_verified",
        "target_collision",
        "controlled_restore_runtime_authorized",
        "restore_performed",
        "write_performed",
        "post_restore_object_guid_verified",
        "post_restore_target_present",
        "post_restore_deleted_object_absent",
        "production_authorized",
    ):
        assert (
            field
            in execute
        )


def test_failure_path_preserves_write_marker():
    execute = _body(
        _source(),
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute",
    )

    assert (
        "catch {"
        in execute
    )

    assert (
        "restore_performed = $RestorePerformed"
        in execute
    )

    assert (
        "write_performed = $WritePerformed"
        in execute
    )


def test_dedicated_restore_transport_exists_but_worker_is_not_connected():
    source = _source()

    assert (
        "function Process-EitasPendingDeletedObjectRestoreExecutions {"
        in source
    )

    assert (
        "function Get-EitasPendingDeletedObjectRestoreExecutions {"
        in source
    )


def test_restore_transport_in_worker_requires_explicit_optin():
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
