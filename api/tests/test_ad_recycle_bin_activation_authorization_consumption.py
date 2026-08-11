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

from app.services.ad_recycle_bin_activation_authorization import (
    build_ad_recycle_bin_activation_authorization,
)

from app.services.ad_recycle_bin_activation_authorization_consumption import (
    AdRecycleBinActivationAuthorizationConsumptionConflict,
    AdRecycleBinActivationAuthorizationConsumptionError,
    consume_ad_recycle_bin_activation_authorization,
)

from app.services.ad_recycle_bin_activation_authorization_persistence import (
    persist_ad_recycle_bin_activation_authorization,
)

from app.services.ad_recycle_bin_activation_intent_persistence import (
    AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,
)

from app.services.ad_recycle_bin_activation_preexecution import (
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
        "subject": "subject-c94-auth-consume",
        "username": "admin-c94-auth-consume",
        "issuer": OIDC_ISSUER,
        "azp": allowed_azp(),
    }


def source_record():
    current_actor = actor()

    return {
        "contract_version":
            AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,

        "intent_id":
            str(
                uuid4()
            ),

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
                - timedelta(
                    seconds=30
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


def evidence_job(
    *,
    job_id,
    created_at,
):
    return {
        "id":
            job_id,

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
                created_at.isoformat(),

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


def make_records(
    tmp_path,
):
    source = source_record()

    authorization_evidence = evidence_job(
        job_id="authorization-evidence-consume",
        created_at=NOW - timedelta(
            seconds=5
        ),
    )

    ticket = build_ad_recycle_bin_activation_ticket(
        source_intent_record=source,
        expected_intent_id=source[
            "intent_id"
        ],
        expected_intent_digest=source[
            "intent_digest"
        ],
        evidence_job=authorization_evidence,
        expected_evidence_job_id="authorization-evidence-consume",
        server_actor=actor(),
        confirmed_forest_name="API.LOCAL",
        current_mode="Simulation",
        now=NOW,
    )

    persisted_ticket = persist_ad_recycle_bin_activation_ticket(
        ticket,
        storage_file=tmp_path / "tickets.json",
        now=NOW + timedelta(
            seconds=1
        ),
    )

    ticket_consumption = consume_ad_recycle_bin_activation_ticket(
        persisted_ticket,
        consumption_registry_file=tmp_path / "ticket-consumptions.json",
        server_actor=actor(),
        current_mode="Simulation",
        now=NOW + timedelta(
            seconds=2
        ),
    )

    authorization = build_ad_recycle_bin_activation_authorization(
        persisted_ticket,
        ticket_consumption,
        server_actor=actor(),
        payload={
            "ticket_id":
                persisted_ticket.ticket_id,

            "ticket_digest":
                persisted_ticket.ticket_digest,

            "consumption_id":
                ticket_consumption.consumption_id,

            "forest_name":
                "API.LOCAL",

            "acknowledge_forest_wide":
                True,

            "acknowledge_irreversible":
                True,

            "acknowledge_no_restore":
                True,

            "authorization_reason":
                "Activation C9.4 explicitement autorisée.",
        },
        current_mode="Simulation",
        now=NOW + timedelta(
            seconds=3
        ),
    )

    authorization_record = persist_ad_recycle_bin_activation_authorization(
        authorization,
        registry_file=tmp_path / "authorizations.json",
        now=NOW + timedelta(
            seconds=4
        ),
    )

    fresh_evidence = evidence_job(
        job_id="preexecution-evidence-consume",
        created_at=NOW + timedelta(
            seconds=5
        ),
    )

    preexecution = build_ad_recycle_bin_activation_preexecution(
        authorization_record,
        fresh_evidence_job=fresh_evidence,
        expected_authorization_id=authorization_record.authorization_id,
        expected_authorization_digest=authorization_record.authorization_digest,
        server_actor=actor(),
        confirmed_forest_name="API.LOCAL",
        current_mode="Simulation",
        now=NOW + timedelta(
            seconds=6
        ),
    )

    return (
        authorization_record,
        preexecution,
    )


def stat_mode(
    path,
):
    return (
        os.stat(
            path
        ).st_mode
        & 0o777
    )


def consume(
    tmp_path,
    *,
    current_actor=None,
    mode="Simulation",
    now=None,
):
    authorization_record, preexecution = make_records(
        tmp_path
    )

    record = consume_ad_recycle_bin_activation_authorization(
        authorization_record,
        preexecution,
        consumption_registry_file=tmp_path / "authorization-consumptions.json",
        server_actor=(
            actor()
            if current_actor is None
            else current_actor
        ),
        current_mode=mode,
        now=(
            NOW + timedelta(
                seconds=7
            )
            if now is None
            else now
        ),
    )

    return (
        authorization_record,
        preexecution,
        record,
    )


def test_valid_consumption_is_one_shot_but_not_runtime_authorization(
    tmp_path,
):
    _, _, record = consume(
        tmp_path
    )

    assert record.state == "activation_authorization_consumed"
    assert record.status == "consumed"

    assert record.human_authorized is True
    assert record.revalidation_passed is True
    assert record.authorization_consumed is True
    assert record.one_shot_consumption is True

    assert record.activation_authorized is True
    assert record.persistence_enabled is True

    assert record.route_enabled is False
    assert record.job_creation_authorized is False
    assert record.runtime_authorized is False
    assert record.production_authorized is False
    assert record.restore_authorized is False
    assert record.write_performed is False

    assert len(
        record.record_digest
    ) == 64


def test_duplicate_authorization_consumption_is_rejected(
    tmp_path,
):
    authorization_record, preexecution = make_records(
        tmp_path
    )

    registry = (
        tmp_path
        / "authorization-consumptions.json"
    )

    consume_ad_recycle_bin_activation_authorization(
        authorization_record,
        preexecution,
        consumption_registry_file=registry,
        server_actor=actor(),
        current_mode="Simulation",
        now=NOW + timedelta(
            seconds=7
        ),
    )

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConsumptionConflict,
        match="already consumed",
    ):
        consume_ad_recycle_bin_activation_authorization(
            authorization_record,
            preexecution,
            consumption_registry_file=registry,
            server_actor=actor(),
            current_mode="Simulation",
            now=NOW + timedelta(
                seconds=8
            ),
        )


def test_registry_and_lock_are_mode_0600(
    tmp_path,
):
    consume(
        tmp_path
    )

    registry = (
        tmp_path
        / "authorization-consumptions.json"
    )

    lock = (
        tmp_path
        / ".authorization-consumptions.json.lock"
    )

    assert stat_mode(
        registry
    ) == 0o600

    assert stat_mode(
        lock
    ) == 0o600


def test_actor_mismatch_is_rejected(
    tmp_path,
):
    current_actor = actor()
    current_actor[
        "subject"
    ] = "other-subject"

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConsumptionConflict,
        match="actor mismatch",
    ):
        consume(
            tmp_path,
            current_actor=current_actor,
        )


def test_production_mode_is_rejected(
    tmp_path,
):
    with pytest.raises(
        AdRecycleBinActivationAuthorizationConsumptionError,
        match="Simulation-only",
    ):
        consume(
            tmp_path,
            mode="Production",
        )


def test_expired_preexecution_is_rejected(
    tmp_path,
):
    authorization_record, preexecution = make_records(
        tmp_path
    )

    expires = datetime.fromisoformat(
        preexecution.expires_at
    )

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConsumptionConflict,
        match="preexecution expired",
    ):
        consume_ad_recycle_bin_activation_authorization(
            authorization_record,
            preexecution,
            consumption_registry_file=tmp_path / "authorization-consumptions.json",
            server_actor=actor(),
            current_mode="Simulation",
            now=expires,
        )


