from pathlib import Path

import pytest

from app.services.ad_explorer import (
    ADExplorerBadRequest,
    ALLOWED_ACTIONS,
    QUERY_REQUIRED_ACTIONS,
    claim_ad_explorer_job,
    create_ad_explorer_job,
    get_ad_explorer_job,
    submit_ad_explorer_job_result,
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

def test_security_descriptor_keeps_guid_semantic_names(
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

    response, _ = create_ad_explorer_job(
        jobs_file,
        {
            "action":
                "get_security_descriptor",
            "query": object_dn,
        },
    )

    job_id = response["job"]["id"]

    claim_ad_explorer_job(
        jobs_file,
        job_id,
        {
            "agent_name": "SRV-DC01",
        },
    )

    guid = (
        "00299570-246d-11d0-"
        "a768-00aa006e0529"
    )

    submit_ad_explorer_job_result(
        jobs_file,
        job_id,
        {
            "success": True,
            "agent_name": "SRV-DC01",
            "result": {
                "action":
                    "get_security_descriptor",
                "read_only": True,
                "rules": [
                    {
                        "identity":
                            "API\\\\Example",
                        "object_type_guid":
                            guid,
                        "object_type_name":
                            "Reset Password",
                        "inherited_object_type_guid":
                            guid,
                        "inherited_object_type_name":
                            "Reset Password",
                    },
                ],
            },
        },
    )

    stored = get_ad_explorer_job(
        jobs_file,
        job_id,
    )

    rule = stored["result"]["rules"][0]

    assert (
        rule["object_type_guid"]
        == guid
    )
    assert (
        rule["object_type_name"]
        == "Reset Password"
    )
    assert (
        rule["inherited_object_type_guid"]
        == guid
    )
    assert (
        rule["inherited_object_type_name"]
        == "Reset Password"
    )
