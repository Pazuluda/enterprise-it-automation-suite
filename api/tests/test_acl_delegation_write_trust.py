import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.acl_delegation_write_binding import (
    calculate_acl_fingerprint,
)
from app.services.acl_delegation_write_trust import (
    AclDelegationWriteTrustBadRequest,
    resolve_trusted_acl_delegation_write_evidence,
)


TARGET_DN = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

SIMULATION_JOB_ID = (
    "7bf650bd-7799-499f-8e42-9973af0b6b0c"
)

SECURITY_JOB_ID = (
    "d519800a-0ccb-4a61-aab9-6c45c57fd190"
)

NOW = datetime(
    2026,
    8,
    9,
    14,
    39,
    0,
    tzinfo=timezone.utc,
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
        "rules": [
            {
                "identity": "API\\Admins du domaine",
                "sid": "S-1-5-21-1-2-3-512",
                "access_control_type": "Allow",
                "active_directory_rights": "GenericAll",
                "inheritance_type": "None",
                "inheritance_flags": "None",
                "propagation_flags": "None",
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
        ],
    }


def simulation_job():
    return {
        "id": SIMULATION_JOB_ID,
        "action": "simulate_acl_delegation",
        "status": "completed",
        "success": True,
        "completed_at": (
            "2026-08-09T14:30:00Z"
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
            },
            "principal": {
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
                "inheritance_type": "Descendents",
                "inheritance_value": 2,
                "object_type_guid": None,
                "inherited_object_type_guid": None,
            },
        },
    }


def security_job():
    value = descriptor()

    return {
        "id": SECURITY_JOB_ID,
        "action": "get_security_descriptor",
        "status": "completed",
        "success": True,
        "completed_at": (
            "2026-08-09T14:38:30Z"
        ),
        "output": deepcopy(value),
        "result": deepcopy(value),
    }


def intent_payload():
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
        "expected_acl_fingerprint": (
            calculate_acl_fingerprint(
                descriptor()
            )
        ),
        "confirm_object_dn": TARGET_DN,
        "confirmation_phrase": (
            "APPLY ACL DELEGATION"
        ),
    }


def write_stores(
    tmp_path,
    simulation=None,
    security=None,
):
    admin_file = tmp_path / "ad-admin-jobs.json"
    explorer_file = (
        tmp_path / "ad-explorer-jobs.json"
    )

    admin_file.write_text(
        json.dumps([
            simulation
            if simulation is not None
            else simulation_job()
        ]),
        encoding="utf-8",
    )

    explorer_file.write_text(
        json.dumps([
            security
            if security is not None
            else security_job()
        ]),
        encoding="utf-8",
    )

    return admin_file, explorer_file


def resolve(tmp_path, payload=None, now=NOW):
    admin_file, explorer_file = write_stores(
        tmp_path
    )

    return (
        resolve_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=admin_file,
            ad_explorer_jobs_file=explorer_file,
            intent_payload=(
                payload
                if payload is not None
                else intent_payload()
            ),
            now=now,
        )
    )


def test_c8_4b1_loads_only_server_evidence(
    tmp_path,
):
    evidence = resolve(tmp_path)

    assert evidence.trusted_source == (
        "server_job_storage"
    )

    assert evidence.trusted_evidence_loaded is True
    assert evidence.binding_validated is True

    assert evidence.simulation_job_id == (
        SIMULATION_JOB_ID
    )

    assert (
        evidence.security_descriptor_job_id
        == SECURITY_JOB_ID
    )

    assert len(evidence.evidence_digest) == 64


def test_c8_4b1_remains_non_authorizing(
    tmp_path,
):
    evidence = resolve(tmp_path)

    assert evidence.job_creation_authorized is False
    assert evidence.runtime_authorized is False
    assert evidence.production_authorized is False
    assert evidence.ad_write_authorized is False


@pytest.mark.parametrize(
    "field",
    [
        "simulation_job",
        "security_descriptor_job",
        "security_descriptor",
        "binding",
        "principal_sid",
        "trusted_evidence",
        "job_creation_authorized",
        "runtime_authorized",
        "production_authorized",
        "ad_write_authorized",
        "created_by",
    ],
)
def test_c8_4b1_rejects_client_supplied_evidence(
    tmp_path,
    field,
):
    payload = intent_payload()
    payload[field] = {"forged": True}

    with pytest.raises(
        AclDelegationWriteTrustBadRequest
    ):
        resolve(tmp_path, payload)


def test_c8_4b1_rejects_missing_simulation(
    tmp_path,
):
    admin_file = tmp_path / "ad-admin-jobs.json"
    explorer_file = (
        tmp_path / "ad-explorer-jobs.json"
    )

    admin_file.write_text(
        "[]",
        encoding="utf-8",
    )

    explorer_file.write_text(
        json.dumps([security_job()]),
        encoding="utf-8",
    )

    with pytest.raises(
        AclDelegationWriteTrustBadRequest
    ):
        resolve_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=admin_file,
            ad_explorer_jobs_file=explorer_file,
            intent_payload=intent_payload(),
            now=NOW,
        )


def test_c8_4b1_rejects_duplicate_simulation_id(
    tmp_path,
):
    admin_file = tmp_path / "ad-admin-jobs.json"
    explorer_file = (
        tmp_path / "ad-explorer-jobs.json"
    )

    job = simulation_job()

    admin_file.write_text(
        json.dumps([
            job,
            deepcopy(job),
        ]),
        encoding="utf-8",
    )

    explorer_file.write_text(
        json.dumps([security_job()]),
        encoding="utf-8",
    )

    with pytest.raises(
        AclDelegationWriteTrustBadRequest
    ):
        resolve_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=admin_file,
            ad_explorer_jobs_file=explorer_file,
            intent_payload=intent_payload(),
            now=NOW,
        )


