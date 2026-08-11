from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

SOURCE = (
    ROOT
    / "agent-windows"
    / "modules"
    / "EitasAdAdmin.ps1"
).read_text(
    encoding="utf-8"
)


def function_body(
    name: str,
) -> str:
    marker = (
        f"function {name} {{"
    )

    start = SOURCE.index(
        marker
    )

    end = SOURCE.find(
        "\nfunction ",
        start + len(marker),
    )

    if end == -1:
        return SOURCE[start:]

    return SOURCE[
        start:end
    ]


HANDLER_NAME = (
    "Invoke-EitasAdAdmin"
    "DeletedObjectRestoreWhatIf"
)


def test_a5c_whatif_handler_exists_but_is_not_dispatched():
    handler = function_body(
        HANDLER_NAME
    )

    dispatcher = function_body(
        "Invoke-EitasAdAdminJob"
    )

    assert (
        "restore_deleted_object_whatif"
        in handler
    )

    assert (
        HANDLER_NAME
        not in dispatcher
    )

    assert (
        "restore_deleted_object_whatif"
        not in dispatcher
    )


def test_a5c_requires_simulation_and_exact_contracts():
    handler = function_body(
        HANDLER_NAME
    )

    for expected in (
        '$Mode -ine "Simulation"',
        '"c9.5a5c-v1"',
        '"c9.5a5b-v1"',
        '"restore_deleted_object_whatif"',
        '"hmac-sha256"',
        '"EITAS-C9.5-A5-WINDOWS-WHATIF-V1"',
    ):
        assert expected in handler


def test_a5c_hmac_derives_separate_key_from_api_key():
    helper = function_body(
        "Get-EitasC95RestoreWhatIfHmacSha256"
    )

    signature = function_body(
        "Test-EitasC95RestoreWhatIfSignature"
    )

    assert (
        "System.Security.Cryptography.HMACSHA256"
        in helper
    )

    assert (
        "EITAS-C9.5-A5-WINDOWS-WHATIF-V1"
        in helper
    )

    assert (
        "Get-EitasApiKey"
        in signature
    )

    assert (
        "Test-EitasC95RestoreWhatIfFixedTimeHex"
        in signature
    )


def test_a5c_signature_is_verified_before_any_ad_read():
    handler = function_body(
        HANDLER_NAME
    )

    signature = handler.index(
        "Test-EitasC95RestoreWhatIfSignature"
    )

    ad_import = handler.index(
        "Import-EitasActiveDirectoryModule"
    )

    fresh_lookup = handler.index(
        "Get-ADObject `"
    )

    assert signature < ad_import
    assert signature < fresh_lookup


def test_a5c_requires_short_ttl_and_unconsumed_one_shot():
    handler = function_body(
        HANDLER_NAME
    )

    for expected in (
        "one_shot_required",
        "source_ticket_consumed",
        "TTL exceeds 15 seconds",
        "envelope expired",
    ):
        assert expected in handler


def test_a5c_global_runtime_and_production_remain_false():
    handler = function_body(
        HANDLER_NAME
    )

    for expected in (
        "route_enabled",
        "agent_endpoint_enabled",
        "job_creation_authorized",
        "claim_authorized",
        "runtime_authorized",
        "production_authorized",
        "execution_authorized",
        "write_performed",
    ):
        assert expected in handler

    assert (
        "C9.5 unsafe WhatIf flag"
        in handler
    )


def test_a5c_revalidates_deleted_object_by_exact_guid():
    handler = function_body(
        HANDLER_NAME
    )

    for expected in (
        "[Guid]::TryParse",
        "-Identity $ObjectGuid `",
        "-IncludeDeletedObjects `",
        "$FreshGuid -ne $ObjectGuid",
        "$Fresh.isDeleted -ne $true",
        "$Fresh.isRecycled -eq $true",
    ):
        assert expected in handler


def test_a5c_revalidates_safe_target_and_collision():
    handler = function_body(
        HANDLER_NAME
    )

    for expected in (
        "Assert-EitasDnSafe",
        "Recycle Bin Feature",
        "schemaNamingContext",
        "rDNAttID",
        "ConvertTo-EitasAdAdminLdapFilterValue",
        "-SearchScope OneLevel `",
        "target collision detected",
    ):
        assert expected in handler


def test_a5c_restore_primitive_is_whatif_only():
    handler = function_body(
        HANDLER_NAME
    )

    assert (
        "Restore-ADObject `"
        in handler
    )

    restore = handler.index(
        "Restore-ADObject `"
    )

    whatif = handler.index(
        "-WhatIf `",
        restore,
    )

    confirm = handler.index(
        "-Confirm:$false `",
        whatif,
    )

    assert restore < whatif < confirm

    assert (
        "restore_performed = $false"
        in handler
    )

    assert (
        "write_performed = $false"
        in handler
    )



def test_a5c_whatif_primitive_remains_isolated_with_a5e_execute_candidate():
    needle = "Restore-ADObject `"

    occurrences = []

    offset = 0

    while True:
        index = SOURCE.find(
            needle,
            offset,
        )

        if index == -1:
            break

        occurrences.append(
            index
        )

        offset = index + len(
            needle
        )

    # A5C retains its isolated WhatIf primitive.
    # A5E3-R2B intentionally adds one second,
    # dormant real-execution primitive.
    assert len(
        occurrences
    ) == 2

    def function_body(
        name,
    ):
        marker = (
            "function "
            + name
            + " {"
        )

        start = SOURCE.index(
            marker
        )

        end = SOURCE.find(
            "\nfunction ",
            start + len(
                marker
            ),
        )

        return SOURCE[
            start:
            end if end != -1 else None
        ]

    whatif = function_body(
        "Invoke-EitasAdAdminDeletedObjectRestoreWhatIf"
    )

    execute = function_body(
        "Invoke-EitasAdAdminDeletedObjectRestoreExecute"
    )

    dispatcher = function_body(
        "Invoke-EitasAdAdminJob"
    )

    assert needle in whatif
    assert "-WhatIf" in whatif

    assert needle in execute
    assert "-WhatIf" not in execute
    assert "-Confirm:$false" in execute

    assert needle not in dispatcher

    assert (
        "restore_deleted_object_execute"
        not in dispatcher
    )

    assert (
        "function Process-EitasPendingDeletedObjectRestoreExecutions {"
        in SOURCE
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
