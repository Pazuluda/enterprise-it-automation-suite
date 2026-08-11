from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from fastapi import HTTPException

import main as api_main


SIMULATION_ID = (
    "11111111-1111-4111-8111-111111111111"
)

FRESH_ID = (
    "22222222-2222-4222-8222-222222222222"
)


def identity():
    return SimpleNamespace(
        subject="oidc-subject",
        username="ultraadmin",
        issuer="https://identity.example.test",
        azp="eitas-portal",
    )


def challenge():
    return SimpleNamespace(
        contract_version="c9.5r2e1d1-v1",
        challenge_id=(
            "33333333-3333-4333-8333-333333333333"
        ),
        state="restore_ticket_challenge_ready",

        ticket_persistence_contract_version="test",
        ticket_id=(
            "44444444-4444-4444-8444-444444444444"
        ),
        ticket_digest="a" * 64,

        ticket_consumption_contract_version="test",
        consumption_id=(
            "55555555-5555-4555-8555-555555555555"
        ),
        consumption_record_digest="b" * 64,

        source_simulation_job_id=SIMULATION_ID,
        source_inventory_job_id=(
            "66666666-6666-4666-8666-666666666666"
        ),
        source_live_job_id=(
            "77777777-7777-4777-8777-777777777777"
        ),
        fresh_live_job_id=FRESH_ID,
        fresh_live_sha256="c" * 64,

        object_guid=(
            "88888888-8888-4888-8888-888888888888"
        ),
        object_class="group",
        class_policy="standard_controlled",

        effective_new_name="GG_C95_RECYCLE_TEST",
        effective_target_path=(
            "OU=test,OU=Users,OU=EITAS,"
            "DC=API,DC=LOCAL"
        ),

        created_at="2026-08-11T09:00:00+00:00",

        one_shot_required=True,

        human_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        restore_authorized=False,
        restore_whatif_authorized=False,
        execution_authorized=False,
        write_performed=False,
    )


def test_route_calls_only_high_level_challenge_service(
    monkeypatch,
):
    captured = {}

    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_server_mode",
        lambda: "Simulation",
    )

    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_oidc_actor",
        lambda value: {
            "subject": value.subject,
            "username": value.username,
            "issuer": value.issuer,
            "azp": value.azp,
        },
    )

    def fake_service(**kwargs):
        captured.update(
            kwargs
        )
        return challenge()

    monkeypatch.setattr(
        api_main,
        "service_build_ad_deleted_object_restore_ticket_challenge",
        fake_service,
    )

    audits = []

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs: audits.append(
            kwargs
        ),
    )

    response = (
        api_main.create_deleted_object_restore_ticket_challenge_api(
            {
                "simulation_job_id":
                    SIMULATION_ID,

                "fresh_live_job_id":
                    FRESH_ID,
            },
            identity=identity(),
        )
    )

    assert (
        response["state"]
        == "restore_ticket_challenge_ready"
    )

    assert (
        response["runtime_authorized"]
        is False
    )

    assert (
        response["production_authorized"]
        is False
    )

    assert (
        response["restore_authorized"]
        is False
    )

    assert (
        response["execution_authorized"]
        is False
    )

    assert (
        response["write_performed"]
        is False
    )

    assert (
        captured["simulation_job_id"]
        == SIMULATION_ID
    )

    assert (
        captured["fresh_live_job_id"]
        == FRESH_ID
    )

    assert (
        captured["current_mode"]
        == "Simulation"
    )

    assert (
        captured["ad_admin_jobs_file"]
        == api_main.AD_ADMIN_JOBS_FILE
    )

    assert (
        captured["deleted_object_jobs_file"]
        == api_main.AD_EXPLORER_JOBS_FILE
    )

    assert (
        captured["ticket_registry_file"]
        == api_main.AD_DELETED_OBJECT_RESTORE_TICKET_FILE
    )

    assert (
        captured["ticket_consumption_registry_file"]
        == api_main.AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_FILE
    )

    assert len(
        audits
    ) == 1

    details = audits[0]["details"]

    assert (
        details["runtime_authorized"]
        is False
    )

    assert (
        details["production_authorized"]
        is False
    )

    assert (
        details["restore_authorized"]
        is False
    )

    assert (
        details["execution_authorized"]
        is False
    )

    assert (
        details["write_performed"]
        is False
    )


def test_client_cannot_spoof_mode_or_authorization(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        api_main,
        "service_build_ad_deleted_object_restore_ticket_challenge",
        lambda **kwargs: calls.append(
            kwargs
        ),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.create_deleted_object_restore_ticket_challenge_api(
            {
                "simulation_job_id":
                    SIMULATION_ID,

                "fresh_live_job_id":
                    FRESH_ID,

                "mode":
                    "Production",

                "restore_authorized":
                    True,
            },
            identity=identity(),
        )

    assert (
        captured.value.status_code
        == 400
    )

    assert calls == []


def test_server_production_mode_is_rejected_before_service(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_server_mode",
        lambda: "Production",
    )

    monkeypatch.setattr(
        api_main,
        "service_build_ad_deleted_object_restore_ticket_challenge",
        lambda **kwargs: calls.append(
            kwargs
        ),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.create_deleted_object_restore_ticket_challenge_api(
            {
                "simulation_job_id":
                    SIMULATION_ID,

                "fresh_live_job_id":
                    FRESH_ID,
            },
            identity=identity(),
        )

    assert (
        captured.value.status_code
        == 409
    )

    assert calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {
            "fresh_live_job_id":
                FRESH_ID,
        },
        {
            "simulation_job_id":
                SIMULATION_ID,
        },
    ],
)
def test_required_ids_are_enforced(
    payload,
):
    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.create_deleted_object_restore_ticket_challenge_api(
            payload,
            identity=identity(),
        )

    assert (
        captured.value.status_code
        == 400
    )


def test_route_maps_service_conflict_to_409(
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_server_mode",
        lambda: "Simulation",
    )

    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_oidc_actor",
        lambda value: {
            "subject": value.subject,
            "username": value.username,
            "issuer": value.issuer,
            "azp": value.azp,
        },
    )

    def conflict(**kwargs):
        raise (
            api_main
            .AdDeletedObjectRestoreTicketChallengeConflict(
                "already used"
            )
        )

    monkeypatch.setattr(
        api_main,
        "service_build_ad_deleted_object_restore_ticket_challenge",
        conflict,
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.create_deleted_object_restore_ticket_challenge_api(
            {
                "simulation_job_id":
                    SIMULATION_ID,

                "fresh_live_job_id":
                    FRESH_ID,
            },
            identity=identity(),
        )

    assert (
        captured.value.status_code
        == 409
    )


def test_main_exposes_high_level_route_but_not_ticket_primitives():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '"/api/ad-admin/deleted-object-restore/ticket-challenge"'
        in source
    )

    route_index = source.index(
        '"/api/ad-admin/deleted-object-restore/ticket-challenge"'
    )

    nearby = source[
        route_index:
        route_index + 5200
    ]

    assert (
        "identity=Depends(AD_ACCESS)"
        in nearby
    )

    assert (
        "service_build_ad_deleted_object_restore_ticket_challenge"
        in nearby
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

    for forbidden in (
        "service_build_ad_deleted_object_restore_runtime_gate",
        "service_build_ad_deleted_object_restore_execution_ticket",
        "service_consume_ad_deleted_object_restore_execution_ticket",
    ):
        assert forbidden not in nearby
