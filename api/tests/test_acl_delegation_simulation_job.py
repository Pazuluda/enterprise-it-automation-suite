from pathlib import Path

import pytest

from app.services.acl_delegation_simulation_job import (
    ACL_DELEGATION_SIMULATION_AD_WRITE_ENABLED,
    ACL_DELEGATION_SIMULATION_JOB_PERSISTENCE_ENABLED,
    ACL_DELEGATION_SIMULATION_PRODUCTION_ENABLED,
    ACL_DELEGATION_SIMULATION_RUNTIME_ENABLED,
    AclDelegationSimulationJobBadRequest,
    assert_acl_delegation_simulation_job_invariants,
    get_acl_delegation_simulation_audit_metadata,
    prepare_acl_delegation_simulation_job_envelope,
)


def valid_payload() -> dict:
    return {
        "action": "simulate_acl_delegation",
        "mode": "Simulation",
        "object_dn": (
            "OU=test,OU=Users,OU=EITAS,"
            "DC=API,DC=LOCAL"
        ),
        "principal_identity": (
            "API\\GG_IT_Admin"
        ),
        "access_control_type": "Allow",
        "rights": [
            "ReadProperty",
            "WriteProperty",
        ],
        "inheritance_type": "Descendents",
        "object_type_guid": (
            "bf967aba-0de6-11d0-a285-00aa003049e2"
        ),
        "inherited_object_type_guid": (
            "bf967aba-0de6-11d0-a285-00aa003049e2"
        ),
    }


def test_c8_3a2_prepares_normalized_envelope():
    envelope = (
        prepare_acl_delegation_simulation_job_envelope(
            valid_payload()
        )
    )

    assert envelope.action == (
        "simulate_acl_delegation"
    )
    assert envelope.mode == "Simulation"

    assert envelope.payload["rights"] == [
        "ReadProperty",
        "WriteProperty",
    ]

    assert (
        envelope.payload["inheritance_type"]
        == "Descendents"
    )

    assert envelope.job_preparation_authorized
    assert envelope.job_persistence_authorized
    assert envelope.runtime_authorized
    assert not envelope.production_authorized
    assert not envelope.ad_write_authorized


def test_c8_3a2_keeps_technical_guids():
    envelope = (
        prepare_acl_delegation_simulation_job_envelope(
            valid_payload()
        )
    )

    assert envelope.payload["object_type_guid"] == (
        "bf967aba-0de6-11d0-a285-00aa003049e2"
    )

    assert (
        envelope.payload[
            "inherited_object_type_guid"
        ]
        == "bf967aba-0de6-11d0-a285-00aa003049e2"
    )


def test_c8_3a2_audit_is_non_authorizing():
    envelope = (
        prepare_acl_delegation_simulation_job_envelope(
            valid_payload()
        )
    )

    audit = (
        get_acl_delegation_simulation_audit_metadata(
            envelope
        )
    )

    assert audit["mode"] == "Simulation"
    assert audit["job_persistence_authorized"]
    assert audit["runtime_authorized"]
    assert not audit["production_authorized"]
    assert not audit["ad_write_authorized"]


def test_c8_3a2_rejects_invalid_contract():
    payload = valid_payload()
    payload["mode"] = "Production"

    with pytest.raises(
        AclDelegationSimulationJobBadRequest
    ):
        prepare_acl_delegation_simulation_job_envelope(
            payload
        )


def test_c8_3a2_runtime_flags_remain_disabled():
    assert (
        ACL_DELEGATION_SIMULATION_JOB_PERSISTENCE_ENABLED
    )
    assert (
        ACL_DELEGATION_SIMULATION_RUNTIME_ENABLED
    )
    assert not (
        ACL_DELEGATION_SIMULATION_PRODUCTION_ENABLED
    )
    assert not (
        ACL_DELEGATION_SIMULATION_AD_WRITE_ENABLED
    )

    assert_acl_delegation_simulation_job_invariants()


def test_c8_3_runtime_is_narrowly_integrated():
    main_source = Path(
        "api/main.py"
    ).read_text(encoding="utf-8")

    admin_source = Path(
        "api/app/services/ad_admin.py"
    ).read_text(encoding="utf-8")

    worker_source = Path(
        "agent-windows/modules/EitasAdAdmin.ps1"
    ).read_text(encoding="utf-8")

    frontend_root = Path("frontend/src")

    frontend_source = "\n".join(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
        for path in frontend_root.rglob("*")
        if path.is_file()
    )

    # Generic AD Admin route is reused:
    # no dedicated HTTP endpoint is introduced.
    assert "simulate_acl_delegation" not in main_source

    # C8.3D exposes the Simulation through the existing
    # AD Explorer UI and the generic AD Admin job route.
    assert "simulate_acl_delegation" in frontend_source
    assert "/api/ad-admin/jobs" in frontend_source

    # Backend and worker are the only runtime exposure.
    assert "simulate_acl_delegation" in admin_source

    dispatch_marker = (
        "function Invoke-EitasAdAdminJob {"
    )

    dispatch_start = worker_source.index(
        dispatch_marker
    )

    dispatch = worker_source[dispatch_start:]

    assert '"simulate_acl_delegation" {' in dispatch
    assert (
        "Invoke-EitasAdAdminAclDelegationSimulationPreview"
        in dispatch
    )


def test_c8_3a2_has_no_acl_write_primitive():
    source = Path(
        "api/app/services/"
        "acl_delegation_simulation_job.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "Set-Acl",
        "SetAccessRule",
        "AddAccessRule",
        "RemoveAccessRule",
        "SetOwner",
    )

    for primitive in forbidden:
        assert primitive not in source
