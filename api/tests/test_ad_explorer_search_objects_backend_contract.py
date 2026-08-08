from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app.services.ad_explorer import (
    ADExplorerBadRequest,
    create_ad_explorer_job,
)


def test_search_objects_job_is_allowed_and_normalized():
    with TemporaryDirectory() as temp_dir:
        jobs_file = Path(temp_dir) / "jobs.json"

        response, audit = create_ad_explorer_job(
            jobs_file,
            {
                "action": "search_objects",
                "query": "srv",
                "base_dn": "DC=API,DC=LOCAL",
                "recursive": True,
                "limit": 5000,
                "created_by": "c6-test",
            },
        )

        job = response["job"]

        assert job["action"] == "search_objects"
        assert job["query"] == "srv"
        assert job["base_dn"] == "DC=API,DC=LOCAL"
        assert job["recursive"] is True
        assert job["limit"] == 1000
        assert job["status"] == "pending"

        assert audit["details"]["action"] == "search_objects"
        assert audit["details"]["query"] == "srv"
        assert audit["details"]["base_dn"] == "DC=API,DC=LOCAL"
        assert audit["details"]["limit"] == 1000


def test_search_objects_requires_a_query():
    with TemporaryDirectory() as temp_dir:
        jobs_file = Path(temp_dir) / "jobs.json"

        with pytest.raises(
            ADExplorerBadRequest,
            match="query est obligatoire",
        ):
            create_ad_explorer_job(
                jobs_file,
                {
                    "action": "search_objects",
                    "base_dn": "DC=API,DC=LOCAL",
                },
            )
