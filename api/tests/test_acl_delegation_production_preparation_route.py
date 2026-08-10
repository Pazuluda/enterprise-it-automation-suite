from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import main as api_main

from app.services.acl_delegation_production_preparation import (
    AclDelegationProductionPreparationError,
)


TARGET_DN = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)


def identity():
    return SimpleNamespace(
        subject="oidc-user-123",
        username="eitas-admin",
    )


def payload():
    return {
        "simulation_job_id": (
            "11111111-1111-4111-"
            "8111-111111111111"
        ),
        "security_descriptor_job_id": (
            "22222222-2222-4222-"
            "8222-222222222222"
        ),
    }


def preparation():
    return SimpleNamespace(
        contract_version=(
            "c8.4d-a3b2b1"
        ),
        state=(
            "production_preparation_dormant"
        ),

        simulation_job_id=(
            "11111111-1111-4111-"
            "8111-111111111111"
        ),
        security_descriptor_job_id=(
            "22222222-2222-4222-"
            "8222-222222222222"
        ),

        target_dn=TARGET_DN,
        target_object_guid=(
            "8838f739-c817-4b45-"
            "90b2-b597ce79312a"
        ),

        principal_identity=(
            "GG_IT_Admin"
        ),
        principal_dn=(
            "CN=GG_IT_Admin,"
            "OU=Groups,OU=EITAS,"
            "DC=API,DC=LOCAL"
        ),
        principal_sid=(
            "S-1-5-21-1101651174-"
            "4260486456-3261528239-1118"
        ),

        access_control_type="Allow",
        rights=(
            "ReadProperty",
            "WriteProperty",
        ),
        inheritance_type=(
            "Descendents"
        ),
        object_type_guid=None,
        inherited_object_type_guid=None,

        dacl_sddl_sha256="3" * 64,
        acl_fingerprint="4" * 64,
        evidence_digest="5" * 64,

        simulation_completed_at=(
            "2026-08-10T07:59:40+00:00"
        ),
        security_descriptor_completed_at=(
            "2026-08-10T07:59:55+00:00"
        ),
        simulation_age_seconds=20.0,
        security_descriptor_age_seconds=5.0,

        required_confirm_object_dn=(
            TARGET_DN
        ),
        required_confirmation_phrase=(
            "APPLY ACL DELEGATION"
        ),

        trusted_source=(
            "server_job_storage"
        ),

        trusted_evidence_loaded=True,
        binding_validated=True,

        human_confirmation_validated=False,
        replay_consumed=False,
        claim_created=False,

        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def test_a3b2b2_route_exists_and_uses_oidc_ad_access():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        '@app.post(\n'
        '    "/api/ad-admin/acl-delegation/'
        'production-preparation"\n'
        ')'
    )

    assert marker in source

    start = source.index(
        marker
    )

    end = source.index(
        '@app.post(\n'
        '    "/api/ad-admin/acl-delegation/'
        'write-intent/identity-envelope"\n'
        ')',
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
        "prepare_acl_delegation_production_evidence("
        in route
    )


def test_a3b2b2_passes_only_server_job_ids_to_service(
    monkeypatch,
):
    calls = []

    def fake_prepare(**kwargs):
        calls.append(
            kwargs
        )

        return preparation()

    monkeypatch.setattr(
        api_main,
        "prepare_acl_delegation_production_evidence",
        fake_prepare,
    )

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs: None,
    )

    result = (
        api_main.prepare_acl_delegation_production_api(
            payload(),
            identity(),
        )
    )

    assert len(calls) == 1

    assert (
        calls[0]["payload"]
        == payload()
    )

    assert result[
        "evidence"
    ][
        "trusted_evidence_loaded"
    ] is True

    assert result[
        "evidence"
    ][
        "binding_validated"
    ] is True


def test_a3b2b2_returns_server_fingerprint(
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "prepare_acl_delegation_production_evidence",
        lambda **kwargs: preparation(),
    )

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs: None,
    )

    result = (
        api_main.prepare_acl_delegation_production_api(
            payload(),
            identity(),
        )
    )

    assert (
        result["dacl"]["acl_fingerprint"]
        == "4" * 64
    )

    assert (
        result["dacl"]["dacl_sddl_sha256"]
        == "3" * 64
    )


def test_a3b2b2_is_strictly_non_authorizing(
    monkeypatch,
):
    monkeypatch.setattr(
        api_main,
        "prepare_acl_delegation_production_evidence",
        lambda **kwargs: preparation(),
    )

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs: None,
    )

    result = (
        api_main.prepare_acl_delegation_production_api(
            payload(),
            identity(),
        )
    )

    assert result[
        "confirmation_requirements"
    ][
        "human_confirmation_validated"
    ] is False

    assert result["anti_replay"] == {
        "replay_consumed": False,
        "claim_created": False,
    }

    assert result["authorization"] == {
        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }


def test_a3b2b2_validation_maps_to_400(
    monkeypatch,
):
    def fail(**kwargs):
        raise AclDelegationProductionPreparationError(
            "Preuve ACL invalide"
        )

    monkeypatch.setattr(
        api_main,
        "prepare_acl_delegation_production_evidence",
        fail,
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.prepare_acl_delegation_production_api(
            payload(),
            identity(),
        )

    assert (
        exc_info.value.status_code
        == 400
    )


def test_a3b2b2_audit_is_non_authorizing(
    monkeypatch,
):
    events = []

    monkeypatch.setattr(
        api_main,
        "prepare_acl_delegation_production_evidence",
        lambda **kwargs: preparation(),
    )

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs: events.append(
            kwargs
        ),
    )

    api_main.prepare_acl_delegation_production_api(
        payload(),
        identity(),
    )

    assert len(events) == 1

    event = events[0]

    assert event["actor"] == (
        "eitas-admin"
    )

    assert event["details"][
        "human_confirmation_validated"
    ] is False

    assert event["details"][
        "replay_consumed"
    ] is False

    assert event["details"][
        "claim_created"
    ] is False

    assert event["details"][
        "production_authorized"
    ] is False

    assert event["details"][
        "ad_write_authorized"
    ] is False


def test_a3b2b2_client_cannot_supply_fingerprint(
    monkeypatch,
):
    received = []

    def fake_prepare(**kwargs):
        received.append(
            kwargs["payload"]
        )

        raise AclDelegationProductionPreparationError(
            "Champs preparation ACL interdits"
        )

    monkeypatch.setattr(
        api_main,
        "prepare_acl_delegation_production_evidence",
        fake_prepare,
    )

    injected = {
        **payload(),
        "expected_acl_fingerprint": (
            "0" * 64
        ),
    }

    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.prepare_acl_delegation_production_api(
            injected,
            identity(),
        )

    assert (
        exc_info.value.status_code
        == 400
    )

    assert len(
        received
    ) == 1


def test_a3b2b2_does_not_create_claim():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        '@app.post(\n'
        '    "/api/ad-admin/acl-delegation/'
        'production-preparation"\n'
        ')'
    )

    start = source.index(
        marker
    )

    end = source.index(
        '@app.post(\n'
        '    "/api/ad-admin/acl-delegation/'
        'write-intent/identity-envelope"\n'
        ')',
        start,
    )

    route = source[
        start:end
    ]

    assert (
        "claim_acl_delegation_write_intent("
        not in route
    )

    assert (
        "persist_acl_delegation_production_confirmation("
        not in route
    )
