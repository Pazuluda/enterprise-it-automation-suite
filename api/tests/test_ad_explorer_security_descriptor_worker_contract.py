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


def acl_guid_catalog_function(
    source: str,
) -> str:
    start = source.index(
        "function Get-EitasAdAclGuidCatalog"
    )

    end = source.index(
        "function Get-EitasAdAclGuidName",
        start,
    )

    return source[start:end]


def acl_guid_name_function(
    source: str,
) -> str:
    start = source.index(
        "function Get-EitasAdAclGuidName"
    )

    end = source.index(
        "function "
        "Invoke-EitasAdExplorerGetSecurityDescriptor",
        start,
    )

    return source[start:end]


def acl_guid_converter_function(
    source: str,
) -> str:
    start = source.index(
        "function Convert-EitasAdAclGuidValue"
    )

    end = source.index(
        "function Get-EitasAdAclGuidCatalog",
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

def test_worker_builds_acl_guid_catalog_from_schema():
    block = acl_guid_catalog_function(
        worker_source()
    )

    for token in (
        "Get-ADRootDSE",
        "schemaNamingContext",
        "configurationNamingContext",
        "objectClass=attributeSchema",
        "objectClass=classSchema",
        "lDAPDisplayName",
        "schemaIDGUID",
    ):
        assert token in block


def test_worker_reads_extended_right_guid_catalog():
    block = acl_guid_catalog_function(
        worker_source()
    )

    for token in (
        "CN=Extended-Rights,",
        "objectClass=controlAccessRight",
        "rightsGuid",
        "displayName",
        "Get-ADObject",
    ):
        assert token in block


def test_worker_normalizes_acl_guids_and_keeps_safe_fallback():
    converter = acl_guid_converter_function(
        worker_source()
    )

    resolver = acl_guid_name_function(
        worker_source()
    )

    assert "[System.Guid]" in converter
    assert "[byte[]]" in converter
    assert 'ToString("D")' in converter
    assert "ToLowerInvariant()" in converter

    assert (
        "00000000-0000-0000-0000-000000000000"
        in resolver
    )

    assert (
        "$Catalog.ContainsKey($NormalizedGuid)"
        in resolver
    )

    assert "return $null" in resolver


def test_worker_enriches_acl_rules_with_guid_names():
    block = security_function(
        worker_source()
    )

    for token in (
        "$ObjectTypeGuid",
        "$InheritedObjectTypeGuid",
        "object_type_guid",
        "object_type_name",
        "inherited_object_type_guid",
        "inherited_object_type_name",
        "Get-EitasAdAclGuidName",
    ):
        assert token in block


def test_worker_builds_guid_catalog_once_before_rules():
    block = security_function(
        worker_source()
    )

    marker = (
        "$GuidCatalog = "
        "Get-EitasAdAclGuidCatalog"
    )

    assert block.count(marker) == 1

    catalog_index = block.index(marker)
    rules_index = block.index(
        "$Rules = @("
    )

    assert catalog_index < rules_index


def test_worker_guid_enrichment_remains_read_only():
    source = worker_source()

    catalog = acl_guid_catalog_function(
        source
    )

    descriptor = security_function(
        source
    )

    assert "Get-ADRootDSE" in catalog
    assert "Get-ADObject" in catalog
    assert "Get-Acl" in descriptor

    forbidden = (
        "Set-Acl",
        "SetAccessRule",
        "AddAccessRule",
        "RemoveAccessRule",
        "SetOwner",
        "Set-AD",
        "New-AD",
        "Remove-AD",
        "Move-AD",
        "Rename-AD",
    )

    for token in forbidden:
        assert token not in catalog
        assert token not in descriptor
