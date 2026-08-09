from pathlib import Path


MODULE_PATH = Path(
    "agent-windows/modules/EitasAdAdmin.ps1"
)

RUNNER_PATH = Path(
    "agent-windows/Run-AdAdminWorker.ps1"
)

module = MODULE_PATH.read_text(
    encoding="utf-8-sig"
)

runner = RUNNER_PATH.read_text(
    encoding="utf-8-sig"
)


def test_c8_4c5c4a_dedicated_helpers_exist():
    for name in (
        "Get-EitasPendingAclPrewriteTickets",
        "Claim-EitasAclPrewriteTicket",
        "Send-EitasAclPrewriteResult",
        "Assert-EitasAclPrewriteTransportAuthorization",
        "Process-EitasPendingAclPrewriteTickets",
    ):
        assert (
            f"function {name} {{"
            in module
        )


def test_c8_4c5c4a_uses_only_dedicated_routes():
    assert (
        "/api/agent/acl-delegation/"
        in module
    )

    assert (
        "prewrite/pending"
        in module
    )

    assert (
        "prewrite/claim/"
        in module
    )

    assert (
        "prewrite/result/"
        in module
    )


def test_c8_4c5c4c_calls_prewrite_validator_with_resolved_mode():
    assert (
        "Invoke-EitasAdAdminAclDelegationPrewriteValidation"
        in module
    )

    processor = module.split(
        "function Process-EitasPendingAclPrewriteTickets {",
        1,
    )[1].split(
        "function Process-EitasPendingAdAdminJobs {",
        1,
    )[0]

    assert (
        "Invoke-EitasAdAdminAclDelegationPrewriteValidation"
        in processor
    )

    assert (
        "-Mode $Mode"
        in processor
    )

    assert (
        '-Mode "Production"'
        not in processor
    )

    assert (
        "Invoke-EitasAdAdminJob "
        not in processor
    )


def test_c8_4c5c4a_checks_transport_authorization():
    assert (
        "prewrite_validation_runtime_authorized"
        in module
    )

    for flag in (
        "job_creation_authorized",
        "runtime_authorized",
        "production_authorized",
        "ad_write_authorized",
    ):
        assert flag in module


def test_c8_4c5c4a_keeps_generic_dispatch_closed():
    assert (
        '"prevalidate_acl_delegation" {'
        not in module
    )

    assert (
        '"apply_acl_delegation" {'
        not in module
    )


def test_c8_4c5c4c_runner_is_wired_exactly_once():
    assert (
        runner.count(
            "Process-EitasPendingAclPrewriteTickets"
        )
        == 1
    )


def test_c8_4c5c4a_has_no_acl_write_primitive():
    forbidden = (
        "Set-Acl",
        "SetAccessRule",
        "AddAccessRule",
        "RemoveAccessRule",
        "ResetAccessRule",
        "SetOwner",
        "ActiveDirectoryAccessRule",
    )

    for token in forbidden:
        assert token not in module


def test_c8_4c5c4c_requires_real_production_mode():
    processor = module.split(
        "function Process-EitasPendingAclPrewriteTickets {",
        1,
    )[1].split(
        "function Process-EitasPendingAdAdminJobs {",
        1,
    )[0]

    assert (
        "Get-EitasAgentMode"
        in processor
    )

    assert (
        '$Mode -ine "Production"'
        in processor
    )

    assert (
        "-Mode $Mode"
        in processor
    )

    assert (
        '-Mode "Production"'
        not in processor
    )


def test_c8_4c5c4c_runner_is_now_explicitly_wired():
    assert (
        "Process-EitasPendingAclPrewriteTickets"
        in runner
    )

    assert (
        runner.count(
            "Process-EitasPendingAclPrewriteTickets"
        )
        == 1
    )


def test_c8_4c5c4c_generic_dispatch_still_not_used():
    processor = module.split(
        "function Process-EitasPendingAclPrewriteTickets {",
        1,
    )[1].split(
        "function Process-EitasPendingAdAdminJobs {",
        1,
    )[0]

    assert (
        "Invoke-EitasAdAdminJob "
        not in processor
    )

    assert (
        '"prevalidate_acl_delegation" {'
        not in module
    )

    assert (
        '"apply_acl_delegation" {'
        not in module
    )
