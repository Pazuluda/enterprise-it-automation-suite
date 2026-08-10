from pathlib import Path

from app.services.ad_deleted_object_restore_preflight import (
    preflight_deleted_object_restore,
)


def write_jobs(
    path: Path,
    *,
    item: dict,
    recycle_enabled: bool,
):
    path.write_text(
        """
{
  "jobs": [
    {
      "id": "inventory-job-1",
      "action": "get_deleted_objects",
      "status": "completed",
      "success": true,
      "completed_at": "2026-08-10T12:00:00Z",
      "result": {
        "recycle_bin": {
          "enabled": %s
        },
        "items": [
          %s
        ]
      }
    }
  ]
}
"""
        % (
            (
                "true"
                if recycle_enabled
                else "false"
            ),
            __import__(
                "json"
            ).dumps(item),
        ),
        encoding="utf-8",
    )


def base_item(**updates):
    item = {
        "object_guid":
            "11111111-2222-3333-4444-555555555555",

        "object_class":
            "user",

        "is_deleted":
            True,

        "is_recycled":
            True,

        "last_known_parent":
            "OU=Users,DC=API,DC=LOCAL",

        "last_known_rdn":
            None,
    }

    item.update(updates)

    return item


def test_real_current_shape_is_blocked_recycled(
    tmp_path,
):
    jobs = (
        tmp_path
        / "jobs.json"
    )

    write_jobs(
        jobs,
        item=base_item(),
        recycle_enabled=False,
    )

    result = (
        preflight_deleted_object_restore(
            jobs,
            object_guid=(
                "11111111-2222-3333-4444-555555555555"
            ),
        )
    )

    assert result["read_only"] is True

    assert (
        result["policy"]["decision"]
        == "blocked_recycled"
    )

    assert (
        result["restore_job_created"]
        is False
    )

    assert (
        result["execution_authorized"]
        is False
    )

    assert (
        result["write_authorized"]
        is False
    )


def test_non_recycled_future_object_requires_live_revalidation(
    tmp_path,
):
    jobs = (
        tmp_path
        / "jobs.json"
    )

    write_jobs(
        jobs,
        item=base_item(
            is_recycled=False,
            last_known_rdn=(
                "CN=Future User"
            ),
        ),
        recycle_enabled=True,
    )

    result = (
        preflight_deleted_object_restore(
            jobs,
            object_guid=(
                "11111111-2222-3333-4444-555555555555"
            ),
        )
    )

    assert (
        result["policy"]["decision"]
        == "needs_live_revalidation"
    )

    assert (
        result[
            "live_revalidation_performed"
        ]
        is False
    )

    assert (
        result["restore_job_created"]
        is False
    )


def test_unknown_guid_is_rejected(
    tmp_path,
):
    jobs = (
        tmp_path
        / "jobs.json"
    )

    write_jobs(
        jobs,
        item=base_item(),
        recycle_enabled=False,
    )

    try:
        preflight_deleted_object_restore(
            jobs,
            object_guid=(
                "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
            ),
        )
    except ValueError as exc:
        assert (
            "introuvable"
            in str(exc)
        )
    else:
        raise AssertionError(
            "ValueError attendu"
        )


def test_empty_guid_is_rejected(
    tmp_path,
):
    jobs = (
        tmp_path
        / "jobs.json"
    )

    write_jobs(
        jobs,
        item=base_item(),
        recycle_enabled=False,
    )

    try:
        preflight_deleted_object_restore(
            jobs,
            object_guid="",
        )
    except ValueError as exc:
        assert (
            "object_guid requis"
            in str(exc)
        )
    else:
        raise AssertionError(
            "ValueError attendu"
        )


def write_inventory_and_live_jobs(
    path,
    *,
    live_id="live-job-1",
    live_query=(
        "11111111-2222-3333-4444-555555555555"
    ),
    live_filters=None,
    live_result=None,
    live_completed_at=None,
):
    import json

    from datetime import (
        datetime,
        timezone,
    )

    if live_filters is None:
        live_filters = {}

    if live_result is None:
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
                live_query,

            "object_class":
                "user",

            "is_deleted":
                True,

            "is_recycled":
                False,

            "recycle_bin_enabled":
                True,

            "last_known_parent":
                "OU=Users,DC=API,DC=LOCAL",

            "last_known_rdn":
                "Future User",

            "requested_new_name":
                str(
                    live_filters.get(
                        "new_name"
                    )
                    or ""
                ),

            "requested_target_path":
                str(
                    live_filters.get(
                        "target_path"
                    )
                    or ""
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

    if live_completed_at is None:
        live_completed_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

    inventory_item = {
        "object_guid":
            "11111111-2222-3333-4444-555555555555",

        "object_class":
            "user",

        "is_deleted":
            True,

        "is_recycled":
            False,

        "last_known_parent":
            "OU=Users,DC=API,DC=LOCAL",

        "last_known_rdn":
            "Future User",
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
                    "2026-08-10T12:00:00Z",

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
                    live_id,

                "action":
                    "revalidate_deleted_object_preflight",

                "status":
                    "completed",

                "success":
                    True,

                "query":
                    live_query,

                "filters":
                    live_filters,

                "completed_at":
                    live_completed_at,

                "result":
                    live_result,
            },
        ],
    }

    path.write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )


