from pathlib import Path


SOURCE = Path(
    "agent-windows/modules/"
    "EitasAdLookup.ps1"
).read_text(
    encoding="utf-8-sig",
)


def test_live_revalidation_function_is_present():
    assert (
        "function "
        "Invoke-EitasAdExplorer"
        "RevalidateDeletedObjectPreflight"
        in SOURCE
    )


def test_live_revalidation_dispatch_is_present():
    assert (
        '"revalidate_deleted_object_preflight" {'
        in SOURCE
    )


def test_live_revalidation_uses_fresh_guid_lookup():
    assert (
        "Get-ADObject `"
        in SOURCE
    )

    assert (
        "-Identity $Guid `"
        in SOURCE
    )

    assert (
        "-IncludeDeletedObjects `"
        in SOURCE
    )

    assert (
        "Fresh object GUID mismatch"
        in SOURCE
    )


def test_live_revalidation_reads_rdn_attribute_from_schema():
    assert (
        "schemaNamingContext"
        in SOURCE
    )

    assert (
        "rDNAttID"
        in SOURCE
    )

    assert (
        "classSchema"
        in SOURCE
    )


def test_collision_lookup_is_one_level_and_escaped():
    assert (
        "function "
        "ConvertTo-EitasLdapFilterValue"
        in SOURCE
    )

    assert (
        "-SearchScope OneLevel `"
        in SOURCE
    )

    assert (
        "$CollisionFilter"
        in SOURCE
    )

    assert (
        "collision_probe_performed"
        in SOURCE
    )


def test_revalidation_is_strictly_non_authorizing():
    function_start = SOURCE.index(
        "function "
        "Invoke-EitasAdExplorer"
        "RevalidateDeletedObjectPreflight"
    )

    function_end = SOURCE.index(
        "function "
        "Invoke-EitasAdExplorerJob",
        function_start,
    )

    block = SOURCE[
        function_start:function_end
    ]

    assert (
        "read_only = $true"
        in block
    )

    assert (
        "restore_job_created = $false"
        in block
    )

    assert (
        "restore_implemented = $false"
        in block
    )

    assert (
        "execution_authorized = $false"
        in block
    )

    assert (
        "write_authorized = $false"
        in block
    )

    assert "Restore-ADObject" not in block

    assert (
        "Enable-ADOptionalFeature"
        not in block
    )
