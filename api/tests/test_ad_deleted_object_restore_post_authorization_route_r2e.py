from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from fastapi import HTTPException

import main as api_main


ROUTE = (
    "/api/ad-admin/"
    "deleted-object-restore/"
    "post-authorization"
)

AUTHORIZATION_ID = (
    "11111111-1111-4111-8111-111111111111"
)

FRESH_LIVE_ID = (
    "22222222-2222-4222-8222-222222222222"
)

PREEXECUTION_ID = (
    "33333333-3333-4333-8333-333333333333"
)

AUTH_CONSUMPTION_ID = (
    "44444444-4444-4444-8444-444444444444"
)

RUNTIME_GATE_ID = (
    "55555555-5555-4555-8555-555555555555"
)

EXECUTION_TICKET_ID = (
    "66666666-6666-4666-8666-666666666666"
)

EXECUTION_CONSUMPTION_ID = (
    "77777777-7777-4777-8777-777777777777"
)

DIGEST = "a" * 64

GUID = (
    "b1018519-8b6e-4788-81c8-3108a188e7b4"
)

NAME = "GG_C95_RECYCLE_TEST"

TARGET = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

CONFIRMATION = (
    f"RESTORE {GUID} AS {NAME} TO {TARGET}"
)


def payload():
    return {
        "authorization_id":
            AUTHORIZATION_ID,

        "authorization_digest":
            DIGEST,

        "fresh_live_job_id":
            FRESH_LIVE_ID,
    }


def actor():
    return {
        "subject":
            "c95-post-auth-subject",

        "username":
            "c95-post-auth-admin",

        "issuer":
            "https://issuer.invalid",

        "azp":
            "eitas-portal",
    }


def result():
    return SimpleNamespace(
        authorization_id=AUTHORIZATION_ID,
        preexecution_id=PREEXECUTION_ID,
        authorization_consumption_id=AUTH_CONSUMPTION_ID,
        runtime_gate_id=RUNTIME_GATE_ID,
        execution_ticket_id=EXECUTION_TICKET_ID,
        execution_consumption_id=EXECUTION_CONSUMPTION_ID,

        object_guid=GUID,
        object_class="group",
        effective_new_name=NAME,
        effective_target_path=TARGET,

        confirmation_text=CONFIRMATION,

        human_authorized=True,
        revalidation_passed=True,
        authorization_consumed=True,
        execution_ticket_consumed=True,

        runtime_authorized=False,
        production_authorized=False,
        restore_authorized=False,
        execution_authorized=False,
        write_performed=False,
    )


def _route_source():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        "def "
        "create_deleted_object_restore_post_authorization_api("
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

    return source[
        start:end
    ]


def test_source_contains_exact_post_authorization_route():
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
        "create_deleted_object_restore_post_authorization_api("
        in source
    )


def test_route_is_between_authorization_and_execution_queue():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    authorization = source.index(
        '"/api/ad-admin/'
        'deleted-object-restore/authorization"'
    )

    post_authorization = source.index(
        f'"{ROUTE}"'
    )

    queue = source.index(
        '"/api/ad-admin/'
        'deleted-object-restore/execution/queue"'
    )

    assert (
        authorization
        < post_authorization
        < queue
    )


def test_route_uses_ad_access_and_high_level_bridge_only():
    route = _route_source()

    assert (
        "identity=Depends(AD_ACCESS)"
        in route
    )

    assert (
        "service_build_"
        "ad_deleted_object_restore_post_authorization_chain("
        in route
    )

    forbidden = (
        "build_ad_deleted_object_restore_preexecution(",
        "consume_ad_deleted_object_restore_authorization(",
        "build_ad_deleted_object_restore_runtime_gate(",
        "build_ad_deleted_object_restore_execution_ticket(",
        "consume_ad_deleted_object_restore_execution_ticket(",
        "service_queue_ad_deleted_object_restore_execution(",
        "_eitas_controlled_restore_signing_secret(",
        "require_worker_api_key",
        "require_roles_or_api_key",
        "API_KEY",
        "Restore-ADObject",
    )

    for token in forbidden:
        assert token not in route


def test_route_payload_surface_is_exact():
    route = _route_source()

    prefix = route[
        :
        route.index(
            "unexpected_fields = sorted("
        )
    ]

    allowed = prefix[
        prefix.index(
            "allowed_fields = {"
        ):
    ]

    expected = {
        "authorization_id",
        "authorization_digest",
        "fresh_live_job_id",
    }

    for field in expected:
        assert (
            f'"{field}"'
            in allowed
        )

    forbidden = (
        "actor",
        "server_actor",
        "current_mode",
        "mode",
        "confirmation_text",
        "execution_consumption_id",
        "human_authorized",
        "runtime_authorized",
        "production_authorized",
        "restore_authorized",
        "execution_authorized",
        "write_performed",
    )

    for field in forbidden:
        assert (
            f'"{field}"'
            not in allowed
        )


