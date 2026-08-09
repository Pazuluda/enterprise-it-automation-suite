from pathlib import Path

import pytest

from app.services.acl_delegation_simulation import (
    ACL_DELEGATION_SIMULATION_ACTION,
    ACL_DELEGATION_SIMULATION_AD_WRITE_ENABLED,
    ACL_DELEGATION_SIMULATION_JOB_CREATION_ENABLED,
    ACL_DELEGATION_SIMULATION_PRODUCTION_ENABLED,
    AclDelegationSimulationBadRequest,
    assert_acl_delegation_simulation_invariants,
    normalize_acl_delegation_simulation_request,
)


def valid_payload() -> dict:
    return {
        "action": ACL_DELEGATION_SIMULATION_ACTION,
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


def test_c8_3a1_normalizes_simulation_contract():
    request = (
        normalize_acl_delegation_simulation_request(
            valid_payload()
        )
    )

    assert request.action == (
        "simulate_acl_delegation"
    )
    assert request.mode == "Simulation"
    assert request.access_control_type == "Allow"
    assert request.rights == (
        "ReadProperty",
        "WriteProperty",
    )
    assert request.inheritance_type == "Descendents"

    assert request.simulation_validation_authorized
    assert request.simulation_job_authorized
    assert not request.production_authorized
    assert not request.ad_write_authorized


def test_c8_3a1_rejects_production():
    payload = valid_payload()
    payload["mode"] = "Production"

    with pytest.raises(
        AclDelegationSimulationBadRequest
    ):
        normalize_acl_delegation_simulation_request(
            payload
        )


def test_c8_3a1_rejects_deny():
    payload = valid_payload()
    payload["access_control_type"] = "Deny"

    with pytest.raises(
        AclDelegationSimulationBadRequest
    ):
        normalize_acl_delegation_simulation_request(
            payload
        )


def test_c8_3a1_rejects_unknown_right():
    payload = valid_payload()
    payload["rights"] = [
        "GenericAll",
    ]

    with pytest.raises(
        AclDelegationSimulationBadRequest
    ):
        normalize_acl_delegation_simulation_request(
            payload
        )


def test_c8_3a1_rejects_invalid_guid():
    payload = valid_payload()
    payload["object_type_guid"] = "not-a-guid"

    with pytest.raises(
        AclDelegationSimulationBadRequest
    ):
        normalize_acl_delegation_simulation_request(
            payload
        )


def test_c8_3a1_normalizes_zero_guid_to_none():
    payload = valid_payload()
    payload["object_type_guid"] = (
        "00000000-0000-0000-0000-000000000000"
    )

    request = (
        normalize_acl_delegation_simulation_request(
            payload
        )
    )

    assert request.object_type_guid is None


def test_c8_3a1_requires_target_and_principal():
    payload = valid_payload()
    payload["object_dn"] = ""

    with pytest.raises(
        AclDelegationSimulationBadRequest
    ):
        normalize_acl_delegation_simulation_request(
            payload
        )

    payload = valid_payload()
    payload["principal_identity"] = ""

    with pytest.raises(
        AclDelegationSimulationBadRequest
    ):
        normalize_acl_delegation_simulation_request(
            payload
        )


def test_c8_3a1_runtime_features_are_dormant():
    assert (
        ACL_DELEGATION_SIMULATION_JOB_CREATION_ENABLED
    )
    assert not (
        ACL_DELEGATION_SIMULATION_PRODUCTION_ENABLED
    )
    assert not (
        ACL_DELEGATION_SIMULATION_AD_WRITE_ENABLED
    )

    assert_acl_delegation_simulation_invariants()


def test_c8_3a1_has_no_acl_write_primitive():
    source = Path(
        "api/app/services/"
        "acl_delegation_simulation.py"
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
