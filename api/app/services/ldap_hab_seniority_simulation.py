from __future__ import annotations

from dataclasses import asdict, dataclass

from app.services.ldap_attribute_value_types import (
    normalize_ldap_typed_value,
)
from app.services.ldap_hab_seniority_candidate import (
    LDAP_HAB_SENIORITY_DORMANT_CANDIDATE,
)
from app.services.ldap_hab_seniority_policy import (
    LDAP_HAB_SENIORITY_POLICY,
)


LDAP_HAB_SIMULATION_CONTRACT_VERSION = "c2.6b.1"

LDAP_HAB_SIMULATION_ACTION = (
    "simulate_hab_seniority_index"
)

LDAP_HAB_SIMULATION_EXECUTION_POLICY = (
    "simulation_only"
)

LDAP_HAB_SIMULATION_VALIDATION_ENABLED = True
LDAP_HAB_SIMULATION_JOB_CREATION_ENABLED = False
LDAP_HAB_SIMULATION_PRODUCTION_ENABLED = False

_ALLOWED_OPERATIONS = frozenset({
    "set",
    "clear",
})


class LDAPHabSimulationBadRequest(ValueError):
    pass


@dataclass(frozen=True)
class LDAPHabSimulationRequest:
    action: str
    object_identity: str
    object_class: str
    attribute_name: str
    operation: str
    value: int | None
    value_type: str
    minimum_value: int
    maximum_value: int
    validation_contract_version: str
    execution_policy: str
    simulation_validation_authorized: bool
    simulation_job_authorized: bool
    production_authorized: bool
    execution_authorized: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _required_text(
    value: object,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise LDAPHabSimulationBadRequest(
            f"{field_name} doit être une chaîne."
        )

    normalized = value.strip()

    if not normalized:
        raise LDAPHabSimulationBadRequest(
            f"{field_name} est obligatoire."
        )

    return normalized


def _normalize_object_dn(value: object) -> str:
    normalized = _required_text(
        value,
        "object_identity",
    )

    if "=" not in normalized or "," not in normalized:
        raise LDAPHabSimulationBadRequest(
            "object_identity doit être un DN LDAP."
        )

    return normalized


def normalize_ldap_hab_simulation_request(
    payload: object,
    agent_mode: object,
) -> LDAPHabSimulationRequest:
    if not LDAP_HAB_SIMULATION_VALIDATION_ENABLED:
        raise LDAPHabSimulationBadRequest(
            "La validation HAB Simulation est désactivée."
        )

    normalized_mode = _required_text(
        agent_mode,
        "agent_mode",
    ).casefold()

    if normalized_mode != "simulation":
        raise LDAPHabSimulationBadRequest(
            "HAB Seniority est disponible uniquement "
            "en mode Simulation."
        )

    if not isinstance(payload, dict):
        raise LDAPHabSimulationBadRequest(
            "Le payload HAB doit être un objet JSON."
        )

    action = _required_text(
        payload.get("action"),
        "action",
    )

    if action != LDAP_HAB_SIMULATION_ACTION:
        raise LDAPHabSimulationBadRequest(
            "Action HAB inconnue."
        )

    object_identity = _normalize_object_dn(
        payload.get("object_identity")
        or payload.get("object_dn")
        or payload.get("distinguished_name")
        or payload.get("dn")
    )

    object_class = _required_text(
        payload.get("object_class"),
        "object_class",
    ).casefold()

    candidate = (
        LDAP_HAB_SENIORITY_DORMANT_CANDIDATE
    )

    if (
        object_class
        not in candidate.allowed_object_classes
    ):
        raise LDAPHabSimulationBadRequest(
            "HAB Seniority est limité aux utilisateurs."
        )

    attribute_name = _required_text(
        payload.get("attribute_name"),
        "attribute_name",
    )

    if (
        attribute_name.casefold()
        != candidate.name.casefold()
    ):
        raise LDAPHabSimulationBadRequest(
            "Attribut HAB inattendu."
        )

    operation = _required_text(
        payload.get("operation"),
        "operation",
    ).casefold()

    if operation not in _ALLOWED_OPERATIONS:
        raise LDAPHabSimulationBadRequest(
            "Opération HAB attendue : set ou clear."
        )

    normalized_value: int | None = None

    if operation == "set":
        result = normalize_ldap_typed_value(
            value_type=candidate.value_type,
            value=payload.get("value"),
            minimum_length=0,
            maximum_length=0,
            minimum_value=candidate.minimum_value,
            maximum_value=candidate.maximum_value,
        )

        if not result.valid:
            codes = ", ".join(
                error["code"]
                for error in result.errors
            )

            raise LDAPHabSimulationBadRequest(
                f"Valeur HAB invalide : {codes}."
            )

        if type(result.normalized_value) is not int:
            raise RuntimeError(
                "La valeur HAB normalisée doit être entière."
            )

        normalized_value = (
            result.normalized_value
        )

    else:
        if not candidate.clearable:
            raise LDAPHabSimulationBadRequest(
                "L'attribut HAB ne peut pas être effacé."
            )

        if payload.get("value") not in (
            None,
            "",
        ):
            raise LDAPHabSimulationBadRequest(
                "L'opération clear ne doit pas "
                "transporter de valeur."
            )

    request = LDAPHabSimulationRequest(
        action=LDAP_HAB_SIMULATION_ACTION,
        object_identity=object_identity,
        object_class=object_class,
        attribute_name=candidate.name,
        operation=operation,
        value=normalized_value,
        value_type=candidate.value_type,
        minimum_value=candidate.minimum_value,
        maximum_value=candidate.maximum_value,
        validation_contract_version=(
            LDAP_HAB_SIMULATION_CONTRACT_VERSION
        ),
        execution_policy=(
            LDAP_HAB_SIMULATION_EXECUTION_POLICY
        ),
        simulation_validation_authorized=True,
        simulation_job_authorized=False,
        production_authorized=False,
        execution_authorized=False,
    )

    if request.simulation_job_authorized:
        raise RuntimeError(
            "Le contrat B1B ne doit pas créer de job."
        )

    if request.production_authorized:
        raise RuntimeError(
            "Le contrat HAB ne doit pas autoriser "
            "la Production."
        )

    if request.execution_authorized:
        raise RuntimeError(
            "Le contrat HAB ne doit pas autoriser "
            "une écriture."
        )

    return request


def assert_ldap_hab_simulation_invariants() -> None:
    if not LDAP_HAB_SIMULATION_VALIDATION_ENABLED:
        raise RuntimeError(
            "Le contrat HAB isolé doit être testable."
        )

    if LDAP_HAB_SIMULATION_JOB_CREATION_ENABLED:
        raise RuntimeError(
            "La création de job HAB doit rester "
            "désactivée en B1B."
        )

    if LDAP_HAB_SIMULATION_PRODUCTION_ENABLED:
        raise RuntimeError(
            "La Production HAB doit rester désactivée."
        )

    if LDAP_HAB_SENIORITY_POLICY.public_exposure:
        raise RuntimeError(
            "HAB ne doit pas être exposé publiquement."
        )

    if LDAP_HAB_SENIORITY_POLICY.write_authorized:
        raise RuntimeError(
            "HAB ne doit pas autoriser d'écriture."
        )

    sample = normalize_ldap_hab_simulation_request(
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
        },
        "Simulation",
    )

    if sample.value != 100:
        raise RuntimeError(
            "La valeur entière HAB n'est pas préservée."
        )

    if type(sample.value) is not int:
        raise RuntimeError(
            "Le type entier HAB n'est pas préservé."
        )


assert_ldap_hab_simulation_invariants()
