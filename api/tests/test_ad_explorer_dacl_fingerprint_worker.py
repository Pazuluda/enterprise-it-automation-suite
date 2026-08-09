from pathlib import Path


MODULE = Path(
    "agent-windows/modules/EitasAdLookup.ps1"
)


def security_descriptor_function() -> str:
    source = MODULE.read_text(
        encoding="utf-8"
    )

    start = source.index(
        "function "
        "Invoke-EitasAdExplorerGetSecurityDescriptor"
    )

    end = source.index(
        "function Invoke-EitasAdExplorerJob",
        start,
    )

    return source[start:end]


def test_c8_4b_worker_reads_only_dacl_sddl():
    function = security_descriptor_function()

    assert (
        "GetSecurityDescriptorSddlForm"
        in function
    )

    assert (
        "AccessControlSections]::Access"
        in function
    )

    assert (
        "AccessControlSections]::Audit"
        not in function
    )

    assert (
        'sacl_included = $false'
        in function
    )


def test_c8_4b_worker_hashes_native_dacl():
    function = security_descriptor_function()

    assert (
        "SHA256]::Create"
        in function
    )

    assert (
        "UTF8.GetBytes"
        in function
    )

    assert (
        'dacl_fingerprint_version = ('
        in function
    )

    assert (
        '"sddl-access-sha256-v1"'
        in function
    )

    assert (
        "dacl_sddl_sha256 = ("
        in function
    )


def test_c8_4b_worker_does_not_return_raw_sddl():
    function = security_descriptor_function()

    lowered = function.lower()

    assert "dacl_sddl =" not in lowered
    assert "raw_sddl =" not in lowered


def test_c8_4b_worker_remains_read_only():
    function = security_descriptor_function()

    forbidden = (
        "Set-Acl",
        "SetAccessRule",
        "AddAccessRule",
        "RemoveAccessRule",
        "ResetAccessRule",
        "SetOwner",
        "SetSecurityDescriptor",
        "ActiveDirectoryAccessRule",
    )

    for token in forbidden:
        assert token not in function
