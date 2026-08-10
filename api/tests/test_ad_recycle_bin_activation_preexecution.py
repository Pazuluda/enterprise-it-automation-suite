from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.security import (
    OIDC_ALLOWED_AZP,
    OIDC_ISSUER,
)

from app.services.ad_recycle_bin_activation_authorization import (
    build_ad_recycle_bin_activation_authorization,
)

from app.services.ad_recycle_bin_activation_authorization_persistence import (
    persist_ad_recycle_bin_activation_authorization,
)

from app.services.ad_recycle_bin_activation_intent_persistence import (
    AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,
)

from app.services.ad_recycle_bin_activation_preexecution import (
    AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_TTL_SECONDS,
    AdRecycleBinActivationPreexecutionConflict,
    AdRecycleBinActivationPreexecutionError,
    assert_ad_recycle_bin_activation_preexecution_invariants,
    build_ad_recycle_bin_activation_preexecution,
)

from app.services.ad_recycle_bin_activation_ticket import (
    build_ad_recycle_bin_activation_ticket,
)

from app.services.ad_recycle_bin_activation_ticket_consumption import (
    consume_ad_recycle_bin_activation_ticket,
)

from app.services.ad_recycle_bin_activation_ticket_persistence import (
    persist_ad_recycle_bin_activation_ticket,
)


NOW = datetime(
    2026,
    8,
    10,
    17,
    15,
    0,
    tzinfo=timezone.utc,
)


def allowed_azp():
    if OIDC_ALLOWED_AZP:
        return sorted(
            OIDC_ALLOWED_AZP
        )[0]

    return "eitas-portal"


def actor():
    return {
        "subject": "subject-c94-preexec",
        "username": "admin-c94-preexec",
        "issuer": OIDC_ISSUER,
        "azp": allowed_azp(),
    }


def source_record():
    current_actor = actor()

    return {
        "contract_version":
            AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,

        "intent_id":
            str(uuid4()),

        "intent_digest":
            "a" * 64,

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
            (
                NOW
                - timedelta(seconds=30)
            ).isoformat(),

        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "activation_authorized": False,
        "restore_authorized": False,
        "write_performed": False,
    }


def evidence_job(
    *,
    job_id,
    created_at,
    recycle_bin_enabled=False,
    replication_ready=True,
    replication_failure_count=0,
):
    return {
        "id": job_id,
        "type": "ad_explorer",
        "action": "get_recycle_bin_activation_evidence",
        "status": "completed",
        "success": True,
        "result": {
            "action": "get_recycle_bin_activation_evidence",
            "read_only": True,
            "forest_name": "API.LOCAL",
            "root_domain": "API.LOCAL",
            "forest_mode": "Windows2025Forest",
            "recycle_bin_enabled": recycle_bin_enabled,
            "recycle_bin_enabled_scope_count": (
                1 if recycle_bin_enabled else 0
            ),
            "domain_controller_count": 1,
            "replication_query_succeeded": True,
            "replication_partner_query_succeeded": True,
            "replication_failure_count": replication_failure_count,
            "replication_partner_count": 0,
            "replication_ready": replication_ready,
            "evidence_created_at": created_at.isoformat(),
            "activation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "restore_authorized": False,
            "write_performed": False,
        },
    }


