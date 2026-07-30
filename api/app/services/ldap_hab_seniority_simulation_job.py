from __future__ import annotations

from dataclasses import asdict, dataclass

from app.services.ldap_attribute_update import (
    LDAP_ATTRIBUTE_UPDATE_ACTION,
    LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED,
    LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED,
)
from app.services.ldap_hab_seniority_simulation import (
    LDAP_HAB_SIMULATION_CONTRACT_VERSION,
    LDAP_HAB_SIMULATION_EXECUTION_POLICY,
    LDAPHabSimulationBadRequest,
    normalize_ldap_hab_simulation_request,
)


LDAP_HAB_SIMULATION_JOB_CONTRACT_VERSION = (
    "c2.6b.2"
)

LDAP_HAB_SIMULATION_JOB_PREPARATION_ENABLED = True
LDAP_HAB_SIMULATION_JOB_PERSISTENCE_ENABLED = True
LDAP_HAB_SIMULATION_AUDIT_VALUES_ENABLED = False

LDAP_HAB_SIMULATION_KIND = (
    "hab_seniority_index"
)


class LDAPHabSimulationJobBadRequest(
    ValueError
):
    pass


@dataclass(frozen=True)
class LDAPHabSimulationJobEnvelope:
    action: str
    object_identity: str
    object_class: str
    changes: tuple[dict, ...]
    created_by: str
    simulation_kind: str
    hab_validation_contract_version: str
    job_contract_version: str
    execution_policy: str
    simulation_job_authorized: bool
    persistence_authorized: bool
    production_authorized: bool
    execution_authorized: bool

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["changes"] = [
            dict(change)
            for change in self.changes
        ]
        return payload


def _normalize_created_by(
    value: object,
) -> str:
    if value is None:
        return "react-admin"

    if not isinstance(value, str):
        raise LDAPHabSimulationJobBadRequest(
            "created_by doit être une chaîne."
        )

    normalized = value.strip()

    if not normalized:
        return "react-admin"

    if len(normalized) > 128:
        raise LDAPHabSimulationJobBadRequest(
            "created_by dépasse 128 caractères."
        )

    if any(
        character in normalized
        for character in (
            "\x00",
            "\r",
            "\n",
        )
    ):
        raise LDAPHabSimulationJobBadRequest(
            "created_by contient un caractère interdit."
        )

    return normalized


def prepare_ldap_hab_simulation_job_envelope(
    payload: object,
    agent_mode: object,
) -> LDAPHabSimulationJobEnvelope:
    if not LDAP_HAB_SIMULATION_JOB_PREPARATION_ENABLED:
        raise LDAPHabSimulationJobBadRequest(
            "La préparation HAB est désactivée."
        )

    if not isinstance(payload, dict):
        raise LDAPHabSimulationJobBadRequest(
            "Le payload HAB doit être un objet JSON."
        )

    try:
        request = (
            normalize_ldap_hab_simulation_request(
                payload,
                agent_mode,
            )
        )
    except LDAPHabSimulationBadRequest as exc:
        raise LDAPHabSimulationJobBadRequest(
            str(exc)
        ) from exc

    created_by = _normalize_created_by(
        payload.get("created_by")
    )

    change = {
        "attribute_name": (
            request.attribute_name
        ),
        "operation": request.operation,
        "value": request.value,
        "value_type": request.value_type,
        "write_authorized": False,
    }

    if request.operation == "set":
        if type(change["value"]) is not int:
            raise RuntimeError(
                "La valeur HAB doit rester entière."
            )

    if request.operation == "clear":
        if change["value"] is not None:
            raise RuntimeError(
                "Une suppression HAB ne doit pas "
                "contenir de valeur."
            )

    envelope = LDAPHabSimulationJobEnvelope(
        action=LDAP_ATTRIBUTE_UPDATE_ACTION,
        object_identity=(
            request.object_identity
        ),
        object_class=request.object_class,
        changes=(change,),
        created_by=created_by,
        simulation_kind=(
            LDAP_HAB_SIMULATION_KIND
        ),
        hab_validation_contract_version=(
            LDAP_HAB_SIMULATION_CONTRACT_VERSION
        ),
        job_contract_version=(
            LDAP_HAB_SIMULATION_JOB_CONTRACT_VERSION
        ),
        execution_policy=(
            LDAP_HAB_SIMULATION_EXECUTION_POLICY
        ),
        simulation_job_authorized=True,
        persistence_authorized=True,
        production_authorized=False,
        execution_authorized=False,
    )

    if not envelope.persistence_authorized:
        raise RuntimeError(
            "B2B doit autoriser la "
            "persistance dédiée du job."
        )

    if envelope.production_authorized:
        raise RuntimeError(
            "La Production HAB doit rester "
            "désactivée."
        )

    if envelope.execution_authorized:
        raise RuntimeError(
            "Une écriture HAB est autorisée."
        )

    return envelope


def get_ldap_hab_simulation_audit_metadata(
    envelope: LDAPHabSimulationJobEnvelope,
) -> dict:
    return {
        "action": envelope.action,
        "object_identity": (
            envelope.object_identity
        ),
        "object_class": (
            envelope.object_class
        ),
        "attribute_names": [
            change["attribute_name"]
            for change in envelope.changes
        ],
        "change_count": len(
            envelope.changes
        ),
        "simulation_kind": (
            envelope.simulation_kind
        ),
        "execution_policy": (
            envelope.execution_policy
        ),
        "production_authorized": False,
        "values_included": False,
    }


def assert_ldap_hab_simulation_job_invariants() -> None:
    if not LDAP_HAB_SIMULATION_JOB_PREPARATION_ENABLED:
        raise RuntimeError(
            "La préparation HAB doit être testable."
        )

    if not LDAP_HAB_SIMULATION_JOB_PERSISTENCE_ENABLED:
        raise RuntimeError(
            "La persistance HAB dédiée doit être "
            "activée en B2B."
        )

    if LDAP_HAB_SIMULATION_AUDIT_VALUES_ENABLED:
        raise RuntimeError(
            "Les valeurs HAB ne doivent pas "
            "être placées dans l'audit."
        )

    if LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED:
        raise RuntimeError(
            "Les jobs LDAP globaux doivent "
            "rester désactivés."
        )

    if LDAP_ATTRIBUTE_UPDATE_PRODUCTION_ENABLED:
        raise RuntimeError(
            "La Production LDAP doit rester "
            "désactivée."
        )

    sample = (
        prepare_ldap_hab_simulation_job_envelope(
            {
                "action": (
                    "simulate_hab_seniority_index"
                ),
                "object_identity": (
                    "CN=Test,OU=Users,"
                    "DC=EXAMPLE,DC=LOCAL"
                ),
                "object_class": "user",
                "attribute_name": (
                    "msDS-HABSeniorityIndex"
                ),
                "operation": "set",
                "value": 100,
                "created_by": "test-suite",
            },
            "Simulation",
        )
    )

    value = sample.changes[0]["value"]

    if value != 100:
        raise RuntimeError(
            "La valeur HAB a été altérée."
        )

    if type(value) is not int:
        raise RuntimeError(
            "Le type entier HAB a été perdu."
        )

    metadata = (
        get_ldap_hab_simulation_audit_metadata(
            sample
        )
    )

    if metadata["values_included"]:
        raise RuntimeError(
            "L'audit HAB contient une valeur."
        )

    if "value" in metadata:
        raise RuntimeError(
            "Une valeur HAB brute apparaît "
            "dans les métadonnées."
        )


assert_ldap_hab_simulation_job_invariants()
