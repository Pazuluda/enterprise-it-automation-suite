from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

import pytest

from app.services.acl_delegation_prewrite_runtime import (
    AclDelegationPrewriteRuntimeConflict,
    AclDelegationPrewriteRuntimeError,
    claim_acl_delegation_prewrite_ticket_for_agent,
    complete_acl_delegation_prewrite_ticket,
)
from app.services.acl_delegation_prewrite_ticket import (
    create_acl_delegation_prewrite_ticket,
)
from app.services.acl_delegation_write_replay import (
    ACL_DELEGATION_WRITE_REPLAY_CONTRACT_VERSION,
    _atomic_write_registry,
    _safe_load_registry,
)


CLAIM_ID = (
    "f50fe166-f5ac-4ea8-"
    "95f6-60e6d206d337"
)

OBJECT_GUID = (
    "8838f739-c817-4b45-"
    "90b2-b597ce79312a"
)

PRINCIPAL_SID = (
    "S-1-5-21-1101651174-"
    "4260486456-3261528239-1118"
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
        "target_object_guid": OBJECT_GUID,

        "principal_dn": (
            "CN=GG_IT_Admin,OU=Groups,"
            "OU=EITAS,DC=API,DC=LOCAL"
        ),
        "principal_sid": PRINCIPAL_SID,

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

        "claim_id": CLAIM_ID,
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


def _ticket(
    tmp_path: Path,
    now: datetime,
):
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

    ticket = (
        create_acl_delegation_prewrite_ticket(
            replay_registry_file=path,
            claim_id=CLAIM_ID,
            now=now,
        )
    )

    return path, ticket


def _success_result():
    return {
        "action": "prevalidate_acl_delegation",
        "contract_version": "c8.4c1",
        "source_claim_contract_version": (
            "c8.4b4"
        ),
        "execution_policy": (
            "prewrite_validation_only"
        ),

        "prewrite_validated": True,
        "object_guid_revalidated": True,
        "dacl_revalidated": True,
        "principal_sid_revalidated": True,

        "target": {
            "object_guid": OBJECT_GUID,
        },

        "principal": {
            "sid": PRINCIPAL_SID,
        },

        "dacl": {
            "dacl_sddl_sha256": "d" * 64,
            "acl_fingerprint": "a" * 64,
        },

        "write_performed": False,

        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }


def test_c8_4c5c1_claim_is_atomic_and_validation_only(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path, ticket = _ticket(
        tmp_path,
        now,
    )

    execution = (
        claim_acl_delegation_prewrite_ticket_for_agent(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            agent_name="SRV-DC01",
            now=now + timedelta(seconds=1),
        )
    )

    assert execution.contract_version == "c8.4c5c"
    assert execution.state == "prewrite_processing"

    assert (
        execution.prewrite_validation_runtime_authorized
        is True
    )

    assert execution.production_authorized is False
    assert execution.ad_write_authorized is False

    assert (
        execution.payload["authorization"]
        == {
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        }
    )

    loaded = _safe_load_registry(
        path
    )

    record = loaded["records"][0]

    assert record["state"] == "prewrite_processing"

    assert (
        record[
            "prewrite_validation_runtime_authorized"
        ]
        is True
    )


def test_c8_4c5c1_second_claim_is_rejected(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path, ticket = _ticket(
        tmp_path,
        now,
    )

    claim_acl_delegation_prewrite_ticket_for_agent(
        replay_registry_file=path,
        ticket_id=ticket.ticket_id,
        agent_name="SRV-DC01",
        now=now,
    )

    with pytest.raises(
        AclDelegationPrewriteRuntimeConflict,
        match="non disponible",
    ):
        claim_acl_delegation_prewrite_ticket_for_agent(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            agent_name="SRV-DC01",
            now=now,
        )


def test_c8_4c5c1_expired_ticket_cannot_be_claimed(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path, ticket = _ticket(
        tmp_path,
        now,
    )

    with pytest.raises(
        AclDelegationPrewriteRuntimeConflict,
        match="expire",
    ):
        claim_acl_delegation_prewrite_ticket_for_agent(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            agent_name="SRV-DC01",
            now=(
                now
                + timedelta(seconds=121)
            ),
        )


def test_c8_4c5c1_success_result_closes_runtime(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path, ticket = _ticket(
        tmp_path,
        now,
    )

    execution = (
        claim_acl_delegation_prewrite_ticket_for_agent(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            agent_name="SRV-DC01",
            now=now,
        )
    )

    completed = (
        complete_acl_delegation_prewrite_ticket(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            execution_id=(
                execution.execution_id
            ),
            agent_name="SRV-DC01",
            success=True,
            result=_success_result(),
            now=now + timedelta(seconds=2),
        )
    )

    assert completed.state == "prewrite_validated"
    assert completed.success is True

    assert (
        completed.prewrite_validation_runtime_authorized
        is False
    )

    assert completed.production_authorized is False
    assert completed.ad_write_authorized is False

    loaded = _safe_load_registry(
        path
    )

    record = loaded["records"][0]

    assert record["state"] == "prewrite_validated"
    assert record["prewrite_success"] is True

    assert (
        record[
            "prewrite_result_summary"
        ]["write_performed"]
        is False
    )


def test_c8_4c5c1_mismatched_result_is_rejected(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path, ticket = _ticket(
        tmp_path,
        now,
    )

    execution = (
        claim_acl_delegation_prewrite_ticket_for_agent(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            agent_name="SRV-DC01",
            now=now,
        )
    )

    bad_result = _success_result()

    bad_result["target"] = {
        "object_guid": (
            "11111111-1111-1111-1111-"
            "111111111111"
        ),
    }

    with pytest.raises(
        AclDelegationPrewriteRuntimeError,
        match="objectGUID resultat ACL incoherent",
    ):
        complete_acl_delegation_prewrite_ticket(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            execution_id=(
                execution.execution_id
            ),
            agent_name="SRV-DC01",
            success=True,
            result=bad_result,
            now=now + timedelta(seconds=2),
        )


def test_c8_4c5c1_failure_closes_runtime(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path, ticket = _ticket(
        tmp_path,
        now,
    )

    execution = (
        claim_acl_delegation_prewrite_ticket_for_agent(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            agent_name="SRV-DC01",
            now=now,
        )
    )

    completed = (
        complete_acl_delegation_prewrite_ticket(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            execution_id=(
                execution.execution_id
            ),
            agent_name="SRV-DC01",
            success=False,
            message=(
                "DACL modifiee avant validation"
            ),
            now=now + timedelta(seconds=2),
        )
    )

    assert completed.state == "prewrite_failed"
    assert completed.success is False

    loaded = _safe_load_registry(
        path
    )

    record = loaded["records"][0]

    assert record["state"] == "prewrite_failed"
    assert record["prewrite_success"] is False

    assert (
        record[
            "prewrite_validation_runtime_authorized"
        ]
        is False
    )


def test_c8_4c5c1_wrong_agent_cannot_complete(
    tmp_path,
):
    now = datetime.now(
        timezone.utc
    )

    path, ticket = _ticket(
        tmp_path,
        now,
    )

    execution = (
        claim_acl_delegation_prewrite_ticket_for_agent(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            agent_name="SRV-DC01",
            now=now,
        )
    )

    with pytest.raises(
        AclDelegationPrewriteRuntimeConflict,
        match="Agent ACL pre-write different",
    ):
        complete_acl_delegation_prewrite_ticket(
            replay_registry_file=path,
            ticket_id=ticket.ticket_id,
            execution_id=(
                execution.execution_id
            ),
            agent_name="FAKE-AGENT",
            success=False,
            message="test",
            now=now,
        )


def test_c8_4c5c2_pending_returns_metadata_only(
    tmp_path,
):
    from app.services.acl_delegation_prewrite_runtime import (
        list_pending_acl_delegation_prewrite_tickets,
    )

    now = datetime.now(
        timezone.utc
    )

    path, ticket = _ticket(
        tmp_path,
        now,
    )

    pending = (
        list_pending_acl_delegation_prewrite_tickets(
            replay_registry_file=path,
            now=now,
        )
    )

    assert pending["count"] == 1

    item = pending["tickets"][0]

    assert item["ticket_id"] == ticket.ticket_id
    assert item["state"] == "prewrite_ticketed"

    assert "payload" not in item
    assert "target" not in item
    assert "principal" not in item
    assert "ace" not in item
    assert "dacl" not in item

    assert item["authorization"] == {
        "prewrite_validation_runtime_authorized": False,
        "job_creation_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "ad_write_authorized": False,
    }


def test_c8_4c5c2_expired_ticket_not_pending(
    tmp_path,
):
    from app.services.acl_delegation_prewrite_runtime import (
        list_pending_acl_delegation_prewrite_tickets,
    )

    now = datetime.now(
        timezone.utc
    )

    path, _ticket_value = _ticket(
        tmp_path,
        now,
    )

    pending = (
        list_pending_acl_delegation_prewrite_tickets(
            replay_registry_file=path,
            now=(
                now
                + timedelta(seconds=121)
            ),
        )
    )

    assert pending == {
        "count": 0,
        "tickets": [],
    }
