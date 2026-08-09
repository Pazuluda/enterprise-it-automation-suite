from __future__ import annotations

from dataclasses import dataclass

from app.services.acl_delegation_simulation import (
    AclDelegationSimulationBadRequest,
    normalize_acl_delegation_simulation_request,
)


ACL_DELEGATION_SIMULATION_JOB_CONTRACT_VERSION = (
    "c8.3a2"
)

ACL_DELEGATION_SIMULATION_JOB_PREPARATION_ENABLED = True

# C8.3A2 remains dormant.
ACL_DELEGATION_SIMULATION_JOB_PERSISTENCE_ENABLED = True
ACL_DELEGATION_SIMULATION_RUNTIME_ENABLED = True
ACL_DELEGATION_SIMULATION_PRODUCTION_ENABLED = False
ACL_DELEGATION_SIMULATION_AD_WRITE_ENABLED = False


class AclDelegationSimulationJobBadRequest(
    ValueError
):
    pass


@dataclass(frozen=True)
class AclDelegationSimulationJobEnvelope:
    action: str
    mode: str
    payload: dict
    contract_version: str
    job_contract_version: str
    execution_policy: str
    job_preparation_authorized: bool
    job_persistence_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    ad_write_authorized: bool


def prepare_acl_delegation_simulation_job_envelope(
    payload: dict,
) -> AclDelegationSimulationJobEnvelope:
    if not (
        ACL_DELEGATION_SIMULATION_JOB_PREPARATION_ENABLED
    ):
        raise AclDelegationSimulationJobBadRequest(
            "La preparation du job ACL Simulation "
            "est desactivee"
        )

    try:
        request = (
            normalize_acl_delegation_simulation_request(
                payload
            )
        )
    except AclDelegationSimulationBadRequest as exc:
        raise AclDelegationSimulationJobBadRequest(
            str(exc)
        ) from exc

    normalized_payload = {
        "object_dn": request.object_dn,
        "principal_identity": (
            request.principal_identity
        ),
        "access_control_type": (
            request.access_control_type
        ),
        "rights": list(request.rights),
        "inheritance_type": (
            request.inheritance_type
        ),
        "object_type_guid": (
            request.object_type_guid
        ),
        "inherited_object_type_guid": (
            request.inherited_object_type_guid
        ),
        "mode": "Simulation",
        "execution_policy": (
            request.execution_policy
        ),
    }

    return AclDelegationSimulationJobEnvelope(
        action=request.action,
        mode="Simulation",
        payload=normalized_payload,
        contract_version=request.contract_version,
        job_contract_version=(
            ACL_DELEGATION_SIMULATION_JOB_CONTRACT_VERSION
        ),
        execution_policy=(
            request.execution_policy
        ),
        job_preparation_authorized=True,
        job_persistence_authorized=True,
        runtime_authorized=True,
        production_authorized=False,
        ad_write_authorized=False,
    )


def get_acl_delegation_simulation_audit_metadata(
    envelope: AclDelegationSimulationJobEnvelope,
) -> dict:
    return {
        "action": envelope.action,
        "mode": envelope.mode,
        "object_dn": envelope.payload["object_dn"],
        "principal_identity": (
            envelope.payload["principal_identity"]
        ),
        "access_control_type": (
            envelope.payload["access_control_type"]
        ),
        "rights": list(
            envelope.payload["rights"]
        ),
        "inheritance_type": (
            envelope.payload["inheritance_type"]
        ),
        "object_type_guid": (
            envelope.payload["object_type_guid"]
        ),
        "inherited_object_type_guid": (
            envelope.payload[
                "inherited_object_type_guid"
            ]
        ),
        "execution_policy": (
            envelope.execution_policy
        ),
        "job_contract_version": (
            envelope.job_contract_version
        ),
        "job_persistence_authorized": True,
        "runtime_authorized": True,
        "production_authorized": False,
        "ad_write_authorized": False,
    }


def assert_acl_delegation_simulation_job_invariants(
) -> None:
    if not (
        ACL_DELEGATION_SIMULATION_JOB_PREPARATION_ENABLED
    ):
        raise RuntimeError(
            "ACL job preparation must remain enabled"
        )

    if not ACL_DELEGATION_SIMULATION_JOB_PERSISTENCE_ENABLED:
        raise RuntimeError(
            "ACL Simulation persistence must remain enabled"
        )

    if not ACL_DELEGATION_SIMULATION_RUNTIME_ENABLED:
        raise RuntimeError(
            "ACL Simulation runtime must remain enabled"
        )

    if ACL_DELEGATION_SIMULATION_PRODUCTION_ENABLED:
        raise RuntimeError(
            "C8.3A2 Production must remain disabled"
        )

    if ACL_DELEGATION_SIMULATION_AD_WRITE_ENABLED:
        raise RuntimeError(
            "C8.3A2 AD writes must remain disabled"
        )

    sample = (
        prepare_acl_delegation_simulation_job_envelope({
            "action": "simulate_acl_delegation",
            "mode": "Simulation",
            "object_dn": (
                "OU=test,OU=Users,OU=EITAS,"
                "DC=API,DC=LOCAL"
            ),
            "principal_identity": (
                "API\\GG_IT_Admin"
            ),
            "access_control_type": "Allow",
            "rights": [
                "ReadProperty",
            ],
            "inheritance_type": "None",
        })
    )

    if not sample.job_persistence_authorized:
        raise RuntimeError(
            "ACL Simulation must authorize persistence"
        )

    if not sample.runtime_authorized:
        raise RuntimeError(
            "ACL Simulation must authorize runtime"
        )

    if sample.production_authorized:
        raise RuntimeError(
            "C8.3A2 must not authorize Production"
        )

    if sample.ad_write_authorized:
        raise RuntimeError(
            "C8.3A2 must not authorize AD writes"
        )


assert_acl_delegation_simulation_job_invariants()
