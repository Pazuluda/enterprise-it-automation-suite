from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.storage import (
    load_json,
    save_json,
)
from app.services.ldap_attribute_candidates import (
    C2_FIRST_WAVE_REVIEWED_CANDIDATES,
)
from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED,
    LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED,
)
from app.services.ldap_hab_seniority_simulation_job import (
    LDAP_HAB_SIMULATION_JOB_PERSISTENCE_ENABLED,
    LDAPHabSimulationJobBadRequest,
    get_ldap_hab_simulation_audit_metadata,
    prepare_ldap_hab_simulation_job_envelope,
)


LDAP_HAB_SIMULATION_PERSISTENCE_CONTRACT_VERSION = (
    "c2.6b.3"
)

LDAP_HAB_SIMULATION_RUNTIME_JOBS_ENABLED = False
LDAP_HAB_SIMULATION_PRODUCTION_ENABLED = False
LDAP_HAB_SIMULATION_AD_EXECUTION_ENABLED = False


class LDAPHabSimulationPersistenceError(
    ValueError
):
    pass


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def create_ldap_hab_simulation_job_record(
    jobs_file: Path,
    payload: object,
    agent_mode: object,
) -> tuple[dict, dict]:
    if not isinstance(jobs_file, Path):
        raise LDAPHabSimulationPersistenceError(
            "jobs_file doit être un objet Path."
        )

    if not LDAP_HAB_SIMULATION_JOB_PERSISTENCE_ENABLED:
        raise LDAPHabSimulationPersistenceError(
            "La persistance HAB dédiée est désactivée."
        )

    try:
        envelope = (
            prepare_ldap_hab_simulation_job_envelope(
                payload,
                agent_mode,
            )
        )
    except LDAPHabSimulationJobBadRequest as exc:
        raise LDAPHabSimulationPersistenceError(
            str(exc)
        ) from exc

    if not envelope.persistence_authorized:
        raise RuntimeError(
            "L'enveloppe HAB n'autorise pas "
            "la persistance dédiée."
        )

    job_id = str(uuid4())

    job_payload = {
        "action": envelope.action,
        "object_identity": (
            envelope.object_identity
        ),
        "object_class": (
            envelope.object_class
        ),
        "changes": [
            dict(change)
            for change in envelope.changes
        ],
        "simulation_kind": (
            envelope.simulation_kind
        ),
        "hab_validation_contract_version": (
            envelope
            .hab_validation_contract_version
        ),
        "job_contract_version": (
            envelope.job_contract_version
        ),
        "persistence_contract_version": (
            LDAP_HAB_SIMULATION_PERSISTENCE_CONTRACT_VERSION
        ),
        "execution_policy": (
            envelope.execution_policy
        ),
        "simulation_job_authorized": True,
        "persistence_authorized": True,
        "production_authorized": False,
        "execution_authorized": False,
    }

    value = job_payload["changes"][0]["value"]

    if (
        job_payload["changes"][0]["operation"]
        == "set"
        and type(value) is not int
    ):
        raise RuntimeError(
            "La valeur HAB persistée doit rester entière."
        )

    job = {
        "id": job_id,
        "type": "ad_admin",
        "status": "pending",
        "created_at": _utc_now_iso(),
        "created_by": envelope.created_by,
        "action": envelope.action,
        "payload": job_payload,
        "claimed_at": None,
        "claimed_by": None,
        "completed_at": None,
        "success": None,
        "message": (
            "Simulation HAB en attente agent"
        ),
        "output": "",
        "result": None,
        "details": None,
    }

    jobs = load_json(
        jobs_file,
        [],
    )

    if not isinstance(jobs, list):
        raise LDAPHabSimulationPersistenceError(
            "Le stockage des jobs HAB "
            "doit contenir une liste JSON."
        )

    jobs.append(job)

    save_json(
        jobs_file,
        jobs,
    )

    audit_details = (
        get_ldap_hab_simulation_audit_metadata(
            envelope
        )
    )

    audit_details.update({
        "job_id": job_id,
        "persistence_contract_version": (
            LDAP_HAB_SIMULATION_PERSISTENCE_CONTRACT_VERSION
        ),
        "persistence_authorized": True,
        "production_authorized": False,
        "execution_authorized": False,
    })

    audit_event = {
        "action": (
            "ldap_hab_simulation_job_created"
        ),
        "request_id": job_id,
        "actor": envelope.created_by,
        "message": (
            "Job HAB de simulation créé"
        ),
        "details": audit_details,
    }

    return {
        "message": (
            "Job HAB de simulation créé"
        ),
        "job": job,
    }, audit_event


def assert_ldap_hab_simulation_persistence_invariants() -> None:
    if not LDAP_HAB_SIMULATION_JOB_PERSISTENCE_ENABLED:
        raise RuntimeError(
            "La persistance HAB dédiée "
            "doit être activée."
        )

    if LDAP_HAB_SIMULATION_RUNTIME_JOBS_ENABLED:
        raise RuntimeError(
            "La route runtime HAB doit rester "
            "désactivée en B2B."
        )

    if LDAP_HAB_SIMULATION_PRODUCTION_ENABLED:
        raise RuntimeError(
            "La Production HAB doit rester désactivée."
        )

    if LDAP_HAB_SIMULATION_AD_EXECUTION_ENABLED:
        raise RuntimeError(
            "L'écriture AD HAB doit rester désactivée."
        )

    if LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED:
        raise RuntimeError(
            "Les jobs LDAP génériques doivent "
            "rester désactivés."
        )

    if LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED:
        raise RuntimeError(
            "La Production LDAP générique "
            "doit rester désactivée."
        )

    if len(C2_FIRST_WAVE_REVIEWED_CANDIDATES) != 5:
        raise RuntimeError(
            "Le registre public LDAP a été modifié."
        )


assert_ldap_hab_simulation_persistence_invariants()
