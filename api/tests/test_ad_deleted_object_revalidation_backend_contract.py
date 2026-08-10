from app.services.ad_explorer import (
    ALLOWED_ACTIONS,
    QUERY_REQUIRED_ACTIONS,
    create_ad_explorer_job,
)


ACTION = (
    "revalidate_deleted_object_preflight"
)

GUID = (
    "11111111-2222-3333-4444-555555555555"
)


def test_revalidation_action_is_read_lookup_contract():
    assert ACTION in ALLOWED_ACTIONS
    assert ACTION in QUERY_REQUIRED_ACTIONS


def test_revalidation_action_requires_guid_query(
    tmp_path,
):
    path = tmp_path / "jobs.json"

    try:
        create_ad_explorer_job(
            path,
            {
                "action": ACTION,
                "query": "",
            },
        )
    except Exception as exc:
        assert (
            "query"
            in str(exc).lower()
        )
    else:
        raise AssertionError(
            "query should be required"
        )


def test_revalidation_job_keeps_guid_and_filters(
    tmp_path,
):
    path = tmp_path / "jobs.json"

    response, _ = create_ad_explorer_job(
        path,
        {
            "action": ACTION,
            "query": GUID,
            "filters": {
                "new_name":
                    "Recovered User",

                "target_path":
                    "OU=Recovery,"
                    "DC=API,DC=LOCAL",
            },
            "created_by":
                "c9.2a3c-test",
        },
    )

    job = response["job"]

    assert job["action"] == ACTION
    assert job["query"] == GUID

    assert (
        job["filters"]["new_name"]
        == "Recovered User"
    )

    assert (
        job["filters"]["target_path"]
        == "OU=Recovery,DC=API,DC=LOCAL"
    )
