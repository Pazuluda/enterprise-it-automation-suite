from contextlib import nullcontext
from pathlib import Path

import pytest

import app.services.acl_delegation_prewrite_status as status_service

from app.services.acl_delegation_prewrite_status import (
    AclDelegationPrewriteStatusError,
    AclDelegationPrewriteStatusNotFound,
    get_acl_delegation_prewrite_status,
)


TICKET_ID = (
    "11111111-1111-4111-"
    "8111-111111111111"
)

CLAIM_ID = (
    "22222222-2222-4222-"
    "8222-222222222222"
)

EXECUTION_ID = (
    "33333333-3333-4333-"
    "8333-333333333333"
)


def record(
    state="prewrite_ticketed",
):
    value = {
        "state": state,

        "actor_subject": (
            "subject-eitas-admin"
        ),

        "prewrite_ticket_id": (
            TICKET_ID
        ),

        "claim_id": CLAIM_ID,

        "prewrite_ticket_created_at": (
            "2026-08-10T08:00:00+00:00"
        ),

        "prewrite_ticket_expires_at": (
            "2026-08-10T08:02:00+00:00"
        ),

        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }

    if state in {
        "prewrite_processing",
        "prewrite_validated",
        "prewrite_failed",
    }:
        value[
            "prewrite_execution_id"
        ] = EXECUTION_ID

        value[
            "prewrite_claimed_at"
        ] = (
            "2026-08-10T08:00:10+00:00"
        )

    if state == "prewrite_validated":
        value[
            "prewrite_completed_at"
        ] = (
            "2026-08-10T08:00:20+00:00"
        )
        value["prewrite_success"] = True

    if state == "prewrite_failed":
        value[
            "prewrite_completed_at"
        ] = (
            "2026-08-10T08:00:20+00:00"
        )
        value["prewrite_success"] = False

    return value


def install_registry(
    monkeypatch,
    value,
):
    monkeypatch.setattr(
        status_service,
        "_normalize_registry_path",
        lambda path: Path(path),
    )

    monkeypatch.setattr(
        status_service,
        "_exclusive_registry_lock",
        lambda path: nullcontext(),
    )

    monkeypatch.setattr(
        status_service,
        "_safe_load_registry",
        lambda path: {
            "records": [value],
        },
    )

    monkeypatch.setattr(
        status_service,
        "_find_ticket_record",
        lambda registry, ticket_id: (
            registry["records"][0]
        ),
    )

    monkeypatch.setattr(
        status_service,
        "_assert_ticket_integrity",
        lambda item: None,
    )


def read_status(
    monkeypatch,
    value,
    subject="subject-eitas-admin",
):
    install_registry(
        monkeypatch,
        value,
    )

    return get_acl_delegation_prewrite_status(
        replay_registry_file=Path(
            "/tmp/replay.json"
        ),
        ticket_id=TICKET_ID,
        actor_subject=subject,
    )


def test_a3c3b_ticketed_is_read_only(
    monkeypatch,
):
    result = read_status(
        monkeypatch,
        record(),
    )

    assert result.state == (
        "prewrite_ticketed"
    )

    assert result.execution_id is None
    assert result.success is None

    assert (
        result.worker_validation_in_progress
        is False
    )

    assert (
        result.validation_completed
        is False
    )

    assert (
        result.confirmation_ready
        is False
    )


def test_a3c3b_processing_exposes_execution_id(
    monkeypatch,
):
    result = read_status(
        monkeypatch,
        record(
            "prewrite_processing"
        ),
    )

    assert (
        result.execution_id
        == EXECUTION_ID
    )

    assert (
        result.worker_validation_in_progress
        is True
    )

    assert result.success is None
    assert result.confirmation_ready is False


def test_a3c3b_validated_is_confirmation_ready(
    monkeypatch,
):
    result = read_status(
        monkeypatch,
        record(
            "prewrite_validated"
        ),
    )

    assert result.success is True

    assert (
        result.validation_completed
        is True
    )

    assert (
        result.confirmation_ready
        is True
    )

    assert {
        result.job_creation_authorized,
        result.runtime_authorized,
        result.production_authorized,
        result.ad_write_authorized,
    } == {
        False,
    }


def test_a3c3b_failed_is_not_confirmation_ready(
    monkeypatch,
):
    result = read_status(
        monkeypatch,
        record(
            "prewrite_failed"
        ),
    )

    assert result.success is False
    assert result.validation_completed is True
    assert result.confirmation_ready is False


def test_a3c3b_hides_other_actor_ticket(
    monkeypatch,
):
    with pytest.raises(
        AclDelegationPrewriteStatusNotFound
    ):
        read_status(
            monkeypatch,
            record(),
            subject="different-subject",
        )


def test_a3c3b_rejects_authorizing_record(
    monkeypatch,
):
    value = record()

    value[
        "production_authorized"
    ] = True

    with pytest.raises(
        AclDelegationPrewriteStatusError,
        match="autorisant",
    ):
        read_status(
            monkeypatch,
            value,
        )


def test_a3c3b_rejects_unexpected_state(
    monkeypatch,
):
    with pytest.raises(
        AclDelegationPrewriteStatusError,
        match="Etat ACL pre-write invalide",
    ):
        read_status(
            monkeypatch,
            record(
                "claimed_dormant"
            ),
        )


def test_a3c3b_source_has_no_mutation_path():
    source = Path(
        "api/app/services/"
        "acl_delegation_prewrite_status.py"
    ).read_text(
        encoding="utf-8"
    )

    for token in (
        "_atomic_write_registry(",
        "persist_acl_delegation_production_confirmation(",
        "claim_acl_delegation_write_intent(",
        "create_acl_delegation_prewrite_ticket(",
        "complete_acl_delegation_prewrite_ticket(",
        "Set-Acl",
        "ActiveDirectoryAccessRule",
    ):
        assert token not in source

    assert (
        "prewrite_ticket_payload"
        not in source
    )
