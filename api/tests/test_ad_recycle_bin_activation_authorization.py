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
    AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_TTL_SECONDS,
    AdRecycleBinActivationAuthorizationConflict,
    AdRecycleBinActivationAuthorizationError,
    assert_ad_recycle_bin_activation_authorization_invariants,
    build_ad_recycle_bin_activation_authorization,
)

from app.services.ad_recycle_bin_activation_intent_persistence import (
    AD_RECYCLE_BIN_ACTIVATION_INTENT_PERSISTENCE_CONTRACT_VERSION,
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
    16,
    45,
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
        "subject": "subject-c94-auth",
        "username": "admin-c94-auth",
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
            "fresh-evidence-auth",

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


def make_records(
    tmp_path,
):
    source = source_record()

    ticket = build_ad_recycle_bin_activation_ticket(
        source_intent_record=source,
        expected_intent_id=source["intent_id"],
        expected_intent_digest=source["intent_digest"],
        evidence_job=evidence_job(),
        expected_evidence_job_id="fresh-evidence-auth",
        server_actor=actor(),
        confirmed_forest_name="API.LOCAL",
        current_mode="Simulation",
        now=NOW,
    )

    persisted = persist_ad_recycle_bin_activation_ticket(
        ticket,
        storage_file=tmp_path / "tickets.json",
        now=NOW + timedelta(seconds=1),
    )

    consumed = consume_ad_recycle_bin_activation_ticket(
        persisted,
        consumption_registry_file=tmp_path / "consumptions.json",
        server_actor=actor(),
        current_mode="Simulation",
        now=NOW + timedelta(seconds=2),
    )

    return persisted, consumed


def payload(
    ticket,
    consumed,
):
    return {
        "ticket_id":
            ticket.ticket_id,

        "ticket_digest":
            ticket.ticket_digest,

        "consumption_id":
            consumed.consumption_id,

        "forest_name":
            "API.LOCAL",

        "acknowledge_forest_wide":
            True,

        "acknowledge_irreversible":
            True,

        "acknowledge_no_restore":
            True,

        "authorization_reason":
            "Activation contrôlée C9.4 explicitement autorisée.",
    }


def build(
    tmp_path,
    *,
    current_actor=None,
    current_mode="Simulation",
    custom_payload=None,
    now=None,
):
    ticket, consumed = make_records(
        tmp_path
    )

    return build_ad_recycle_bin_activation_authorization(
        ticket,
        consumed,
        server_actor=(
            actor()
            if current_actor is None
            else current_actor
        ),
        payload=(
            payload(
                ticket,
                consumed,
            )
            if custom_payload is None
            else custom_payload(
                ticket,
                consumed,
            )
        ),
        current_mode=current_mode,
        now=(
            NOW + timedelta(seconds=3)
            if now is None
            else now
        ),
    )


def test_valid_authorization_is_human_bound_but_not_runtime_authorized(
    tmp_path,
):
    authorization = build(
        tmp_path
    )

    assert authorization.human_authorized is True
    assert authorization.activation_authorized is True

    assert authorization.persistence_enabled is False
    assert authorization.route_enabled is False
    assert authorization.job_creation_authorized is False
    assert authorization.runtime_authorized is False
    assert authorization.production_authorized is False
    assert authorization.restore_authorized is False
    assert authorization.write_performed is False

    assert authorization.authorization_consumed is False
    assert authorization.one_shot_required is True

    assert authorization.state == "activation_authorization_dormant"
    assert authorization.status == "authorized"

    assert len(authorization.authorization_digest) == 64


def test_authorization_ttl_is_at_most_60_seconds(
    tmp_path,
):
    authorization = build(
        tmp_path
    )

    issued = datetime.fromisoformat(
        authorization.issued_at
    )

    expires = datetime.fromisoformat(
        authorization.expires_at
    )

    assert int(
        (
            expires
            - issued
        ).total_seconds()
    ) <= AD_RECYCLE_BIN_ACTIVATION_AUTHORIZATION_TTL_SECONDS


@pytest.mark.parametrize(
    "field",
    [
        "acknowledge_forest_wide",
        "acknowledge_irreversible",
        "acknowledge_no_restore",
    ],
)
def test_each_explicit_acknowledgement_is_required(
    tmp_path,
    field,
):
    def bad_payload(
        ticket,
        consumed,
    ):
        value = payload(
            ticket,
            consumed,
        )

        value[field] = False

        return value

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConflict,
        match="must be true",
    ):
        build(
            tmp_path,
            custom_payload=bad_payload,
        )


