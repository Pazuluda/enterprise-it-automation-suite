from copy import deepcopy
from pathlib import Path

import pytest

from app.services.acl_delegation_write_binding import (
    AclDelegationWriteBindingBadRequest,
    calculate_acl_fingerprint,
    validate_acl_delegation_write_binding,
)


TARGET_DN = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

SIMULATION_JOB_ID = (
    "0359e373-70b2-47a0-b785-f7cb80967ac4"
)

SECURITY_JOB_ID = (
    "deebe24c-a62e-4b03-9f92-546d38a984df"
)


def descriptor():
    return {
        "action": "get_security_descriptor",
        "object_dn": TARGET_DN,
        "object_guid": (
            "8838f739-c817-4b45-"
            "90b2-b597ce79312a"
        ),
        "dacl_fingerprint_version": (
            "sddl-access-sha256-v1"
        ),
        "dacl_sddl_sha256": "a" * 64,
        "read_only": True,
        "sacl_included": False,
        "inheritance_enabled": True,
        "access_rules_protected": False,
        "generated_at": "2026-08-09T10:00:00Z",
        "owner": "API\\Admins du domaine",
        "owner_sid": "S-1-5-21-1-2-3-512",
        "rules": [
            {
                "identity": "API\\Admins du domaine",
                "sid": "S-1-5-21-1-2-3-512",
                "access_control_type": "Allow",
                "active_directory_rights": (
                    "GenericAll"
                ),
                "inheritance_type": "None",
                "inheritance_flags": "None",
                "propagation_flags": "None",
                "is_inherited": False,
                "object_type_guid": (
                    "00000000-0000-0000-"
                    "0000-000000000000"
                ),
                "object_type_name": None,
                "inherited_object_type_guid": (
                    "00000000-0000-0000-"
                    "0000-000000000000"
                ),
                "inherited_object_type_name": None,
            },
            {
                "identity": "Tout le monde",
                "sid": "S-1-1-0",
                "access_control_type": "Deny",
                "active_directory_rights": (
                    "WriteProperty, ReadProperty"
                ),
                "inheritance_type": "Descendents",
                "inheritance_flags": (
                    "ContainerInherit"
                ),
                "propagation_flags": (
                    "InheritOnly"
                ),
                "is_inherited": True,
                "object_type_guid": (
                    "bf967aba-0de6-11d0-"
                    "a285-00aa003049e2"
                ),
                "object_type_name": "user",
                "inherited_object_type_guid": (
                    "bf967aba-0de6-11d0-"
                    "a285-00aa003049e2"
                ),
                "inherited_object_type_name": (
                    "user"
                ),
            },
        ],
    }


def simulation_job():
    return {
        "id": SIMULATION_JOB_ID,
        "action": "simulate_acl_delegation",
        "status": "completed",
        "success": True,
        "completed_at": (
            "2026-08-09T13:43:51Z"
        ),
        "payload": {
            "object_dn": TARGET_DN,
            "principal_identity": "GG_IT_Admin",
            "access_control_type": "Allow",
            "rights": [
                "ReadProperty",
                "WriteProperty",
            ],
            "inheritance_type": "Descendents",
            "object_type_guid": None,
            "inherited_object_type_guid": None,
            "mode": "Simulation",
            "execution_policy": "simulation_only",
        },
        "output": {
            "action": "simulate_acl_delegation",
            "mode": "Simulation",
            "simulated": True,
            "write_performed": False,
            "production_authorized": False,
            "ad_write_authorized": False,
            "execution_policy": "simulation_only",
            "target": {
                "dn": TARGET_DN,
                "object_guid": (
                    "8838f739-c817-4b45-"
                    "90b2-b597ce79312a"
                ),
                "name": "test",
                "object_class": (
                    "organizationalUnit"
                ),
            },
            "principal": {
                "name": "GG_IT_Admin",
                "dn": (
                    "CN=GG_IT_Admin,"
                    "OU=Groups,OU=EITAS,"
                    "DC=API,DC=LOCAL"
                ),
                "sid": (
                    "S-1-5-21-1101651174-"
                    "4260486456-3261528239-1118"
                ),
            },
            "ace": {
                "access_control_type": "Allow",
                "rights": [
                    "ReadProperty",
                    "WriteProperty",
                ],
                "rights_mask": 48,
                "inheritance_type": (
                    "Descendents"
                ),
                "inheritance_value": 2,
                "object_type_guid": None,
                "inherited_object_type_guid": None,
            },
        },
    }


def security_job():
    return {
        "id": SECURITY_JOB_ID,
        "action": "get_security_descriptor",
        "status": "completed",
        "success": True,
        "completed_at": (
            "2026-08-09T13:44:10Z"
        ),
        "result": descriptor(),
        "output": descriptor(),
    }


