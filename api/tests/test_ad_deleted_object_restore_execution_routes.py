from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from fastapi import HTTPException

import main as api_main

from app.core import security
from app.core.security import AuthenticatedIdentity


WORKER_KEY = (
    "unit-test-worker-key-1234567890"
)


def _oidc_identity():
    return AuthenticatedIdentity(
        auth_type="oidc",
        subject="oidc-subject-123",
        username="eitas-admin",
        roles=frozenset(
            {
                "ADAdmin",
            }
        ),
        claims={
            "iss":
                "https://identity.example.invalid/"
                "realms/eitas",

            "azp":
                "eitas-portal",
        },
    )


def test_strict_worker_auth_accepts_valid_x_api_key(
    monkeypatch,
):
    monkeypatch.setattr(
        security,
        "API_KEY",
        WORKER_KEY,
    )

    identity = (
        security.require_worker_api_key(
            x_api_key=WORKER_KEY,
            authorization=None,
        )
    )

    assert identity.auth_type == "api_key"
    assert identity.subject == "worker-api-key"
    assert identity.roles == frozenset()


def test_strict_worker_auth_rejects_bearer_even_with_valid_worker_key(
    monkeypatch,
):
    monkeypatch.setattr(
        security,
        "API_KEY",
        WORKER_KEY,
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        security.require_worker_api_key(
            x_api_key=WORKER_KEY,
            authorization="Bearer anything",
        )

    assert captured.value.status_code == 401


def test_strict_worker_auth_rejects_wrong_key(
    monkeypatch,
):
    monkeypatch.setattr(
        security,
        "API_KEY",
        WORKER_KEY,
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        security.require_worker_api_key(
            x_api_key="wrong-worker-key",
            authorization=None,
        )

    assert captured.value.status_code == 401


def test_restore_routes_use_oidc_for_human_and_strict_key_for_worker():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '"/api/ad-admin/deleted-object-restore/execution/queue"'
        in source
    )

    assert (
        "identity=Depends(AD_ACCESS)"
        in source
    )

    assert (
        '"/api/agent/deleted-object-restore/execution/pending"'
        in source
    )

    assert (
        '"/api/agent/deleted-object-restore/execution/claim/"'
        in source
    )

    assert source.count(
        "require_worker_api_key"
    ) >= 3


def test_human_queue_rejects_client_mode_spoof():
    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.queue_deleted_object_restore_execution_api(
            {
                "execution_consumption_id":
                    "11111111-1111-4111-8111-111111111111",

                "confirmation_text":
                    "anything",

                "mode":
                    "Production",
            },
            identity=_oidc_identity(),
        )

    assert captured.value.status_code == 400

    assert (
        "mode"
        in str(
            captured.value.detail
        )
    )


def test_human_queue_uses_server_mode_actor_and_server_secret(
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "API_KEY",
        WORKER_KEY,
    )

    monkeypatch.setattr(
        api_main,
        "_eitas_agent_mode_load_config",
        lambda: {
            "mode":
                "Simulation",
        },
    )

    source = SimpleNamespace(
        execution_consumption_id=(
            "11111111-1111-4111-8111-111111111111"
        ),
    )

    captured = {}

    def fake_get(
        *,
        consumption_registry_file,
        execution_consumption_id,
    ):
        captured[
            "lookup_file"
        ] = consumption_registry_file

        captured[
            "lookup_id"
        ] = execution_consumption_id

        return source

    def fake_build(
        received_source,
        *,
        server_actor,
        signing_secret,
        current_mode,
        confirmation_text,
    ):
        assert received_source is source

        captured["actor"] = server_actor
        captured["secret"] = signing_secret
        captured["mode"] = current_mode
        captured["confirmation"] = confirmation_text

        return SimpleNamespace(
            envelope_id=(
                "22222222-2222-4222-8222-222222222222"
            ),
        )

    ticket = SimpleNamespace(
        contract_version="c9.5a5e2-v1",
        state="restore_execution_pending",

        transport_ticket_id=(
            "33333333-3333-4333-8333-333333333333"
        ),

        envelope_id=(
            "22222222-2222-4222-8222-222222222222"
        ),

        execution_consumption_id=(
            "11111111-1111-4111-8111-111111111111"
        ),

        execution_ticket_id=(
            "44444444-4444-4444-8444-444444444444"
        ),

        object_guid=(
            "b1018519-8b6e-4788-81c8-3108a188e7b4"
        ),

        effective_new_name=(
            "GG_C95_RECYCLE_TEST"
        ),

        effective_target_path=(
            "OU=test,OU=Users,OU=EITAS,"
            "DC=API,DC=LOCAL"
        ),

        created_at="2026-08-10T22:00:00+00:00",
        expires_at="2026-08-10T22:00:10+00:00",
        payload_digest="a" * 64,

        controlled_restore_runtime_authorized=False,
        production_authorized=False,
        write_performed=False,
    )

    def fake_queue(
        envelope,
        *,
        transport_registry_file,
        signing_secret,
        current_mode,
    ):
        captured[
            "transport_file"
        ] = transport_registry_file

        assert envelope.envelope_id == (
            "22222222-2222-4222-8222-222222222222"
        )

        assert signing_secret == WORKER_KEY
        assert current_mode == "Simulation"

        return ticket

    monkeypatch.setattr(
        api_main,
        "service_get_ad_deleted_object_restore_execution_consumption",
        fake_get,
    )

    monkeypatch.setattr(
        api_main,
        "service_build_ad_deleted_object_restore_windows_execution_envelope",
        fake_build,
    )

    monkeypatch.setattr(
        api_main,
        "service_queue_ad_deleted_object_restore_execution",
        fake_queue,
    )

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs: None,
    )

    response = (
        api_main.queue_deleted_object_restore_execution_api(
            {
                "execution_consumption_id":
                    source.execution_consumption_id,

                "confirmation_text":
                    (
                        "RESTORE "
                        "b1018519-8b6e-4788-81c8-3108a188e7b4 "
                        "AS GG_C95_RECYCLE_TEST TO "
                        "OU=test,OU=Users,OU=EITAS,"
                        "DC=API,DC=LOCAL"
                    ),
            },
            identity=_oidc_identity(),
        )
    )

    assert captured["mode"] == "Simulation"
    assert captured["secret"] == WORKER_KEY

    assert captured["actor"] == {
        "subject":
            "oidc-subject-123",

        "username":
            "eitas-admin",

        "issuer":
            "https://identity.example.invalid/"
            "realms/eitas",

        "azp":
            "eitas-portal",
    }

    assert response["state"] == "restore_execution_pending"

    assert (
        response["authorization"][
            "controlled_restore_runtime_authorized"
        ]
        is False
    )

    assert (
        response["authorization"][
            "production_authorized"
        ]
        is False
    )

    assert "payload" not in response
    assert "signature" not in response


