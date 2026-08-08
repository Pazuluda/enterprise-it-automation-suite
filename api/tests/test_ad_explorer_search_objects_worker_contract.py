from pathlib import Path


WORKER = Path(
    "agent-windows/modules/EitasAdLookup.ps1"
).read_text(
    encoding="utf-8",
)


def test_search_objects_worker_exists_and_is_dispatched():
    assert (
        "function Invoke-EitasAdExplorerSearchObjects"
        in WORKER
    )
    assert '"search_objects" {' in WORKER
    assert (
        "Invoke-EitasAdExplorerSearchObjects "
        "-Config $Config -Payload $Payload"
        in WORKER
    )


def test_search_objects_uses_native_ldap_search_and_safe_boundary():
    start = WORKER.index(
        "function Invoke-EitasAdExplorerSearchObjects"
    )
    end = WORKER.index(
        "function Invoke-EitasAdExplorerJob",
        start,
    )
    block = WORKER[start:end]

    assert "Escape-EitasLdapFilterValue" in block
    assert "Assert-EitasDnSafe" in block
    assert "-AllowDomainRoot" in block
    assert "Get-ADObject" in block
    assert "-LDAPFilter $LdapFilter" in block
    assert "-SearchScope $SearchScope" in block
    assert "-ResultSetSize $Limit" in block
    assert "[Math]::Min(" in block
    assert "1000" in block


def test_search_objects_covers_all_c6_object_types():
    start = WORKER.index(
        "function Invoke-EitasAdExplorerSearchObjects"
    )
    end = WORKER.index(
        "function Invoke-EitasAdExplorerJob",
        start,
    )
    block = WORKER[start:end]

    expected = (
        "objectClass=organizationalUnit",
        "objectClass=container",
        "objectClass=group",
        "objectClass=user",
        "objectClass=computer",
        "objectClass=contact",
    )

    for marker in expected:
        assert marker in block

    assert 'action = "search_objects"' in block
    assert '$Type = "ou"' in block
    assert "type = $Type" in block
    assert "group_scope = $GroupScope" in block
    assert "group_category = $GroupCategory" in block
    assert "distinguished_name" in block


def test_search_objects_filter_construction_is_powershell_51_safe():
    start = WORKER.index(
        "function Invoke-EitasAdExplorerSearchObjects"
    )
    end = WORKER.index(
        "function Invoke-EitasAdExplorerJob",
        start,
    )
    block = WORKER[start:end]

    assert "$TypeFilter = @(" in block
    assert "$QueryFilter = @(" in block
    assert "$LdapFilter = @(" in block

    assert block.count(") -join \"\"") >= 3

    assert "\n        + " not in block


def test_search_objects_filters_unsupported_container_subclasses():
    start = WORKER.index(
        "function Invoke-EitasAdExplorerSearchObjects"
    )
    end = WORKER.index(
        "function Invoke-EitasAdExplorerJob",
        start,
    )
    block = WORKER[start:end]

    expected_classes = (
        "organizationalunit",
        "container",
        "group",
        "user",
        "computer",
        "contact",
    )

    for object_class in expected_classes:
        quoted = chr(34) + object_class + chr(34)
        assert quoted in block

    assert "$SupportedObjectClasses -notcontains" in block
    assert "continue" in block

    assert "grouppolicycontainer" not in block.lower()
    assert "rpccontainer" not in block.lower()