def test_c8_4b1_rejects_missing_security_read(
    tmp_path,
):
    admin_file = tmp_path / "ad-admin-jobs.json"
    explorer_file = (
        tmp_path / "ad-explorer-jobs.json"
    )

    admin_file.write_text(
        json.dumps([simulation_job()]),
        encoding="utf-8",
    )

    explorer_file.write_text(
        "[]",
        encoding="utf-8",
    )

    with pytest.raises(
        AclDelegationWriteTrustBadRequest
    ):
        resolve_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=admin_file,
            ad_explorer_jobs_file=explorer_file,
            intent_payload=intent_payload(),
            now=NOW,
        )


def test_c8_4b1_rejects_same_storage_file(
    tmp_path,
):
    path = tmp_path / "jobs.json"

    path.write_text(
        json.dumps([
            simulation_job(),
            security_job(),
        ]),
        encoding="utf-8",
    )

    with pytest.raises(
        AclDelegationWriteTrustBadRequest
    ):
        resolve_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=path,
            ad_explorer_jobs_file=path,
            intent_payload=intent_payload(),
            now=NOW,
        )


def test_c8_4b1_rejects_stale_simulation(
    tmp_path,
):
    simulation = simulation_job()

    simulation["completed_at"] = (
        "2026-08-09T14:00:00Z"
    )

    admin_file, explorer_file = write_stores(
        tmp_path,
        simulation=simulation,
    )

    with pytest.raises(
        AclDelegationWriteTrustBadRequest,
        match="Simulation ACL trop ancien",
    ):
        resolve_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=admin_file,
            ad_explorer_jobs_file=explorer_file,
            intent_payload=intent_payload(),
            now=NOW,
        )


def test_c8_4b1_rejects_stale_security_read(
    tmp_path,
):
    security = security_job()

    security["completed_at"] = (
        "2026-08-09T14:35:00Z"
    )

    admin_file, explorer_file = write_stores(
        tmp_path,
        security=security,
    )

    with pytest.raises(
        AclDelegationWriteTrustBadRequest,
        match="Security Descriptor trop ancien",
    ):
        resolve_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=admin_file,
            ad_explorer_jobs_file=explorer_file,
            intent_payload=intent_payload(),
            now=NOW,
        )


def test_c8_4b1_rejects_future_security_read(
    tmp_path,
):
    security = security_job()

    security["completed_at"] = (
        "2026-08-09T14:40:00Z"
    )

    admin_file, explorer_file = write_stores(
        tmp_path,
        security=security,
    )

    with pytest.raises(
        AclDelegationWriteTrustBadRequest,
        match="Security Descriptor date dans le futur",
    ):
        resolve_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=admin_file,
            ad_explorer_jobs_file=explorer_file,
            intent_payload=intent_payload(),
            now=NOW,
        )


def test_c8_4b1_rejects_tampered_simulation(
    tmp_path,
):
    simulation = simulation_job()

    simulation["output"]["write_performed"] = True

    admin_file, explorer_file = write_stores(
        tmp_path,
        simulation=simulation,
    )

    with pytest.raises(
        AclDelegationWriteTrustBadRequest
    ):
        resolve_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=admin_file,
            ad_explorer_jobs_file=explorer_file,
            intent_payload=intent_payload(),
            now=NOW,
        )


def test_c8_4b1_rejects_tampered_descriptor(
    tmp_path,
):
    security = security_job()

    security["result"]["object_dn"] = (
        "OU=Other,OU=Users,OU=EITAS,"
        "DC=API,DC=LOCAL"
    )

    admin_file, explorer_file = write_stores(
        tmp_path,
        security=security,
    )

    with pytest.raises(
        AclDelegationWriteTrustBadRequest
    ):
        resolve_trusted_acl_delegation_write_evidence(
            ad_admin_jobs_file=admin_file,
            ad_explorer_jobs_file=explorer_file,
            intent_payload=intent_payload(),
            now=NOW,
        )


def test_c8_4b1_digest_is_deterministic(
    tmp_path,
):
    first = resolve(tmp_path)

    second = resolve(tmp_path)

    assert (
        first.evidence_digest
        == second.evidence_digest
    )



def test_c8_4b1_runtime_exposure_stays_closed():
    admin_source = Path(
        "api/app/services/ad_admin.py"
    ).read_text(
        encoding="utf-8"
    )

    main_source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    worker_source = Path(
        "agent-windows/modules/"
        "EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8"
    )

    frontend_source = Path(
        "frontend/src/features/"
        "active-directory/"
        "AdExplorerPage.jsx"
    ).read_text(
        encoding="utf-8"
    )

    # The C8.4D React intent is structural only.
    # Generic backend and Windows runtime exposure
    # must still remain completely closed.
    assert "apply_acl_delegation" not in admin_source
    assert "apply_acl_delegation" not in main_source
    assert "apply_acl_delegation" not in worker_source

    assert (
        'action: "apply_acl_delegation"'
        in frontend_source
    )

    assert (
        '"write-intent/identity-envelope"'
        in frontend_source
    )

    assert (
        '"write-intent/claim"'
        in frontend_source
    )

    assert (
        '"prewrite-ticket"'
        in frontend_source
    )

    assert (
        '"prewrite-status/"'
        in frontend_source
    )

    assert (
        "/api/agent/acl-delegation/prewrite/"
        not in frontend_source
    )



def test_c8_4b1_contains_no_acl_write_primitive():
    source = Path(
        "api/app/services/"
        "acl_delegation_write_trust.py"
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