def test_forest_mismatch_is_rejected(
    tmp_path,
):
    def bad_payload(
        ticket,
        consumed,
    ):
        value = payload(
            ticket,
            consumed,
        )

        value["forest_name"] = "OTHER.LOCAL"

        return value

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConflict,
        match="forest confirmation mismatch",
    ):
        build(
            tmp_path,
            custom_payload=bad_payload,
        )


def test_ticket_id_mismatch_is_rejected(
    tmp_path,
):
    def bad_payload(
        ticket,
        consumed,
    ):
        value = payload(
            ticket,
            consumed,
        )

        value["ticket_id"] = str(
            uuid4()
        )

        return value

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConflict,
        match="ticket id confirmation mismatch",
    ):
        build(
            tmp_path,
            custom_payload=bad_payload,
        )


def test_ticket_digest_mismatch_is_rejected(
    tmp_path,
):
    def bad_payload(
        ticket,
        consumed,
    ):
        value = payload(
            ticket,
            consumed,
        )

        value["ticket_digest"] = "f" * 64

        return value

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConflict,
        match="ticket digest confirmation mismatch",
    ):
        build(
            tmp_path,
            custom_payload=bad_payload,
        )


def test_consumption_id_mismatch_is_rejected(
    tmp_path,
):
    def bad_payload(
        ticket,
        consumed,
    ):
        value = payload(
            ticket,
            consumed,
        )

        value["consumption_id"] = str(
            uuid4()
        )

        return value

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConflict,
        match="consumption id confirmation mismatch",
    ):
        build(
            tmp_path,
            custom_payload=bad_payload,
        )


def test_actor_subject_mismatch_is_rejected(
    tmp_path,
):
    current_actor = actor()
    current_actor["subject"] = "other-subject"

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConflict,
        match="actor mismatch",
    ):
        build(
            tmp_path,
            current_actor=current_actor,
        )


def test_wrong_oidc_issuer_is_rejected(
    tmp_path,
):
    current_actor = actor()
    current_actor["issuer"] = "https://wrong.invalid/"

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConflict,
        match="OIDC issuer mismatch",
    ):
        build(
            tmp_path,
            current_actor=current_actor,
        )


def test_unknown_payload_field_is_rejected(
    tmp_path,
):
    def bad_payload(
        ticket,
        consumed,
    ):
        value = payload(
            ticket,
            consumed,
        )

        value["client_actor"] = "forbidden"

        return value

    with pytest.raises(
        AdRecycleBinActivationAuthorizationError,
        match="unknown fields",
    ):
        build(
            tmp_path,
            custom_payload=bad_payload,
        )


def test_short_reason_is_rejected(
    tmp_path,
):
    def bad_payload(
        ticket,
        consumed,
    ):
        value = payload(
            ticket,
            consumed,
        )

        value["authorization_reason"] = "ok"

        return value

    with pytest.raises(
        AdRecycleBinActivationAuthorizationError,
        match="authorization_reason",
    ):
        build(
            tmp_path,
            custom_payload=bad_payload,
        )


def test_production_mode_is_rejected(
    tmp_path,
):
    with pytest.raises(
        AdRecycleBinActivationAuthorizationError,
        match="Simulation-only",
    ):
        build(
            tmp_path,
            current_mode="Production",
        )


def test_expired_ticket_is_rejected(
    tmp_path,
):
    ticket, consumed = make_records(
        tmp_path
    )

    expires = datetime.fromisoformat(
        ticket.expires_at
    )

    with pytest.raises(
        AdRecycleBinActivationAuthorizationConflict,
        match="expired",
    ):
        build_ad_recycle_bin_activation_authorization(
            ticket,
            consumed,
            server_actor=actor(),
            payload=payload(
                ticket,
                consumed,
            ),
            current_mode="Simulation",
            now=expires,
        )


def test_ticket_consumption_binding_is_immutable(
    tmp_path,
):
    ticket, consumed = make_records(
        tmp_path
    )

    altered = replace(
        consumed,
        ticket_digest="f" * 64,
    )

    with pytest.raises(
        AdRecycleBinActivationAuthorizationError,
    ):
        build_ad_recycle_bin_activation_authorization(
            ticket,
            altered,
            server_actor=actor(),
            payload=payload(
                ticket,
                consumed,
            ),
            current_mode="Simulation",
            now=NOW + timedelta(seconds=3),
        )


def test_digest_mutation_is_rejected(
    tmp_path,
):
    authorization = build(
        tmp_path
    )

    altered = replace(
        authorization,
        authorization_reason="Une autre justification contrôlée.",
    )

    with pytest.raises(
        AdRecycleBinActivationAuthorizationError,
        match="digest mismatch",
    ):
        assert_ad_recycle_bin_activation_authorization_invariants(
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

    assert (
        "ad_recycle_bin_activation_authorization"
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