def make_authorization_record(
    tmp_path,
):
    source = source_record()

    initial_evidence = evidence_job(
        job_id="authorization-evidence",
        created_at=NOW - timedelta(seconds=5),
    )

    ticket = build_ad_recycle_bin_activation_ticket(
        source_intent_record=source,
        expected_intent_id=source["intent_id"],
        expected_intent_digest=source["intent_digest"],
        evidence_job=initial_evidence,
        expected_evidence_job_id="authorization-evidence",
        server_actor=actor(),
        confirmed_forest_name="API.LOCAL",
        current_mode="Simulation",
        now=NOW,
    )

    persisted_ticket = persist_ad_recycle_bin_activation_ticket(
        ticket,
        storage_file=tmp_path / "tickets.json",
        now=NOW + timedelta(seconds=1),
    )

    consumption = consume_ad_recycle_bin_activation_ticket(
        persisted_ticket,
        consumption_registry_file=tmp_path / "consumptions.json",
        server_actor=actor(),
        current_mode="Simulation",
        now=NOW + timedelta(seconds=2),
    )

    authorization = build_ad_recycle_bin_activation_authorization(
        persisted_ticket,
        consumption,
        server_actor=actor(),
        payload={
            "ticket_id": persisted_ticket.ticket_id,
            "ticket_digest": persisted_ticket.ticket_digest,
            "consumption_id": consumption.consumption_id,
            "forest_name": "API.LOCAL",
            "acknowledge_forest_wide": True,
            "acknowledge_irreversible": True,
            "acknowledge_no_restore": True,
            "authorization_reason":
                "Activation C9.4 explicitement autorisée.",
        },
        current_mode="Simulation",
        now=NOW + timedelta(seconds=3),
    )

    return persist_ad_recycle_bin_activation_authorization(
        authorization,
        registry_file=tmp_path / "authorizations.json",
        now=NOW + timedelta(seconds=4),
    )


def fresh_evidence(
    *,
    created_at=None,
    **kwargs,
):
    return evidence_job(
        job_id="preexecution-evidence",
        created_at=(
            NOW + timedelta(seconds=5)
            if created_at is None
            else created_at
        ),
        **kwargs,
    )


def build(
    tmp_path,
    *,
    fresh=None,
    current_actor=None,
    mode="Simulation",
    confirmed_forest="API.LOCAL",
    now=None,
):
    authorization = make_authorization_record(
        tmp_path
    )

    return build_ad_recycle_bin_activation_preexecution(
        authorization,
        fresh_evidence_job=(
            fresh_evidence()
            if fresh is None
            else fresh
        ),
        expected_authorization_id=authorization.authorization_id,
        expected_authorization_digest=authorization.authorization_digest,
        server_actor=(
            actor()
            if current_actor is None
            else current_actor
        ),
        confirmed_forest_name=confirmed_forest,
        current_mode=mode,
        now=(
            NOW + timedelta(seconds=6)
            if now is None
            else now
        ),
    )


def test_valid_preexecution_requires_fresh_revalidation_but_no_runtime(
    tmp_path,
):
    preexecution = build(
        tmp_path
    )

    assert preexecution.state == "activation_preexecution_ready_dormant"
    assert preexecution.status == "ready"

    assert preexecution.human_authorized is True
    assert preexecution.revalidation_passed is True
    assert preexecution.authorization_consumption_required is True
    assert preexecution.authorization_consumed is False

    assert preexecution.activation_authorized is True
    assert preexecution.persistence_enabled is False
    assert preexecution.route_enabled is False
    assert preexecution.job_creation_authorized is False
    assert preexecution.runtime_authorized is False
    assert preexecution.production_authorized is False
    assert preexecution.restore_authorized is False
    assert preexecution.write_performed is False

    assert len(preexecution.preexecution_digest) == 64


def test_preexecution_ttl_is_at_most_45_seconds(
    tmp_path,
):
    preexecution = build(
        tmp_path
    )

    issued = datetime.fromisoformat(
        preexecution.issued_at
    )

    expires = datetime.fromisoformat(
        preexecution.expires_at
    )

    assert int(
        (
            expires
            - issued
        ).total_seconds()
    ) <= AD_RECYCLE_BIN_ACTIVATION_PREEXECUTION_TTL_SECONDS


def test_fresh_evidence_must_be_newer_than_authorization(
    tmp_path,
):
    authorization = make_authorization_record(
        tmp_path
    )

    old = evidence_job(
        job_id="too-old-evidence",
        created_at=datetime.fromisoformat(
            authorization.persisted_at
        ),
    )

    with pytest.raises(
        AdRecycleBinActivationPreexecutionConflict,
        match="newer than persisted authorization",
    ):
        build_ad_recycle_bin_activation_preexecution(
            authorization,
            fresh_evidence_job=old,
            expected_authorization_id=authorization.authorization_id,
            expected_authorization_digest=authorization.authorization_digest,
            server_actor=actor(),
            confirmed_forest_name="API.LOCAL",
            current_mode="Simulation",
            now=NOW + timedelta(seconds=6),
        )


