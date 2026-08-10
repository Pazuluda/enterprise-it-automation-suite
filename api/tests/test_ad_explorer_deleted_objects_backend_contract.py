from pathlib import Path

import pytest

from app.services.ad_explorer import (
    ADExplorerBadRequest,
    ALLOWED_ACTIONS,
    QUERY_REQUIRED_ACTIONS,
    create_ad_explorer_job,
)


def test_deleted_objects_action_is_allowed_read_only_query():
    assert (
        "get_deleted_objects"
        in ALLOWED_ACTIONS
    )

    assert (
        "get_deleted_objects"
        not in QUERY_REQUIRED_ACTIONS
    )


def test_deleted_objects_job_does_not_require_query(
    tmp_path: Path,
):
    jobs_file = (
        tmp_path
        / "ad-explorer-jobs.json"
    )

    response, audit = (
        create_ad_explorer_job(
            jobs_file,
            {
                "action":
                    "get_deleted_objects",
                "limit": 150,
                "created_by":
                    "c9-read-only-test",
            },
        )
    )

    job = response["job"]

    assert (
        job["type"]
        == "ad_explorer"
    )

    assert (
        job["action"]
        == "get_deleted_objects"
    )

    assert (
        job["status"]
        == "pending"
    )

    assert (
        job["limit"]
        == 150
    )

    assert (
        job["created_by"]
        == "c9-read-only-test"
    )

    assert (
        audit["details"]["action"]
        == "get_deleted_objects"
    )


@pytest.mark.parametrize(
    "action",
    (
        "restore_object",
        "restore_deleted_object",
        "enable_recycle_bin",
    ),
)
def test_c9_write_actions_remain_forbidden(
    tmp_path: Path,
    action: str,
):
    jobs_file = (
        tmp_path
        / "ad-explorer-jobs.json"
    )

    with pytest.raises(
        ADExplorerBadRequest
    ):
        create_ad_explorer_job(
            jobs_file,
            {
                "action": action,
            },
        )


def test_deleted_objects_contract_adds_no_restore_primitive():
    source = Path(
        "api/app/services/ad_explorer.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "Restore-ADObject",
        "Enable-ADOptionalFeature",
        "restore_deleted_object",
        "restore_object",
    )

    for token in forbidden:
        assert token not in source
