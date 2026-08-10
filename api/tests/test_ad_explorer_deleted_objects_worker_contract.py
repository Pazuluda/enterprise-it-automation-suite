from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

WORKER = (
    ROOT
    / "agent-windows"
    / "modules"
    / "EitasAdLookup.ps1"
)


def source() -> str:
    return WORKER.read_text(
        encoding="utf-8-sig"
    )


def deleted_objects_function(
    text: str,
) -> str:
    start = text.index(
        "function "
        "Invoke-EitasAdExplorerGetDeletedObjects"
    )

    end = text.index(
        "function Invoke-EitasAdExplorerJob",
        start,
    )

    return text[start:end]


def test_worker_exposes_deleted_objects_action():
    text = source()

    assert (
        '"get_deleted_objects" {'
        in text
    )

    assert (
        "Invoke-EitasAdExplorerGetDeletedObjects"
        in text
    )




def test_deleted_objects_accepts_worker_config_object():
    block = deleted_objects_function(
        source()
    )

    assert "[object]$Config" in block
    assert "[hashtable]$Config" not in block

def test_deleted_objects_reads_native_deleted_objects():
    block = deleted_objects_function(
        source()
    )

    for token in (
        "Get-ADRootDSE",
        "Get-ADOptionalFeature",
        "Recycle Bin Feature",
        "Get-ADObject",
        "(isDeleted=TRUE)",
        "-IncludeDeletedObjects",
        "CN=Deleted Objects,",
    ):
        assert token in block


def test_deleted_objects_reads_restore_metadata():
    block = deleted_objects_function(
        source()
    )

    for token in (
        "objectGUID",
        "objectClass",
        "isDeleted",
        "isRecycled",
        "lastKnownParent",
        "msDS-LastKnownRDN",
        "whenCreated",
        "whenChanged",
    ):
        assert token in block


def test_deleted_objects_reports_retention_state():
    block = deleted_objects_function(
        source()
    )

    for token in (
        "tombstoneLifetime",
        "msDS-DeletedObjectLifetime",
        "recycle_bin",
        "feature_found",
        "enabled_scope_count",
        "tombstone_lifetime_days",
        "deleted_object_lifetime_days",
    ):
        assert token in block


def test_deleted_objects_excludes_container_itself():
    block = deleted_objects_function(
        source()
    )

    assert (
        "$DeletedObjectsDn"
        in block
    )

    assert (
        "$_.DistinguishedName"
        in block
    )


def test_deleted_objects_has_bounded_limit():
    block = deleted_objects_function(
        source()
    )

    assert "$Limit = 200" in block
    assert "$Limit -lt 1" in block
    assert "$Limit -gt 1000" in block
    assert "Select-Object" in block
    assert "-First $Limit" in block


def test_deleted_objects_is_explicitly_read_only():
    block = deleted_objects_function(
        source()
    )

    assert (
        'action = "get_deleted_objects"'
        in block
    )

    assert "read_only = $true" in block

    assert (
        "restore_implemented = $false"
        in block
    )


def test_deleted_objects_reports_restore_capability_only():
    block = deleted_objects_function(
        source()
    )

    assert (
        "recycle_bin_disabled"
        in block
    )

    assert (
        "recycled_not_restorable"
        in block
    )

    assert (
        "restore_capability"
        in block
    )


def test_deleted_objects_contains_no_write_primitive():
    block = deleted_objects_function(
        source()
    )

    forbidden = (
        "Restore-ADObject",
        "Enable-ADOptionalFeature",
        "Set-AD",
        "New-AD",
        "Remove-AD",
        "Move-AD",
        "Rename-AD",
        "Set-Acl",
        "AddAccessRule",
        "SetAccessRule",
        "RemoveAccessRule",
    )

    for token in forbidden:
        assert token not in block


def test_c9_restore_runtime_still_absent():
    text = source()

    forbidden = (
        "Restore-ADObject",
        "Enable-ADOptionalFeature",
        '"restore_object"',
        '"restore_deleted_object"',
    )

    for token in forbidden:
        assert token not in text
