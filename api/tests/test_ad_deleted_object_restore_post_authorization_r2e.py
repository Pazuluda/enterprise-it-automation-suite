from __future__ import annotations

import hashlib
import json

from pathlib import Path
from types import SimpleNamespace

import pytest

import app.services.ad_deleted_object_restore_post_authorization as m


AUTH_ID = "11111111-1111-4111-8111-111111111111"
FRESH_ID = "22222222-2222-4222-8222-222222222222"
PRE_ID = "33333333-3333-4333-8333-333333333333"
AUTH_CONSUMPTION_ID = "44444444-4444-4444-8444-444444444444"
RUNTIME_ID = "55555555-5555-4555-8555-555555555555"
EXECUTION_TICKET_ID = "66666666-6666-4666-8666-666666666666"
EXECUTION_CONSUMPTION_ID = "77777777-7777-4777-8777-777777777777"

GUID = "b1018519-8b6e-4788-81c8-3108a188e7b4"
DIGEST = "a" * 64
NAME = "GG_C95_RECYCLE_TEST"

TARGET = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

CONFIRMATION = (
    f"RESTORE {GUID} AS {NAME} TO {TARGET}"
)


def actor():
    return {
        "subject": "subject",
        "username": "admin",
        "issuer": "https://issuer.invalid",
        "azp": "eitas-portal",
    }


def authorization():
    return SimpleNamespace(
        authorization_id=AUTH_ID,
        authorization_digest=DIGEST,
        object_guid=GUID,
        object_class="group",
        effective_new_name=NAME,
        effective_target_path=TARGET,
    )


