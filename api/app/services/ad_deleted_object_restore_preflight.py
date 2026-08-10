from __future__ import annotations

import json

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path
from typing import Any

from app.services.ad_deleted_object_preflight import (
    evaluate_deleted_object_preflight,
)


def _jobs_from_payload(
    payload: Any,
) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [
            item
            for item in payload
            if isinstance(item, dict)
        ]

    if isinstance(payload, dict):
        items = (
            payload.get("jobs")
            or payload.get("items")
            or []
        )

        if isinstance(items, list):
            return [
                item
                for item in items
                if isinstance(item, dict)
            ]

    return []


def _load_jobs(
    jobs_path: Path,
) -> list[dict[str, Any]]:
    payload = json.loads(
        jobs_path.read_text(
            encoding="utf-8"
        )
    )

    return _jobs_from_payload(
        payload
    )


def _clean(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _bool_or_none(
    value: Any,
) -> bool | None:
    if value is True:
        return True

    if value is False:
        return False

    return None


def _parse_timestamp(
    value: Any,
) -> datetime:
    raw = _clean(value)

    if not raw:
        raise ValueError(
            "Horodatage live manquant"
        )

    if raw.endswith("Z"):
        raw = (
            raw[:-1]
            + "+00:00"
        )

    try:
        parsed = (
            datetime.fromisoformat(
                raw
            )
        )
    except ValueError as exc:
        raise ValueError(
            "Horodatage live invalide"
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def _latest_deleted_inventory(
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    matches = [
        job
        for job in jobs
        if (
            job.get("action")
            == "get_deleted_objects"
            and job.get("status")
            == "completed"
            and job.get("success")
            is True
            and isinstance(
                job.get("result"),
                dict,
            )
        )
    ]

    if not matches:
        raise ValueError(
            "Aucun inventaire read-only "
            "des objets supprimés disponible"
        )

    matches.sort(
        key=lambda job: str(
            job.get("completed_at")
            or ""
        )
    )

    return matches[-1]


def _find_live_job(
    jobs: list[dict[str, Any]],
    live_job_id: str,
) -> dict[str, Any]:
    matches = [
        job
        for job in jobs
        if (
            _clean(
                job.get("id")
            )
            == live_job_id
        )
    ]

    if len(matches) != 1:
        raise ValueError(
            "Job de revalidation live "
            "introuvable"
        )

    return matches[0]


def _validate_live_binding(
    job: dict[str, Any],
    *,
    object_guid: str,
    requested_new_name: str,
    requested_target_path: str,
    max_age_seconds: int,
) -> dict[str, Any]:
    if (
        job.get("action")
        != "revalidate_deleted_object_preflight"
    ):
        raise ValueError(
            "Action du job live invalide"
        )

    if (
        job.get("status")
        != "completed"
        or job.get("success")
        is not True
    ):
        raise ValueError(
            "Job live non terminé avec succès"
        )

    job_query = _clean(
        job.get("query")
    )

    if (
        job_query.lower()
        != object_guid.lower()
    ):
        raise ValueError(
            "GUID du job live différent"
        )

    filters = (
        job.get("filters")
        or {}
    )

    if not isinstance(
        filters,
        dict,
    ):
        raise ValueError(
            "Filtres du job live invalides"
        )

    job_new_name = _clean(
        filters.get("new_name")
    )

    job_target_path = _clean(
        filters.get("target_path")
    )

    if (
        job_new_name
        != requested_new_name
    ):
        raise ValueError(
            "new_name du job live différent"
        )

    if (
        job_target_path
        != requested_target_path
    ):
        raise ValueError(
            "target_path du job live différent"
        )

    result = job.get("result")

    if not isinstance(
        result,
        dict,
    ):
        raise ValueError(
            "Résultat live invalide"
        )

    if (
        result.get("action")
        != "revalidate_deleted_object_preflight"
    ):
        raise ValueError(
            "Action du résultat live invalide"
        )

    if (
        result.get("object_found")
        is not True
    ):
        raise ValueError(
            "Objet live non confirmé"
        )

    result_guid = _clean(
        result.get("object_guid")
    )

    if (
        result_guid.lower()
        != object_guid.lower()
    ):
        raise ValueError(
            "GUID du résultat live différent"
        )

    if (
        result.get("read_only")
        is not True
        or
        result.get(
            "live_revalidation_performed"
        )
        is not True
    ):
        raise ValueError(
            "Résultat live non read-only"
        )

    if (
        result.get(
            "restore_job_created"
        )
        is not False
        or
        result.get(
            "restore_implemented"
        )
        is not False
        or
        result.get(
            "execution_authorized"
        )
        is not False
        or
        result.get(
            "write_authorized"
        )
        is not False
    ):
        raise ValueError(
            "Résultat live autorisant refusé"
        )

    result_new_name = _clean(
        result.get(
            "requested_new_name"
        )
    )

    result_target_path = _clean(
        result.get(
            "requested_target_path"
        )
    )

    if (
        result_new_name
        != requested_new_name
    ):
        raise ValueError(
            "new_name du résultat live différent"
        )

    if (
        result_target_path
        != requested_target_path
    ):
        raise ValueError(
            "target_path du résultat live différent"
        )

    parent_exists = _bool_or_none(
        result.get("parent_exists")
    )

    parent_deleted = _bool_or_none(
        result.get("parent_deleted")
    )

    target_collision = _bool_or_none(
        result.get("target_collision")
    )

    collision_probe_performed = (
        result.get(
            "collision_probe_performed"
        )
    )

    effective_name = (
        _clean(
            result.get(
                "effective_new_name"
            )
        )
        or result_new_name
        or _clean(
            result.get(
                "last_known_rdn"
            )
        )
    )

    effective_target = (
        _clean(
            result.get(
                "effective_target_path"
            )
        )
        or result_target_path
        or _clean(
            result.get(
                "last_known_parent"
            )
        )
    )

    candidate_collision_proof_required = (
        result.get("is_deleted")
        is True
        and
        result.get("is_recycled")
        is False
        and
        result.get(
            "recycle_bin_enabled"
        )
        is True
        and
        bool(effective_name)
        and
        bool(effective_target)
        and
        parent_exists is True
        and
        parent_deleted is False
    )

    if (
        candidate_collision_proof_required
        and
        (
            collision_probe_performed
            is not True
            or
            target_collision is None
        )
    ):
        raise ValueError(
            "Preuve de collision live incomplète"
        )

    completed_at = _parse_timestamp(
        job.get("completed_at")
    )

    now = datetime.now(
        timezone.utc
    )

    age_seconds = (
        now - completed_at
    ).total_seconds()

    if age_seconds < -5:
        raise ValueError(
            "Horodatage live dans le futur"
        )

    if (
        age_seconds
        > max_age_seconds
    ):
        raise ValueError(
            "Revalidation live expirée"
        )

    return result


def preflight_deleted_object_restore(
    jobs_path: Path,
    *,
    object_guid: str,
    requested_new_name: str | None = None,
    requested_target_path: str | None = None,
    live_job_id: str | None = None,
    live_revalidation_max_age_seconds: int = 120,
) -> dict[str, Any]:
    guid = _clean(
        object_guid
    )

    new_name = _clean(
        requested_new_name
    )

    target_path = _clean(
        requested_target_path
    )

    bound_live_job_id = _clean(
        live_job_id
    )

    if not guid:
        raise ValueError(
            "object_guid requis"
        )

    if (
        live_revalidation_max_age_seconds
        < 1
        or
        live_revalidation_max_age_seconds
        > 600
    ):
        raise ValueError(
            "TTL live invalide"
        )

    jobs = _load_jobs(
        jobs_path
    )

    inventory_job = (
        _latest_deleted_inventory(
            jobs
        )
    )

    inventory_result = (
        inventory_job["result"]
    )

    items = inventory_result.get(
        "items"
    )

    if not isinstance(
        items,
        list,
    ):
        raise ValueError(
            "Inventaire supprimé invalide"
        )

    matches = [
        item
        for item in items
        if (
            isinstance(item, dict)
            and
            _clean(
                item.get("object_guid")
            ).lower()
            == guid.lower()
        )
    ]

    if len(matches) != 1:
        raise ValueError(
            "Objet supprimé introuvable "
            "dans le dernier inventaire"
        )

    inventory_item = matches[0]

    recycle = (
        inventory_result.get(
            "recycle_bin"
        )
        or {}
    )

    if not bound_live_job_id:
        policy = (
            evaluate_deleted_object_preflight(
                inventory_item,
                recycle_bin_enabled=(
                    recycle.get("enabled")
                    is True
                ),
                requested_new_name=(
                    new_name or None
                ),
                requested_target_path=(
                    target_path or None
                ),
                target_parent_exists=None,
                target_parent_deleted=None,
                target_dn_exists=None,
            )
        )

        return {
            "read_only":
                True,

            "source_job_id":
                inventory_job.get("id"),

            "source_completed_at":
                inventory_job.get(
                    "completed_at"
                ),

            "object_guid":
                guid,

            "policy":
                policy,

            "live_revalidation_performed":
                False,

            "live_job_id":
                None,

            "restore_job_created":
                False,

            "restore_implemented":
                False,

            "execution_authorized":
                False,

            "write_authorized":
                False,
        }

    live_job = _find_live_job(
        jobs,
        bound_live_job_id,
    )

    live_result = (
        _validate_live_binding(
            live_job,
            object_guid=guid,
            requested_new_name=new_name,
            requested_target_path=target_path,
            max_age_seconds=(
                live_revalidation_max_age_seconds
            ),
        )
    )

    fresh_item = {
        "object_guid":
            _clean(
                live_result.get(
                    "object_guid"
                )
            ),

        "object_class":
            _clean(
                live_result.get(
                    "object_class"
                )
            ),

        "is_deleted":
            live_result.get(
                "is_deleted"
            ),

        "is_recycled":
            live_result.get(
                "is_recycled"
            ),

        "last_known_parent":
            _clean(
                live_result.get(
                    "last_known_parent"
                )
            ),

        "last_known_rdn":
            _clean(
                live_result.get(
                    "last_known_rdn"
                )
            ),
    }

    policy = (
        evaluate_deleted_object_preflight(
            fresh_item,
            recycle_bin_enabled=(
                live_result.get(
                    "recycle_bin_enabled"
                )
                is True
            ),
            requested_new_name=(
                new_name or None
            ),
            requested_target_path=(
                target_path or None
            ),
            target_parent_exists=(
                _bool_or_none(
                    live_result.get(
                        "parent_exists"
                    )
                )
            ),
            target_parent_deleted=(
                _bool_or_none(
                    live_result.get(
                        "parent_deleted"
                    )
                )
            ),
            target_dn_exists=(
                _bool_or_none(
                    live_result.get(
                        "target_collision"
                    )
                )
            ),
        )
    )

    return {
        "read_only":
            True,

        "source_job_id":
            inventory_job.get("id"),

        "source_completed_at":
            inventory_job.get(
                "completed_at"
            ),

        "object_guid":
            guid,

        "policy":
            policy,

        "live_revalidation_performed":
            True,

        "live_job_id":
            bound_live_job_id,

        "live_job_completed_at":
            live_job.get(
                "completed_at"
            ),

        "restore_job_created":
            False,

        "restore_implemented":
            False,

        "execution_authorized":
            False,

        "write_authorized":
            False,
    }
