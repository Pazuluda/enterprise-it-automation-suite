from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import app.services.ad_deleted_object_restore_human_authorization as m


TICKET_ID = (
    "11111111-1111-4111-8111-111111111111"
)

CONSUMPTION_ID = (
    "22222222-2222-4222-8222-222222222222"
)

SIMULATION_ID = (
    "33333333-3333-4333-8333-333333333333"
)

INVENTORY_ID = (
    "44444444-4444-4444-8444-444444444444"
)

SOURCE_LIVE_ID = (
    "55555555-5555-4555-8555-555555555555"
)

FRESH_LIVE_ID = (
    "66666666-6666-4666-8666-666666666666"
)

GUID = (
    "b1018519-8b6e-4788-81c8-3108a188e7b4"
)

NAME = "GG_C95_RECYCLE_TEST"

TARGET = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)


def ticket():
    return SimpleNamespace(
        ticket_id=TICKET_ID,
        ticket_digest="a" * 64,
        source_simulation_job_id=SIMULATION_ID,
        source_inventory_job_id=INVENTORY_ID,
        source_live_job_id=SOURCE_LIVE_ID,
        fresh_live_job_id=FRESH_LIVE_ID,
        fresh_live_sha256="b" * 64,
        object_guid=GUID,
        object_class="group",
        class_policy="standard_controlled",
        effective_new_name=NAME,
        effective_target_path=TARGET,
    )


def consumption():
    return SimpleNamespace(
        consumption_id=CONSUMPTION_ID,
        record_digest="c" * 64,
        ticket_id=TICKET_ID,
        ticket_digest="a" * 64,
        source_simulation_job_id=SIMULATION_ID,
    )


def persisted():
    return SimpleNamespace(
        ticket_id=TICKET_ID,
        ticket_digest="a" * 64,
        consumption_id=CONSUMPTION_ID,
        consumption_record_digest="c" * 64,
        source_simulation_job_id=SIMULATION_ID,
        source_inventory_job_id=INVENTORY_ID,
        source_live_job_id=SOURCE_LIVE_ID,
        fresh_live_job_id=FRESH_LIVE_ID,
        fresh_live_sha256="b" * 64,
        object_guid=GUID,
        object_class="group",
        class_policy="standard_controlled",
        effective_new_name=NAME,
        effective_target_path=TARGET,
        one_shot_required=True,
        authorization_consumed=False,
        human_authorized=True,
        route_enabled=False,
        job_creation_authorized=False,
        claim_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        restore_authorized=False,
        restore_whatif_authorized=False,
        execution_authorized=False,
        write_performed=False,
    )


def payload():
    return {
        "ticket_id":
            TICKET_ID,

        "ticket_digest":
            "a" * 64,

        "consumption_id":
            CONSUMPTION_ID,

        "object_guid":
            GUID,

        "effective_new_name":
            NAME,

        "effective_target_path":
            TARGET,

        "acknowledge_exact_object":
            True,

        "acknowledge_exact_target":
            True,

        "acknowledge_restore_write":
            True,

        "authorization_reason":
            "Validation humaine controlee C9.5 R2E.",
    }


def actor():
    return {
        "subject":
            "c95-r2e-subject",

        "username":
            "c95-r2e-admin",

        "issuer":
            "https://issuer.invalid",

        "azp":
            "eitas-portal",
    }


def test_bridge_contract_remains_non_runtime():
    assert (
        m.AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_CONTRACT_VERSION
        == "c9.5r2e1d4e2-v1"
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_ENABLED
        is True
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_ROUTE_ENABLED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_RUNTIME_AUTHORIZED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_PRODUCTION_AUTHORIZED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_RESTORE_AUTHORIZED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_EXECUTION_AUTHORIZED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_HUMAN_AUTHORIZATION_WRITE_PERFORMED
        is False
    )