def intent_payload():
    fingerprint = calculate_acl_fingerprint(
        descriptor()
    )

    return {
        "action": "apply_acl_delegation",
        "mode": "Production",
        "object_dn": TARGET_DN,
        "principal_identity": "GG_IT_Admin",
        "access_control_type": "Allow",
        "rights": [
            "ReadProperty",
            "WriteProperty",
        ],
        "inheritance_type": "Descendents",
        "object_type_guid": None,
        "inherited_object_type_guid": None,
        "simulation_job_id": SIMULATION_JOB_ID,
        "security_descriptor_job_id": (
            SECURITY_JOB_ID
        ),
        "expected_acl_fingerprint": fingerprint,
        "confirm_object_dn": TARGET_DN,
        "confirmation_phrase": (
            "APPLY ACL DELEGATION"
        ),
    }


def test_c8_4a2_validates_complete_binding():
    binding = validate_acl_delegation_write_binding(
        intent_payload(),
        simulation_job(),
        security_job(),
    )

    assert binding.binding_validated is True
    assert binding.target_dn == TARGET_DN

    assert binding.target_object_guid == (
        "8838f739-c817-4b45-"
        "90b2-b597ce79312a"
    )

    assert binding.dacl_sddl_sha256 == (
        "a" * 64
    )

    assert binding.principal_sid == (
        "S-1-5-21-1101651174-"
        "4260486456-3261528239-1118"
    )

    assert binding.acl_rule_count == 2

    assert binding.job_creation_authorized is False
    assert binding.runtime_authorized is False
    assert binding.production_authorized is False
    assert binding.ad_write_authorized is False


def test_c8_4a2_fingerprint_is_order_independent():
    first = descriptor()
    second = deepcopy(first)

    second["rules"].reverse()

    assert calculate_acl_fingerprint(
        first
    ) == calculate_acl_fingerprint(second)


def test_c8_4b_fingerprint_detects_native_dacl_change():
    first = descriptor()
    second = deepcopy(first)

    second["dacl_sddl_sha256"] = "b" * 64

    assert calculate_acl_fingerprint(
        first
    ) != calculate_acl_fingerprint(second)


def test_c8_4b_fingerprint_detects_object_guid_change():
    first = descriptor()
    second = deepcopy(first)

    second["object_guid"] = (
        "11111111-2222-4333-"
        "8444-555555555555"
    )

    assert calculate_acl_fingerprint(
        first
    ) != calculate_acl_fingerprint(second)


def test_c8_4b_rejects_missing_simulation_object_guid():
    job = simulation_job()

    job["output"]["target"].pop(
        "object_guid"
    )

    with pytest.raises(
        AclDelegationWriteBindingBadRequest,
        match="simulation.target.object_guid",
    ):
        validate_acl_delegation_write_binding(
            intent_payload(),
            job,
            security_job(),
        )


def test_c8_4b_rejects_target_object_guid_change():
    job = simulation_job()

    job["output"]["target"]["object_guid"] = (
        "11111111-2222-4333-"
        "8444-555555555555"
    )

    with pytest.raises(
        AclDelegationWriteBindingBadRequest,
        match="objectGUID",
    ):
        validate_acl_delegation_write_binding(
            intent_payload(),
            job,
            security_job(),
        )


def test_c8_4a2_right_order_is_canonical():
    first = descriptor()
    second = deepcopy(first)

    second["rules"][1][
        "active_directory_rights"
    ] = "ReadProperty, WriteProperty"

    assert calculate_acl_fingerprint(
        first
    ) == calculate_acl_fingerprint(second)


def test_c8_4a2_ignores_display_metadata():
    first = descriptor()
    second = deepcopy(first)

    second["generated_at"] = (
        "2099-01-01T00:00:00Z"
    )

    second["owner"] = "DISPLAY ONLY"

    second["rules"][0]["identity"] = (
        "DISPLAY CHANGED"
    )

    second["rules"][1][
        "object_type_name"
    ] = "Renamed semantic label"

    assert calculate_acl_fingerprint(
        first
    ) == calculate_acl_fingerprint(second)


@pytest.mark.parametrize(
    "field,new_value",
    [
        (
            "access_control_type",
            "Deny",
        ),
        (
            "active_directory_rights",
            "GenericRead",
        ),
        (
            "inheritance_type",
            "All",
        ),
        (
            "inheritance_flags",
            "ObjectInherit",
        ),
        (
            "propagation_flags",
            "InheritOnly",
        ),
        (
            "is_inherited",
            True,
        ),
        (
            "object_type_guid",
            (
                "bf967a86-0de6-11d0-"
                "a285-00aa003049e2"
            ),
        ),
        (
            "inherited_object_type_guid",
            (
                "bf967a9c-0de6-11d0-"
                "a285-00aa003049e2"
            ),
        ),
    ],
)
def test_c8_4a2_fingerprint_detects_dacl_change(
    field,
    new_value,
):
    first = descriptor()
    second = deepcopy(first)

    second["rules"][0][field] = new_value

    assert calculate_acl_fingerprint(
        first
    ) != calculate_acl_fingerprint(second)


