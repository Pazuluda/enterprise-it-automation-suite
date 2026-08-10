import json
from copy import deepcopy
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

import pytest

from app.services.acl_delegation_production_preparation import (
    ACL_DELEGATION_PRODUCTION_PREPARATION_CONTRACT_VERSION,
    AclDelegationProductionPreparationError,
    prepare_acl_delegation_production_evidence,
)
from app.services.acl_delegation_write_binding import (
    calculate_acl_fingerprint,
)


NOW = datetime(
    2026,
    8,
    10,
    8,
    0,
    0,
    tzinfo=timezone.utc,
)

TARGET_DN = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

SIMULATION_JOB_ID = (
    "11111111-1111-4111-"
    "8111-111111111111"
)

SECURITY_JOB_ID = (
    "22222222-2222-4222-"
    "8222-222222222222"
)

TARGET_GUID = (
    "8838f739-c817-4b45-"
    "90b2-b597ce79312a"
)

PRINCIPAL_SID = (
    "S-1-5-21-1101651174-"
    "4260486456-3261528239-1118"
)


def descriptor():
    return {
        "action": (
            "get_security_descriptor"
        ),
        "object_dn": TARGET_DN,
        "object_guid": TARGET_GUID,

        "dacl_fingerprint_version": (
            "sddl-access-sha256-v1"
        ),
        "dacl_sddl_sha256": (
            "3" * 64
        ),

        "read_only": True,
        "sacl_included": False,

        "inheritance_enabled": True,
        "access_rules_protected": False,

        "generated_at": (
            "2026-08-10T07:59:58Z"
        ),

        "owner": (
            "API\\Admins du domaine"
        ),
        "owner_sid": (
            "S-1-5-21-1-2-3-512"
        ),

        "rules": [
            {
                "identity": (
                    "API\\Admins du domaine"
                ),
                "sid": (
                    "S-1-5-21-1-2-3-512"
                ),
                "access_control_type": (
                    "Allow"
                ),
                "active_directory_rights": (
                    "GenericAll"
                ),
                "inheritance_type": (
                    "None"
                ),
                "inheritance_flags": (
                    "None"
                ),
                "propagation_flags": (
                    "None"
                ),
                "is_inherited": False,
                "object_type_guid": (
                    "00000000-0000-0000-"
                    "0000-000000000000"
                ),
                "inherited_object_type_guid": (
                    "00000000-0000-0000-"
                    "0000-000000000000"
                ),
            },
            {
                "identity": (
                    "Tout le monde"
                ),
                "sid": "S-1-1-0",
                "access_control_type": (
                    "Deny"
                ),
                "active_directory_rights": (
                    "WriteProperty, ReadProperty"
                ),
                "inheritance_type": (
                    "Descendents"
                ),
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
                "inherited_object_type_guid": (
                    "bf967aba-0de6-11d0-"
                    "a285-00aa003049e2"
                ),
            },
        ],
    }


