import json

from datetime import (
    datetime,
    timezone,
)

import pytest

from fastapi import (
    HTTPException,
)

import main as api_main

from app.services.ad_admin import (
    ADAdminConflict,
    claim_ad_admin_job,
    get_pending_ad_admin_jobs,
)


GUID = (
    "11111111-2222-3333-4444-555555555555"
)

LIVE_JOB_ID = (
    "22222222-3333-4444-5555-666666666666"
)


def write_candidate_jobs(
    path,
):
    completed_at = (
        datetime.now(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )

    payload = {
        "jobs": [
            {
                "id":
                    "inventory-job-auth-route",

                "action":
                    "get_deleted_objects",

                "status":
                    "completed",

                "success":
                    True,

                "completed_at":
                    completed_at,

                "result": {
                    "recycle_bin": {
                        "enabled":
                            True,
                    },

                    "items": [
                        {
                            "object_guid":
                                GUID,

                            "object_class":
                                "user",

                            "is_deleted":
                                True,

                            "is_recycled":
                                False,

                            "last_known_parent":
                                (
                                    "OU=Users,"
                                    "DC=API,"
                                    "DC=LOCAL"
                                ),

                            "last_known_rdn":
                                "Synthetic User",
                        },
                    ],
                },
            },
            {
                "id":
                    LIVE_JOB_ID,

                "action":
                    (
                        "revalidate_deleted_object_"
                        "preflight"
                    ),

                "status":
                    "completed",

                "success":
                    True,

                "query":
                    GUID,

                "filters":
                    {},

                "completed_at":
                    completed_at,

                "result": {
                    "action":
                        (
                            "revalidate_deleted_object_"
                            "preflight"
                        ),

                    "read_only":
                        True,

                    "live_revalidation_performed":
                        True,

                    "object_found":
                        True,

                    "object_guid":
                        GUID,

                    "object_class":
                        "user",

                    "rdn_attribute":
                        "cn",

                    "is_deleted":
                        True,

                    "is_recycled":
                        False,

                    "recycle_bin_enabled":
                        True,

                    "last_known_parent":
                        (
                            "OU=Users,"
                            "DC=API,"
                            "DC=LOCAL"
                        ),

                    "last_known_rdn":
                        "Synthetic User",

                    "requested_new_name":
                        "",

                    "requested_target_path":
                        "",

                    "effective_new_name":
                        "Synthetic User",

                    "effective_target_path":
                        (
                            "OU=Users,"
                            "DC=API,"
                            "DC=LOCAL"
                        ),

                    "parent_exists":
                        True,

                    "parent_deleted":
                        False,

                    "parent_recycled":
                        False,

                    "collision_probe_performed":
                        True,

                    "target_collision":
                        False,

                    "restore_job_created":
                        False,

                    "restore_implemented":
                        False,

                    "execution_authorized":
                        False,

                    "write_authorized":
                        False,
                },
            },
        ],
    }

    path.write_text(
        json.dumps(
            payload,
        ),
        encoding="utf-8",
    )


def test_authenticated_route_creates_only_prepared_record(
    tmp_path,
    monkeypatch,
):
    ad_admin_jobs = (
        tmp_path
        / "ad-admin-jobs.json"
    )

    ad_explorer_jobs = (
        tmp_path
        / "ad-explorer-jobs.json"
    )

    write_candidate_jobs(
        ad_explorer_jobs
    )

    monkeypatch.setattr(
        api_main,
        "AD_ADMIN_JOBS_FILE",
        ad_admin_jobs,
    )

    monkeypatch.setattr(
        api_main,
        "AD_EXPLORER_JOBS_FILE",
        ad_explorer_jobs,
    )

    monkeypatch.setattr(
        api_main,
        "_eitas_agent_mode_load_config",
        lambda: {
            "mode":
                "Simulation",
        },
    )

    audits = []

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs:
            audits.append(
                dict(kwargs)
            ),
    )

    response = (
        api_main
        .prepare_ad_deleted_object_restore_simulation(
            payload={
                "object_guid":
                    GUID,

                "live_job_id":
                    LIVE_JOB_ID,

                "created_by":
                    "spoofed-client-user",
            },
            identity={
                "preferred_username":
                    "c9-route-test-user",

                "sub":
                    "synthetic-subject",
            },
        )
    )

    job = response["job"]

    assert (
        job["status"]
        == "prepared"
    )

    assert (
        job["type"]
        == "ad_admin"
    )

    assert (
        job["action"]
        == "simulate_deleted_object_restore"
    )

    assert (
        job["created_by"]
        == "c9-route-test-user"
    )

    assert (
        job["created_by"]
        != "spoofed-client-user"
    )

    payload = job["payload"]

    assert (
        payload["created_by"]
        == "c9-route-test-user"
    )

    assert (
        payload["policy_decision"]
        == "candidate_preflight"
    )

    assert (
        payload["preflight_passed"]
        is True
    )

    assert (
        payload["simulation_candidate"]
        is True
    )

    assert (
        payload["worker_claim_authorized"]
        is False
    )

    assert (
        payload["worker_runtime_authorized"]
        is False
    )

    assert (
        payload["restore_cmdlet_authorized"]
        is False
    )

    assert (
        payload["restore_whatif_authorized"]
        is False
    )

    assert (
        payload["execution_authorized"]
        is False
    )

    assert (
        payload["write_authorized"]
        is False
    )

    persisted = json.loads(
        ad_admin_jobs.read_text(
            encoding="utf-8"
        )
    )

    assert len(persisted) == 1

    assert (
        persisted[0]["id"]
        == job["id"]
    )

    pending = (
        get_pending_ad_admin_jobs(
            ad_admin_jobs
        )
    )

    assert all(
        candidate.get("id")
        != job["id"]
        for candidate in pending.get(
            "jobs",
            [],
        )
    )

    with pytest.raises(
        ADAdminConflict
    ):
        claim_ad_admin_job(
            ad_admin_jobs,
            job["id"],
            {
                "claimed_by":
                    "synthetic-worker",
            },
        )

    assert len(audits) == 1

    assert (
        audits[0]["actor"]
        == "c9-route-test-user"
    )

    assert (
        audits[0]["details"][
            "status"
        ]
        == "prepared"
    )

    assert (
        audits[0]["details"][
            "worker_claim_authorized"
        ]
        is False
    )

    assert (
        audits[0]["details"][
            "worker_runtime_authorized"
        ]
        is False
    )


