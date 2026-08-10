from pathlib import Path
import re


WINDOWS_PATH = Path(
    "agent-windows/modules/"
    "EitasAdLookup.ps1"
)

FUNCTION_NAME = (
    "Invoke-EitasAdExplorer"
    "GetRecycleBinActivationEvidence"
)

ACTION = (
    "get_recycle_bin_activation_evidence"
)


def windows_source() -> str:
    return WINDOWS_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )


def function_body() -> str:
    source = windows_source()

    marker = (
        "function "
        + FUNCTION_NAME
        + " {"
    )

    start = source.index(
        marker
    )

    end = source.find(
        "\nfunction ",
        start + len(marker),
    )

    if end < 0:
        end = len(source)

    return source[
        start:end
    ]


def test_read_only_evidence_function_exists():
    assert (
        "function "
        + FUNCTION_NAME
    ) in windows_source()


def test_read_only_evidence_is_dispatched_by_lookup_only():
    source = windows_source()

    assert (
        '"'
        + ACTION
        + '" {'
    ) in source

    admin = Path(
        "agent-windows/modules/"
        "EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8",
        errors="replace",
    )

    assert ACTION not in admin


def test_required_read_only_queries_are_present():
    body = function_body()

    for command in (
        "Get-ADForest",
        "Get-ADOptionalFeature",
        "Get-ADDomainController",
        "Get-ADReplicationFailure",
        "Get-ADReplicationPartnerMetadata",
        "Get-Date",
    ):
        assert command in body


def test_evidence_result_contract_is_present():
    body = function_body()

    fields = (
        "read_only",
        "forest_name",
        "root_domain",
        "forest_mode",
        "recycle_bin_enabled",
        "recycle_bin_enabled_scope_count",
        "domain_controller_count",
        "replication_query_succeeded",
        "replication_partner_query_succeeded",
        "replication_failure_count",
        "replication_ready",
        "evidence_created_at",
        "activation_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "write_performed",
    )

    for field in fields:
        assert field in body


def test_all_authorization_flags_are_false():
    body = function_body()

    for field in (
        "activation_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "write_performed",
    ):
        assert re.search(
            rf"{field}\s*=\s*\$false",
            body,
            flags=re.IGNORECASE,
        )


def test_collector_contains_no_ad_write_primitive():
    body = function_body()

    forbidden = (
        r"\bEnable-ADOptionalFeature\b",
        r"\bRestore-ADObject\b",
        r"\bSet-AD[A-Za-z0-9_-]*\b",
        r"\bNew-AD[A-Za-z0-9_-]*\b",
        r"\bRemove-AD[A-Za-z0-9_-]*\b",
        r"\bMove-AD[A-Za-z0-9_-]*\b",
        r"\bRename-AD[A-Za-z0-9_-]*\b",
    )

    for pattern in forbidden:
        assert not re.search(
            pattern,
            body,
            flags=re.IGNORECASE,
        )


def test_single_dc_zero_partner_case_is_not_rejected():
    body = function_body()

    assert (
        "$ReplicationFailures.Count"
        in body
    )

    assert (
        "$ReplicationPartners.Count"
        in body
    )

    assert not re.search(
        r"ReplicationPartners\.Count\s+-lt\s+1",
        body,
        flags=re.IGNORECASE,
    )
