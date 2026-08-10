from pathlib import Path

from app.services.ad_explorer import (
    ALLOWED_ACTIONS,
    QUERY_REQUIRED_ACTIONS,
    create_ad_explorer_job,
)


ACTION = (
    "get_recycle_bin_activation_evidence"
)


def test_activation_evidence_action_is_allowed():
    assert ACTION in ALLOWED_ACTIONS


def test_activation_evidence_does_not_require_query():
    assert ACTION not in QUERY_REQUIRED_ACTIONS


def test_activation_evidence_uses_read_only_lookup_queue(
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
                "action": ACTION,
                "created_by": (
                    "c9-test"
                ),
            },
        )
    )

    job = response["job"]

    assert job["type"] == "ad_explorer"
    assert job["action"] == ACTION
    assert job["status"] == "pending"

    assert audit["details"]["action"] == ACTION


def test_activation_evidence_is_not_ad_admin_action():
    source = Path(
        "api/app/services/ad_admin.py"
    ).read_text(
        encoding="utf-8"
    )

    assert ACTION not in source