def simulation_job():
    return {
        "id": SIMULATION_JOB_ID,
        "action": (
            "simulate_acl_delegation"
        ),
        "status": "completed",
        "success": True,

        "completed_at": (
            NOW
            - timedelta(
                seconds=20
            )
        ).isoformat(),

        "payload": {
            "object_dn": TARGET_DN,
            "principal_identity": (
                "GG_IT_Admin"
            ),
            "access_control_type": (
                "Allow"
            ),
            "rights": [
                "ReadProperty",
                "WriteProperty",
            ],
            "inheritance_type": (
                "Descendents"
            ),
            "object_type_guid": None,
            "inherited_object_type_guid": (
                None
            ),
            "mode": "Simulation",
            "execution_policy": (
                "simulation_only"
            ),
        },

        "output": {
            "action": (
                "simulate_acl_delegation"
            ),
            "mode": "Simulation",
            "simulated": True,

            "write_performed": False,
            "production_authorized": (
                False
            ),
            "ad_write_authorized": False,

            "execution_policy": (
                "simulation_only"
            ),

            "target": {
                "dn": TARGET_DN,
                "object_guid": (
                    TARGET_GUID
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
                "sid": PRINCIPAL_SID,
            },

            "ace": {
                "access_control_type": (
                    "Allow"
                ),
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
                "inherited_object_type_guid": (
                    None
                ),
            },
        },
    }


def security_job():
    value = descriptor()

    return {
        "id": SECURITY_JOB_ID,
        "action": (
            "get_security_descriptor"
        ),
        "status": "completed",
        "success": True,

        "completed_at": (
            NOW
            - timedelta(
                seconds=5
            )
        ).isoformat(),

        "result": deepcopy(
            value
        ),
        "output": deepcopy(
            value
        ),
    }


def write_jobs(
    tmp_path,
    *,
    simulation=None,
    security=None,
):
    admin_path = (
        tmp_path
        / "ad-admin-jobs.json"
    )

    explorer_path = (
        tmp_path
        / "ad-explorer-jobs.json"
    )

    admin_path.write_text(
        json.dumps([
            (
                simulation
                if simulation is not None
                else simulation_job()
            )
        ]),
        encoding="utf-8",
    )

    explorer_path.write_text(
        json.dumps([
            (
                security
                if security is not None
                else security_job()
            )
        ]),
        encoding="utf-8",
    )

    return (
        admin_path,
        explorer_path,
    )


def prepare(
    tmp_path,
    *,
    now=NOW,
):
    (
        admin_path,
        explorer_path,
    ) = write_jobs(
        tmp_path
    )

    return (
        prepare_acl_delegation_production_evidence(
            ad_admin_jobs_file=(
                admin_path
            ),
            ad_explorer_jobs_file=(
                explorer_path
            ),
            payload={
                "simulation_job_id": (
                    SIMULATION_JOB_ID
                ),
                "security_descriptor_job_id": (
                    SECURITY_JOB_ID
                ),
            },
            now=now,
        )
    )


def test_a3b2b1_prepares_server_fingerprint(
    tmp_path,
):
    result = prepare(
        tmp_path
    )

    assert result.contract_version == (
        ACL_DELEGATION_PRODUCTION_PREPARATION_CONTRACT_VERSION
    )

    assert result.state == (
        "production_preparation_dormant"
    )

    assert result.acl_fingerprint == (
        calculate_acl_fingerprint(
            descriptor()
        )
    )

    assert len(
        result.acl_fingerprint
    ) == 64

    assert result.target_dn == TARGET_DN

    assert (
        result.target_object_guid
        == TARGET_GUID
    )

    assert (
        result.principal_sid
        == PRINCIPAL_SID
    )


def test_a3b2b1_uses_trusted_server_binding(
    tmp_path,
):
    result = prepare(
        tmp_path
    )

    assert (
        result.trusted_source
        == "server_job_storage"
    )

    assert (
        result.trusted_evidence_loaded
        is True
    )

    assert (
        result.binding_validated
        is True
    )

    assert (
        result.simulation_job_id
        == SIMULATION_JOB_ID
    )

    assert (
        result.security_descriptor_job_id
        == SECURITY_JOB_ID
    )

    assert len(
        result.evidence_digest
    ) == 64


def test_a3b2b1_does_not_validate_human_confirmation(
    tmp_path,
):
    result = prepare(
        tmp_path
    )

    assert (
        result.required_confirm_object_dn
        == TARGET_DN
    )

    assert (
        result.required_confirmation_phrase
        == "APPLY ACL DELEGATION"
    )

    assert (
        result.human_confirmation_validated
        is False
    )

    assert result.claim_created is False
    assert result.replay_consumed is False


def test_a3b2b1_never_authorizes_write(
    tmp_path,
):
    result = prepare(
        tmp_path
    )

    assert {
        result.job_creation_authorized,
        result.runtime_authorized,
        result.production_authorized,
        result.ad_write_authorized,
    } == {
        False,
    }


def test_a3b2b1_rejects_client_fingerprint_injection(
    tmp_path,
):
    (
        admin_path,
        explorer_path,
    ) = write_jobs(
        tmp_path
    )

    with pytest.raises(
        AclDelegationProductionPreparationError,
        match="interdits",
    ):
        prepare_acl_delegation_production_evidence(
            ad_admin_jobs_file=(
                admin_path
            ),
            ad_explorer_jobs_file=(
                explorer_path
            ),
            payload={
                "simulation_job_id": (
                    SIMULATION_JOB_ID
                ),
                "security_descriptor_job_id": (
                    SECURITY_JOB_ID
                ),
                "expected_acl_fingerprint": (
                    "0" * 64
                ),
            },
            now=NOW,
        )


def test_a3b2b1_rejects_stale_descriptor(
    tmp_path,
):
    stale_simulation = simulation_job()

    stale_simulation["completed_at"] = (
        NOW
        - timedelta(
            seconds=180
        )
    ).isoformat()

    stale = security_job()

    stale["completed_at"] = (
        NOW
        - timedelta(
            seconds=121
        )
    ).isoformat()

    (
        admin_path,
        explorer_path,
    ) = write_jobs(
        tmp_path,
        simulation=stale_simulation,
        security=stale,
    )

    with pytest.raises(
        AclDelegationProductionPreparationError,
        match="Security Descriptor trop ancien",
    ):
        prepare_acl_delegation_production_evidence(
            ad_admin_jobs_file=(
                admin_path
            ),
            ad_explorer_jobs_file=(
                explorer_path
            ),
            payload={
                "simulation_job_id": (
                    SIMULATION_JOB_ID
                ),
                "security_descriptor_job_id": (
                    SECURITY_JOB_ID
                ),
            },
            now=NOW,
        )


def test_a3b2b1_rejects_non_read_only_descriptor(
    tmp_path,
):
    invalid = security_job()

    invalid["result"][
        "read_only"
    ] = False

    invalid["output"][
        "read_only"
    ] = False

    (
        admin_path,
        explorer_path,
    ) = write_jobs(
        tmp_path,
        security=invalid,
    )

    with pytest.raises(
        AclDelegationProductionPreparationError,
        match="read-only",
    ):
        prepare_acl_delegation_production_evidence(
            ad_admin_jobs_file=(
                admin_path
            ),
            ad_explorer_jobs_file=(
                explorer_path
            ),
            payload={
                "simulation_job_id": (
                    SIMULATION_JOB_ID
                ),
                "security_descriptor_job_id": (
                    SECURITY_JOB_ID
                ),
            },
            now=NOW,
        )


def test_a3b2b1_contains_no_runtime_or_write_path():
    source = Path(
        "api/app/services/"
        "acl_delegation_production_preparation.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "claim_acl_delegation_write_intent(",
        "persist_acl_delegation_production_confirmation(",
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
