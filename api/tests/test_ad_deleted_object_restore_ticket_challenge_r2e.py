from __future__ import annotations

import json
import os

from dataclasses import replace
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.services.ad_deleted_object_restore_simulation import (
    DELETED_OBJECT_RESTORE_SIMULATION_CONTRACT_VERSION,
)
from app.services.ad_deleted_object_restore_simulation_persistence import (
    DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_CONTRACT_VERSION,
)
from app.services.ad_deleted_object_restore_ticket_challenge import (
    AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_CONTRACT_VERSION,
    AdDeletedObjectRestoreTicketChallengeConflict,
    AdDeletedObjectRestoreTicketChallengeError,
    assert_ad_deleted_object_restore_ticket_challenge_invariants,
    build_ad_deleted_object_restore_ticket_challenge,
)


GUID = (
    "b1018519-8b6e-4788-81c8-3108a188e7b4"
)

NAME = (
    "GG_C95_RECYCLE_TEST"
)

TARGET = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)


def _iso(
    value: datetime,
) -> str:
    return (
        value.astimezone(
            timezone.utc
        )
        .isoformat()
    )


def _ids() -> dict[str, str]:
    return {
        "simulation":
            str(uuid4()),

        "inventory":
            str(uuid4()),

        "source_live":
            str(uuid4()),

        "fresh_live":
            str(uuid4()),
    }


