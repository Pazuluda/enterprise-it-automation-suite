from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from fastapi import HTTPException

import main as api_main


ROUTE = (
    "/api/ad-admin/"
    "deleted-object-restore/"
    "authorization"
)

TICKET_ID = (
    "11111111-1111-4111-8111-111111111111"
)

CONSUMPTION_ID = (
    "22222222-2222-4222-8222-222222222222"
)

SIMULATION_ID = (
    "33333333-3333-4333-8333-333333333333"
)

FRESH_LIVE_ID = (
    "44444444-4444-4444-8444-444444444444"
)

AUTHORIZATION_ID = (
    "55555555-5555-4555-8555-555555555555"
)

GUID = (
    "b1018519-8b6e-4788-81c8-3108a188e7b4"
)

NAME = "GG_C95_RECYCLE_TEST"

TARGET = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
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
            "c95-route-subject",

        "username":
            "c95-route-admin",

        "issuer":
            "https://issuer.invalid",

        "azp":
            "eitas-portal",
    }


def authorization():
    return SimpleNamespace(
        authorization_id=AUTHORIZATION_ID,
        authorization_digest="b" * 64,
        ticket_id=TICKET_ID,
        ticket_digest="a" * 64,
        consumption_id=CONSUMPTION_ID,
        source_simulation_job_id=SIMULATION_ID,
        fresh_live_job_id=FRESH_LIVE_ID,
        object_guid=GUID,
        object_class="group",
        effective_new_name=NAME,
        effective_target_path=TARGET,
        human_authorized=True,
        authorization_consumed=False,
        runtime_authorized=False,
        production_authorized=False,
        restore_authorized=False,
        restore_whatif_authorized=False,
        execution_authorized=False,
        write_performed=False,
        expires_at="2026-08-11T12:00:00+00:00",
    )


def test_source_contains_exact_human_authorization_route():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    assert source.count(
        f'"{ROUTE}"'
    ) == 1

    assert (
        "def "
        "create_deleted_object_restore_human_authorization_api("
        in source
    )


def test_route_uses_ad_access_and_high_level_bridge_only():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        "def "
        "create_deleted_object_restore_human_authorization_api("
    )

    start = source.index(
        marker
    )

    end = source.index(
        '@app.post(\n'
        '    "/api/ad-admin/'
        'deleted-object-restore/execution/queue"',
        start,
    )

    route = source[
        start:end
    ]

    assert (
        "identity=Depends(AD_ACCESS)"
        in route
    )

    assert (
        "service_build_and_persist_"
        "ad_deleted_object_restore_human_authorization("
        in route
    )

    forbidden = (
        "build_ad_deleted_object_restore_authorization(",
        "persist_ad_deleted_object_restore_authorization(",
        "build_ad_deleted_object_restore_preexecution(",
        "consume_ad_deleted_object_restore_authorization(",
        "build_ad_deleted_object_restore_runtime_gate(",
        "require_roles_or_api_key",
        "Depends(require_api_key)",
        "SECURITY_OR_API_KEY_ACCESS",
    )

    for token in forbidden:
        assert token not in route


def test_route_payload_surface_is_exact():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        "def "
        "create_deleted_object_restore_human_authorization_api("
    )

    start = source.index(
        marker
    )

    end = source.index(
        "unexpected_fields = sorted(",
        start,
    )

    prefix = source[
        start:end
    ]

    expected = {
        "ticket_id",
        "ticket_digest",
        "consumption_id",
        "object_guid",
        "effective_new_name",
        "effective_target_path",
        "acknowledge_exact_object",
        "acknowledge_exact_target",
        "acknowledge_restore_write",
        "authorization_reason",
    }

    for field in expected:
        assert (
            f'"{field}"'
            in prefix
        )

    forbidden = (
        "actor",
        "server_actor",
        "current_mode",
        "mode",
        "human_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "restore_whatif_authorized",
        "execution_authorized",
        "write_authorized",
        "write_performed",
    )

    allowed_block = prefix[
        prefix.index(
            "allowed_fields = {"
        ):
    ]

    for field in forbidden:
        assert (
            f'"{field}"'
            not in allowed_block
        )


@pytest.mark.parametrize(
    "field",
    [
        "actor",
        "mode",
        "human_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "execution_authorized",
        "write_authorized",
    ],
)
def test_server_owned_fields_are_rejected_before_service(
    monkeypatch,
    field: str,
):
    called = []

    monkeypatch.setattr(
        api_main,
        "service_build_and_persist_ad_deleted_object_restore_human_authorization",
        lambda **kwargs:
            called.append(
                kwargs
            ),
    )

    supplied = payload()
    supplied[field] = True

    with pytest.raises(
        HTTPException
    ) as captured:
        (
            api_main
            .create_deleted_object_restore_human_authorization_api(
                supplied,
                identity=object(),
            )
        )

    assert (
        captured.value.status_code
        == 400
    )

    assert called == []


