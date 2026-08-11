from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.security import (
    OIDC_ALLOWED_AZP,
    OIDC_ISSUER,
)

from app.services.ad_recycle_bin_activation_intent_persistence import (
    AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,
)

from app.services.ad_recycle_bin_activation_ticket import (
    AD_RECYCLE_BIN_ACTIVATION_TICKET_TTL_SECONDS,
    AdRecycleBinActivationTicketError,
    assert_ad_recycle_bin_activation_ticket_invariants,
    build_ad_recycle_bin_activation_ticket,
)


NOW = datetime(
    2026,
    8,
    10,
    16,
    4,
    0,
    tzinfo=timezone.utc,
)

SOURCE_EVIDENCE_TIME = (
    NOW
    - timedelta(
        seconds=30
    )
)

FRESH_EVIDENCE_TIME = (
    NOW
    - timedelta(
        seconds=5
    )
)

INTENT_ID = str(
    uuid4()
)

INTENT_DIGEST = "a" * 64


def allowed_azp() -> str:
    if OIDC_ALLOWED_AZP:
        return sorted(
            OIDC_ALLOWED_AZP
        )[0]

    return "eitas-portal"


def actor():
    return {
        "subject":
            "subject-c94",

        "username":
            "admin-c94",

        "issuer":
            OIDC_ISSUER,

        "azp":
            allowed_azp(),
    }


def source_record():
    current_actor = actor()

    return {
        "contract_version":
            AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,

        "intent_id":
            INTENT_ID,

        "intent_digest":
            INTENT_DIGEST,

        "state":
            "activation_intent_dormant",

        "status":
            "dormant",

        "forest_name":
            "API.LOCAL",

        "root_domain":
            "API.LOCAL",

        "actor_subject":
            current_actor["subject"],

        "actor_username":
            current_actor["username"],

        "actor_issuer":
            current_actor["issuer"],

        "actor_azp":
            current_actor["azp"],

        "evidence_sha256":
            "b" * 64,

        "evidence_created_at":
            SOURCE_EVIDENCE_TIME.isoformat(),

        "created_at":
            (
                NOW
                - timedelta(
                    minutes=2
                )
            ).isoformat(),

        "persisted_at":
            (
                NOW
                - timedelta(
                    minutes=2
                )
            ).isoformat(),

        "job_creation_authorized":
            False,

        "runtime_authorized":
            False,

        "production_authorized":
            False,

        "activation_authorized":
            False,

        "restore_authorized":
            False,

        "write_performed":
            False,
    }


def evidence_result():
    return {
        "action":
            "get_recycle_bin_activation_evidence",

        "read_only":
            True,

        "forest_name":
            "API.LOCAL",

        "root_domain":
            "API.LOCAL",

        "forest_mode":
            "Windows2025Forest",

        "recycle_bin_enabled":
            False,

        "recycle_bin_enabled_scope_count":
            0,

        "domain_controller_count":
            1,

        "replication_query_succeeded":
            True,

        "replication_partner_query_succeeded":
            True,

        "replication_failure_count":
            0,

        "replication_partner_count":
            0,

        "replication_ready":
            True,

        "evidence_created_at":
            FRESH_EVIDENCE_TIME.isoformat(),

        "activation_authorized":
            False,

        "runtime_authorized":
            False,

        "production_authorized":
            False,

        "restore_authorized":
            False,

        "write_performed":
            False,
    }


def evidence_job():
    return {
        "id":
            "fresh-evidence-job-c94",

        "type":
            "ad_explorer",

        "action":
            "get_recycle_bin_activation_evidence",

        "status":
            "completed",

        "success":
            True,

        "result":
            evidence_result(),
    }


def build(
    *,
    source=None,
    evidence=None,
    current_actor=None,
    confirmed_forest="API.LOCAL",
    mode="Simulation",
    expected_intent_id=INTENT_ID,
    expected_intent_digest=INTENT_DIGEST,
    expected_evidence_job_id="fresh-evidence-job-c94",
):
    return build_ad_recycle_bin_activation_ticket(
        source_intent_record=(
            source_record()
            if source is None
            else source
        ),

        expected_intent_id=
            expected_intent_id,

        expected_intent_digest=
            expected_intent_digest,

        evidence_job=(
            evidence_job()
            if evidence is None
            else evidence
        ),

        expected_evidence_job_id=
            expected_evidence_job_id,

        server_actor=(
            actor()
            if current_actor is None
            else current_actor
        ),

        confirmed_forest_name=
            confirmed_forest,

        current_mode=
            mode,

        now=
            NOW,
    )


def test_valid_ticket_remains_dormant():
    ticket = build()

    assert ticket.state == (
        "activation_ticket_dormant"
    )

    assert ticket.status == "dormant"

    assert ticket.one_shot_required is True
    assert ticket.replay_consumed is False

    assert ticket.persistence_enabled is False
    assert ticket.route_enabled is False
    assert ticket.job_creation_authorized is False
    assert ticket.claim_authorized is False
    assert ticket.runtime_authorized is False
    assert ticket.production_authorized is False
    assert ticket.activation_authorized is False
    assert ticket.restore_authorized is False
    assert ticket.write_performed is False

    assert len(ticket.ticket_digest) == 64


def test_ticket_has_exact_short_ttl():
    ticket = build()

    issued = datetime.fromisoformat(
        ticket.issued_at
    )

    expires = datetime.fromisoformat(
        ticket.expires_at
    )

    assert (
        expires - issued
    ).total_seconds() == (
        AD_RECYCLE_BIN_ACTIVATION_TICKET_TTL_SECONDS
    )


def test_source_intent_id_mismatch_rejected():
    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="source intent id mismatch",
    ):
        build(
            expected_intent_id=str(
                uuid4()
            )
        )


