from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.ad_deleted_object_restore_preflight import (
    preflight_deleted_object_restore,
)


DELETED_OBJECT_RESTORE_SIMULATION_CONTRACT_VERSION = (
    "c9.2b-v1"
)

DELETED_OBJECT_RESTORE_SIMULATION_PREPARATION_ENABLED = (
    True
)

DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_ENABLED = (
    True
)

DELETED_OBJECT_RESTORE_SIMULATION_CMDLET_ENABLED = (
    False
)


class DeletedObjectRestoreSimulationBadRequest(
    ValueError
):
    pass


def _clean(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(value).strip()


def prepare_deleted_object_restore_simulation(
    jobs_path: Path,
    payload: dict[str, Any],
    *,
    agent_mode: object,
    live_revalidation_max_age_seconds: int = 120,
) -> dict[str, Any]:
    if not (
        DELETED_OBJECT_RESTORE_SIMULATION_PREPARATION_ENABLED
    ):
        raise DeletedObjectRestoreSimulationBadRequest(
            "Simulation preparation disabled"
        )

    mode = _clean(
        agent_mode
    )

    if mode.lower() != "simulation":
        raise DeletedObjectRestoreSimulationBadRequest(
            "Restore simulation requires mode Simulation"
        )

    object_guid = _clean(
        payload.get("object_guid")
    )

    live_job_id = _clean(
        payload.get("live_job_id")
    )

    requested_new_name = _clean(
        payload.get("new_name")
    )

    requested_target_path = _clean(
        payload.get("target_path")
    )

    created_by = _clean(
        payload.get("created_by")
    )

    if not object_guid:
        raise DeletedObjectRestoreSimulationBadRequest(
            "object_guid required"
        )

    if not live_job_id:
        raise DeletedObjectRestoreSimulationBadRequest(
            "live_job_id required"
        )

    if not created_by:
        raise DeletedObjectRestoreSimulationBadRequest(
            "created_by required"
        )

    if len(created_by) > 128:
        raise DeletedObjectRestoreSimulationBadRequest(
            "created_by exceeds 128 characters"
        )

    try:
        preflight = (
            preflight_deleted_object_restore(
                jobs_path,
                object_guid=object_guid,
                requested_new_name=(
                    requested_new_name
                    or None
                ),
                requested_target_path=(
                    requested_target_path
                    or None
                ),
                live_job_id=live_job_id,
                live_revalidation_max_age_seconds=(
                    live_revalidation_max_age_seconds
                ),
            )
        )
    except ValueError as exc:
        raise DeletedObjectRestoreSimulationBadRequest(
            str(exc)
        ) from exc

    policy = preflight.get(
        "policy"
    )

    if not isinstance(
        policy,
        dict,
    ):
        raise DeletedObjectRestoreSimulationBadRequest(
            "Invalid preflight policy"
        )

    if (
        preflight.get(
            "live_revalidation_performed"
        )
        is not True
    ):
        raise DeletedObjectRestoreSimulationBadRequest(
            "Live revalidation required"
        )

    if (
        policy.get("decision")
        != "candidate_preflight"
    ):
        raise DeletedObjectRestoreSimulationBadRequest(
            "Object is not eligible for Simulation: "
            + str(
                policy.get("decision")
            )
        )

    if (
        policy.get(
            "preflight_passed"
        )
        is not True
        or
        policy.get(
            "simulation_candidate"
        )
        is not True
    ):
        raise DeletedObjectRestoreSimulationBadRequest(
            "Simulation preflight not validated"
        )

    forbidden_true = (
        preflight.get(
            "execution_authorized"
        )
        is True
        or
        preflight.get(
            "write_authorized"
        )
        is True
        or
        preflight.get(
            "restore_implemented"
        )
        is True
        or
        policy.get(
            "execution_authorized"
        )
        is True
        or
        policy.get(
            "write_authorized"
        )
        is True
    )

    if forbidden_true:
        raise DeletedObjectRestoreSimulationBadRequest(
            "Authorizing preflight rejected"
        )

    return {
        "contract_version":
            DELETED_OBJECT_RESTORE_SIMULATION_CONTRACT_VERSION,

        "action":
            "simulate_deleted_object_restore",

        "mode":
            "Simulation",

        "created_by":
            created_by,

        "object_guid":
            object_guid,

        "live_job_id":
            live_job_id,

        "source_inventory_job_id":
            preflight.get(
                "source_job_id"
            ),

        "live_job_completed_at":
            preflight.get(
                "live_job_completed_at"
            ),

        "requested_new_name":
            requested_new_name,

        "requested_target_path":
            requested_target_path,

        "effective_new_name":
            policy.get(
                "effective_new_name"
            ),

        "effective_target_path":
            policy.get(
                "effective_target_path"
            ),

        "object_class":
            policy.get(
                "object_class"
            ),

        "class_policy":
            policy.get(
                "class_policy"
            ),

        "manual_review_required":
            policy.get(
                "manual_review_required"
            ),

        "policy_decision":
            policy.get(
                "decision"
            ),

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


def assert_deleted_object_restore_simulation_invariants() -> None:
    if not (
        DELETED_OBJECT_RESTORE_SIMULATION_PREPARATION_ENABLED
    ):
        raise RuntimeError(
            "Simulation preparation must remain enabled"
        )

    if not (
        DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_ENABLED
    ):
        raise RuntimeError(
            "Simulation persistence must remain enabled"
        )

    if (
        DELETED_OBJECT_RESTORE_SIMULATION_CMDLET_ENABLED
    ):
        raise RuntimeError(
            "Restore cmdlet must remain disabled"
        )


assert_deleted_object_restore_simulation_invariants()
