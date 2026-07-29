from __future__ import annotations

from dataclasses import asdict, dataclass

from app.services.ldap_attribute_validation import (
    LDAP_ATTRIBUTE_VALIDATION_CONTRACT_VERSION,
    LDAP_ATTRIBUTE_VALIDATION_WRITES_ENABLED,
    validate_reviewed_ldap_attribute_request,
)


LDAP_ATTRIBUTE_UPDATE_CONTRACT_VERSION = "c2.4b.1"
LDAP_ATTRIBUTE_UPDATE_ACTION = "update_ldap_attributes"
LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED = False
LDAP_ATTRIBUTE_UPDATE_MAX_CHANGES = 5


class LDAPAttributeUpdateBadRequest(ValueError):
    pass


@dataclass(frozen=True)
class LDAPAttributeUpdateRequest:
    action: str
    object_identity: str
    object_class: str
    changes: tuple[dict, ...]
    validation_contract_version: str
    update_contract_version: str
    execution_authorized: bool = False

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["changes"] = [
            dict(change)
            for change in self.changes
        ]
        return payload


def _normalize_required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise LDAPAttributeUpdateBadRequest(
            f"{field_name} doit être une chaîne de caractères."
        )

    normalized = value.strip()

    if not normalized:
        raise LDAPAttributeUpdateBadRequest(
            f"{field_name} est obligatoire."
        )

    return normalized


def _normalize_object_dn(value: object) -> str:
    normalized = _normalize_required_text(
        value,
        "object_identity",
    )

    if "=" not in normalized or "," not in normalized:
        raise LDAPAttributeUpdateBadRequest(
            "object_identity doit être un DN LDAP."
        )

    return normalized


def normalize_ldap_attribute_update_request(
    payload: object,
) -> LDAPAttributeUpdateRequest:
    if not isinstance(payload, dict):
        raise LDAPAttributeUpdateBadRequest(
            "Le payload LDAP doit être un objet JSON."
        )

    action = _normalize_required_text(
        payload.get("action"),
        "action",
    )

    if action != LDAP_ATTRIBUTE_UPDATE_ACTION:
        raise LDAPAttributeUpdateBadRequest(
            "Action LDAP inconnue."
        )

    object_identity = _normalize_object_dn(
        payload.get("object_identity")
        or payload.get("object_dn")
        or payload.get("distinguished_name")
        or payload.get("dn")
    )

    object_class = _normalize_required_text(
        payload.get("object_class"),
        "object_class",
    ).casefold()

    raw_changes = payload.get("changes")

    if not isinstance(raw_changes, list):
        raise LDAPAttributeUpdateBadRequest(
            "changes doit être une liste JSON."
        )

    if not raw_changes:
        raise LDAPAttributeUpdateBadRequest(
            "Au moins un changement LDAP est obligatoire."
        )

    if len(raw_changes) > LDAP_ATTRIBUTE_UPDATE_MAX_CHANGES:
        raise LDAPAttributeUpdateBadRequest(
            "Un job LDAP est limité à cinq changements."
        )

    normalized_changes = []
    seen_attributes = set()

    for index, raw_change in enumerate(raw_changes):
        if not isinstance(raw_change, dict):
            raise LDAPAttributeUpdateBadRequest(
                f"Le changement LDAP {index + 1} doit être un objet JSON."
            )

        decision = validate_reviewed_ldap_attribute_request(
            attribute_name=raw_change.get("attribute_name"),
            object_class=object_class,
            operation=raw_change.get("operation"),
            value=raw_change.get("value"),
        )

        if not decision.valid:
            codes = ", ".join(
                error["code"]
                for error in decision.errors
            )

            raise LDAPAttributeUpdateBadRequest(
                f"Changement LDAP {index + 1} invalide : {codes}."
            )

        duplicate_key = decision.normalized_attribute_name.casefold()

        if duplicate_key in seen_attributes:
            raise LDAPAttributeUpdateBadRequest(
                "Un attribut LDAP ne peut apparaître qu’une fois par job."
            )

        seen_attributes.add(duplicate_key)

        normalized_changes.append({
            "attribute_name": decision.normalized_attribute_name,
            "operation": decision.normalized_operation,
            "value": decision.normalized_value,
            "value_type": decision.value_type,
            "write_authorized": False,
        })

    request = LDAPAttributeUpdateRequest(
        action=LDAP_ATTRIBUTE_UPDATE_ACTION,
        object_identity=object_identity,
        object_class=object_class,
        changes=tuple(normalized_changes),
        validation_contract_version=(
            LDAP_ATTRIBUTE_VALIDATION_CONTRACT_VERSION
        ),
        update_contract_version=(
            LDAP_ATTRIBUTE_UPDATE_CONTRACT_VERSION
        ),
        execution_authorized=False,
    )

    if request.execution_authorized:
        raise RuntimeError(
            "Le normaliseur LDAP ne doit pas autoriser l’exécution."
        )

    return request


def assert_ldap_attribute_update_invariants() -> None:
    if LDAP_ATTRIBUTE_UPDATE_JOBS_ENABLED:
        raise RuntimeError(
            "Les jobs LDAP doivent rester désactivés."
        )

    if LDAP_ATTRIBUTE_VALIDATION_WRITES_ENABLED:
        raise RuntimeError(
            "Le contrat de validation doit rester non autorisant."
        )

    sample = normalize_ldap_attribute_update_request({
        "action": "update_ldap_attributes",
        "object_identity": (
            "CN=Test,OU=Users,OU=EITAS,DC=API,DC=LOCAL"
        ),
        "object_class": "user",
        "changes": [{
            "attribute_name": "employeeType",
            "operation": "set",
            "value": "Interne",
        }],
    })

    if sample.execution_authorized:
        raise RuntimeError(
            "L’échantillon LDAP autorise une exécution."
        )


assert_ldap_attribute_update_invariants()
