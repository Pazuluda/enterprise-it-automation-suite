from __future__ import annotations

import importlib
from pathlib import Path


CHAIN_MODULES = (
    "app.services.ad_deleted_object_restore_ticket",
    "app.services.ad_deleted_object_restore_ticket_persistence",
    "app.services.ad_deleted_object_restore_ticket_consumption",
    "app.services.ad_deleted_object_restore_authorization",
    "app.services.ad_deleted_object_restore_authorization_persistence",
    "app.services.ad_deleted_object_restore_preexecution",
    "app.services.ad_deleted_object_restore_authorization_consumption",
    "app.services.ad_deleted_object_restore_runtime_gate",
)


SERVICE_FILES = tuple(
    Path(
        module.replace(
            "app.services.",
            "api/app/services/",
        ).replace(".", "/") + ".py"
    )
    for module in CHAIN_MODULES
)


DANGEROUS_TRUE_SUFFIXES = (
    "ROUTE_ENABLED",
    "AGENT_ENDPOINTS_ENABLED",
    "JOB_CREATION_AUTHORIZED",
    "CLAIM_AUTHORIZED",
    "RUNTIME_AUTHORIZED",
    "PRODUCTION_AUTHORIZED",
    "RESTORE_AUTHORIZED",
    "RESTORE_WHATIF_AUTHORIZED",
    "EXECUTION_AUTHORIZED",
    "WRITE_PERFORMED",
)


def test_c95_security_barrier_contract_versions_are_exact():
    expected = {
        "app.services.ad_deleted_object_restore_ticket":
            "c9.5a4b-v1",
        "app.services.ad_deleted_object_restore_authorization":
            "c9.5a4c-v1",
        "app.services.ad_deleted_object_restore_authorization_persistence":
            "c9.5a4c3-v1",
        "app.services.ad_deleted_object_restore_preexecution":
            "c9.5a4d-v1",
        "app.services.ad_deleted_object_restore_authorization_consumption":
            "c9.5a4d3-v1",
        "app.services.ad_deleted_object_restore_runtime_gate":
            "c9.5a4e-v1",
    }

    for module_name, contract in expected.items():
        module = importlib.import_module(
            module_name
        )

        values = [
            value
            for name, value in vars(module).items()
            if (
                name.endswith(
                    "_CONTRACT_VERSION"
                )
                and isinstance(value, str)
            )
        ]

        assert contract in values


def test_c95_runtime_gate_remains_fully_dormant():
    module = importlib.import_module(
        "app.services."
        "ad_deleted_object_restore_runtime_gate"
    )

    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_PERSISTENCE_ENABLED
        is False
    )
    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_ROUTE_ENABLED
        is False
    )
    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_AGENT_ENDPOINTS_ENABLED
        is False
    )
    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_JOB_CREATION_AUTHORIZED
        is False
    )
    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_CLAIM_AUTHORIZED
        is False
    )
    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_RUNTIME_AUTHORIZED
        is False
    )
    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_PRODUCTION_AUTHORIZED
        is False
    )
    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_RESTORE_AUTHORIZED
        is False
    )
    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_RESTORE_WHATIF_AUTHORIZED
        is False
    )
    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_EXECUTION_AUTHORIZED
        is False
    )
    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_WRITE_PERFORMED
        is False
    )


def test_c95_chain_contains_no_dangerous_true_constant():
    violations = []

    for module_name in CHAIN_MODULES:
        module = importlib.import_module(
            module_name
        )

        for name, value in vars(module).items():
            if not isinstance(
                value,
                bool,
            ):
                continue

            if not any(
                name.endswith(suffix)
                for suffix in DANGEROUS_TRUE_SUFFIXES
            ):
                continue

            if value is True:
                violations.append(
                    module_name
                    + ":"
                    + name
                )

    assert violations == []


def test_c95_services_contain_no_restore_cmdlet():
    for path in SERVICE_FILES:
        source = path.read_text(
            encoding="utf-8"
        )

        assert "Restore-ADObject" not in source


def test_c95_services_contain_no_recycle_bin_activation_cmdlet():
    for path in SERVICE_FILES:
        source = path.read_text(
            encoding="utf-8"
        )

        assert "Enable-ADOptionalFeature" not in source


def test_c95_runtime_gate_has_no_process_or_worker_transport():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_runtime_gate.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "subprocess",
        "powershell",
        "pwsh",
        "service_create_ad_admin_job",
        "claim_ad_admin_job",
        "AD_ADMIN_JOBS_FILE",
    )

    for token in forbidden:
        assert token not in source


def test_c95_main_does_not_integrate_security_barrier_services():
    main = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "ad_deleted_object_restore_ticket",
        "ad_deleted_object_restore_authorization",
        "ad_deleted_object_restore_preexecution",
        "ad_deleted_object_restore_authorization_consumption",
        "ad_deleted_object_restore_runtime_gate",
        "build_ad_deleted_object_restore_runtime_gate",
        "consume_ad_deleted_object_restore_authorization",
    )

    for token in forbidden:
        assert token not in main


def test_c95_only_existing_readonly_and_simulation_surfaces_remain():
    main = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '"/api/ad-explorer/deleted-objects/preflight"'
        in main
    )

    assert (
        '"restore-simulation/prepare"'
        in main
    )

    forbidden = (
        '"restore/execute"',
        '"restore/apply"',
        '"restore/commit"',
        '"restore/run"',
        '"restore/claim"',
    )

    for token in forbidden:
        assert token not in main


def test_c95_windows_worker_remains_preview_only():
    windows = Path(
        "agent-windows/modules/EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "simulate_deleted_object_restore"
        in windows
    )

    assert "Restore-ADObject" not in windows

    assert (
        "ad_deleted_object_restore_runtime_gate"
        not in windows
    )

    assert (
        "authorization_consumption_id"
        not in windows
    )


def test_c95_runtime_gate_source_is_nonpersistent():
    module = importlib.import_module(
        "app.services."
        "ad_deleted_object_restore_runtime_gate"
    )

    assert (
        module.AD_DELETED_OBJECT_RESTORE_RUNTIME_GATE_PERSISTENCE_ENABLED
        is False
    )

    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_runtime_gate.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "open(",
        "write_text(",
        "write_bytes(",
        "os.replace",
        "json.dump",
        "mkdir(",
        "flock",
    )

    for token in forbidden:
        assert token not in source
