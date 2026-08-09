from pathlib import Path

import pytest

from app.services.ad_explorer import (
    ADExplorerBadRequest,
    ALLOWED_ACTIONS,
    QUERY_REQUIRED_ACTIONS,
    create_ad_explorer_job,
)


def test_security_descriptor_action_is_allowed():
    assert (
        "get_security_descriptor"
        in ALLOWED_ACTIONS
    )

    assert (
        "get_security_descriptor"
        in QUERY_REQUIRED_ACTIONS
    )


def test_security_descriptor_requires_object_query(
    tmp_path: Path,
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
                "action":
                    "get_security_descriptor",
            },
        )


def test_security_descriptor_job_keeps_read_contract(
    tmp_path: Path,
):
    jobs_file = (
        tmp_path
        / "ad-explorer-jobs.json"
    )

    object_dn = (
        "OU=test,"
        "OU=Users,"
        "OU=EITAS,"
        "DC=API,"
        "DC=LOCAL"
    )

    response, audit = (
        create_ad_explorer_job(
            jobs_file,
            {
                "action":
                    "get_security_descriptor",
                "query": object_dn,
                "created_by":
                    "c8-security-read-test",
            },
        )
    )

    job = response["job"]

    assert job["type"] == "ad_explorer"
    assert (
        job["action"]
        == "get_security_descriptor"
    )
    assert job["query"] == object_dn
    assert job["status"] == "pending"
    assert (
        job["created_by"]
        == "c8-security-read-test"
    )

    assert (
        audit["details"]["action"]
        == "get_security_descriptor"
    )

    assert (
        audit["details"]["query"]
        == object_dn
    )
