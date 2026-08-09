from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

import pytest

from app.services.acl_delegation_prewrite_ticket import (
    AclDelegationPrewriteTicketConflict,
    AclDelegationPrewriteTicketError,
    create_acl_delegation_prewrite_ticket,
)
from app.services.acl_delegation_write_replay import (
    ACL_DELEGATION_WRITE_REPLAY_CONTRACT_VERSION,
    _atomic_write_registry,
    _safe_load_registry,
)
from app.services.ad_admin import (
    ADAdminBadRequest,
    create_ad_admin_job,
)


def _claimed_record(
    now: datetime,
) -> dict:
    claimed_at = (
        now
        - timedelta(seconds=10)
    ).isoformat()

    return {
        "consumption_id": (
            "261e1585-83b8-4c17-"
            "b949-556423ad21c2"
        ),
        "evidence_digest": "e" * 64,
        "simulation_job_id": (
            "eeaceb8e-93e2-452a-"
            "9697-12daff04c9c9"
        ),
        "security_descriptor_job_id": (
            "f6b6d649-f641-4bf8-"
            "83ce-9e86b3db3bc9"
        ),
        "target_dn": (
            "OU=test,OU=Users,OU=EITAS,"
            "DC=API,DC=LOCAL"
        ),
        "target_object_guid": (
            "8838f739-c817-4b45-"
            "90b2-b597ce79312a"
        ),
        "principal_dn": (
            "CN=GG_IT_Admin,OU=Groups,"
            "OU=EITAS,DC=API,DC=LOCAL"
        ),
        "principal_sid": (
            "S-1-5-21-1101651174-"
            "4260486456-3261528239-1118"
        ),
        "access_control_type": "Allow",
        "rights": [
            "ReadProperty",
            "WriteProperty",
        ],
        "inheritance_type": "Descendents",
        "object_type_guid": None,
        "inherited_object_type_guid": None,
        "dacl_sddl_sha256": "d" * 64,
        "acl_fingerprint": "a" * 64,

        "consumed_at": claimed_at,
        "state": "claimed_dormant",

        "claim_id": (
            "f50fe166-f5ac-4ea8-"
            "95f6-60e6d206d337"
        ),
        "contract_version_claim": "c8.4b4",
        "envelope_digest": "b" * 64,
        "server_nonce": "server-nonce",

        "actor_subject": "subject-1",
        "actor_username": "ultraadmin",
        "actor_roles": ["UltraAdmin"],
        "actor_issuer": "https://identity.test",
        "actor_azp": "eitas-portal",

        "issued_at": (
            now
            - timedelta(seconds=20)
        ).isoformat(),
        "expires_at": (
            now
            + timedelta(minutes=5)
        ).isoformat(),
        "claimed_at": claimed_at,

        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }


def _registry_path(
    tmp_path: Path,
    now: datetime,
) -> Path:
    path = tmp_path / (
        "acl-delegation-write-replay.json"
    )

    _atomic_write_registry(
        path,
        {
            "contract_version": (
                ACL_DELEGATION_WRITE_REPLAY_CONTRACT_VERSION
            ),
            "records": [
                _claimed_record(now)
            ],
        },
    )

    return path