def test_production_rejected_before_loading_registries(
    monkeypatch,
    tmp_path: Path,
):
    touched = []

    monkeypatch.setattr(
        m,
        "_load_ticket_record",
        lambda *args, **kwargs:
            touched.append(
                "ticket"
            ),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreHumanAuthorizationError
    ):
        (
            m.build_and_persist_ad_deleted_object_restore_human_authorization(
                ticket_registry_file=(
                    tmp_path
                    / "ticket.json"
                ),
                ticket_consumption_registry_file=(
                    tmp_path
                    / "consumption.json"
                ),
                authorization_registry_file=(
                    tmp_path
                    / "authorization.json"
                ),
                server_actor=actor(),
                payload=payload(),
                current_mode="Production",
            )
        )

    assert touched == []


def test_missing_ticket_registry_is_not_found(
    tmp_path: Path,
):
    with pytest.raises(
        m.AdDeletedObjectRestoreHumanAuthorizationNotFound
    ):
        m._load_ticket_record(
            tmp_path / "missing-ticket.json",
            ticket_id=TICKET_ID,
        )


def test_relative_registry_path_rejected():
    with pytest.raises(
        m.AdDeletedObjectRestoreHumanAuthorizationError
    ):
        m._assert_absolute_path(
            Path(
                "relative.json"
            ),
            field="test",
        )


def test_symlink_registry_path_rejected(
    tmp_path: Path,
):
    target = (
        tmp_path
        / "target.json"
    )

    target.write_text(
        "{}",
        encoding="utf-8",
    )

    link = (
        tmp_path
        / "link.json"
    )

    link.symlink_to(
        target
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreHumanAuthorizationError
    ):
        m._assert_absolute_path(
            link,
            field="test",
        )