def test_human_queue_rejects_server_production_mode(
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "_eitas_agent_mode_load_config",
        lambda: {
            "mode":
                "Production",
        },
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.queue_deleted_object_restore_execution_api(
            {
                "execution_consumption_id":
                    "11111111-1111-4111-8111-111111111111",

                "confirmation_text":
                    "something",
            },
            identity=_oidc_identity(),
        )

    assert captured.value.status_code == 409


def test_pending_route_uses_server_simulation_mode(
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "_eitas_agent_mode_load_config",
        lambda: {
            "mode":
                "Simulation",
        },
    )

    expected = {
        "count": 0,
        "tickets": [],
    }

    monkeypatch.setattr(
        api_main,
        "service_list_pending_ad_deleted_object_restore_executions",
        lambda **kwargs: expected,
    )

    response = (
        api_main.get_pending_deleted_object_restore_executions_api(
            worker=SimpleNamespace(),
        )
    )

    assert response == expected


def test_pending_route_rejects_server_production_mode(
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "_eitas_agent_mode_load_config",
        lambda: {
            "mode":
                "Production",
        },
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.get_pending_deleted_object_restore_executions_api(
            worker=SimpleNamespace(),
        )

    assert captured.value.status_code == 409


def test_claim_route_uses_server_mode_secret_and_returns_payload(
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "API_KEY",
        WORKER_KEY,
    )

    monkeypatch.setattr(
        api_main,
        "_eitas_agent_mode_load_config",
        lambda: {
            "mode":
                "Simulation",
        },
    )

    captured = {}

    claim = SimpleNamespace(
        contract_version=(
            "c9.5a5e2-claim-v1"
        ),

        state=(
            "restore_execution_processing"
        ),

        transport_ticket_id=(
            "11111111-1111-4111-8111-111111111111"
        ),

        transport_execution_id=(
            "22222222-2222-4222-8222-222222222222"
        ),

        envelope_id=(
            "33333333-3333-4333-8333-333333333333"
        ),

        execution_consumption_id=(
            "44444444-4444-4444-8444-444444444444"
        ),

        execution_ticket_id=(
            "55555555-5555-4555-8555-555555555555"
        ),

        claimed_at="2026-08-10T22:00:01+00:00",
        claimed_by="SRV-DC01",
        expires_at="2026-08-10T22:00:10+00:00",

        payload_digest="a" * 64,

        payload={
            "signature":
                "b" * 64,

            "operation":
                "restore_deleted_object_execute",
        },

        controlled_restore_runtime_authorized=True,
        production_authorized=False,
        write_performed=False,
    )

    def fake_claim(
        *,
        transport_registry_file,
        transport_ticket_id,
        agent_name,
        signing_secret,
        current_mode,
    ):
        captured[
            "ticket_id"
        ] = transport_ticket_id

        captured[
            "agent_name"
        ] = agent_name

        captured[
            "secret"
        ] = signing_secret

        captured[
            "mode"
        ] = current_mode

        return claim

    monkeypatch.setattr(
        api_main,
        "service_claim_ad_deleted_object_restore_execution_for_agent",
        fake_claim,
    )

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs: None,
    )

    response = (
        api_main.claim_deleted_object_restore_execution_api(
            claim.transport_ticket_id,
            {
                "agent_name":
                    "SRV-DC01",
            },
            worker=SimpleNamespace(),
        )
    )

    assert captured["mode"] == "Simulation"
    assert captured["secret"] == WORKER_KEY
    assert captured["agent_name"] == "SRV-DC01"

    assert response["payload"] == claim.payload

    assert (
        response["authorization"][
            "controlled_restore_runtime_authorized"
        ]
        is True
    )

    assert (
        response["authorization"][
            "production_authorized"
        ]
        is False
    )

    assert (
        response["authorization"][
            "write_performed"
        ]
        is False
    )