def test_c8_4c5a_creates_atomic_dormant_ticket(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path = _registry_path(
        tmp_path,
        now,
    )

    ticket = (
        create_acl_delegation_prewrite_ticket(
            replay_registry_file=path,
            claim_id=(
                "f50fe166-f5ac-4ea8-"
                "95f6-60e6d206d337"
            ),
            now=now,
        )
    )

    assert ticket.contract_version == "c8.4c5a"
    assert ticket.state == "prewrite_ticketed"

    assert (
        ticket.prewrite_validation_runtime_authorized
        is False
    )

    assert ticket.job_creation_authorized is False
    assert ticket.production_authorized is False
    assert ticket.ad_write_authorized is False

    registry = _safe_load_registry(
        path
    )

    record = registry["records"][0]

    assert record["state"] == "prewrite_ticketed"

    assert (
        record[
            "prewrite_validation_runtime_authorized"
        ]
        is False
    )


def test_c8_4c5a_payload_is_server_derived(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path = _registry_path(
        tmp_path,
        now,
    )

    ticket = (
        create_acl_delegation_prewrite_ticket(
            replay_registry_file=path,
            claim_id=(
                "f50fe166-f5ac-4ea8-"
                "95f6-60e6d206d337"
            ),
            now=now,
        )
    )

    payload = ticket.payload

    assert payload["contract_version"] == "c8.4b4"
    assert payload["state"] == "claimed_dormant"

    assert payload["target"]["object_guid"] == (
        "8838f739-c817-4b45-"
        "90b2-b597ce79312a"
    )

    assert payload["principal"]["sid"] == (
        "S-1-5-21-1101651174-"
        "4260486456-3261528239-1118"
    )

    assert payload["ace"]["rights"] == [
        "ReadProperty",
        "WriteProperty",
    ]

    assert payload["authorization"] == {
        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }


def test_c8_4c5a_is_idempotent_for_same_claim(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path = _registry_path(
        tmp_path,
        now,
    )

    first = create_acl_delegation_prewrite_ticket(
        replay_registry_file=path,
        claim_id=(
            "f50fe166-f5ac-4ea8-"
            "95f6-60e6d206d337"
        ),
        now=now,
    )

    second = create_acl_delegation_prewrite_ticket(
        replay_registry_file=path,
        claim_id=(
            "f50fe166-f5ac-4ea8-"
            "95f6-60e6d206d337"
        ),
        now=now + timedelta(seconds=1),
    )

    assert second.ticket_id == first.ticket_id
    assert second.payload_digest == first.payload_digest

    registry = _safe_load_registry(
        path
    )

    assert len(registry["records"]) == 1


def test_c8_4c5a_rejects_unknown_claim(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path = _registry_path(
        tmp_path,
        now,
    )

    with pytest.raises(
        AclDelegationPrewriteTicketError,
        match="Claim ACL introuvable",
    ):
        create_acl_delegation_prewrite_ticket(
            replay_registry_file=path,
            claim_id="unknown",
            now=now,
        )


def test_c8_4c5a_rejects_stale_claim(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path = _registry_path(
        tmp_path,
        now,
    )

    registry = _safe_load_registry(
        path
    )

    old = (
        now
        - timedelta(minutes=10)
    ).isoformat()

    registry["records"][0][
        "claimed_at"
    ] = old

    registry["records"][0][
        "consumed_at"
    ] = old

    _atomic_write_registry(
        path,
        registry,
    )

    with pytest.raises(
        AclDelegationPrewriteTicketError,
        match="Claim ACL trop ancien",
    ):
        create_acl_delegation_prewrite_ticket(
            replay_registry_file=path,
            claim_id=(
                "f50fe166-f5ac-4ea8-"
                "95f6-60e6d206d337"
            ),
            now=now,
        )


def test_c8_4c5a_generic_ad_admin_route_cannot_create_action(
    tmp_path,
):
    jobs = tmp_path / "ad-admin-jobs.json"

    with pytest.raises(
        ADAdminBadRequest,
        match="Action AD Admin inconnue",
    ):
        create_ad_admin_job(
            jobs,
            {
                "action": (
                    "prevalidate_acl_delegation"
                ),
                "claim_id": "attacker-controlled",
            },
        )

    assert not jobs.exists()


def test_c8_4c5a_registry_reloads_after_ticket(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path = _registry_path(
        tmp_path,
        now,
    )

    ticket = create_acl_delegation_prewrite_ticket(
        replay_registry_file=path,
        claim_id=(
            "f50fe166-f5ac-4ea8-"
            "95f6-60e6d206d337"
        ),
        now=now,
    )

    loaded = _safe_load_registry(
        path
    )

    record = loaded["records"][0]

    assert (
        record["prewrite_ticket_id"]
        == ticket.ticket_id
    )

    assert (
        record["prewrite_ticket_payload_digest"]
        == ticket.payload_digest
    )


def test_c8_4c5a_source_remains_non_authorizing():
    source = Path(
        "api/app/services/"
        "acl_delegation_prewrite_ticket.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "ACL_DELEGATION_PREWRITE_RUNTIME_ENABLED = False"
        in source
    )

    assert (
        "ACL_DELEGATION_PREWRITE_AD_WRITE_AUTHORIZED = False"
        in source
    )

    for forbidden in (
        "Set-Acl",
        "SetAccessRule",
        "AddAccessRule",
        "ActiveDirectoryAccessRule",
    ):
        assert forbidden not in source



def test_c8_4c5a_expired_existing_ticket_is_not_reactivated(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path = _registry_path(
        tmp_path,
        now,
    )

    first = create_acl_delegation_prewrite_ticket(
        replay_registry_file=path,
        claim_id=(
            "f50fe166-f5ac-4ea8-"
            "95f6-60e6d206d337"
        ),
        now=now,
    )

    with pytest.raises(
        AclDelegationPrewriteTicketConflict,
        match="Ticket ACL pre-write expire",
    ):
        create_acl_delegation_prewrite_ticket(
            replay_registry_file=path,
            claim_id=first.claim_id,
            now=(
                now
                + timedelta(
                    seconds=121
                )
            ),
        )

    loaded = _safe_load_registry(
        path
    )

    assert (
        loaded["records"][0][
            "prewrite_ticket_id"
        ]
        == first.ticket_id
    )