def _source_simulation(
    now: datetime,
    ids: dict[str, str],
) -> dict:
    payload = {
        "contract_version":
            DELETED_OBJECT_RESTORE_SIMULATION_CONTRACT_VERSION,

        "persistence_contract_version":
            DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_CONTRACT_VERSION,

        "mode":
            "Simulation",

        "policy_decision":
            "candidate_preflight",

        "class_policy":
            "standard_controlled",

        "preflight_passed":
            True,

        "simulation_candidate":
            True,

        "simulation_job_authorized":
            True,

        "simulation_job_persistence_authorized":
            True,

        "worker_claim_authorized":
            False,

        "worker_runtime_authorized":
            False,

        "production_authorized":
            False,

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

        "manual_review_required":
            False,

        "object_guid":
            GUID,

        "object_class":
            "group",

        "effective_new_name":
            NAME,

        "effective_target_path":
            TARGET,

        "live_job_id":
            ids["source_live"],

        "live_job_completed_at":
            _iso(
                now
                - timedelta(
                    seconds=20
                )
            ),

        "source_inventory_job_id":
            ids["inventory"],

        "created_by":
            "c9.5-r2e-test",
    }

    return {
        "id":
            ids["simulation"],

        "type":
            "ad_admin",

        "status":
            "prepared",

        "created_at":
            _iso(
                now
                - timedelta(
                    seconds=15
                )
            ),

        "created_by":
            "c9.5-r2e-test",

        "action":
            "simulate_deleted_object_restore",

        "payload":
            payload,

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


def _inventory_job(
    now: datetime,
    ids: dict[str, str],
) -> dict:
    return {
        "id":
            ids["inventory"],

        "type":
            "ad_explorer",

        "action":
            "get_deleted_objects",

        "status":
            "completed",

        "success":
            True,

        "completed_at":
            _iso(
                now
                - timedelta(
                    seconds=30
                )
            ),

        "result": {
            "recycle_bin": {
                "enabled":
                    True,
            },

            "items": [
                {
                    "object_guid":
                        GUID,

                    "object_class":
                        "group",

                    "is_deleted":
                        True,

                    "is_recycled":
                        False,

                    "last_known_parent":
                        (
                            "CN=Users,"
                            "DC=API,DC=LOCAL"
                        ),

                    "last_known_rdn":
                        NAME,
                }
            ],
        },
    }


def _fresh_live_job(
    now: datetime,
    ids: dict[str, str],
) -> dict:
    return {
        "id":
            ids["fresh_live"],

        "type":
            "ad_explorer",

        "action":
            "revalidate_deleted_object_preflight",

        "status":
            "completed",

        "success":
            True,

        "query":
            GUID,

        "filters": {
            "new_name":
                NAME,

            "target_path":
                TARGET,
        },

        "completed_at":
            _iso(
                now
                - timedelta(
                    seconds=2
                )
            ),

        "result": {
            "action":
                "revalidate_deleted_object_preflight",

            "read_only":
                True,

            "live_revalidation_performed":
                True,

            "object_found":
                True,

            "object_guid":
                GUID,

            "object_class":
                "group",

            "rdn_attribute":
                "cn",

            "is_deleted":
                True,

            "is_recycled":
                False,

            "recycle_bin_enabled":
                True,

            "last_known_parent":
                (
                    "CN=Users,"
                    "DC=API,DC=LOCAL"
                ),

            "last_known_rdn":
                NAME,

            "requested_new_name":
                NAME,

            "requested_target_path":
                TARGET,

            "effective_new_name":
                NAME,

            "effective_target_path":
                TARGET,

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
        },
    }


def _write_sources(
    tmp_path: Path,
    now: datetime,
):
    ids = _ids()

    ad_admin_jobs = (
        tmp_path
        / "ad-admin-jobs.json"
    )

    deleted_jobs = (
        tmp_path
        / "ad-explorer-jobs.json"
    )

    ad_admin_jobs.write_text(
        json.dumps(
            [
                _source_simulation(
                    now,
                    ids,
                )
            ]
        ),
        encoding="utf-8",
    )

    deleted_jobs.write_text(
        json.dumps(
            [
                _inventory_job(
                    now,
                    ids,
                ),
                _fresh_live_job(
                    now,
                    ids,
                ),
            ]
        ),
        encoding="utf-8",
    )

    return (
        ids,
        ad_admin_jobs,
        deleted_jobs,
    )


def _build(
    tmp_path: Path,
    now: datetime,
):
    (
        ids,
        ad_admin_jobs,
        deleted_jobs,
    ) = _write_sources(
        tmp_path,
        now,
    )

    ticket_registry = (
        tmp_path
        / "restore-ticket-registry.json"
    )

    consumption_registry = (
        tmp_path
        / "restore-ticket-consumption.json"
    )

    challenge = (
        build_ad_deleted_object_restore_ticket_challenge(
            ad_admin_jobs_file=(
                ad_admin_jobs
            ),
            deleted_object_jobs_file=(
                deleted_jobs
            ),
            ticket_registry_file=(
                ticket_registry
            ),
            ticket_consumption_registry_file=(
                consumption_registry
            ),
            simulation_job_id=(
                ids["simulation"]
            ),
            fresh_live_job_id=(
                ids["fresh_live"]
            ),
            current_mode="Simulation",
            now=now,
        )
    )

    return (
        challenge,
        ids,
        ad_admin_jobs,
        deleted_jobs,
        ticket_registry,
        consumption_registry,
    )


def test_real_ticket_challenge_chain_is_non_authorizing(
    tmp_path: Path,
):
    now = datetime.now(
        timezone.utc
    )

    (
        challenge,
        ids,
        _,
        _,
        ticket_registry,
        consumption_registry,
    ) = _build(
        tmp_path,
        now,
    )

    assert (
        challenge.contract_version
        == AD_DELETED_OBJECT_RESTORE_TICKET_CHALLENGE_CONTRACT_VERSION
    )

    assert (
        challenge.state
        == "restore_ticket_challenge_ready"
    )

    assert (
        challenge.source_simulation_job_id
        == ids["simulation"]
    )

    assert (
        challenge.fresh_live_job_id
        == ids["fresh_live"]
    )

    assert (
        challenge.object_guid
        == GUID
    )

    assert (
        challenge.object_class
        == "group"
    )

    assert (
        challenge.class_policy
        == "standard_controlled"
    )

    assert (
        challenge.effective_new_name
        == NAME
    )

    assert (
        challenge.effective_target_path
        == TARGET
    )

    assert (
        challenge.one_shot_required
        is True
    )

    assert (
        challenge.human_authorized
        is False
    )

    assert (
        challenge.runtime_authorized
        is False
    )

    assert (
        challenge.production_authorized
        is False
    )

    assert (
        challenge.restore_authorized
        is False
    )

    assert (
        challenge.restore_whatif_authorized
        is False
    )

    assert (
        challenge.execution_authorized
        is False
    )

    assert (
        challenge.write_performed
        is False
    )

    assert len(
        challenge.ticket_digest
    ) == 64

    assert len(
        challenge.consumption_record_digest
    ) == 64

    assert len(
        challenge.challenge_digest
    ) == 64

    assert ticket_registry.exists()
    assert consumption_registry.exists()

    assert (
        ticket_registry.stat().st_mode
        & 0o777
    ) == 0o600

    assert (
        consumption_registry.stat().st_mode
        & 0o777
    ) == 0o600

    ticket_data = json.loads(
        ticket_registry.read_text(
            encoding="utf-8"
        )
    )

    consumption_data = json.loads(
        consumption_registry.read_text(
            encoding="utf-8"
        )
    )

    assert len(
        ticket_data["records"]
    ) == 1

    assert len(
        consumption_data["records"]
    ) == 1

    assert (
        ticket_data["records"][0][
            "source_simulation_job_id"
        ]
        == ids["simulation"]
    )

    assert (
        consumption_data["records"][0][
            "source_simulation_job_id"
        ]
        == ids["simulation"]
    )

    assert_ad_deleted_object_restore_ticket_challenge_invariants(
        challenge
    )


def test_same_simulation_cannot_issue_second_challenge(
    tmp_path: Path,
):
    now = datetime.now(
        timezone.utc
    )

    (
        _,
        ids,
        ad_admin_jobs,
        deleted_jobs,
        ticket_registry,
        consumption_registry,
    ) = _build(
        tmp_path,
        now,
    )

    with pytest.raises(
        AdDeletedObjectRestoreTicketChallengeConflict,
        match="already used",
    ):
        build_ad_deleted_object_restore_ticket_challenge(
            ad_admin_jobs_file=(
                ad_admin_jobs
            ),
            deleted_object_jobs_file=(
                deleted_jobs
            ),
            ticket_registry_file=(
                ticket_registry
            ),
            ticket_consumption_registry_file=(
                consumption_registry
            ),
            simulation_job_id=(
                ids["simulation"]
            ),
            fresh_live_job_id=(
                ids["fresh_live"]
            ),
            current_mode="Simulation",
            now=(
                now
                + timedelta(
                    seconds=1
                )
            ),
        )

    ticket_data = json.loads(
        ticket_registry.read_text(
            encoding="utf-8"
        )
    )

    consumption_data = json.loads(
        consumption_registry.read_text(
            encoding="utf-8"
        )
    )

    assert len(
        ticket_data["records"]
    ) == 1

    assert len(
        consumption_data["records"]
    ) == 1


def test_production_rejected_before_any_persistence(
    tmp_path: Path,
):
    now = datetime.now(
        timezone.utc
    )

    (
        ids,
        ad_admin_jobs,
        deleted_jobs,
    ) = _write_sources(
        tmp_path,
        now,
    )

    ticket_registry = (
        tmp_path
        / "restore-ticket-registry.json"
    )

    consumption_registry = (
        tmp_path
        / "restore-ticket-consumption.json"
    )

    with pytest.raises(
        AdDeletedObjectRestoreTicketChallengeError,
        match="Simulation-only",
    ):
        build_ad_deleted_object_restore_ticket_challenge(
            ad_admin_jobs_file=(
                ad_admin_jobs
            ),
            deleted_object_jobs_file=(
                deleted_jobs
            ),
            ticket_registry_file=(
                ticket_registry
            ),
            ticket_consumption_registry_file=(
                consumption_registry
            ),
            simulation_job_id=(
                ids["simulation"]
            ),
            fresh_live_job_id=(
                ids["fresh_live"]
            ),
            current_mode="Production",
            now=now,
        )

    assert not ticket_registry.exists()
    assert not consumption_registry.exists()

    assert not (
        tmp_path
        / ".ad-deleted-object-restore-ticket-challenge.lock"
    ).exists()


def test_challenge_digest_detects_mutation(
    tmp_path: Path,
):
    now = datetime.now(
        timezone.utc
    )

    challenge = _build(
        tmp_path,
        now,
    )[0]

    unsafe = replace(
        challenge,
        runtime_authorized=True,
    )

    with pytest.raises(
        AdDeletedObjectRestoreTicketChallengeError,
        match="unsafe ticket challenge flag",
    ):
        assert_ad_deleted_object_restore_ticket_challenge_invariants(
            unsafe
        )


def test_service_contains_no_restore_or_runtime_transport_primitive():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_ticket_challenge.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden_restore = (
        "Restore"
        + "-ADObject"
    )

    assert forbidden_restore not in source

    for forbidden in (
        "queue_ad_deleted_object_restore_execution",
        "build_ad_deleted_object_restore_runtime_gate",
        "build_ad_deleted_object_restore_execution_ticket",
        "consume_ad_deleted_object_restore_execution_ticket",
        "build_ad_deleted_object_restore_windows_execution_envelope",
    ):
        assert forbidden not in source


def test_main_does_not_expose_ticket_challenge_or_ticket_primitives():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "service_build_ad_deleted_object_restore_ticket_challenge"
        in source
    )

    assert (
        "build_ad_deleted_object_restore_ticket("
        not in source
    )

    assert (
        "persist_ad_deleted_object_restore_ticket("
        not in source
    )

    assert (
        "consume_ad_deleted_object_restore_ticket("
        not in source
    )
