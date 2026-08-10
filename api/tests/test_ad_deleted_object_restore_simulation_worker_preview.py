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


def test_c9_preview_function_exists_but_is_not_dispatched():
    name = (
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreSimulationPreview"
    )

    assert (
        f"function {name} {{"
        in SOURCE
    )

    dispatcher = function_body(
        "Invoke-EitasAdAdminJob"
    )

    assert (
        "simulate_deleted_object_restore"
        not in dispatcher
    )

    assert name not in dispatcher


def test_c9_preview_rejects_non_simulation_before_ad_reads():
    preview = function_body(
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreSimulationPreview"
    )

    mode_guard = preview.index(
        '$Mode -ine "Simulation"'
    )

    module_import = preview.index(
        "Import-EitasActiveDirectoryModule"
    )

    fresh_lookup = preview.index(
        "Get-ADObject `"
    )

    assert mode_guard < module_import
    assert mode_guard < fresh_lookup


def test_c9_preview_requires_locked_candidate_contract():
    preview = function_body(
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreSimulationPreview"
    )

    for expected in (
        "candidate_preflight",
        "preflight_passed",
        "simulation_candidate",
        "simulation_job_authorized",
        "simulation_job_persistence_authorized",
        "standard_controlled",
        "manual_review_required",
    ):
        assert expected in preview


def test_c9_preview_requires_all_runtime_authorizations_false():
    preview = function_body(
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreSimulationPreview"
    )

    for field in (
        "worker_claim_authorized",
        "worker_runtime_authorized",
        "restore_cmdlet_authorized",
        "restore_whatif_authorized",
        "execution_authorized",
        "write_authorized",
        "restore_implemented",
        "restore_performed",
    ):
        assert field in preview

    assert (
        "$FieldValue -ne $false"
        in preview
    )


def test_c9_preview_revalidates_deleted_object_by_guid():
    preview = function_body(
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreSimulationPreview"
    )

    assert (
        "[Guid]::TryParse"
        in preview
    )

    assert (
        "-Identity $Guid `"
        in preview
    )

    assert (
        "-IncludeDeletedObjects `"
        in preview
    )

    assert (
        "$FreshGuid -ne $Guid"
        in preview
    )

    assert (
        "$Fresh.isDeleted -ne $true"
        in preview
    )

    assert (
        "$Fresh.isRecycled -eq $true"
        in preview
    )


def test_c9_preview_checks_recycle_bin_and_first_wave_class():
    preview = function_body(
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreSimulationPreview"
    )

    assert (
        "Get-ADOptionalFeature"
        in preview
    )

    assert (
        "Recycle Bin Feature"
        in preview
    )

    for object_class in (
        "user",
        "group",
        "computer",
        "contact",
    ):
        assert (
            f'"{object_class}"'
            in preview
        )


def test_c9_preview_uses_schema_rdn_and_safe_parent():
    preview = function_body(
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreSimulationPreview"
    )

    assert (
        "schemaNamingContext"
        in preview
    )

    assert "rDNAttID" in preview

    assert (
        "Assert-EitasDnSafe"
        in preview
    )

    assert (
        "effective_target_path"
        in preview
    )


def test_c9_preview_collision_probe_is_one_level_and_escaped():
    preview = function_body(
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreSimulationPreview"
    )

    helper = function_body(
        "ConvertTo-EitasAdAdminLdapFilterValue"
    )

    assert (
        r"$Builder.Append('\00')"
        in helper
    )

    assert (
        r"$Builder.Append('\28')"
        in helper
    )

    assert (
        r"$Builder.Append('\29')"
        in helper
    )

    assert (
        r"$Builder.Append('\2a')"
        in helper
    )

    assert (
        r"$Builder.Append('\5c')"
        in helper
    )

    assert (
        "ConvertTo-EitasAdAdminLdapFilterValue"
        in preview
    )

    assert (
        "-SearchScope OneLevel `"
        in preview
    )

    assert (
        "$CollisionFilter"
        in preview
    )

    assert (
        "Target name collision detected"
        in preview
    )


def test_c9_preview_result_is_explicitly_non_authorizing():
    preview = function_body(
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreSimulationPreview"
    )

    for expected in (
        "simulated = $true",
        "preview_only = $true",
        "read_only = $true",
        "recycle_bin_enabled = $true",
        "is_deleted = $true",
        "is_recycled = $false",
        "parent_exists = $true",
        "collision_probe_performed = $true",
        "target_collision = $false",
        "worker_claim_authorized = $false",
        "worker_runtime_authorized = $false",
        "restore_cmdlet_authorized = $false",
        "restore_whatif_authorized = $false",
        "execution_authorized = $false",
        "write_authorized = $false",
        "restore_implemented = $false",
        "restore_performed = $false",
        "write_performed = $false",
        "production_authorized = $false",
    ):
        assert expected in preview


def test_c9_preview_contains_no_ad_write_primitive():
    preview = function_body(
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreSimulationPreview"
    )

    forbidden = (
        "Restore-ADObject",
        "Enable-ADOptionalFeature",
        "Set-ADObject",
        "Set-ADUser",
        "Set-ADComputer",
        "Add-ADGroupMember",
        "Remove-ADGroupMember",
        "Move-ADObject",
        "Rename-ADObject",
        "Remove-ADObject",
        "New-ADObject",
        "New-ADUser",
        "New-ADGroup",
        "Set-Acl",
        "AddAccessRule",
        "SetAccessRule",
    )

    for primitive in forbidden:
        assert primitive not in preview