@pytest.mark.parametrize(
    "field",
    [
        "actor",
        "server_actor",
        "mode",
        "current_mode",
        "confirmation_text",
        "execution_consumption_id",
        "production_authorized",
        "restore_authorized",
    ],
)
def test_server_owned_fields_rejected_before_service(
    monkeypatch,
    field: str,
):
    called = []

    monkeypatch.setattr(
        api_main,
        "service_build_ad_deleted_object_restore_post_authorization_chain",
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
        api_main.create_deleted_object_restore_post_authorization_api(
            supplied,
            identity=object(),
        )

    assert (
        captured.value.status_code
        == 400
    )

    assert called == []


def test_non_simulation_rejected_before_actor_and_service(
    monkeypatch,
):
    actors = []
    services = []

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
            actors.append(
                identity
            ),
    )

    monkeypatch.setattr(
        api_main,
        "service_build_ad_deleted_object_restore_post_authorization_chain",
        lambda **kwargs:
            services.append(
                kwargs
            ),
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.create_deleted_object_restore_post_authorization_api(
            payload(),
            identity=object(),
        )

    assert (
        captured.value.status_code
        == 409
    )

    assert actors == []
    assert services == []


def test_route_derives_actor_mode_and_registry_paths_server_side(
    monkeypatch,
):
    captured = {}
    expected_result = result()
    expected_actor = actor()

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
            expected_actor,
    )

    def fake_service(**kwargs):
        captured.update(
            kwargs
        )

        return expected_result

    monkeypatch.setattr(
        api_main,
        "service_build_ad_deleted_object_restore_post_authorization_chain",
        fake_service,
    )

    audits = []

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs:
            audits.append(
                kwargs
            ),
    )

    response = (
        api_main.create_deleted_object_restore_post_authorization_api(
            payload(),
            identity=object(),
        )
    )

    assert (
        captured["authorization_registry_file"]
        == api_main.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_FILE
    )

    assert (
        captured["authorization_consumption_registry_file"]
        == api_main.AD_DELETED_OBJECT_RESTORE_AUTHORIZATION_CONSUMPTION_FILE
    )

    assert (
        captured["execution_consumption_registry_file"]
        == api_main.AD_DELETED_OBJECT_RESTORE_EXECUTION_CONSUMPTION_FILE
    )

    assert (
        captured["jobs_path"]
        == api_main.AD_EXPLORER_JOBS_FILE
    )

    assert (
        captured["authorization_id"]
        == AUTHORIZATION_ID
    )

    assert (
        captured["authorization_digest"]
        == DIGEST
    )

    assert (
        captured["fresh_live_job_id"]
        == FRESH_LIVE_ID
    )

    assert (
        captured["server_actor"]
        == expected_actor
    )

    assert (
        captured["current_mode"]
        == "Simulation"
    )

    assert (
        response["execution_consumption_id"]
        == EXECUTION_CONSUMPTION_ID
    )

    assert (
        response["confirmation_text"]
        == CONFIRMATION
    )

    assert (
        response["production_authorized"]
        is False
    )

    assert (
        response["write_performed"]
        is False
    )

    assert len(
        audits
    ) == 1

    details = audits[0][
        "details"
    ]

    assert (
        "authorization_digest"
        not in details
    )

    assert (
        "confirmation_text"
        not in details
    )


@pytest.mark.parametrize(
    (
        "exception_type",
        "expected_status",
    ),
    [
        (
            api_main.AdDeletedObjectRestorePostAuthorizationNotFound,
            404,
        ),
        (
            api_main.AdDeletedObjectRestorePostAuthorizationConflict,
            409,
        ),
        (
            api_main.AdDeletedObjectRestorePostAuthorizationError,
            400,
        ),
    ],
)
def test_service_errors_are_mapped(
    monkeypatch,
    exception_type,
    expected_status: int,
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
        raise exception_type(
            "probe"
        )

    monkeypatch.setattr(
        api_main,
        "service_build_ad_deleted_object_restore_post_authorization_chain",
        fail,
    )

    with pytest.raises(
        HTTPException
    ) as captured:
        api_main.create_deleted_object_restore_post_authorization_api(
            payload(),
            identity=object(),
        )

    assert (
        captured.value.status_code
        == expected_status
    )


def test_route_does_not_queue_or_sign_execution():
    route = _route_source()

    assert (
        "service_queue_ad_deleted_object_restore_execution"
        not in route
    )

    assert (
        "service_build_ad_deleted_object_restore_windows_execution_envelope"
        not in route
    )

    assert (
        "_eitas_controlled_restore_signing_secret"
        not in route
    )