def test_mismatched_preexecution_binding_is_rejected(
    tmp_path,
):
    authorization_record, preexecution = make_records(
        tmp_path
    )

    altered = replace(
        preexecution,
        authorization_record_digest="f" * 64,
    )

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConsumptionError,
    ):
        consume_ad_recycle_bin_activation_authorization(
            authorization_record,
            altered,
            consumption_registry_file=tmp_path / "authorization-consumptions.json",
            server_actor=actor(),
            current_mode="Simulation",
            now=NOW + timedelta(
                seconds=7
            ),
        )


def test_existing_registry_symlink_is_rejected(
    tmp_path,
):
    authorization_record, preexecution = make_records(
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
        / "authorization-consumptions.json"
    )

    registry.symlink_to(
        target
    )

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConsumptionError,
        match="must not be a symlink",
    ):
        consume_ad_recycle_bin_activation_authorization(
            authorization_record,
            preexecution,
            consumption_registry_file=registry,
            server_actor=actor(),
            current_mode="Simulation",
            now=NOW + timedelta(
                seconds=7
            ),
        )


def test_dangling_registry_symlink_is_rejected(
    tmp_path,
):
    authorization_record, preexecution = make_records(
        tmp_path
    )

    registry = (
        tmp_path
        / "authorization-consumptions.json"
    )

    registry.symlink_to(
        tmp_path
        / "missing.json"
    )

    assert registry.exists() is False
    assert registry.is_symlink() is True

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConsumptionError,
        match="must not be a symlink",
    ):
        consume_ad_recycle_bin_activation_authorization(
            authorization_record,
            preexecution,
            consumption_registry_file=registry,
            server_actor=actor(),
            current_mode="Simulation",
            now=NOW + timedelta(
                seconds=7
            ),
        )


