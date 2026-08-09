from pathlib import Path


SOURCE = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
).read_text(
    encoding="utf-8"
)


def function_body(name: str) -> str:
    marker = f"function {name} {{"

    start = SOURCE.index(marker)

    next_function = SOURCE.find(
        "\nfunction ",
        start + len(marker),
    )

    if next_function == -1:
        return SOURCE[start:]

    return SOURCE[start:next_function]


def test_c8_3b1_exposes_dormant_preview_function():
    assert (
        "function "
        "Invoke-EitasAdAdminAclDelegationSimulationPreview {"
        in SOURCE
    )

    preview = function_body(
        "Invoke-EitasAdAdminAclDelegationSimulationPreview"
    )

    assert (
        'action = "simulate_acl_delegation"'
        in preview
    )

    assert "simulated = $true" in preview
    assert "write_performed = $false" in preview
    assert "production_authorized = $false" in preview
    assert "ad_write_authorized = $false" in preview


def test_c8_3b1_rejects_production_before_resolution():
    preview = function_body(
        "Invoke-EitasAdAdminAclDelegationSimulationPreview"
    )

    mode_guard = preview.index(
        '$Mode -ine "Simulation"'
    )

    target_resolution = preview.index(
        "Resolve-EitasAdAdminObject"
    )

    principal_resolution = preview.index(
        "Resolve-EitasAdAdminAclPrincipal"
    )

    assert mode_guard < target_resolution
    assert mode_guard < principal_resolution


def test_c8_3b1_reuses_managed_target_guard():
    preview = function_body(
        "Invoke-EitasAdAdminAclDelegationSimulationPreview"
    )

    assert "Resolve-EitasAdAdminObject" in preview
    assert "Assert-EitasDnSafe" in preview


def test_c8_4b_simulation_binds_target_object_guid():
    resolver = function_body(
        "Resolve-EitasAdAdminObject"
    )

    preview = function_body(
        "Invoke-EitasAdAdminAclDelegationSimulationPreview"
    )

    assert "objectGUID" in resolver
    assert "$Target.ObjectGUID" in preview
    assert "object_guid = (" in preview


def test_c8_3b1_resolves_security_principal_sid():
    resolver = function_body(
        "Resolve-EitasAdAdminAclPrincipal"
    )

    assert "Get-EitasAdDomainDn" in resolver
    assert "objectSid=*" in resolver
    assert "Get-ADGroup" in resolver
    assert "Get-ADUser" in resolver
    assert "Get-ADComputer" in resolver
    assert ".SID" in resolver
    assert ".Value" in resolver


def test_c8_3b1_validates_native_ad_rights_and_scope():
    preview = function_body(
        "Invoke-EitasAdAdminAclDelegationSimulationPreview"
    )

    assert (
        "System.DirectoryServices.ActiveDirectoryRights"
        in preview
    )

    assert (
        "System.DirectoryServices."
        "ActiveDirectorySecurityInheritance"
        in preview
    )

    for right in (
        "ReadProperty",
        "WriteProperty",
        "CreateChild",
        "DeleteChild",
        "ListChildren",
        "ReadControl",
        "ExtendedRight",
        "GenericRead",
    ):
        assert f'"{right}"' in preview


def test_c8_3b1_keeps_raw_guid_preview_fields():
    preview = function_body(
        "Invoke-EitasAdAdminAclDelegationSimulationPreview"
    )

    assert (
        "Convert-EitasAdAdminAclGuidValue"
        in preview
    )

    assert "object_type_guid" in preview
    assert "inherited_object_type_guid" in preview


def test_c8_3c1_dispatches_preview_only():
    dispatch_start = SOURCE.index(
        "function Invoke-EitasAdAdminJob {"
    )

    dispatch = SOURCE[dispatch_start:]

    assert (
        '"simulate_acl_delegation" {'
        in dispatch
    )

    assert (
        "Invoke-EitasAdAdminAclDelegationSimulationPreview"
        in dispatch
    )

    assert (
        "-Config $Config"
        in dispatch
    )

    assert (
        "-Payload $Payload"
        in dispatch
    )

    assert (
        "-Mode $Mode"
        in dispatch
    )


def test_c8_3b1_has_no_acl_write_primitive():
    forbidden = (
        "Set-Acl",
        "SetAccessRule",
        "AddAccessRule",
        "RemoveAccessRule",
        "SetOwner",
    )

    for primitive in forbidden:
        assert primitive not in SOURCE