def test_stale_fresh_evidence_is_rejected(
    tmp_path,
):
    with pytest.raises(
        AdRecycleBinActivationPreexecutionConflict,
        match="stale",
    ):
        build(
            tmp_path,
            fresh=fresh_evidence(
                created_at=NOW - timedelta(seconds=100),
            ),
        )


def test_recycle_bin_already_enabled_is_rejected(
    tmp_path,
):
    with pytest.raises(
        AdRecycleBinActivationPreexecutionConflict,
        match="already enabled",
    ):
        build(
            tmp_path,
            fresh=fresh_evidence(
                recycle_bin_enabled=True,
            ),
        )


def test_replication_failure_is_rejected(
    tmp_path,
):
    with pytest.raises(
        AdRecycleBinActivationPreexecutionConflict,
        match="replication failures",
    ):
        build(
            tmp_path,
            fresh=fresh_evidence(
                replication_failure_count=1,
                replication_ready=False,
            ),
        )


def test_replication_not_ready_is_rejected(
    tmp_path,
):
    with pytest.raises(
        AdRecycleBinActivationPreexecutionConflict,
        match="not ready",
    ):
        build(
            tmp_path,
            fresh=fresh_evidence(
                replication_ready=False,
            ),
        )


def test_actor_mismatch_is_rejected(
    tmp_path,
):
    current_actor = actor()
    current_actor["subject"] = "other-subject"

    with pytest.raises(
        AdRecycleBinActivationPreexecutionConflict,
        match="actor mismatch",
    ):
        build(
            tmp_path,
            current_actor=current_actor,
        )


def test_forest_mismatch_is_rejected(
    tmp_path,
):
    with pytest.raises(
        AdRecycleBinActivationPreexecutionConflict,
        match="forest confirmation mismatch",
    ):
        build(
            tmp_path,
            confirmed_forest="OTHER.LOCAL",
        )


def test_production_mode_is_rejected(
    tmp_path,
):
    with pytest.raises(
        AdRecycleBinActivationPreexecutionError,
        match="Simulation-only",
    ):
        build(
            tmp_path,
            mode="Production",
        )


def test_expired_authorization_is_rejected(
    tmp_path,
):
    authorization = make_authorization_record(
        tmp_path
    )

    expires = datetime.fromisoformat(
        authorization.expires_at
    )

    with pytest.raises(
        AdRecycleBinActivationPreexecutionConflict,
        match="expired",
    ):
        build_ad_recycle_bin_activation_preexecution(
            authorization,
            fresh_evidence_job=fresh_evidence(
                created_at=expires - timedelta(seconds=1),
            ),
            expected_authorization_id=authorization.authorization_id,
            expected_authorization_digest=authorization.authorization_digest,
            server_actor=actor(),
            confirmed_forest_name="API.LOCAL",
            current_mode="Simulation",
            now=expires,
        )


def test_authorization_digest_mismatch_is_rejected(
    tmp_path,
):
    authorization = make_authorization_record(
        tmp_path
    )

    with pytest.raises(
        AdRecycleBinActivationPreexecutionConflict,
        match="authorization digest mismatch",
    ):
        build_ad_recycle_bin_activation_preexecution(
            authorization,
            fresh_evidence_job=fresh_evidence(),
            expected_authorization_id=authorization.authorization_id,
            expected_authorization_digest="f" * 64,
            server_actor=actor(),
            confirmed_forest_name="API.LOCAL",
            current_mode="Simulation",
            now=NOW + timedelta(seconds=6),
        )


def test_preexecution_digest_mutation_is_rejected(
    tmp_path,
):
    preexecution = build(
        tmp_path
    )

    altered = replace(
        preexecution,
        forest_name="OTHER.LOCAL",
    )

    with pytest.raises(
        AdRecycleBinActivationPreexecutionError,
        match="digest mismatch",
    ):
        assert_ad_recycle_bin_activation_preexecution_invariants(
            altered
        )


def test_service_is_not_runtime_integrated():
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

    assert "ad_recycle_bin_activation_preexecution" not in main
    assert "activate_recycle_bin" not in admin
    assert "activate_recycle_bin" not in windows
    assert "Enable-ADOptionalFeature" not in windows
    assert "Restore-ADObject" not in windows