def test_production_mode_is_rejected_before_persistence(
    tmp_path,
    monkeypatch,
):
    ad_admin_jobs = (
        tmp_path
        / "ad-admin-jobs.json"
    )

    ad_explorer_jobs = (
        tmp_path
        / "ad-explorer-jobs.json"
    )

    write_candidate_jobs(
        ad_explorer_jobs
    )

    monkeypatch.setattr(
        api_main,
        "AD_ADMIN_JOBS_FILE",
        ad_admin_jobs,
    )

    monkeypatch.setattr(
        api_main,
        "AD_EXPLORER_JOBS_FILE",
        ad_explorer_jobs,
    )

    monkeypatch.setattr(
        api_main,
        "_eitas_agent_mode_load_config",
        lambda: {
            "mode":
                "Production",
        },
    )

    audits = []

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs:
            audits.append(
                dict(kwargs)
            ),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        (
            api_main
            .prepare_ad_deleted_object_restore_simulation(
                payload={
                    "object_guid":
                        GUID,

                    "live_job_id":
                        LIVE_JOB_ID,
                },
                identity={
                    "preferred_username":
                        "c9-route-test-user",
                },
            )
        )

    assert (
        captured.value.status_code
        == 400
    )

    if ad_admin_jobs.exists():
        persisted = json.loads(
            ad_admin_jobs.read_text(
                encoding="utf-8"
            )
        )

        assert persisted == []

    assert audits == []


def test_authenticated_actor_uses_subject_fallback():
    identity = {
        "sub":
            "subject-only-user",
    }

    assert (
        api_main
        ._c9_authenticated_actor(
            identity
        )
        == "subject-only-user"
    )