def test_lock_symlink_is_rejected(
    tmp_path,
):
    authorization_record, preexecution = make_records(
        tmp_path
    )

    registry = (
        tmp_path
        / "authorization-consumptions.json"
    )

    lock = (
        tmp_path
        / ".authorization-consumptions.json.lock"
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
        AdRecycleBinActivationAuthorizationConsumptionError,
        match="must not be a symlink",
    ):
        consume_ad_recycle_bin_activation_authorization(
            authorization_record,
            preexecution,
            consumption_registry_file=registry,
            server_actor=actor(),
            current_mode="Simulation",
            now=NOW + timedelta(
                seconds=7
            ),
        )


def test_persisted_record_contains_no_runtime_or_write_rights(
    tmp_path,
):
    consume(
        tmp_path
    )

    registry = (
        tmp_path
        / "authorization-consumptions.json"
    )

    raw = registry.read_text(
        encoding="utf-8"
    )

    assert '"authorization_consumed": true' in raw

    assert '"runtime_authorized": true' not in raw
    assert '"production_authorized": true' not in raw
    assert '"restore_authorized": true' not in raw
    assert '"write_performed": true' not in raw


def test_tampered_registry_record_is_rejected(
    tmp_path,
):
    authorization_record, preexecution, _ = consume(
        tmp_path
    )

    registry = (
        tmp_path
        / "authorization-consumptions.json"
    )

    data = json.loads(
        registry.read_text(
            encoding="utf-8"
        )
    )

    data[
        "records"
    ][0][
        "forest_name"
    ] = "OTHER.LOCAL"

    registry.write_text(
        json.dumps(
            data
        ),
        encoding="utf-8",
    )

    another_root = (
        tmp_path
        / "another"
    )

    another_root.mkdir()

    second_authorization, second_preexecution = make_records(
        another_root
    )

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConsumptionError,
        match="record digest mismatch",
    ):
        consume_ad_recycle_bin_activation_authorization(
            second_authorization,
            second_preexecution,
            consumption_registry_file=registry,
            server_actor=actor(),
            current_mode="Simulation",
            now=NOW + timedelta(
                seconds=7
            ),
        )


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
        "ad_recycle_bin_activation_authorization_consumption"
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