def test_source_intent_digest_mismatch_rejected():
    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="source intent digest mismatch",
    ):
        build(
            expected_intent_digest="c" * 64
        )


def test_non_dormant_source_status_rejected():
    source = source_record()
    source["status"] = "pending"

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="status is not dormant",
    ):
        build(
            source=source
        )


def test_unsafe_source_flag_rejected():
    source = source_record()
    source["activation_authorized"] = True

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="unsafe authorization flag",
    ):
        build(
            source=source
        )


def test_actor_subject_mismatch_rejected():
    current_actor = actor()
    current_actor["subject"] = "other-subject"

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="actor mismatch",
    ):
        build(
            current_actor=current_actor
        )


def test_actor_issuer_mismatch_rejected():
    current_actor = actor()
    current_actor["issuer"] = "https://wrong.invalid/"

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="OIDC issuer mismatch",
    ):
        build(
            current_actor=current_actor
        )


def test_forest_confirmation_mismatch_rejected():
    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="confirmed_forest_name mismatch",
    ):
        build(
            confirmed_forest="OTHER.LOCAL"
        )


def test_evidence_job_id_mismatch_rejected():
    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="fresh evidence job id mismatch",
    ):
        build(
            expected_evidence_job_id="wrong-job"
        )


def test_wrong_evidence_action_rejected():
    evidence = evidence_job()
    evidence["action"] = "get_deleted_objects"

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="fresh evidence action is invalid",
    ):
        build(
            evidence=evidence
        )


def test_failed_evidence_job_rejected():
    evidence = evidence_job()
    evidence["success"] = False

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="did not succeed",
    ):
        build(
            evidence=evidence
        )


def test_non_read_only_evidence_rejected():
    evidence = evidence_job()
    evidence["result"]["read_only"] = False

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="not read-only",
    ):
        build(
            evidence=evidence
        )


def test_enabled_recycle_bin_rejected():
    evidence = evidence_job()
    evidence["result"]["recycle_bin_enabled"] = True

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="already enabled",
    ):
        build(
            evidence=evidence
        )


def test_replication_failure_rejected():
    evidence = evidence_job()
    evidence["result"]["replication_failure_count"] = 1

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="replication failures",
    ):
        build(
            evidence=evidence
        )


def test_replication_not_ready_rejected():
    evidence = evidence_job()
    evidence["result"]["replication_ready"] = False

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="replication is not ready",
    ):
        build(
            evidence=evidence
        )


def test_unsafe_evidence_flag_rejected():
    evidence = evidence_job()
    evidence["result"]["production_authorized"] = True

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="unsafe authorization flag",
    ):
        build(
            evidence=evidence
        )


def test_stale_fresh_evidence_rejected():
    evidence = evidence_job()

    evidence["result"]["evidence_created_at"] = (
        NOW
        - timedelta(
            seconds=121
        )
    ).isoformat()

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="fresh evidence is stale",
    ):
        build(
            evidence=evidence
        )


def test_evidence_must_be_newer_than_source():
    evidence = evidence_job()

    evidence["result"]["evidence_created_at"] = (
        SOURCE_EVIDENCE_TIME
    ).isoformat()

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="not newer than source evidence",
    ):
        build(
            evidence=evidence
        )


def test_production_mode_rejected():
    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="Simulation-only",
    ):
        build(
            mode="Production"
        )


def test_ticket_digest_detects_mutation():
    ticket = build()

    tampered = replace(
        ticket,
        forest_name="OTHER.LOCAL",
    )

    with pytest.raises(
        AdRecycleBinActivationTicketError,
        match="ticket digest mismatch",
    ):
        assert_ad_recycle_bin_activation_ticket_invariants(
            tampered
        )


def test_ticket_service_is_not_runtime_integrated():
    main = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    admin = Path(
        "api/app/services/ad_admin.py"
    ).read_text(
        encoding="utf-8"
    )

    windows = Path(
        "agent-windows/modules/EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8",
        errors="replace",
    )

    assert (
        "ad_recycle_bin_activation_ticket"
        not in main
    )

    assert "activate_recycle_bin" not in admin
    assert "activate_recycle_bin" not in windows

    assert "Enable-ADOptionalFeature" not in windows
    # C9.5-A5C now permits exactly one isolated
    # Restore-ADObject primitive, and only as WhatIf.
    handler_name = (
        "Invoke-EitasAdAdmin"
        "DeletedObjectRestoreWhatIf"
    )

    handler_marker = (
        f"function {handler_name} {{"
    )

    assert handler_marker in windows

    handler_start = windows.index(
        handler_marker
    )

    handler_end = windows.find(
        "\nfunction ",
        handler_start + len(
            handler_marker
        ),
    )

    handler = windows[
        handler_start:
        handler_end
        if handler_end != -1
        else None
    ]

    assert (
        handler.count(
            "Restore-ADObject `"
        )
        == 1
    )

    assert "-WhatIf `" in handler
    assert "-Confirm:$false `" in handler

    assert (
        "restore_performed = $false"
        in handler
    )

    assert (
        "write_performed = $false"
        in handler
    )

    dispatcher_marker = (
        "function Invoke-EitasAdAdminJob {"
    )

    dispatcher_start = windows.index(
        dispatcher_marker
    )

    dispatcher_end = windows.find(
        "\nfunction ",
        dispatcher_start + len(
            dispatcher_marker
        ),
    )

    dispatcher = windows[
        dispatcher_start:
        dispatcher_end
        if dispatcher_end != -1
        else None
    ]

    assert "Restore-ADObject" not in dispatcher
    assert handler_name not in dispatcher

    assert (
        "restore_deleted_object_whatif"
        not in dispatcher
    )
