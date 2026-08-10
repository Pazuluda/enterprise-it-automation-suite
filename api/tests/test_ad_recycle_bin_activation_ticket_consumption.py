import json
import os
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
    build_ad_recycle_bin_activation_ticket,
)

from app.services.ad_recycle_bin_activation_ticket_consumption import (
    AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_CONTRACT_VERSION,
    AdRecycleBinActivationTicketConsumptionConflict,
    AdRecycleBinActivationTicketConsumptionError,
    consume_ad_recycle_bin_activation_ticket,
)

from app.services.ad_recycle_bin_activation_ticket_persistence import (
    persist_ad_recycle_bin_activation_ticket,
)


NOW = datetime(
    2026,
    8,
    10,
    16,
    30,
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
        "subject": "subject-c94-consume",
        "username": "admin-c94-consume",
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


def evidence_job():
    return {
        "id":
            "fresh-evidence-consumption",

        "type":
            "ad_explorer",

        "action":
            "get_recycle_bin_activation_evidence",

        "status":
            "completed",

        "success":
            True,

        "result": {
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
                (
                    NOW
                    - timedelta(seconds=5)
                ).isoformat(),

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
        },
    }


def make_persisted_ticket(
    tmp_path,
):
    source = source_record()

    ticket = build_ad_recycle_bin_activation_ticket(
        source_intent_record=source,
        expected_intent_id=source["intent_id"],
        expected_intent_digest=source["intent_digest"],
        evidence_job=evidence_job(),
        expected_evidence_job_id="fresh-evidence-consumption",
        server_actor=actor(),
        confirmed_forest_name="API.LOCAL",
        current_mode="Simulation",
        now=NOW,
    )

    return persist_ad_recycle_bin_activation_ticket(
        ticket,
        storage_file=tmp_path / "tickets.json",
        now=NOW + timedelta(seconds=1),
    )


def stat_mode(path):
    return os.stat(path).st_mode & 0o777


def consume(
    ticket,
    registry,
    *,
    current_actor=None,
    mode="Simulation",
    now=None,
):
    return consume_ad_recycle_bin_activation_ticket(
        ticket,
        consumption_registry_file=registry,
        server_actor=(
            actor()
            if current_actor is None
            else current_actor
        ),
        current_mode=mode,
        now=(
            NOW + timedelta(seconds=2)
            if now is None
            else now
        ),
    )


def test_ticket_is_consumed_once_without_authorizing_runtime(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    registry = (
        tmp_path
        / "consumptions.json"
    )

    record = consume(
        ticket,
        registry,
    )

    assert record.state == "activation_ticket_consumed"
    assert record.consumed is True

    assert record.job_creation_authorized is False
    assert record.runtime_authorized is False
    assert record.production_authorized is False
    assert record.activation_authorized is False
    assert record.restore_authorized is False
    assert record.write_performed is False

    assert len(record.record_digest) == 64

    data = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    assert data["contract_version"] == (
        AD_RECYCLE_BIN_ACTIVATION_TICKET_CONSUMPTION_CONTRACT_VERSION
    )

    assert len(data["records"]) == 1


def test_second_consumption_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    registry = (
        tmp_path
        / "consumptions.json"
    )

    consume(
        ticket,
        registry,
    )

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionConflict,
        match="already consumed",
    ):
        consume(
            ticket,
            registry,
            now=NOW + timedelta(seconds=3),
        )


def test_actor_subject_mismatch_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    current_actor = actor()
    current_actor["subject"] = "other-subject"

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionConflict,
        match="actor mismatch",
    ):
        consume(
            ticket,
            tmp_path / "consumptions.json",
            current_actor=current_actor,
        )


def test_wrong_issuer_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    current_actor = actor()
    current_actor["issuer"] = "https://wrong.invalid/"

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionConflict,
        match="OIDC issuer mismatch",
    ):
        consume(
            ticket,
            tmp_path / "consumptions.json",
            current_actor=current_actor,
        )


def test_expired_ticket_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    expires = datetime.fromisoformat(
        ticket.expires_at
    )

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionConflict,
        match="expired ticket",
    ):
        consume(
            ticket,
            tmp_path / "consumptions.json",
            now=expires,
        )


def test_future_issued_ticket_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    altered = replace(
        ticket,
        issued_at=(
            NOW + timedelta(seconds=10)
        ).isoformat(),
    )

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionError,
    ):
        consume(
            altered,
            tmp_path / "consumptions.json",
        )


def test_production_mode_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionError,
        match="Simulation-only",
    ):
        consume(
            ticket,
            tmp_path / "consumptions.json",
            mode="Production",
        )


def test_registry_and_lock_are_mode_0600(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    registry = (
        tmp_path
        / "consumptions.json"
    )

    consume(
        ticket,
        registry,
    )

    lock = (
        tmp_path
        / ".consumptions.json.lock"
    )

    assert stat_mode(registry) == 0o600
    assert stat_mode(lock) == 0o600


def test_existing_registry_symlink_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    target = (
        tmp_path
        / "target.json"
    )

    target.write_text(
        '{"safe":true}',
        encoding="utf-8",
    )

    registry = (
        tmp_path
        / "consumptions.json"
    )

    registry.symlink_to(
        target
    )

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionError,
        match="must not be a symlink",
    ):
        consume(
            ticket,
            registry,
        )


def test_dangling_registry_symlink_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    registry = (
        tmp_path
        / "consumptions.json"
    )

    registry.symlink_to(
        tmp_path
        / "missing.json"
    )

    assert registry.exists() is False
    assert registry.is_symlink() is True

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionError,
        match="must not be a symlink",
    ):
        consume(
            ticket,
            registry,
        )


def test_symlink_lock_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    registry = (
        tmp_path
        / "consumptions.json"
    )

    lock = (
        tmp_path
        / ".consumptions.json.lock"
    )

    target = (
        tmp_path
        / "lock-target"
    )

    target.write_text(
        "",
        encoding="utf-8",
    )

    lock.symlink_to(
        target
    )

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionError,
        match="must not be a symlink",
    ):
        consume(
            ticket,
            registry,
        )


def test_wrong_registry_version_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    registry = (
        tmp_path
        / "consumptions.json"
    )

    registry.write_text(
        json.dumps(
            {
                "contract_version":
                    "wrong-version",
                "records":
                    [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionError,
        match="registry contract version mismatch",
    ):
        consume(
            ticket,
            registry,
        )


def test_tampered_consumption_record_is_rejected(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    registry = (
        tmp_path
        / "consumptions.json"
    )

    consume(
        ticket,
        registry,
    )

    data = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    data["records"][0]["forest_name"] = "OTHER.LOCAL"

    registry.write_text(
        json.dumps(
            data
        ),
        encoding="utf-8",
    )

    second_ticket = make_persisted_ticket(
        tmp_path
        / "second"
    )

    with pytest.raises(
        AdRecycleBinActivationTicketConsumptionError,
        match="record digest mismatch",
    ):
        consume(
            second_ticket,
            registry,
        )


def test_registry_never_contains_pending(
    tmp_path,
):
    ticket = make_persisted_ticket(
        tmp_path
    )

    registry = (
        tmp_path
        / "consumptions.json"
    )

    consume(
        ticket,
        registry,
    )

    raw = registry.read_text(
        encoding="utf-8"
    )

    assert '"status": "pending"' not in raw
    assert "activation_ticket_consumed" in raw


def test_consumption_service_is_not_runtime_integrated():
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
        "ad_recycle_bin_activation_ticket_consumption"
        not in main
    )

    assert "activate_recycle_bin" not in admin
    assert "activate_recycle_bin" not in windows
