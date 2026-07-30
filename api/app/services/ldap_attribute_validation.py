from __future__ import annotations

from dataclasses import asdict, dataclass

from app.services.ldap_attribute_candidates import (
    LDAP_REVIEWED_CANDIDATES_AUTHORIZE_WRITES,
    get_reviewed_ldap_candidate,
)
from app.services.ldap_attribute_value_types import (
    normalize_ldap_typed_value,
)


LDAP_ATTRIBUTE_VALIDATION_CONTRACT_VERSION = "c2.5c.1"
LDAP_ATTRIBUTE_VALIDATION_WRITES_ENABLED = False
_ALLOWED_OPERATIONS = frozenset({"set", "clear"})


@dataclass(frozen=True)
class LDAPAttributeValidationDecision:
    valid: bool
    write_authorized: bool
    contract_version: str
    requested_attribute_name: object
    normalized_attribute_name: str | None
    normalized_object_class: str | None
    normalized_operation: str | None
    normalized_value: str | int | bool | None
    value_type: str | None
    minimum_length: int | None
    maximum_length: int | None
    minimum_value: int | None
    maximum_value: int | None
    clearable: bool | None
    required_roles: tuple[str, ...]
    errors: tuple[dict[str, str], ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["required_roles"] = list(self.required_roles)
        payload["errors"] = [dict(item) for item in self.errors]

        if self.minimum_value is None:
            payload.pop("minimum_value", None)

        if self.maximum_value is None:
            payload.pop("maximum_value", None)

        return payload


def _error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def validate_reviewed_ldap_attribute_request(
    *,
    attribute_name: object,
    object_class: object,
    operation: object,
    value: object = None,
) -> LDAPAttributeValidationDecision:
    errors: list[dict[str, str]] = []
    candidate = get_reviewed_ldap_candidate(attribute_name)
    normalized_class = (
        object_class.strip().casefold()
        if isinstance(object_class, str) and object_class.strip()
        else None
    )
    normalized_operation = (
        operation.strip().casefold()
        if isinstance(operation, str) and operation.strip()
        else None
    )
    normalized_value: str | int | bool | None = None

    if candidate is None:
        errors.append(_error("unknown_attribute", "Attribut LDAP non controle."))

    if normalized_class is None:
        errors.append(_error("invalid_object_class", "Classe d'objet obligatoire."))
    elif candidate and normalized_class not in candidate.allowed_object_classes:
        errors.append(
            _error(
                "unsupported_object_class",
                "Classe d'objet non autorisee pour cet attribut.",
            )
        )

    if normalized_operation not in _ALLOWED_OPERATIONS:
        errors.append(_error("invalid_operation", "Operation attendue: set ou clear."))
    elif normalized_operation == "set":
        if candidate:
            result = normalize_ldap_typed_value(
                value_type=candidate.value_type,
                value=value,
                minimum_length=candidate.minimum_length,
                maximum_length=candidate.maximum_length,
                minimum_value=getattr(
                    candidate,
                    "minimum_value",
                    None,
                ),
                maximum_value=getattr(
                    candidate,
                    "maximum_value",
                    None,
                ),
            )

            normalized_value = (
                result.normalized_value
            )

            errors.extend(
                result.errors
            )

        elif not isinstance(value, str):
            errors.append(
                _error(
                    "invalid_value_type",
                    "Valeur texte obligatoire.",
                )
            )
    elif normalized_operation == "clear":
        if candidate and not candidate.clearable:
            errors.append(
                _error("attribute_not_clearable", "Attribut non effacable.")
            )

        if value not in (None, ""):
            errors.append(
                _error(
                    "clear_value_must_be_empty",
                    "L'operation clear ne doit pas transporter de valeur.",
                )
            )

    decision = LDAPAttributeValidationDecision(
        valid=not errors,
        write_authorized=False,
        contract_version=LDAP_ATTRIBUTE_VALIDATION_CONTRACT_VERSION,
        requested_attribute_name=attribute_name,
        normalized_attribute_name=candidate.name if candidate else None,
        normalized_object_class=normalized_class,
        normalized_operation=normalized_operation,
        normalized_value=normalized_value,
        value_type=candidate.value_type if candidate else None,
        minimum_length=candidate.minimum_length if candidate else None,
        maximum_length=candidate.maximum_length if candidate else None,
        minimum_value=(
            getattr(candidate, "minimum_value", None)
            if candidate
            else None
        ),
        maximum_value=(
            getattr(candidate, "maximum_value", None)
            if candidate
            else None
        ),
        clearable=candidate.clearable if candidate else None,
        required_roles=(
            tuple(sorted(candidate.required_roles, key=str.casefold))
            if candidate
            else ()
        ),
        errors=tuple(errors),
    )

    if decision.write_authorized:
        raise RuntimeError("Le contrat LDAP ne doit jamais autoriser une ecriture.")

    return decision


def assert_ldap_attribute_validation_invariants() -> None:
    if LDAP_ATTRIBUTE_VALIDATION_WRITES_ENABLED:
        raise RuntimeError("Les ecritures du contrat LDAP doivent rester desactivees.")

    if LDAP_REVIEWED_CANDIDATES_AUTHORIZE_WRITES:
        raise RuntimeError("Le registre LDAP doit rester non autorisant.")

    sample = validate_reviewed_ldap_attribute_request(
        attribute_name="employeeType",
        object_class="user",
        operation="set",
        value="Interne",
    )

    if not sample.valid or sample.write_authorized:
        raise RuntimeError("Invariant du contrat LDAP invalide.")


assert_ldap_attribute_validation_invariants()
