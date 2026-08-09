from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi import HTTPException

import main as api_main

from app.services.acl_delegation_prewrite_ticket import (
    AclDelegationPrewriteTicketConflict,
)
from app.services.acl_delegation_write_replay import (
    AclDelegationWriteReplayStorageError,
)


def _identity():
    return SimpleNamespace(
        subject="subject-1",
        username="ultraadmin",
    )


def _ticket():
    return SimpleNamespace(
        contract_version="c8.4c5a",
        state="prewrite_ticketed",
        ticket_id="ticket-1",
        claim_id="claim-1",
        consumption_id="consumption-1",
        created_at="2026-08-09T20:00:00+00:00",
        expires_at="2026-08-09T20:02:00+00:00",
        payload_digest="a" * 64,
    )


def test_c8_4c5b_route_exists_and_uses_ad_access():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        '"/api/ad-admin/acl-delegation/prewrite-ticket"'
        in source
    )

    assert (
        "identity=Depends(AD_ACCESS)"
        in source
    )


def test_c8_4c5b_rejects_client_injection():
    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.create_acl_delegation_prewrite_ticket_api(
            {
                "claim_id": "claim-1",
                "target": {
                    "object_guid": "attacker"
                },
            },
            _identity(),
        )

    assert exc_info.value.status_code == 400

    assert (
        "Champs ticket ACL interdits"
        in str(exc_info.value.detail)
    )


def test_c8_4c5b_success_returns_no_windows_payload(
    monkeypatch,
):
    audit_events = []

    monkeypatch.setattr(
        api_main,
        "create_acl_delegation_prewrite_ticket",
        lambda **kwargs: _ticket(),
    )

    monkeypatch.setattr(
        api_main,
        "write_audit_log",
        lambda **kwargs: audit_events.append(
            kwargs
        ),
    )

    result = (
        api_main.create_acl_delegation_prewrite_ticket_api(
            {
                "claim_id": "claim-1",
            },
            _identity(),
        )
    )

    assert result["contract_version"] == "c8.4c5a"
    assert result["state"] == "prewrite_ticketed"

    assert "payload" not in result
    assert "target" not in result
    assert "principal" not in result
    assert "ace" not in result
    assert "dacl" not in result

    assert result["authorization"] == {
        "prewrite_validation_runtime_authorized": False,
        "job_creation_authorized": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }

    assert len(audit_events) == 1

    assert (
        audit_events[0]["actor"]
        == "ultraadmin"
    )


def test_c8_4c5b_conflict_maps_to_409(
    monkeypatch,
):
    def fail(**kwargs):
        raise AclDelegationPrewriteTicketConflict(
            "Ticket ACL pre-write expire"
        )

    monkeypatch.setattr(
        api_main,
        "create_acl_delegation_prewrite_ticket",
        fail,
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.create_acl_delegation_prewrite_ticket_api(
            {
                "claim_id": "claim-1",
            },
            _identity(),
        )

    assert exc_info.value.status_code == 409


def test_c8_4c5b_storage_failure_maps_to_503(
    monkeypatch,
):
    def fail(**kwargs):
        raise AclDelegationWriteReplayStorageError(
            "internal path detail"
        )

    monkeypatch.setattr(
        api_main,
        "create_acl_delegation_prewrite_ticket",
        fail,
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.create_acl_delegation_prewrite_ticket_api(
            {
                "claim_id": "claim-1",
            },
            _identity(),
        )

    assert exc_info.value.status_code == 503

    assert (
        exc_info.value.detail
        == "Stockage de securite ACL indisponible"
    )


def test_c8_4c5b_generic_action_still_closed():
    from app.services.ad_admin import ALLOWED_ACTIONS

    assert (
        "prevalidate_acl_delegation"
        not in ALLOWED_ACTIONS
    )

    assert (
        "apply_acl_delegation"
        not in ALLOWED_ACTIONS
    )
