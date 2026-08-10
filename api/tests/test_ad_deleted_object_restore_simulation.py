import json

from datetime import (
    datetime,
    timezone,
)

from app.services.ad_deleted_object_restore_simulation import (
    DELETED_OBJECT_RESTORE_SIMULATION_CMDLET_ENABLED,
    DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_ENABLED,
    DeletedObjectRestoreSimulationBadRequest,
    prepare_deleted_object_restore_simulation,
)


GUID = (
    "11111111-2222-3333-4444-555555555555"
)


def write_candidate_jobs(
    path,
    *,
    recycled=False,
    live_job_id="live-job-1",
    live_filters=None,
):
    if live_filters is None:
        live_filters = {}

    completed_at = datetime.now(
        timezone.utc
    ).isoformat()

    new_name = str(
        live_filters.get("new_name")
        or ""
    )

    target_path = str(
        live_filters.get("target_path")
        or ""
    )

    inventory_item = {
        "object_guid":
            GUID,

        "object_class":
            "user",

        "is_deleted":
            True,

        "is_recycled":
            recycled,

        "last_known_parent":
            "OU=Users,DC=API,DC=LOCAL",

        "last_known_rdn":
            "Future User",
    }

    live_result = {
        "action":
            "revalidate_deleted_object_preflight",

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
            recycled,

        "recycle_bin_enabled":
            True,

        "last_known_parent":
            "OU=Users,DC=API,DC=LOCAL",

        "last_known_rdn":
            "Future User",

        "requested_new_name":
            new_name,

        "requested_target_path":
            target_path,

        "effective_new_name":
            (
                new_name
                or "Future User"
            ),

        "effective_target_path":
            (
                target_path
                or "OU=Users,DC=API,DC=LOCAL"
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
    }

    payload = {
        "jobs": [
            {
                "id":
                    "inventory-job-1",

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
                        inventory_item,
                    ],
                },
            },
            {
                "id":
                    live_job_id,

                "action":
                    "revalidate_deleted_object_preflight",

                "status":
                    "completed",

                "success":
                    True,

                "query":
                    GUID,

                "filters":
                    live_filters,

                "completed_at":
                    completed_at,

                "result":
                    live_result,
            },
        ],
    }

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_candidate_prepares_locked_simulation_envelope(
    tmp_path,
):
    jobs = tmp_path / "jobs.json"

    write_candidate_jobs(
        jobs
    )

    envelope = (
        prepare_deleted_object_restore_simulation(
            jobs,
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

    assert (
        envelope["action"]
        == "simulate_deleted_object_restore"
    )

    assert (
        envelope["mode"]
        == "Simulation"
    )

    assert (
        envelope["policy_decision"]
        == "candidate_preflight"
    )

    assert (
        envelope["preflight_passed"]
        is True
    )

    assert (
        envelope["simulation_candidate"]
        is True
    )

    assert (
        envelope["simulation_job_authorized"]
        is True
    )

    assert (
        envelope[
            "simulation_job_persistence_authorized"
        ]
        is True
    )

    assert (
        envelope["restore_cmdlet_authorized"]
        is False
    )

    assert (
        envelope["restore_whatif_authorized"]
        is False
    )

    assert (
        envelope["execution_authorized"]
        is False
    )

    assert (
        envelope["write_authorized"]
        is False
    )


def test_non_simulation_mode_is_rejected(
    tmp_path,
):
    jobs = tmp_path / "jobs.json"

    write_candidate_jobs(
        jobs
    )

    try:
        prepare_deleted_object_restore_simulation(
            jobs,
            {
                "object_guid":
                    GUID,

                "live_job_id":
                    "live-job-1",

                "created_by":
                    "unit-test",
            },
            agent_mode="Production",
        )
    except DeletedObjectRestoreSimulationBadRequest as exc:
        assert (
            "mode Simulation"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Production devait être refusé"
        )


def test_recycled_object_is_rejected(
    tmp_path,
):
    jobs = tmp_path / "jobs.json"

    write_candidate_jobs(
        jobs,
        recycled=True,
    )

    try:
        prepare_deleted_object_restore_simulation(
            jobs,
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
    except DeletedObjectRestoreSimulationBadRequest as exc:
        assert (
            "blocked_recycled"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Objet recyclé devait être refusé"
        )


def test_unknown_live_job_is_rejected(
    tmp_path,
):
    jobs = tmp_path / "jobs.json"

    write_candidate_jobs(
        jobs
    )

    try:
        prepare_deleted_object_restore_simulation(
            jobs,
            {
                "object_guid":
                    GUID,

                "live_job_id":
                    "unknown-live-job",

                "created_by":
                    "unit-test",
            },
            agent_mode="Simulation",
        )
    except DeletedObjectRestoreSimulationBadRequest as exc:
        assert (
            "introuvable"
            in str(exc).lower()
            or
            "not found"
            in str(exc).lower()
        )
    else:
        raise AssertionError(
            "Job live inconnu devait être refusé"
        )


def test_changed_name_breaks_live_binding(
    tmp_path,
):
    jobs = tmp_path / "jobs.json"

    write_candidate_jobs(
        jobs,
        live_filters={
            "new_name":
                "Name A",
        },
    )

    try:
        prepare_deleted_object_restore_simulation(
            jobs,
            {
                "object_guid":
                    GUID,

                "live_job_id":
                    "live-job-1",

                "new_name":
                    "Name B",

                "created_by":
                    "unit-test",
            },
            agent_mode="Simulation",
        )
    except DeletedObjectRestoreSimulationBadRequest as exc:
        assert (
            "new_name"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Binding modifié devait être refusé"
        )


def test_runtime_capabilities_remain_disabled():
    assert (
        DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_ENABLED
        is True
    )

    assert (
        DELETED_OBJECT_RESTORE_SIMULATION_CMDLET_ENABLED
        is False
    )
