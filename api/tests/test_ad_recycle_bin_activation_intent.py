from datetime import datetime, timedelta, timezone

import pytest

from app.services.ad_recycle_bin_activation_intent import (
    AD_RECYCLE_BIN_ACTIVATION_INTENT_CONTRACT_VERSION,
    AdRecycleBinActivationIntentError,
    assert_ad_recycle_bin_activation_intent_invariants,
    build_ad_recycle_bin_activation_intent,
)


NOW = datetime(
    2026,
    8,
    10,
    15,
    0,
    tzinfo=timezone.utc,
)


def valid_payload():
    return {
        "forest_name": "API.LOCAL",
        "acknowledge_forest_wide": True,
        "acknowledge_irreversible": True,
        "acknowledge_no_restore": True,
        "requested_reason": (
            "C9.3 dormant readiness preparation"
        ),
    }


def valid_evidence():
    return {
        "forest_name": "API.LOCAL",
        "root_domain": "API.LOCAL",
        "forest_mode": "Windows2025Forest",
        "recycle_bin_enabled": False,
        "replication_ready": True,
        "evidence_created_at": NOW.isoformat(),
    }


def valid_actor():
    return {
        "subject": "oidc-subject-test",
        "username": "eitas-admin",
        "issuer": "https://identity.example.invalid/",
        "azp": "eitas-portal",
    }


def build(
    payload=None,
    evidence=None,
    actor=None,
    *,
    mode="Simulation",
    now=NOW,
):
    return build_ad_recycle_bin_activation_intent(
        (
            valid_payload()
            if payload is None
            else payload
        ),
        current_mode=mode,
        server_evidence=(
            valid_evidence()
            if evidence is None
            else evidence
        ),
        server_actor=(
            valid_actor()
            if actor is None
            else actor
        ),
        now=now,
    )


def test_valid_intent_is_dormant_and_non_authorizing():
    intent = build()

    assert intent.contract_version == (
        AD_RECYCLE_BIN_ACTIVATION_INTENT_CONTRACT_VERSION
    )

    assert intent.state == "activation_intent_dormant"

    assert intent.forest_name == "API.LOCAL"
    assert intent.root_domain == "API.LOCAL"
    assert intent.forest_mode == "Windows2025Forest"

    assert intent.recycle_bin_enabled is False
    assert intent.replication_ready is True

    assert len(intent.evidence_sha256) == 64

    assert intent.actor_subject == "oidc-subject-test"
    assert intent.actor_username == "eitas-admin"
    assert intent.actor_azp == "eitas-portal"

    assert intent.acknowledge_forest_wide is True
    assert intent.acknowledge_irreversible is True
    assert intent.acknowledge_no_restore is True

    assert intent.persistence_enabled is False
    assert intent.job_creation_authorized is False
    assert intent.runtime_authorized is False
    assert intent.production_authorized is False
    assert intent.activation_authorized is False
    assert intent.restore_authorized is False
    assert intent.write_performed is False

    assert_ad_recycle_bin_activation_intent_invariants(
        intent
    )


def test_production_mode_is_rejected():
    with pytest.raises(
        AdRecycleBinActivationIntentError,
        match="only in Simulation mode",
    ):
        build(
            mode="Production"
        )


def test_enabled_recycle_bin_is_rejected():
    evidence = valid_evidence()
    evidence["recycle_bin_enabled"] = True

    with pytest.raises(
        AdRecycleBinActivationIntentError,
        match="must still be disabled",
    ):
        build(
            evidence=evidence
        )


def test_replication_not_ready_is_rejected():
    evidence = valid_evidence()
    evidence["replication_ready"] = False

    with pytest.raises(
        AdRecycleBinActivationIntentError,
        match="Replication readiness is required",
    ):
        build(
            evidence=evidence
        )


def test_stale_server_evidence_is_rejected():
    evidence = valid_evidence()

    evidence["evidence_created_at"] = (
        NOW
        - timedelta(
            seconds=301
        )
    ).isoformat()

    with pytest.raises(
        AdRecycleBinActivationIntentError,
        match="Server evidence is stale",
    ):
        build(
            evidence=evidence
        )


def test_future_server_evidence_is_rejected():
    evidence = valid_evidence()

    evidence["evidence_created_at"] = (
        NOW
        + timedelta(
            seconds=31
        )
    ).isoformat()

    with pytest.raises(
        AdRecycleBinActivationIntentError,
        match="from the future",
    ):
        build(
            evidence=evidence
        )


def test_forest_mismatch_is_rejected():
    payload = valid_payload()
    payload["forest_name"] = "OTHER.LOCAL"

    with pytest.raises(
        AdRecycleBinActivationIntentError,
        match="does not match server evidence",
    ):
        build(
            payload=payload
        )


@pytest.mark.parametrize(
    "field",
    [
        "acknowledge_forest_wide",
        "acknowledge_irreversible",
        "acknowledge_no_restore",
    ],
)
def test_all_safety_acknowledgements_are_required(
    field,
):
    payload = valid_payload()
    payload[field] = False

    with pytest.raises(
        AdRecycleBinActivationIntentError,
        match=field,
    ):
        build(
            payload=payload
        )


@pytest.mark.parametrize(
    "field",
    [
        "created_by",
        "actor_subject",
        "actor_username",
        "issuer",
        "azp",
    ],
)
def test_client_identity_spoofing_is_rejected(
    field,
):
    payload = valid_payload()
    payload[field] = "spoofed"

    with pytest.raises(
        AdRecycleBinActivationIntentError,
        match="Client identity fields are forbidden",
    ):
        build(
            payload=payload
        )


def test_unknown_client_field_is_rejected():
    payload = valid_payload()
    payload["runtime_authorized"] = True

    with pytest.raises(
        AdRecycleBinActivationIntentError,
        match="Unknown activation intent fields",
    ):
        build(
            payload=payload
        )


def test_server_actor_is_authoritative():
    payload = valid_payload()

    intent = build(
        payload=payload,
        actor={
            "subject": "trusted-sub",
            "username": "trusted-user",
            "issuer": "https://trusted.invalid/",
            "azp": "trusted-portal",
        },
    )

    assert intent.actor_subject == "trusted-sub"
    assert intent.actor_username == "trusted-user"
    assert intent.actor_issuer == (
        "https://trusted.invalid/"
    )
    assert intent.actor_azp == "trusted-portal"


def test_evidence_digest_is_deterministic():
    first = build()
    second = build()

    assert first.evidence_sha256 == (
        second.evidence_sha256
    )
