from pathlib import Path


WORKER = Path(
    "agent-windows/modules/"
    "EitasAdAdmin.ps1"
).read_text(
    encoding="utf-8"
)


def function_source(
    function_name,
    next_function_name,
):
    start = WORKER.index(
        "function "
        + function_name
        + " {"
    )

    end = WORKER.index(
        "function "
        + next_function_name
        + " {",
        start + 1,
    )

    return WORKER[
        start:end
    ]


CURRENT_STATE = function_source(
    "Get-EitasAdAdminAclCurrentState",
    (
        "Invoke-EitasAdAdminAclDelegation"
        "PrewriteValidation"
    ),
)

PREWRITE = function_source(
    (
        "Invoke-EitasAdAdminAclDelegation"
        "PrewriteValidation"
    ),
    (
        "Invoke-EitasAdAdminAclDelegation"
        "SimulationPreview"
    ),
)


def test_c8_4c1_has_dedicated_prewrite_engine():
    assert (
        "function "
        "Invoke-EitasAdAdminAclDelegation"
        "PrewriteValidation"
        in WORKER
    )

    assert (
        'contract_version = "c8.4c1"'
        in PREWRITE
    )

    assert (
        'execution_policy = (\n'
        '            "prewrite_validation_only"\n'
        '        )'
        in PREWRITE
    )


def test_c8_4c1_requires_b4_dormant_claim():
    assert (
        '-cne "c8.4b4"'
        in PREWRITE
    )

    assert (
        '-cne "claimed_dormant"'
        in PREWRITE
    )

    assert "claim_id" in PREWRITE
    assert "consumption_id" in PREWRITE


def test_c8_4c1_requires_production_context_but_does_not_authorize_it():
    assert (
        '$Mode -ine "Production"'
        in PREWRITE
    )

    assert (
        "production_authorized = $false"
        in PREWRITE
    )

    assert (
        "ad_write_authorized = $false"
        in PREWRITE
    )

    assert (
        "write_performed = $false"
        in PREWRITE
    )


def test_c8_4c1_rejects_any_authorizing_claim_flag():
    for marker in (
        "job_creation_authorized",
        "runtime_authorized",
        "production_authorized",
        "ad_write_authorized",
    ):
        assert marker in PREWRITE

    assert (
        "$FlagValue -isnot [bool]"
        in PREWRITE
    )

    assert (
        "$FlagValue -ne $false"
        in PREWRITE
    )


def test_c8_4c1_rereads_native_dacl_immediately():
    assert (
        "Get-Acl"
        in CURRENT_STATE
    )

    assert (
        "GetSecurityDescriptorSddlForm"
        in CURRENT_STATE
    )

    assert (
        "AccessControlSections]::Access"
        in CURRENT_STATE
    )

    assert (
        "SHA256]::Create()"
        in CURRENT_STATE
    )

    assert (
        "Encoding]::UTF8.GetBytes"
        in CURRENT_STATE
    )

    assert (
        '"sddl-access-sha256-v1"'
        in CURRENT_STATE
    )


def test_c8_4c1_revalidates_object_guid():
    assert (
        "object_guid"
        in CURRENT_STATE
    )

    assert (
        "objectGUID ACL modifie "
        "depuis le claim"
        in PREWRITE
    )

    assert (
        "object_guid_revalidated = $true"
        in PREWRITE
    )


def test_c8_4c1_revalidates_native_dacl_hash():
    assert (
        "dacl_sddl_sha256"
        in CURRENT_STATE
    )

    assert (
        "DACL ACL modifiee depuis le claim"
        in PREWRITE
    )

    assert (
        "dacl_revalidated = $true"
        in PREWRITE
    )


def test_c8_4c1_revalidates_principal_sid():
    assert (
        "Resolve-EitasAdAdminAclPrincipal"
        in PREWRITE
    )

    assert (
        '"SID principal ACL modifie "'
        in PREWRITE
    )

    assert (
        '"depuis le claim"'
        in PREWRITE
    )

    assert (
        "principal_sid_revalidated = $true"
        in PREWRITE
    )


def test_c8_4c1_keeps_allow_only_and_safe_rights():
    assert (
        "C8.4C1 autorise uniquement "
        in PREWRITE
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
        assert (
            '"'
            + right
            + '"'
            in PREWRITE
        )

    for forbidden in (
        '"GenericAll"',
        '"WriteDacl"',
        '"WriteOwner"',
        '"AccessSystemSecurity"',
    ):
        assert forbidden not in PREWRITE


def test_c8_4c1_is_not_exposed_in_generic_worker_switch():
    switch_start = WORKER.index(
        "function Invoke-EitasAdAdminJob {"
    )

    switch_source = WORKER[
        switch_start:
    ]

    assert (
        '"prevalidate_acl_delegation" {'
        not in switch_source
    )

    assert (
        '"apply_acl_delegation" {'
        not in switch_source
    )


def test_c8_4c1_has_no_acl_write_primitive():
    for primitive in (
        "Set-Acl",
        "SetAccessRule",
        "AddAccessRule",
        "RemoveAccessRule",
        "ResetAccessRule",
        "SetOwner",
        "ActiveDirectoryAccessRule",
    ):
        assert primitive not in PREWRITE
        assert primitive not in CURRENT_STATE


def test_c8_4c1_uses_ps51_safe_operator_layout():
    for section in (
        CURRENT_STATE,
        PREWRITE,
    ):
        bad_lines = [
            line
            for line in section.splitlines()
            if line.lstrip().startswith("+ ")
        ]

        assert bad_lines == []
