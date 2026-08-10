from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import main as api_main

from app.services.acl_delegation_prewrite_status import (
    AclDelegationPrewriteStatusNotFound,
)


TICKET_ID = (
    "11111111-1111-4111-"
    "8111-111111111111"
)


def identity(
    subject="subject-eitas-admin",
):
    return SimpleNamespace(
        subject=subject,
        username="eitas-admin",
    )


def status():
    return SimpleNamespace(
        contract_version=(
            "c8.4d-a3c3b"
        ),

        state=(
            "prewrite_validated"
        ),

        ticket_id=TICKET_ID,
        claim_id="claim-1",
        execution_id="execution-1",

        created_at=(
            "2026-08-10T08:00:00+00:00"
        ),
        expires_at=(
            "2026-08-10T08:02:00+00:00"
        ),
        claimed_at=(
            "2026-08-10T08:00:10+00:00"
        ),
        completed_at=(
            "2026-08-10T08:00:20+00:00"
        ),

        success=True,

        worker_validation_in_progress=False,
        validation_completed=True,
        confirmation_ready=True,

        job_creation_authorized=False,
        runtime_authorized=False,
        production_authorized=False,
        ad_write_authorized=False,
    )


def test_a3c3b_route_exists_and_uses_ad_access():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        '@app.get(\n'
        '    "/api/ad-admin/acl-delegation/'
        'prewrite-status/{ticket_id}"\n'
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

    route = source[
        start:end
    ]

    assert (
        "identity=Depends(AD_ACCESS)"
        in route
    )

    assert (
        "identity.subject"
        in route
    )

    assert (
        "get_acl_delegation_prewrite_status("
        in route
    )

    assert (
        "require_api_key"
        not in route
    )


def test_a3c3b_success_returns_only_safe_metadata(
    monkeypatch,
):
    calls = []

    def fake_status(**kwargs):
        calls.append(
            kwargs
        )

        return status()

    monkeypatch.setattr(
        api_main,
        "get_acl_delegation_prewrite_status",
        fake_status,
    )

    result = (
        api_main.get_acl_delegation_prewrite_status_api(
            TICKET_ID,
            identity(),
        )
    )

    assert len(calls) == 1

    assert calls[0][
        "actor_subject"
    ] == (
        "subject-eitas-admin"
    )

    assert (
        result["execution_id"]
        == "execution-1"
    )

    assert result[
        "validation"
    ][
        "confirmation_ready"
    ] is True

    assert result["authorization"] == {
        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }

    assert "payload" not in result
    assert "principal" not in result
    assert "dacl" not in result
    assert "actor" not in result


def test_a3c3b_other_actor_is_404(
    monkeypatch,
):
    def fail(**kwargs):
        raise AclDelegationPrewriteStatusNotFound(
            "internal"
        )

    monkeypatch.setattr(
        api_main,
        "get_acl_delegation_prewrite_status",
        fail,
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.get_acl_delegation_prewrite_status_api(
            TICKET_ID,
            identity(),
        )

    assert (
        exc_info.value.status_code
        == 404
    )

    assert (
        exc_info.value.detail
        == "Statut ACL pre-write introuvable"
    )


def test_a3c3b_missing_subject_is_forbidden():
    with pytest.raises(
        HTTPException
    ) as exc_info:
        api_main.get_acl_delegation_prewrite_status_api(
            TICKET_ID,
            identity(
                subject=""
            ),
        )

    assert (
        exc_info.value.status_code
        == 403
    )


def test_a3c3b_route_does_not_mutate_registry():
    source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    marker = (
        '@app.get(\n'
        '    "/api/ad-admin/acl-delegation/'
        'prewrite-status/{ticket_id}"\n'
        ')'
    )

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

    route = source[
        start:end
    ]

    for token in (
        "_atomic_write_registry(",
        "claim_acl_delegation_write_intent(",
        "create_acl_delegation_prewrite_ticket(",
        "complete_acl_delegation_prewrite_ticket(",
        "persist_acl_delegation_production_confirmation(",
    ):
        assert token not in route
