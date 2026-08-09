from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

WORKER = (
    ROOT
    / "agent-windows"
    / "modules"
    / "EitasAdLookup.ps1"
)


def worker_source() -> str:
    return WORKER.read_text(
        encoding="utf-8-sig"
    )


def security_function(
    source: str,
) -> str:
    start = source.index(
        "function "
        "Invoke-EitasAdExplorerGetSecurityDescriptor"
    )

    end = source.index(
        "function Invoke-EitasAdExplorerJob",
        start,
    )

    return source[start:end]


def test_worker_exposes_security_descriptor_action():
    source = worker_source()

    assert (
        "get_security_descriptor"
        in source
    )

    assert (
        "Invoke-EitasAdExplorerGetSecurityDescriptor"
        in source
    )


def test_worker_uses_read_only_acl_operation():
    block = security_function(
        worker_source()
    )

    assert "Get-Acl" in block
    assert "Set-Acl" not in block
    assert "read_only = $true" in block
    assert "sacl_included = $false" in block


def test_worker_keeps_eitas_dn_guard():
    block = security_function(
        worker_source()
    )

    assert "Assert-EitasDnSafe" in block
    assert "-DistinguishedName $ObjectDn" in block


def test_worker_reads_owner_and_dacl_rules():
    block = security_function(
        worker_source()
    )

    for token in (
        "$Acl.Owner",
        "$Acl.Access",
        "IdentityReference",
        "ActiveDirectoryRights",
        "AccessControlType",
        "ObjectType",
        "InheritedObjectType",
        "InheritanceType",
        "IsInherited",
    ):
        assert token in block


def test_worker_reports_inheritance_and_rule_counts():
    block = security_function(
        worker_source()
    )

    for token in (
        "inheritance_enabled",
        "access_rules_protected",
        "access_rule_count",
        "explicit_rule_count",
        "inherited_rule_count",
    ):
        assert token in block


def test_worker_does_not_touch_sacl():
    block = security_function(
        worker_source()
    )

    forbidden = (
        "Audit",
        "SetAccessRule",
        "AddAccessRule",
        "RemoveAccessRule",
        "SetOwner",
    )

    for token in forbidden:
        assert token not in block


def test_worker_rejects_split_security_identifier_cast():
    source = worker_source()

    bad = (
        "[System.Security.Principal.SecurityIdentifier]"
        "\n                $IdentityReference"
    )

    assert bad not in source