def test_wrong_registry_contract_is_rejected(
    tmp_path: Path,
):
    path = (
        tmp_path
        / "ticket.json"
    )

    path.write_text(
        (
            '{"contract_version":"wrong",'
            '"records":[]}'
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreHumanAuthorizationError
    ):
        m._load_registry_records(
            path,
            field="test",
            expected_contract_version="expected",
            required=True,
        )


def test_exact_high_level_orchestration(
    monkeypatch,
    tmp_path: Path,
):
    seen = []

    source_ticket = ticket()
    source_consumption = consumption()
    output = persisted()

    monkeypatch.setattr(
        m,
        "_load_ticket_record",
        lambda *args, **kwargs:
            source_ticket,
    )

    monkeypatch.setattr(
        m,
        "_load_consumption_record",
        lambda *args, **kwargs:
            source_consumption,
    )

    monkeypatch.setattr(
        m,
        "_load_authorization_records",
        lambda *args, **kwargs:
            [],
    )

    def fake_build(
        ticket_record,
        consumption_record,
        *,
        server_actor,
        payload,
        current_mode,
        now=None,
    ):
        seen.append(
            (
                "build",
                ticket_record,
                consumption_record,
                server_actor,
                payload,
                current_mode,
            )
        )

        return SimpleNamespace(
            authorization_id=(
                "77777777-7777-4777-8777-777777777777"
            )
        )

    def fake_persist(
        authorization,
        *,
        registry_file,
        now=None,
    ):
        seen.append(
            (
                "persist",
                authorization,
                registry_file,
            )
        )

        return output

    monkeypatch.setattr(
        m,
        "build_ad_deleted_object_restore_authorization",
        fake_build,
    )

    monkeypatch.setattr(
        m,
        "persist_ad_deleted_object_restore_authorization",
        fake_persist,
    )

    monkeypatch.setattr(
        m,
        "assert_ad_deleted_object_restore_authorization_persistence_invariants",
        lambda value:
            None,
    )

    result = (
        m.build_and_persist_ad_deleted_object_restore_human_authorization(
            ticket_registry_file=(
                tmp_path
                / "ticket.json"
            ),
            ticket_consumption_registry_file=(
                tmp_path
                / "consumption.json"
            ),
            authorization_registry_file=(
                tmp_path
                / "authorization.json"
            ),
            server_actor=actor(),
            payload=payload(),
            current_mode="Simulation",
        )
    )

    assert result is output

    assert [
        item[0]
        for item in seen
    ] == [
        "build",
        "persist",
    ]

    assert (
        seen[0][1]
        is source_ticket
    )

    assert (
        seen[0][2]
        is source_consumption
    )

    assert (
        seen[0][3]
        == actor()
    )

    assert (
        seen[0][4]
        == payload()
    )

    assert (
        seen[0][5]
        == "Simulation"
    )


def test_existing_authorization_blocks_replay(
    monkeypatch,
    tmp_path: Path,
):
    source_ticket = ticket()
    source_consumption = consumption()

    existing = SimpleNamespace(
        ticket_id=TICKET_ID,
        consumption_id=CONSUMPTION_ID,
        source_simulation_job_id=SIMULATION_ID,
    )

    monkeypatch.setattr(
        m,
        "_load_ticket_record",
        lambda *args, **kwargs:
            source_ticket,
    )

    monkeypatch.setattr(
        m,
        "_load_consumption_record",
        lambda *args, **kwargs:
            source_consumption,
    )

    monkeypatch.setattr(
        m,
        "_load_authorization_records",
        lambda *args, **kwargs:
            [
                existing,
            ],
    )

    called = []

    monkeypatch.setattr(
        m,
        "build_ad_deleted_object_restore_authorization",
        lambda *args, **kwargs:
            called.append(
                "build"
            ),
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreHumanAuthorizationConflict
    ):
        (
            m.build_and_persist_ad_deleted_object_restore_human_authorization(
                ticket_registry_file=(
                    tmp_path
                    / "ticket.json"
                ),
                ticket_consumption_registry_file=(
                    tmp_path
                    / "consumption.json"
                ),
                authorization_registry_file=(
                    tmp_path
                    / "authorization.json"
                ),
                server_actor=actor(),
                payload=payload(),
                current_mode="Simulation",
            )
        )

    assert called == []


def test_ticket_consumption_mismatch_rejected(
    monkeypatch,
    tmp_path: Path,
):
    source_ticket = ticket()

    source_consumption = (
        consumption()
    )

    source_consumption.ticket_digest = (
        "f" * 64
    )

    monkeypatch.setattr(
        m,
        "_load_ticket_record",
        lambda *args, **kwargs:
            source_ticket,
    )

    monkeypatch.setattr(
        m,
        "_load_consumption_record",
        lambda *args, **kwargs:
            source_consumption,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreHumanAuthorizationConflict
    ):
        (
            m.build_and_persist_ad_deleted_object_restore_human_authorization(
                ticket_registry_file=(
                    tmp_path
                    / "ticket.json"
                ),
                ticket_consumption_registry_file=(
                    tmp_path
                    / "consumption.json"
                ),
                authorization_registry_file=(
                    tmp_path
                    / "authorization.json"
                ),
                server_actor=actor(),
                payload=payload(),
                current_mode="Simulation",
            )
        )


def test_builder_conflict_is_mapped(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        m,
        "_load_ticket_record",
        lambda *args, **kwargs:
            ticket(),
    )

    monkeypatch.setattr(
        m,
        "_load_consumption_record",
        lambda *args, **kwargs:
            consumption(),
    )

    monkeypatch.setattr(
        m,
        "_load_authorization_records",
        lambda *args, **kwargs:
            [],
    )

    def fail(*args, **kwargs):
        raise (
            m.AdDeletedObjectRestoreAuthorizationConflict(
                "expired"
            )
        )

    monkeypatch.setattr(
        m,
        "build_ad_deleted_object_restore_authorization",
        fail,
    )

    with pytest.raises(
        m.AdDeletedObjectRestoreHumanAuthorizationConflict
    ):
        (
            m.build_and_persist_ad_deleted_object_restore_human_authorization(
                ticket_registry_file=(
                    tmp_path
                    / "ticket.json"
                ),
                ticket_consumption_registry_file=(
                    tmp_path
                    / "consumption.json"
                ),
                authorization_registry_file=(
                    tmp_path
                    / "authorization.json"
                ),
                server_actor=actor(),
                payload=payload(),
                current_mode="Simulation",
            )
        )


def test_source_contains_no_restore_or_execution_path():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_human_authorization.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "Restore" + "-ADObject"
        not in source
    )

    assert (
        "execution/queue"
        not in source
    )

    assert (
        "Restore-ADObject"
        not in source
    )