def test_c8_4a2_fingerprint_detects_sid_change():
    first = descriptor()
    second = deepcopy(first)

    second["rules"][0]["sid"] = "S-1-5-18"

    assert calculate_acl_fingerprint(
        first
    ) != calculate_acl_fingerprint(second)


def test_c8_4a2_detects_protection_change():
    first = descriptor()
    second = deepcopy(first)

    second["access_rules_protected"] = True

    assert calculate_acl_fingerprint(
        first
    ) != calculate_acl_fingerprint(second)


def test_c8_4a2_detects_inheritance_state_change():
    first = descriptor()
    second = deepcopy(first)

    second["inheritance_enabled"] = False

    assert calculate_acl_fingerprint(
        first
    ) != calculate_acl_fingerprint(second)


def test_c8_4a2_rejects_changed_rights_after_simulation():
    payload = intent_payload()

    payload["rights"] = [
        "GenericRead",
    ]

    with pytest.raises(
        AclDelegationWriteBindingBadRequest
    ):
        validate_acl_delegation_write_binding(
            payload,
            simulation_job(),
            security_job(),
        )


def test_c8_4a2_rejects_different_target():
    payload = intent_payload()

    payload["object_dn"] = (
        "OU=Other,OU=Users,OU=EITAS,"
        "DC=API,DC=LOCAL"
    )

    payload["confirm_object_dn"] = (
        payload["object_dn"]
    )

    with pytest.raises(
        AclDelegationWriteBindingBadRequest
    ):
        validate_acl_delegation_write_binding(
            payload,
            simulation_job(),
            security_job(),
        )


def test_c8_4a2_rejects_failed_simulation():
    job = simulation_job()
    job["success"] = False

    with pytest.raises(
        AclDelegationWriteBindingBadRequest
    ):
        validate_acl_delegation_write_binding(
            intent_payload(),
            job,
            security_job(),
        )


def test_c8_4a2_rejects_invalid_simulation_invariant():
    job = simulation_job()

    job["output"]["write_performed"] = True

    with pytest.raises(
        AclDelegationWriteBindingBadRequest
    ):
        validate_acl_delegation_write_binding(
            intent_payload(),
            job,
            security_job(),
        )


def test_c8_4a2_rejects_security_read_before_simulation():
    job = security_job()

    job["completed_at"] = (
        "2026-08-09T13:00:00Z"
    )

    with pytest.raises(
        AclDelegationWriteBindingBadRequest
    ):
        validate_acl_delegation_write_binding(
            intent_payload(),
            simulation_job(),
            job,
        )


def test_c8_4a2_rejects_wrong_security_job_id():
    job = security_job()

    job["id"] = (
        "11111111-1111-1111-1111-111111111111"
    )

    with pytest.raises(
        AclDelegationWriteBindingBadRequest
    ):
        validate_acl_delegation_write_binding(
            intent_payload(),
            simulation_job(),
            job,
        )


def test_c8_4a2_rejects_stale_fingerprint():
    payload = intent_payload()

    payload["expected_acl_fingerprint"] = (
        "0" * 64
    )

    with pytest.raises(
        AclDelegationWriteBindingBadRequest
    ):
        validate_acl_delegation_write_binding(
            payload,
            simulation_job(),
            security_job(),
        )


def test_c8_4a2_rejects_non_read_only_descriptor():
    job = security_job()

    job["result"]["read_only"] = False

    with pytest.raises(
        AclDelegationWriteBindingBadRequest
    ):
        validate_acl_delegation_write_binding(
            intent_payload(),
            simulation_job(),
            job,
        )


def test_c8_4a2_remains_dormant():
    admin_source = Path(
        "api/app/services/ad_admin.py"
    ).read_text(encoding="utf-8")

    main_source = Path(
        "api/main.py"
    ).read_text(encoding="utf-8")

    worker_source = Path(
        "agent-windows/modules/EitasAdAdmin.ps1"
    ).read_text(encoding="utf-8")

    frontend_source = "\n".join(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
        for path in Path(
            "frontend/src"
        ).rglob("*")
        if path.is_file()
    )

    for source in (
        admin_source,
        main_source,
        worker_source,
        frontend_source,
    ):
        assert "apply_acl_delegation" not in source


def test_c8_4a2_contains_no_acl_write_primitive():
    source = Path(
        "api/app/services/"
        "acl_delegation_write_binding.py"
    ).read_text(
        encoding="utf-8"
    )

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
        assert token not in source
