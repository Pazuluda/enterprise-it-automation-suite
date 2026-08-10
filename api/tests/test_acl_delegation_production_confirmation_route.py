from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import main as api_main

from app.services.acl_delegation_production_confirmation import (
    AclDelegationProductionConfirmationConflict,
    AclDelegationProductionConfirmationError,
)
from app.services.acl_delegation_production_confirmation_persistence import (
    AclDelegationProductionConfirmationPersistenceConflict,
)
from app.services.acl_delegation_write_replay import (
    AclDelegationWriteReplayStorageError,
)


ROUTE = (
    "/api/ad-admin/acl-delegation/"
    "production-confirmation"
)


def _identity():
    return SimpleNamespace(
        subject="subject-eitas-admin",
        username="eitas-admin",
        roles=(
            "UltraAdmin",
        ),
        issuer=(
            "https://10.10.10.11:62443/"
            "auth/realms/eitas"
        ),
        azp="eitas-portal",
    )


def _payload():
    return {
        "claim_id": "claim-1",
        "ticket_id": "ticket-1",
        "execution_id": "execution-1",
        "confirm_object_dn": (
            "OU=test,OU=Users,OU=EITAS,"
            "DC=API,DC=LOCAL"
        ),
        "confirmation_phrase": (
            "APPLY ACL DELEGATION"
        ),
    }


def _confirmation():
    return SimpleNamespace(
        contract_version="c8.4d-a2c1",
        state=(
            "production_confirmation_dormant"
        ),
        source_state="prewrite_validated",

        confirmation_id="confirmation-1",
        confirmation_digest="a" * 64,
        confirmation_created_at=(
            "2026-08-10T08:00:00+00:00"
        ),

        claim_id="claim-1",
        ticket_id="ticket-1",
        execution_id="execution-1",

        actor_subject=(
            "subject-eitas-admin"
        ),
        actor_username="eitas-admin",

        target_dn=(
            "OU=test,OU=Users,OU=EITAS,"
            "DC=API,DC=LOCAL"
        ),
        target_object_guid=(
            "8838f739-c817-4b45-"
            "90b2-b597ce79312a"
        ),

        principal_sid=(
            "S-1-5-21-1101651174-"
            "4260486456-3261528239-1118"
        ),

        dacl_sddl_sha256="b" * 64,
        acl_fingerprint="c" * 64,

        confirmation_validated=True,
        confirmation_consumed=True,

        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def test_a2c2b_route_exists_and_uses_ad_access():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        '@app.post(\n'
        '    "/api/ad-admin/acl-delegation/'
        'production-confirmation"\n'
        ')'
    )

    assert marker in source

    start = source.index(
        marker
    )

    end = source.index(
        '@app.get(\n'
        '    "/api/agent/acl-delegation/'
        'prewrite/pending"\n'
        ')',
        start,
    )

    route = source[start:end]

    assert (
        "identity=Depends(AD_ACCESS)"
        in route
    )

    assert (
        "persist_acl_delegation_production_confirmation("
        in route
    )


def test_a2c2b_rejects_client_injection():
    payload = {
        **_payload(),
        "ad_write_authorized": True,
    }

    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.confirm_acl_delegation_production_api(
            payload,
            _identity(),
        )

    assert (
        exc_info.value.status_code
        == 400
    )

    assert (
        "Champs confirmation ACL interdits"
        in str(exc_info.value.detail)
    )


def test_a2c2b_rejects_missing_required_field():
    payload = _payload()

    payload[
        "confirmation_phrase"
    ] = ""

    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.confirm_acl_delegation_production_api(
            payload,
            _identity(),
        )

    assert (
        exc_info.value.status_code
        == 400
    )

    assert (
        "confirmation_phrase"
        in str(exc_info.value.detail)
    )


def test_a2c2b_success_is_non_authorizing(
    monkeypatch,
):
    audit_events = []

    monkeypatch.setattr(
        api_main,
        "persist_acl_delegation_production_confirmation",
        lambda **kwargs: _confirmation(),
    )

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs: audit_events.append(
            kwargs
        ),
    )

    result = (
        api_main.confirm_acl_delegation_production_api(
            _payload(),
            _identity(),
        )
    )

    assert result["state"] == (
        "production_confirmation_dormant"
    )

    assert result["source_state"] == (
        "prewrite_validated"
    )

    assert result["confirmation"] == {
        "validated": True,
        "consumed": True,
    }

    assert result["authorization"] == {
        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }

    assert (
        "confirmation_phrase"
        not in result
    )

    assert len(audit_events) == 1

    audit = audit_events[0]

    assert audit["action"] == (
        "acl_delegation_production_confirmation_consumed"
    )

    assert audit["actor"] == (
        "eitas-admin"
    )

    assert (
        "APPLY ACL DELEGATION"
        not in str(audit)
    )


@pytest.mark.parametrize(
    "exception",
    [
        AclDelegationProductionConfirmationConflict(
            "Acteur OIDC different"
        ),
        AclDelegationProductionConfirmationPersistenceConflict(
            "Confirmation Production ACL deja consommee"
        ),
    ],
)
def test_a2c2b_conflicts_map_to_409(
    monkeypatch,
    exception,
):
    def fail(**kwargs):
        raise exception

    monkeypatch.setattr(
        api_main,
        "persist_acl_delegation_production_confirmation",
        fail,
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.confirm_acl_delegation_production_api(
            _payload(),
            _identity(),
        )

    assert (
        exc_info.value.status_code
        == 409
    )


def test_a2c2b_validation_failure_maps_to_400(
    monkeypatch,
):
    def fail(**kwargs):
        raise AclDelegationProductionConfirmationError(
            "Horodatage confirmation ACL invalide"
        )

    monkeypatch.setattr(
        api_main,
        "persist_acl_delegation_production_confirmation",
        fail,
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.confirm_acl_delegation_production_api(
            _payload(),
            _identity(),
        )

    assert (
        exc_info.value.status_code
        == 400
    )


def test_a2c2b_storage_failure_maps_to_503(
    monkeypatch,
):
    def fail(**kwargs):
        raise AclDelegationWriteReplayStorageError(
            "internal path detail"
        )

    monkeypatch.setattr(
        api_main,
        "persist_acl_delegation_production_confirmation",
        fail,
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.confirm_acl_delegation_production_api(
            _payload(),
            _identity(),
        )

    assert (
        exc_info.value.status_code
        == 503
    )

    assert (
        exc_info.value.detail
        == "Stockage de securite ACL indisponible"
    )


def test_a2c2b_generic_acl_runtime_remains_closed():
    from app.services.ad_admin import (
        ALLOWED_ACTIONS,
    )

    assert (
        "apply_acl_delegation"
        not in ALLOWED_ACTIONS
    )

    assert (
        "prevalidate_acl_delegation"
        not in ALLOWED_ACTIONS
    )


def test_a2c2b_windows_apply_still_absent():
    worker = Path(
        "agent-windows/modules/"
        "EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8-sig"
    )

    start = worker.index(
        "function Invoke-EitasAdAdminJob"
    )

    end = worker.index(
        "function Process-EitasPendingAclPrewriteTickets",
        start,
    )

    generic = worker[start:end]

    assert (
        '"apply_acl_delegation"'
        not in generic
    )
