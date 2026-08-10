from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.storage import (
    load_json,
    save_json,
)
from app.services.ad_deleted_object_restore_simulation import (
    DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_ENABLED,
    DeletedObjectRestoreSimulationBadRequest,
    prepare_deleted_object_restore_simulation,
)


DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_CONTRACT_VERSION = (
    "c9.2b-a3b-v1"
)

DELETED_OBJECT_RESTORE_SIMULATION_WORKER_CLAIM_ENABLED = (
    False
)

DELETED_OBJECT_RESTORE_SIMULATION_WORKER_RUNTIME_ENABLED = (
    False
)

DELETED_OBJECT_RESTORE_SIMULATION_PRODUCTION_ENABLED = (
    False
)

DELETED_OBJECT_RESTORE_SIMULATION_AD_WRITE_ENABLED = (
    False
)


class DeletedObjectRestoreSimulationPersistenceError(
    ValueError
):
    pass


def _utc_now_iso() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def create_deleted_object_restore_simulation_record(
    ad_admin_jobs_file: Path,
    deleted_objects_jobs_file: Path,
    payload: dict[str, Any],
    *,
    agent_mode: object,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(
        ad_admin_jobs_file,
        Path,
    ):
        raise DeletedObjectRestoreSimulationPersistenceError(
            "ad_admin_jobs_file must be a Path"
        )

    if not isinstance(
        deleted_objects_jobs_file,
        Path,
    ):
        raise DeletedObjectRestoreSimulationPersistenceError(
            "deleted_objects_jobs_file must be a Path"
        )

    if not (
        DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_ENABLED
    ):
        raise DeletedObjectRestoreSimulationPersistenceError(
            "Restore Simulation persistence disabled"
        )

    if (
        DELETED_OBJECT_RESTORE_SIMULATION_WORKER_CLAIM_ENABLED
    ):
        raise RuntimeError(
            "Windows claim must remain disabled"
        )

    if (
        DELETED_OBJECT_RESTORE_SIMULATION_WORKER_RUNTIME_ENABLED
    ):
        raise RuntimeError(
            "Windows runtime must remain disabled"
        )

    if (
        DELETED_OBJECT_RESTORE_SIMULATION_PRODUCTION_ENABLED
    ):
        raise RuntimeError(
            "Production must remain disabled"
        )

    if (
        DELETED_OBJECT_RESTORE_SIMULATION_AD_WRITE_ENABLED
    ):
        raise RuntimeError(
            "AD writes must remain disabled"
        )

    try:
        envelope = (
            prepare_deleted_object_restore_simulation(
                deleted_objects_jobs_file,
                payload,
                agent_mode=agent_mode,
            )
        )
    except DeletedObjectRestoreSimulationBadRequest as exc:
        raise DeletedObjectRestoreSimulationPersistenceError(
            str(exc)
        ) from exc

    if (
        envelope.get(
            "simulation_job_authorized"
        )
        is not True
    ):
        raise DeletedObjectRestoreSimulationPersistenceError(
            "Simulation preparation not authorized"
        )

    if (
        envelope.get(
            "simulation_job_persistence_authorized"
        )
        is not True
    ):
        raise DeletedObjectRestoreSimulationPersistenceError(
            "Simulation persistence not authorized"
        )

    forbidden_true = (
        envelope.get(
            "restore_cmdlet_authorized"
        )
        is True
        or
        envelope.get(
            "restore_whatif_authorized"
        )
        is True
        or
        envelope.get(
            "execution_authorized"
        )
        is True
        or
        envelope.get(
            "write_authorized"
        )
        is True
        or
        envelope.get(
            "restore_implemented"
        )
        is True
        or
        envelope.get(
            "restore_performed"
        )
        is True
    )

    if forbidden_true:
        raise DeletedObjectRestoreSimulationPersistenceError(
            "Authorizing Simulation envelope rejected"
        )

    if (
        envelope.get("mode")
        != "Simulation"
    ):
        raise DeletedObjectRestoreSimulationPersistenceError(
            "Simulation mode required"
        )

    if (
        envelope.get("action")
        != "simulate_deleted_object_restore"
    ):
        raise DeletedObjectRestoreSimulationPersistenceError(
            "Invalid Simulation action"
        )

    job_id = str(
        uuid4()
    )

    job_payload = dict(
        envelope
    )

    job_payload.update({
        "persistence_contract_version":
            DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_CONTRACT_VERSION,

        "worker_claim_authorized":
            False,

        "worker_runtime_authorized":
            False,

        "production_authorized":
            False,

        "execution_authorized":
            False,

        "write_authorized":
            False,
    })

    job = {
        "id":
            job_id,

        "type":
            "ad_admin",

        "status":
            "prepared",

        "created_at":
            _utc_now_iso(),

        "created_by":
            envelope["created_by"],

        "action":
            envelope["action"],

        "payload":
            job_payload,

        "claimed_at":
            None,

        "claimed_by":
            None,

        "completed_at":
            None,

        "success":
            None,

        "message":
            (
                "Restore Simulation prepared; "
                "Windows runtime disabled"
            ),

        "output":
            "",

        "result":
            None,

        "details":
            None,
    }

    jobs = load_json(
        ad_admin_jobs_file,
        [],
    )

    if not isinstance(
        jobs,
        list,
    ):
        raise DeletedObjectRestoreSimulationPersistenceError(
            "AD Admin job storage must contain a JSON list"
        )

    jobs.append(
        job
    )

    save_json(
        ad_admin_jobs_file,
        jobs,
    )

    audit_event = {
        "action":
            "deleted_object_restore_simulation_prepared",

        "request_id":
            job_id,

        "actor":
            envelope["created_by"],

        "message":
            "Deleted object restore Simulation prepared",

        "details": {
            "job_id":
                job_id,

            "action":
                envelope["action"],

            "object_guid":
                envelope["object_guid"],

            "live_job_id":
                envelope["live_job_id"],

            "policy_decision":
                envelope["policy_decision"],

            "class_policy":
                envelope["class_policy"],

            "persistence_contract_version":
                DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_CONTRACT_VERSION,

            "status":
                "prepared",

            "worker_claim_authorized":
                False,

            "worker_runtime_authorized":
                False,

            "production_authorized":
                False,

            "execution_authorized":
                False,

            "write_authorized":
                False,
        },
    }

    return {
        "message":
            "Restore Simulation prepared",

        "job":
            job,
    }, audit_event


def assert_deleted_object_restore_simulation_persistence_invariants(
) -> None:
    if not (
        DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_ENABLED
    ):
        raise RuntimeError(
            "Simulation persistence must remain enabled"
        )

    if (
        DELETED_OBJECT_RESTORE_SIMULATION_WORKER_CLAIM_ENABLED
    ):
        raise RuntimeError(
            "Windows claim must remain disabled"
        )

    if (
        DELETED_OBJECT_RESTORE_SIMULATION_WORKER_RUNTIME_ENABLED
    ):
        raise RuntimeError(
            "Windows runtime must remain disabled"
        )

    if (
        DELETED_OBJECT_RESTORE_SIMULATION_PRODUCTION_ENABLED
    ):
        raise RuntimeError(
            "Production must remain disabled"
        )

    if (
        DELETED_OBJECT_RESTORE_SIMULATION_AD_WRITE_ENABLED
    ):
        raise RuntimeError(
            "AD writes must remain disabled"
        )


assert_deleted_object_restore_simulation_persistence_invariants()