def test_completed_live_job_is_bound_to_policy(
    tmp_path,
):
    jobs = (
        tmp_path
        / "jobs.json"
    )

    write_inventory_and_live_jobs(
        jobs,
    )

    result = (
        preflight_deleted_object_restore(
            jobs,
            object_guid=(
                "11111111-2222-3333-4444-555555555555"
            ),
            live_job_id=(
                "live-job-1"
            ),
        )
    )

    assert (
        result[
            "live_revalidation_performed"
        ]
        is True
    )

    assert (
        result["live_job_id"]
        == "live-job-1"
    )

    assert (
        result["policy"]["decision"]
        == "candidate_preflight"
    )

    assert (
        result["policy"][
            "preflight_passed"
        ]
        is True
    )

    assert (
        result["execution_authorized"]
        is False
    )

    assert (
        result["write_authorized"]
        is False
    )


def test_live_job_binding_rejects_changed_name(
    tmp_path,
):
    jobs = (
        tmp_path
        / "jobs.json"
    )

    write_inventory_and_live_jobs(
        jobs,
        live_filters={
            "new_name":
                "Name A",
        },
    )

    try:
        preflight_deleted_object_restore(
            jobs,
            object_guid=(
                "11111111-2222-3333-4444-555555555555"
            ),
            requested_new_name=(
                "Name B"
            ),
            live_job_id=(
                "live-job-1"
            ),
        )
    except ValueError as exc:
        assert (
            "new_name"
            in str(exc)
        )
    else:
        raise AssertionError(
            "ValueError attendu"
        )


def test_stale_live_job_is_rejected(
    tmp_path,
):
    jobs = (
        tmp_path
        / "jobs.json"
    )

    write_inventory_and_live_jobs(
        jobs,
        live_completed_at=(
            "2020-01-01T00:00:00Z"
        ),
    )

    try:
        preflight_deleted_object_restore(
            jobs,
            object_guid=(
                "11111111-2222-3333-4444-555555555555"
            ),
            live_job_id=(
                "live-job-1"
            ),
        )
    except ValueError as exc:
        assert (
            "expir"
            in str(exc).lower()
        )
    else:
        raise AssertionError(
            "ValueError attendu"
        )


def test_authorizing_live_result_is_rejected(
    tmp_path,
):
    jobs = (
        tmp_path
        / "jobs.json"
    )

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
            "11111111-2222-3333-4444-555555555555",

        "object_class":
            "user",

        "is_deleted":
            True,

        "is_recycled":
            False,

        "recycle_bin_enabled":
            True,

        "last_known_parent":
            "OU=Users,DC=API,DC=LOCAL",

        "last_known_rdn":
            "Future User",

        "requested_new_name":
            "",

        "requested_target_path":
            "",

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
            True,
    }

    write_inventory_and_live_jobs(
        jobs,
        live_result=live_result,
    )

    try:
        preflight_deleted_object_restore(
            jobs,
            object_guid=(
                "11111111-2222-3333-4444-555555555555"
            ),
            live_job_id=(
                "live-job-1"
            ),
        )
    except ValueError as exc:
        assert (
            "autorisant"
            in str(exc)
        )
    else:
        raise AssertionError(
            "ValueError attendu"
        )


def test_live_result_action_must_match(
    tmp_path,
):
    import json

    jobs = tmp_path / "jobs.json"

    write_inventory_and_live_jobs(
        jobs,
    )

    payload = json.loads(
        jobs.read_text(
            encoding="utf-8"
        )
    )

    payload["jobs"][1]["result"][
        "action"
    ] = "unexpected_action"

    jobs.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    try:
        preflight_deleted_object_restore(
            jobs,
            object_guid=(
                "11111111-2222-3333-4444-555555555555"
            ),
            live_job_id="live-job-1",
        )
    except ValueError as exc:
        assert (
            "résultat live"
            in str(exc).lower()
        )
    else:
        raise AssertionError(
            "ValueError attendu"
        )


def test_live_result_must_confirm_object_found(
    tmp_path,
):
    import json

    jobs = tmp_path / "jobs.json"

    write_inventory_and_live_jobs(
        jobs,
    )

    payload = json.loads(
        jobs.read_text(
            encoding="utf-8"
        )
    )

    payload["jobs"][1]["result"][
        "object_found"
    ] = False

    jobs.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    try:
        preflight_deleted_object_restore(
            jobs,
            object_guid=(
                "11111111-2222-3333-4444-555555555555"
            ),
            live_job_id="live-job-1",
        )
    except ValueError as exc:
        assert (
            "non confirmé"
            in str(exc).lower()
        )
    else:
        raise AssertionError(
            "ValueError attendu"
        )


def test_candidate_requires_real_collision_probe(
    tmp_path,
):
    import json

    jobs = tmp_path / "jobs.json"

    write_inventory_and_live_jobs(
        jobs,
    )

    payload = json.loads(
        jobs.read_text(
            encoding="utf-8"
        )
    )

    result = (
        payload["jobs"][1]["result"]
    )

    result[
        "collision_probe_performed"
    ] = False

    result[
        "target_collision"
    ] = False

    jobs.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    try:
        preflight_deleted_object_restore(
            jobs,
            object_guid=(
                "11111111-2222-3333-4444-555555555555"
            ),
            live_job_id="live-job-1",
        )
    except ValueError as exc:
        assert (
            "collision"
            in str(exc).lower()
        )
    else:
        raise AssertionError(
            "ValueError attendu"
        )
