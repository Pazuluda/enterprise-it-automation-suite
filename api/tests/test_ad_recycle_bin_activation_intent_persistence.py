from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from app.services.ad_recycle_bin_activation_intent import (
    build_ad_recycle_bin_activation_intent,
)

from app.services.ad_recycle_bin_activation_intent_persistence import (
    AdRecycleBinActivationIntentPersistenceError,
    assert_ad_recycle_bin_activation_intent_persistence_invariants,
    persist_ad_recycle_bin_activation_intent,
)


NOW = datetime(
    2026,
    8,
    10,
    15,
    30,
    tzinfo=timezone.utc,
)


def build_intent():
    return build_ad_recycle_bin_activation_intent(
        {
            "forest_name": "API.LOCAL",
            "acknowledge_forest_wide": True,
            "acknowledge_irreversible": True,
            "acknowledge_no_restore": True,
            "requested_reason": "C9.3 persistence test",
        },
        current_mode="Simulation",
        server_evidence={
            "forest_name": "API.LOCAL",
            "root_domain": "API.LOCAL",
            "forest_mode": "Windows2025Forest",
            "recycle_bin_enabled": False,
            "replication_ready": True,
            "evidence_created_at": NOW.isoformat(),
        },
        server_actor={
            "subject": "subject-test",
            "username": "eitas-admin",
            "issuer": "https://identity.invalid/",
            "azp": "eitas-portal",
        },
        now=NOW,
    )


def test_persisted_intent_remains_dormant(
    tmp_path: Path,
):
    storage = tmp_path / "activation-intents.json"

    persisted = persist_ad_recycle_bin_activation_intent(
        build_intent(),
        storage_file=storage,
        now=NOW,
    )

    assert persisted.status == "dormant"
    assert persisted.state == "activation_intent_dormant"

    assert persisted.job_creation_authorized is False
    assert persisted.runtime_authorized is False
    assert persisted.production_authorized is False
    assert persisted.activation_authorized is False
    assert persisted.restore_authorized is False
    assert persisted.write_performed is False

    assert len(persisted.intent_digest) == 64

    assert_ad_recycle_bin_activation_intent_persistence_invariants(
        persisted
    )


def test_storage_record_is_not_pending(
    tmp_path: Path,
):
    storage = tmp_path / "activation-intents.json"

    persist_ad_recycle_bin_activation_intent(
        build_intent(),
        storage_file=storage,
        now=NOW,
    )

    data = json.loads(
        storage.read_text(
            encoding="utf-8"
        )
    )

    assert len(data["records"]) == 1

    record = data["records"][0]

    assert record["status"] == "dormant"
    assert record["status"] != "pending"

    assert record["job_creation_authorized"] is False
    assert record["runtime_authorized"] is False
    assert record["production_authorized"] is False
    assert record["activation_authorized"] is False
    assert record["restore_authorized"] is False
    assert record["write_performed"] is False


def test_two_intents_are_stored_as_two_dormant_records(
    tmp_path: Path,
):
    storage = tmp_path / "activation-intents.json"

    first = persist_ad_recycle_bin_activation_intent(
        build_intent(),
        storage_file=storage,
        now=NOW,
    )

    second = persist_ad_recycle_bin_activation_intent(
        build_intent(),
        storage_file=storage,
        now=NOW,
    )

    assert first.intent_id != second.intent_id

    data = json.loads(
        storage.read_text(
            encoding="utf-8"
        )
    )

    assert len(data["records"]) == 2

    assert {
        record["status"]
        for record in data["records"]
    } == {
        "dormant"
    }


def test_storage_permissions_are_private(
    tmp_path: Path,
):
    storage = tmp_path / "activation-intents.json"

    persist_ad_recycle_bin_activation_intent(
        build_intent(),
        storage_file=storage,
        now=NOW,
    )

    mode = (
        storage.stat().st_mode
        & 0o777
    )

    assert mode == 0o600

    lock_mode = (
        storage.with_name(
            storage.name + ".lock"
        ).stat().st_mode
        & 0o777
    )

    assert lock_mode == 0o600


def test_symlink_storage_is_rejected(
    tmp_path: Path,
):
    real_storage = tmp_path / "real.json"

    real_storage.write_text(
        '{"records":[]}',
        encoding="utf-8",
    )

    symlink_storage = tmp_path / "link.json"

    symlink_storage.symlink_to(
        real_storage
    )

    with pytest.raises(
        AdRecycleBinActivationIntentPersistenceError,
        match="must not be a symlink",
    ):
        persist_ad_recycle_bin_activation_intent(
            build_intent(),
            storage_file=symlink_storage,
            now=NOW,
        )


def test_invalid_storage_is_rejected(
    tmp_path: Path,
):
    storage = tmp_path / "activation-intents.json"

    storage.write_text(
        "not-json",
        encoding="utf-8",
    )

    with pytest.raises(
        AdRecycleBinActivationIntentPersistenceError,
        match="Unable to read",
    ):
        persist_ad_recycle_bin_activation_intent(
            build_intent(),
            storage_file=storage,
            now=NOW,
        )


def test_registry_never_contains_pending_authorization(
    tmp_path: Path,
):
    storage = tmp_path / "activation-intents.json"

    for _ in range(3):
        persist_ad_recycle_bin_activation_intent(
            build_intent(),
            storage_file=storage,
            now=NOW,
        )

    raw = storage.read_text(
        encoding="utf-8"
    )

    assert '"status": "pending"' not in raw
    assert '"activation_authorized": true' not in raw
    assert '"runtime_authorized": true' not in raw
    assert '"production_authorized": true' not in raw
    assert '"restore_authorized": true' not in raw
    assert '"write_performed": true' not in raw
