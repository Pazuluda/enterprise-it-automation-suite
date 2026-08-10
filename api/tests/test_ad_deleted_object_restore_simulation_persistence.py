import json

from pathlib import Path

import pytest

import app.services.ad_deleted_object_restore_simulation_persistence as persistence

from app.services.ad_admin import (
    ADAdminConflict,
    claim_ad_admin_job,
    get_pending_ad_admin_jobs,
)


GUID = (
    "11111111-2222-3333-4444-555555555555"
)


def safe_envelope():
    return {
        "contract_version":
            "c9.2b-v1",

        "action":
            "simulate_deleted_object_restore",

        "mode":
            "Simulation",

        "created_by":
            "unit-test",

        "object_guid":
            GUID,

        "live_job_id":
            "live-job-1",

        "source_inventory_job_id":
            "inventory-job-1",

        "live_job_completed_at":
            "2026-08-10T12:00:00Z",

        "requested_new_name":
            "",

        "requested_target_path":
            "",

        "effective_new_name":
            "Future User",

        "effective_target_path":
            "OU=Users,DC=API,DC=LOCAL",

        "object_class":
            "user",

        "class_policy":
            "standard_controlled",

        "manual_review_required":
            False,

        "policy_decision":
            "candidate_preflight",

        "preflight_passed":
            True,

        "simulation_candidate":
            True,

        "simulation_job_authorized":
            True,

        "simulation_job_persistence_authorized":
            True,

        "restore_cmdlet_authorized":
            False,

        "restore_whatif_authorized":
            False,

        "execution_authorized":
            False,

        "write_authorized":
            False,

        "restore_implemented":
            False,

        "restore_performed":
            False,
    }


def install_safe_prepare(
    monkeypatch,
    envelope=None,
):
    if envelope is None:
        envelope = safe_envelope()

    monkeypatch.setattr(
        persistence,
        "prepare_deleted_object_restore_simulation",
        lambda *args, **kwargs: dict(
            envelope
        ),
    )


def test_persists_restore_simulation_as_prepared(
    tmp_path,
    monkeypatch,
):
    install_safe_prepare(
        monkeypatch
    )

    ad_jobs = (
        tmp_path
        / "ad-admin-jobs.json"
    )

    deleted_jobs = (
        tmp_path
        / "deleted-jobs.json"
    )

    response, audit = (
        persistence
        .create_deleted_object_restore_simulation_record(
            ad_jobs,
            deleted_jobs,
            {
                "object_guid":
                    GUID,

                "live_job_id":
                    "live-job-1",

                "created_by":
                    "unit-test",
            },
            agent_mode="Simulation",
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
        job["payload"][
            "worker_claim_authorized"
        ]
        is False
    )

    assert (
        job["payload"][
            "worker_runtime_authorized"
        ]
        is False
    )

    assert (
        job["payload"][
            "execution_authorized"
        ]
        is False
    )

    assert (
        job["payload"][
            "write_authorized"
        ]
        is False
    )

    persisted = json.loads(
        ad_jobs.read_text(
            encoding="utf-8"
        )
    )

    assert len(persisted) == 1
    assert persisted[0]["id"] == job["id"]

    assert (
        audit["details"]["status"]
        == "prepared"
    )


def test_prepared_restore_job_not_returned_as_pending(
    tmp_path,
    monkeypatch,
):
    install_safe_prepare(
        monkeypatch
    )

    ad_jobs = (
        tmp_path
        / "ad-admin-jobs.json"
    )

    deleted_jobs = (
        tmp_path
        / "deleted-jobs.json"
    )

    response, _ = (
        persistence
        .create_deleted_object_restore_simulation_record(
            ad_jobs,
            deleted_jobs,
            {},
            agent_mode="Simulation",
        )
    )

    job_id = response["job"]["id"]

    pending = get_pending_ad_admin_jobs(
        ad_jobs
    )

    assert all(
        job.get("id") != job_id
        for job in pending.get(
            "jobs",
            [],
        )
    )


def test_prepared_restore_job_cannot_be_claimed(
    tmp_path,
    monkeypatch,
):
    install_safe_prepare(
        monkeypatch
    )

    ad_jobs = (
        tmp_path
        / "ad-admin-jobs.json"
    )

    deleted_jobs = (
        tmp_path
        / "deleted-jobs.json"
    )

    response, _ = (
        persistence
        .create_deleted_object_restore_simulation_record(
            ad_jobs,
            deleted_jobs,
            {},
            agent_mode="Simulation",
        )
    )

    job_id = response["job"]["id"]

    with pytest.raises(
        ADAdminConflict
    ):
        claim_ad_admin_job(
            ad_jobs,
            job_id,
            {
                "claimed_by":
                    "unit-test-worker",
            },
        )


def test_authorizing_envelope_is_rejected(
    tmp_path,
    monkeypatch,
):
    envelope = safe_envelope()

    envelope[
        "execution_authorized"
    ] = True

    install_safe_prepare(
        monkeypatch,
        envelope,
    )

    with pytest.raises(
        persistence
        .DeletedObjectRestoreSimulationPersistenceError
    ):
        persistence.create_deleted_object_restore_simulation_record(
            tmp_path
            / "ad-admin-jobs.json",

            tmp_path
            / "deleted-jobs.json",

            {},

            agent_mode="Simulation",
        )


def test_runtime_capabilities_remain_disabled():
    assert (
        persistence
        .DELETED_OBJECT_RESTORE_SIMULATION_WORKER_CLAIM_ENABLED
        is False
    )

    assert (
        persistence
        .DELETED_OBJECT_RESTORE_SIMULATION_WORKER_RUNTIME_ENABLED
        is False
    )

    assert (
        persistence
        .DELETED_OBJECT_RESTORE_SIMULATION_PRODUCTION_ENABLED
        is False
    )

    assert (
        persistence
        .DELETED_OBJECT_RESTORE_SIMULATION_AD_WRITE_ENABLED
        is False
    )


def test_generic_and_windows_runtime_do_not_know_restore_action():
    root = Path(
        __file__
    ).resolve().parents[2]

    ad_admin = (
        root
        / "api"
        / "app"
        / "services"
        / "ad_admin.py"
    ).read_text(
        encoding="utf-8"
    )

    main = (
        root
        / "api"
        / "main.py"
    ).read_text(
        encoding="utf-8"
    )

    windows = (
        root
        / "agent-windows"
        / "modules"
        / "EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8-sig",
        errors="replace",
    )

    action = (
        "simulate_deleted_object_restore"
    )

    assert action not in ad_admin
    assert action not in main

    dispatch_marker = (
        "function Invoke-EitasAdAdminJob {"
    )

    dispatch_start = windows.index(
        dispatch_marker
    )

    dispatch_end = windows.find(
        "\nfunction ",
        dispatch_start
        + len(dispatch_marker),
    )

    if dispatch_end == -1:
        dispatcher = windows[
            dispatch_start:
        ]
    else:
        dispatcher = windows[
            dispatch_start:dispatch_end
        ]

    assert action not in dispatcher