def test_non_simulation_mode_rejected_before_actor_and_service(
    monkeypatch,
):
    actor_called = []
    service_called = []

    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_server_mode",
        lambda:
            "Production",
    )

    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_oidc_actor",
        lambda identity:
            actor_called.append(
                identity
            ),
    )

    monkeypatch.setattr(
        api_main,
        "service_build_and_persist_ad_deleted_object_restore_human_authorization",
        lambda **kwargs:
            service_called.append(
                kwargs
            ),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        (
            api_main
            .create_deleted_object_restore_human_authorization_api(
                payload(),
                identity=object(),
            )
        )

    assert (
        captured.value.status_code
        == 409
    )

    assert actor_called == []
    assert service_called == []


def test_success_uses_server_actor_mode_and_exact_registry_paths(
    monkeypatch,
):
    seen = {}
    audits = []

    result = authorization()

    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_server_mode",
        lambda:
            "Simulation",
    )

    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_oidc_actor",
        lambda identity:
            actor(),
    )

    def fake_service(**kwargs):
        seen.update(
            kwargs
        )

        return result

    monkeypatch.setattr(
        api_main,
        "service_build_and_persist_ad_deleted_object_restore_human_authorization",
        fake_service,
    )

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs:
            audits.append(
                kwargs
            ),
    )

    request_payload = payload()

    response = (
        api_main
        .create_deleted_object_restore_human_authorization_api(
            request_payload,
            identity=object(),
        )
    )

    assert (
        seen["ticket_registry_file"]
        == api_main.AD_DELETED_OBJECT_RESTORE_TICKET_FILE
    )

    assert (
        seen["ticket_consumption_registry_file"]
        == api_main.AD_DELETED_OBJECT_RESTORE_TICKET_CONSUMPTION_FILE
    )

    assert (
        seen["authorization_registry_file"]
        == api_main.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_FILE
    )

    assert (
        seen["server_actor"]
        == actor()
    )

    assert (
        seen["payload"]
        is request_payload
    )

    assert (
        seen["current_mode"]
        == "Simulation"
    )

    assert (
        response["authorization_id"]
        == AUTHORIZATION_ID
    )

    assert response[
        "human_authorized"
    ] is True

    assert response[
        "authorization_consumed"
    ] is False

    assert response[
        "runtime_authorized"
    ] is False

    assert response[
        "production_authorized"
    ] is False

    assert response[
        "restore_authorized"
    ] is False

    assert response[
        "execution_authorized"
    ] is False

    assert response[
        "write_performed"
    ] is False

    assert len(
        audits
    ) == 1

    audit = audits[0]

    assert (
        audit["action"]
        == "ad_deleted_object_restore_human_authorization_created"
    )

    assert (
        audit["request_id"]
        == AUTHORIZATION_ID
    )

    assert (
        audit["actor"]
        == actor()["username"]
    )

    details = audit[
        "details"
    ]

    assert details[
        "human_authorized"
    ] is True

    assert details[
        "authorization_consumed"
    ] is False

    assert details[
        "runtime_authorized"
    ] is False

    assert details[
        "production_authorized"
    ] is False

    assert details[
        "restore_authorized"
    ] is False

    assert details[
        "execution_authorized"
    ] is False

    assert details[
        "write_performed"
    ] is False

    assert (
        "authorization_reason"
        not in details
    )

    assert (
        "ticket_digest"
        not in details
    )

    assert (
        "authorization_digest"
        not in details
    )


@pytest.mark.parametrize(
    "exception,status",
    [
        (
            api_main.AdDeletedObjectRestoreHumanAuthorizationNotFound(
                "missing"
            ),
            404,
        ),
        (
            api_main.AdDeletedObjectRestoreHumanAuthorizationConflict(
                "conflict"
            ),
            409,
        ),
        (
            api_main.AdDeletedObjectRestoreHumanAuthorizationError(
                "invalid"
            ),
            400,
        ),
    ],
)
def test_bridge_errors_map_to_http(
    monkeypatch,
    exception,
    status: int,
):
    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_server_mode",
        lambda:
            "Simulation",
    )

    monkeypatch.setattr(
        api_main,
        "_eitas_controlled_restore_oidc_actor",
        lambda identity:
            actor(),
    )

    def fail(**kwargs):
        raise exception

    monkeypatch.setattr(
        api_main,
        "service_build_and_persist_ad_deleted_object_restore_human_authorization",
        fail,
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        (
            api_main
            .create_deleted_object_restore_human_authorization_api(
                payload(),
                identity=object(),
            )
        )

    assert (
        captured.value.status_code
        == status
    )


def test_main_contains_no_direct_a4_a5_authorization_primitives():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden_calls = (
        "build_ad_deleted_object_restore_authorization(",
        "persist_ad_deleted_object_restore_authorization(",
        "build_ad_deleted_object_restore_preexecution(",
        "consume_ad_deleted_object_restore_authorization(",
        "build_ad_deleted_object_restore_runtime_gate(",
    )

    for token in forbidden_calls:
        assert token not in source


def test_authorization_registry_is_server_owned_constant():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    expected = '''AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_FILE = (
    DATA_DIR
    / "ad-deleted-object-restore-authorization.json"
)
'''

    assert expected in source