def final_consumption():
    return SimpleNamespace(
        execution_consumption_id=EXECUTION_CONSUMPTION_ID,
        authorization_id=AUTH_ID,
        authorization_digest=DIGEST,
        object_guid=GUID,
        object_class="group",
        effective_new_name=NAME,
        effective_target_path=TARGET,
        confirmation_sha256=hashlib.sha256(
            json.dumps(
                {
                    "confirmation_text":
                        CONFIRMATION,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode(
                "utf-8"
            )
        ).hexdigest(),
        human_authorized=True,
        revalidation_passed=True,
        execution_ticket_consumed=True,
        one_shot_consumption=True,
        route_enabled=False,
        agent_endpoint_enabled=False,
        job_creation_authorized=False,
        claim_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        restore_authorized=False,
        restore_whatif_authorized=False,
        execution_authorized=False,
        write_performed=False,
    )


def test_contract_is_non_runtime():
    assert (
        m.AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_CONTRACT_VERSION
        == "c9.5r2e1d4e3-v1"
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_ROUTE_ENABLED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_AGENT_ENDPOINT_ENABLED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_RUNTIME_AUTHORIZED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_PRODUCTION_AUTHORIZED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_RESTORE_AUTHORIZED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_EXECUTION_AUTHORIZED
        is False
    )

    assert (
        m.AD_DELETED_OBJECT_RESTORE_POST_AUTHORIZATION_WRITE_PERFORMED
        is False
    )


def test_production_rejected_before_authorization_load(
    monkeypatch,
    tmp_path: Path,
):
    called = []

    monkeypatch.setattr(
        m,
        "_load_authorization_record",
        lambda *args, **kwargs:
            called.append("load"),
    )

    with pytest.raises(
        m.AdDeletedObjectRestorePostAuthorizationError
    ):
        m.build_ad_deleted_object_restore_post_authorization_chain(
            authorization_registry_file=tmp_path / "authorization.json",
            authorization_consumption_registry_file=tmp_path / "auth-consumption.json",
            execution_consumption_registry_file=tmp_path / "exec-consumption.json",
            jobs_path=tmp_path / "jobs.json",
            authorization_id=AUTH_ID,
            authorization_digest=DIGEST,
            fresh_live_job_id=FRESH_ID,
            server_actor=actor(),
            current_mode="Production",
        )

    assert called == []


def test_relative_path_rejected():
    with pytest.raises(
        m.AdDeletedObjectRestorePostAuthorizationError
    ):
        m._safe_absolute_path(
            Path("relative.json"),
            field="test",
        )


def test_missing_authorization_registry_is_not_found(
    tmp_path: Path,
):
    with pytest.raises(
        m.AdDeletedObjectRestorePostAuthorizationNotFound
    ):
        m._load_authorization_record(
            tmp_path / "missing.json",
            authorization_id=AUTH_ID,
        )


def test_authorization_digest_mismatch_blocks_chain(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        m,
        "_load_authorization_record",
        lambda *args, **kwargs:
            authorization(),
    )

    called = []

    monkeypatch.setattr(
        m,
        "build_ad_deleted_object_restore_preexecution",
        lambda *args, **kwargs:
            called.append("preexecution"),
    )

    with pytest.raises(
        m.AdDeletedObjectRestorePostAuthorizationConflict
    ):
        m.build_ad_deleted_object_restore_post_authorization_chain(
            authorization_registry_file=tmp_path / "authorization.json",
            authorization_consumption_registry_file=tmp_path / "auth-consumption.json",
            execution_consumption_registry_file=tmp_path / "exec-consumption.json",
            jobs_path=tmp_path / "jobs.json",
            authorization_id=AUTH_ID,
            authorization_digest="b" * 64,
            fresh_live_job_id=FRESH_ID,
            server_actor=actor(),
            current_mode="Simulation",
        )

    assert called == []


def test_exact_orchestration_order(
    monkeypatch,
    tmp_path: Path,
):
    auth = authorization()
    seen = []

    pre = SimpleNamespace(
        preexecution_id=PRE_ID
    )

    auth_consumption = SimpleNamespace(
        authorization_consumption_id=AUTH_CONSUMPTION_ID
    )

    runtime = SimpleNamespace(
        runtime_gate_id=RUNTIME_ID
    )

    execution_ticket = SimpleNamespace(
        execution_ticket_id=EXECUTION_TICKET_ID
    )

    consumption = final_consumption()

    monkeypatch.setattr(
        m,
        "_load_authorization_record",
        lambda *args, **kwargs:
            auth,
    )

    def prebuild(
        authorization_record,
        **kwargs,
    ):
        seen.append("preexecution")

        assert authorization_record is auth
        assert kwargs["fresh_live_job_id"] == FRESH_ID
        assert kwargs["expected_authorization_id"] == AUTH_ID
        assert kwargs["expected_authorization_digest"] == DIGEST
        assert kwargs["expected_object_guid"] == GUID
        assert kwargs["confirmed_new_name"] == NAME
        assert kwargs["confirmed_target_path"] == TARGET

        return pre

    def consume_auth(
        authorization_record,
        preexecution_record,
        **kwargs,
    ):
        seen.append("authorization_consumption")
        assert authorization_record is auth
        assert preexecution_record is pre
        return auth_consumption

    def runtime_build(
        source,
        **kwargs,
    ):
        seen.append("runtime_gate")
        assert source is auth_consumption
        return runtime

    def expected_confirmation(
        source,
    ):
        seen.append("confirmation")
        assert source is runtime
        return CONFIRMATION

    def ticket_build(
        source,
        **kwargs,
    ):
        seen.append("execution_ticket")
        assert source is runtime
        assert kwargs["confirmation_text"] == CONFIRMATION
        return execution_ticket

    def consume_execution(
        source,
        **kwargs,
    ):
        seen.append("execution_consumption")
        assert source is execution_ticket
        return consumption

    monkeypatch.setattr(
        m,
        "build_ad_deleted_object_restore_preexecution",
        prebuild,
    )

    monkeypatch.setattr(
        m,
        "consume_ad_deleted_object_restore_authorization",
        consume_auth,
    )

    monkeypatch.setattr(
        m,
        "build_ad_deleted_object_restore_runtime_gate",
        runtime_build,
    )

    monkeypatch.setattr(
        m,
        "expected_ad_deleted_object_restore_confirmation",
        expected_confirmation,
    )

    monkeypatch.setattr(
        m,
        "build_ad_deleted_object_restore_execution_ticket",
        ticket_build,
    )

    monkeypatch.setattr(
        m,
        "consume_ad_deleted_object_restore_execution_ticket",
        consume_execution,
    )

    monkeypatch.setattr(
        m,
        "assert_ad_deleted_object_restore_execution_consumption_invariants",
        lambda value:
            None,
    )

    result = (
        m.build_ad_deleted_object_restore_post_authorization_chain(
            authorization_registry_file=tmp_path / "authorization.json",
            authorization_consumption_registry_file=tmp_path / "auth-consumption.json",
            execution_consumption_registry_file=tmp_path / "exec-consumption.json",
            jobs_path=tmp_path / "jobs.json",
            authorization_id=AUTH_ID,
            authorization_digest=DIGEST,
            fresh_live_job_id=FRESH_ID,
            server_actor=actor(),
            current_mode="Simulation",
        )
    )

    assert seen == [
        "preexecution",
        "authorization_consumption",
        "runtime_gate",
        "confirmation",
        "execution_ticket",
        "execution_consumption",
    ]

    assert result.authorization_id == AUTH_ID
    assert result.preexecution_id == PRE_ID
    assert result.authorization_consumption_id == AUTH_CONSUMPTION_ID
    assert result.runtime_gate_id == RUNTIME_ID
    assert result.execution_ticket_id == EXECUTION_TICKET_ID
    assert result.execution_consumption_id == EXECUTION_CONSUMPTION_ID
    assert result.confirmation_text == CONFIRMATION

    assert result.human_authorized is True
    assert result.revalidation_passed is True
    assert result.authorization_consumed is True
    assert result.execution_ticket_consumed is True

    assert result.runtime_authorized is False
    assert result.production_authorized is False
    assert result.restore_authorized is False
    assert result.execution_authorized is False
    assert result.write_performed is False


def test_low_level_conflict_is_mapped(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        m,
        "_load_authorization_record",
        lambda *args, **kwargs:
            authorization(),
    )

    def fail(*args, **kwargs):
        raise (
            m.AdDeletedObjectRestorePreexecutionConflict(
                "fresh live rejected"
            )
        )

    monkeypatch.setattr(
        m,
        "build_ad_deleted_object_restore_preexecution",
        fail,
    )

    with pytest.raises(
        m.AdDeletedObjectRestorePostAuthorizationConflict
    ):
        m.build_ad_deleted_object_restore_post_authorization_chain(
            authorization_registry_file=tmp_path / "authorization.json",
            authorization_consumption_registry_file=tmp_path / "auth-consumption.json",
            execution_consumption_registry_file=tmp_path / "exec-consumption.json",
            jobs_path=tmp_path / "jobs.json",
            authorization_id=AUTH_ID,
            authorization_digest=DIGEST,
            fresh_live_job_id=FRESH_ID,
            server_actor=actor(),
            current_mode="Simulation",
        )


def test_bad_final_binding_rejected(
    monkeypatch,
):
    auth = authorization()
    consumption = final_consumption()

    consumption.object_guid = (
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    )

    monkeypatch.setattr(
        m,
        "assert_ad_deleted_object_restore_execution_consumption_invariants",
        lambda value:
            None,
    )

    with pytest.raises(
        m.AdDeletedObjectRestorePostAuthorizationError
    ):
        m._assert_final_consumption(
            consumption,
            authorization=auth,
            confirmation_text=CONFIRMATION,
        )


def test_bad_confirmation_digest_rejected(
    monkeypatch,
):
    auth = authorization()
    consumption = final_consumption()

    consumption.confirmation_sha256 = (
        "f" * 64
    )

    monkeypatch.setattr(
        m,
        "assert_ad_deleted_object_restore_execution_consumption_invariants",
        lambda value:
            None,
    )

    with pytest.raises(
        m.AdDeletedObjectRestorePostAuthorizationError
    ):
        m._assert_final_consumption(
            consumption,
            authorization=auth,
            confirmation_text=CONFIRMATION,
        )


def test_final_consumption_remains_non_authorizing(
    monkeypatch,
):
    auth = authorization()
    consumption = final_consumption()

    consumption.restore_authorized = True

    monkeypatch.setattr(
        m,
        "assert_ad_deleted_object_restore_execution_consumption_invariants",
        lambda value:
            None,
    )

    with pytest.raises(
        m.AdDeletedObjectRestorePostAuthorizationError
    ):
        m._assert_final_consumption(
            consumption,
            authorization=auth,
            confirmation_text=CONFIRMATION,
        )


def test_source_has_no_queue_or_restore_cmdlet():
    source = Path(
        "api/app/services/"
        "ad_deleted_object_restore_post_authorization.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "execution/queue" not in source
    assert "Restore-ADObject" not in source


def test_main_imports_high_level_post_authorization_bridge_only():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "from app.services."
        "ad_deleted_object_restore_post_authorization import ("
        in source
    )

    assert (
        "service_build_ad_deleted_object_restore_post_authorization_chain"
        in source
    )

    forbidden = (
        "build_ad_deleted_object_restore_preexecution(",
        "consume_ad_deleted_object_restore_authorization(",
        "build_ad_deleted_object_restore_runtime_gate(",
        "build_ad_deleted_object_restore_execution_ticket(",
        "consume_ad_deleted_object_restore_execution_ticket(",
    )

    for token in forbidden:
        assert token not in source
