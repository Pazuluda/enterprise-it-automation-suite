import json
from pathlib import Path
import tempfile

import pytest

from app.services.ad_admin import (
    ADAdminBadRequest,
    ALLOWED_ACTIONS,
    create_ad_admin_job,
)


ROOT = Path(__file__).resolve().parents[2]

WORKER = (
    ROOT
    / "agent-windows"
    / "modules"
    / "EitasAdAdmin.ps1"
)


def extract_function(
    source: str,
    name: str,
) -> str:
    marker = f"function {name} {{"

    start = source.index(marker)

    end = source.find(
        "\nfunction ",
        start + len(marker),
    )

    if end == -1:
        return source[start:]

    return source[start:end]


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
        "object_type_guid": None,
        "inherited_object_type_guid": None,
        "created_by": "c8.3c1-test",
    }


def create_job(payload: dict):
    with tempfile.TemporaryDirectory() as directory:
        jobs_file = (
            Path(directory)
            / "ad-admin-jobs.json"
        )

        response, audit = create_ad_admin_job(
            jobs_file,
            payload,
        )

        jobs = json.loads(
            jobs_file.read_text(
                encoding="utf-8"
            )
        )

    assert len(jobs) == 1

    return response, audit, jobs[0]


def test_c8_3c1_action_is_enabled():
    assert (
        "simulate_acl_delegation"
        in ALLOWED_ACTIONS
    )


def test_c8_3c1_persists_normalized_simulation_job():
    response, audit, job = create_job(
        valid_payload()
    )

    assert job["action"] == (
        "simulate_acl_delegation"
    )

    assert job["status"] == "pending"

    assert job["payload"] == {
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
        "object_type_guid": None,
        "inherited_object_type_guid": None,
        "mode": "Simulation",
        "execution_policy": "simulation_only",
    }

    assert response["job"]["payload"] == (
        job["payload"]
    )

    assert audit["details"][
        "production_authorized"
    ] is False

    assert audit["details"][
        "ad_write_authorized"
    ] is False

    assert audit["details"][
        "job_persistence_authorized"
    ] is True

    assert audit["details"][
        "runtime_authorized"
    ] is True


def test_c8_3c1_rejects_production_payload():
    payload = valid_payload()
    payload["mode"] = "Production"

    with tempfile.TemporaryDirectory() as directory:
        with pytest.raises(
            ADAdminBadRequest
        ):
            create_ad_admin_job(
                Path(directory)
                / "ad-admin-jobs.json",
                payload,
            )


def test_c8_3c1_rejects_deny():
    payload = valid_payload()
    payload["access_control_type"] = "Deny"

    with tempfile.TemporaryDirectory() as directory:
        with pytest.raises(
            ADAdminBadRequest
        ):
            create_ad_admin_job(
                Path(directory)
                / "ad-admin-jobs.json",
                payload,
            )


def test_c8_3c1_rejects_unapproved_right():
    payload = valid_payload()
    payload["rights"] = [
        "GenericAll",
    ]

    with tempfile.TemporaryDirectory() as directory:
        with pytest.raises(
            ADAdminBadRequest
        ):
            create_ad_admin_job(
                Path(directory)
                / "ad-admin-jobs.json",
                payload,
            )


def test_c8_3c1_worker_dispatches_preview():
    source = WORKER.read_text(
        encoding="utf-8"
    )

    dispatch = extract_function(
        source,
        "Invoke-EitasAdAdminJob",
    )

    assert (
        '"simulate_acl_delegation" {'
        in dispatch
    )

    assert (
        "Invoke-EitasAdAdminAclDelegationSimulationPreview"
        in dispatch
    )


def test_c8_3c1_preview_still_refuses_production():
    source = WORKER.read_text(
        encoding="utf-8"
    )

    preview = extract_function(
        source,
        "Invoke-EitasAdAdminAclDelegationSimulationPreview",
    )

    mode_guard = preview.index(
        '$Mode -ine "Simulation"'
    )

    target_resolution = preview.index(
        "Resolve-EitasAdAdminObject"
    )

    assert mode_guard < target_resolution

    assert (
        "production_authorized = $false"
        in preview
    )

    assert (
        "ad_write_authorized = $false"
        in preview
    )

    assert (
        "write_performed = $false"
        in preview
    )


def test_c8_3c1_has_no_acl_write_primitive():
    source = WORKER.read_text(
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


def test_c8_3c1_uses_existing_ad_admin_rbac_route():
    main_source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '@app.post("/api/ad-admin/jobs")'
        in main_source
    )

    assert (
        "Depends(AD_ACCESS)"
        in main_source
    )

    assert (
        '"ADAdmin"'
        in main_source
    )

    assert (
        '"UltraAdmin"'
        in main_source
    )
