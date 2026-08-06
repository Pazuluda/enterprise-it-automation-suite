from __future__ import annotations

import re
from fastapi import HTTPException

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.storage import load_json, save_json
from app.services.ldap_attribute_update import (
    prepare_ldap_attribute_update_simulation_payload,
)


class ADAdminError(Exception):
    pass


class ADAdminBadRequest(ADAdminError):
    pass


class ADAdminNotFound(ADAdminError):
    pass


class ADAdminConflict(ADAdminError):
    pass


ALLOWED_ACTIONS = {
    "create_ou",
    "create_group",
    "create_user",
    "create_computer",
    "add_group_member",
    "remove_group_member",
    "move_object",
    "rename_object",
    "delete_object",
    "update_object_properties",
    "enable_account",
    "disable_account",
    "unlock_account",
    "reset_password",
}


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def normalize_limit(value, default: int = 100) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = default

    return max(1, min(limit, 1000))


def clean_string(value) -> str:
    return str(value or "").strip()


# BLOC299A - Redaction des secrets des jobs AD Admin

SENSITIVE_JOB_KEYS = frozenset({
    "temporary_password",
    "password",
    "new_password",
})


def collect_sensitive_values(value) -> set[str]:
    values = set()

    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).strip().lower()

            if normalized_key in SENSITIVE_JOB_KEYS:
                secret = clean_string(child)

                if secret:
                    values.add(secret)

            values.update(
                collect_sensitive_values(child)
            )

    elif isinstance(value, list):
        for child in value:
            values.update(
                collect_sensitive_values(child)
            )

    return values


def sanitize_job_value(
    value,
    sensitive_values: set[str] | None = None,
):
    if sensitive_values is None:
        sensitive_values = collect_sensitive_values(value)

    if isinstance(value, dict):
        sanitized = {}

        for key, child in value.items():
            normalized_key = str(key).strip().lower()

            if normalized_key in SENSITIVE_JOB_KEYS:
                continue

            sanitized[key] = sanitize_job_value(
                child,
                sensitive_values,
            )

        return sanitized

    if isinstance(value, list):
        return [
            sanitize_job_value(
                child,
                sensitive_values,
            )
            for child in value
        ]

    if isinstance(value, str):
        sanitized = value

        for secret in sensitive_values:
            if secret:
                sanitized = sanitized.replace(
                    secret,
                    "[REDACTED]",
                )

        return sanitized

    return value


def remove_sensitive_values_in_place(value) -> int:
    removed = 0

    if isinstance(value, dict):
        for key in list(value):
            normalized_key = str(key).strip().lower()

            if normalized_key in SENSITIVE_JOB_KEYS:
                del value[key]
                removed += 1
                continue

            removed += remove_sensitive_values_in_place(
                value[key]
            )

    elif isinstance(value, list):
        for child in value:
            removed += remove_sensitive_values_in_place(
                child
            )

    return removed


def normalize_bool(value, default: bool = False) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    normalized = clean_string(value).lower()

    if normalized in {
        "1",
        "true",
        "yes",
        "oui",
        "enabled",
        "active",
    }:
        return True

    if normalized in {
        "0",
        "false",
        "no",
        "non",
        "disabled",
        "inactive",
    }:
        return False

    return default


def get_dns_domain_from_dn(value: str) -> str:
    parts = [
        part.strip()
        for part in clean_string(value).split(",")
        if part.strip().upper().startswith("DC=")
    ]

    return ".".join(
        part.split("=", 1)[1]
        for part in parts
        if "=" in part
    )


def validate_user_principal_name(value: str) -> str:
    clean = clean_string(value)

    if not clean:
        raise ADAdminBadRequest(
            "user_principal_name est obligatoire"
        )

    if len(clean) > 1024:
        raise ADAdminBadRequest(
            "user_principal_name est limité à 1024 caractères"
        )

    if not re.fullmatch(
        r"[A-Za-z0-9._-]+@[A-Za-z0-9.-]+",
        clean,
    ):
        raise ADAdminBadRequest(
            "user_principal_name doit être un UPN valide"
        )

    return clean


CREATE_USER_PROFILE_FIELD_SPECS = {
    "title": (
        ("title", "Title"),
        128,
    ),
    "department": (
        ("department", "Department"),
        64,
    ),
    "division": (
        ("division", "Division"),
        256,
    ),
    "company": (
        ("company", "Company"),
        64,
    ),
    "manager": (
        ("manager", "Manager"),
        2048,
    ),
    "office": (
        (
            "office",
            "Office",
            "physical_delivery_office_name",
            "physicalDeliveryOfficeName",
        ),
        128,
    ),
    "telephone_number": (
        (
            "telephone_number",
            "telephoneNumber",
            "office_phone",
            "officePhone",
            "OfficePhone",
        ),
        64,
    ),
    "mobile": (
        (
            "mobile",
            "Mobile",
            "mobile_phone",
            "mobilePhone",
            "MobilePhone",
        ),
        64,
    ),
    "street_address": (
        (
            "street_address",
            "streetAddress",
            "StreetAddress",
        ),
        1024,
    ),
    "postal_code": (
        (
            "postal_code",
            "postalCode",
            "PostalCode",
        ),
        40,
    ),
    "city": (
        ("city", "City", "l"),
        128,
    ),
    "state": (
        ("state", "State", "st"),
        128,
    ),
}


def normalize_create_user_profile(
    payload: dict,
) -> dict[str, str]:
    normalized = {}

    for (
        target_name,
        (
            aliases,
            maximum_length,
        ),
    ) in CREATE_USER_PROFILE_FIELD_SPECS.items():
        raw_value = None

        for alias in aliases:
            if (
                alias in payload
                and payload.get(alias) is not None
            ):
                raw_value = payload.get(alias)
                break

        if raw_value is None:
            continue

        if not isinstance(raw_value, str):
            raise ADAdminBadRequest(
                f"{target_name} doit être une chaîne"
            )

        value = raw_value.strip()

        if not value:
            continue

        if any(
            ord(character) < 32
            for character in value
        ):
            raise ADAdminBadRequest(
                f"{target_name} contient un caractère "
                "de contrôle interdit"
            )

        if len(value) > maximum_length:
            raise ADAdminBadRequest(
                f"{target_name} est limité à "
                f"{maximum_length} caractères"
            )

        if target_name == "manager":
            value = validate_dn(
                value,
                "manager",
            )

        normalized[target_name] = value

    return normalized


def validate_dn(value: str, field_name: str) -> str:
    clean = clean_string(value)

    if not clean:
        raise ADAdminBadRequest(f"{field_name} est obligatoire")

    if "=" not in clean or "," not in clean:
        raise ADAdminBadRequest(f"{field_name} doit être un DN LDAP valide")

    return clean


def validate_name(value: str, field_name: str) -> str:
    clean = clean_string(value)

    if not clean:
        raise ADAdminBadRequest(f"{field_name} est obligatoire")

    forbidden = [",", "+", "=", "<", ">", "#", ";", '"', "\\"]

    if any(char in clean for char in forbidden):
        raise ADAdminBadRequest(f"{field_name} contient un caractère interdit")

    return clean


# BLOC300A - Validation sécurisée des ordinateurs AD


def validate_computer_name(value) -> str:
    clean = clean_string(value).upper()

    if not clean:
        raise ADAdminBadRequest(
            "Le nom ordinateur est obligatoire"
        )

    if not re.fullmatch(
        r"[A-Z0-9-]{1,15}",
        clean,
    ):
        raise ADAdminBadRequest(
            "Le nom ordinateur doit contenir 1 à 15 caractères : "
            "lettres A-Z, chiffres et tirets"
        )

    if clean.startswith("-") or clean.endswith("-"):
        raise ADAdminBadRequest(
            "Le nom ordinateur ne peut pas commencer ou finir par un tiret"
        )

    if clean.isdigit():
        raise ADAdminBadRequest(
            "Le nom ordinateur ne peut pas contenir uniquement des chiffres"
        )

    return clean


def validate_computer_target_ou(value) -> str:
    clean = validate_dn(
        value,
        "target_ou_dn",
    )

    parts = [
        part.strip().upper()
        for part in clean.split(",")
        if part.strip()
    ]

    if not parts or not parts[0].startswith("OU="):
        raise ADAdminBadRequest(
            "La destination ordinateur doit être une OU"
        )

    is_computer_scope = any(
        parts[index] == "OU=COMPUTERS"
        and parts[index + 1] == "OU=EITAS"
        for index in range(len(parts) - 1)
    )

    if not is_computer_scope:
        raise ADAdminBadRequest(
            "La destination ordinateur doit appartenir à "
            "OU=Computers,OU=EITAS"
        )

    return clean


def normalize_update_object_properties(
    raw_properties,
) -> dict:
    if not isinstance(raw_properties, dict):
        raise HTTPException(
            status_code=400,
            detail="properties doit être un objet JSON",
        )

    allowed_properties = {
        "description",
        "location",
        "operatingSystem",
        "operating_system",
        "operatingSystemVersion",
        "operating_system_version",
        "operatingSystemServicePack",
        "operating_system_service_pack",
        "displayName",
        "display_name",
        "givenName",
        "personalTitle",
        "personal_title",
        "initials",
        "preferredLanguage",
        "preferred_language",
        "sn",
        "mail",
        "wWWHomePage",
        "info",
        "notes",
        "remarks",
        "user_notes",
        "uidNumber",
        "uid_number",
        "gidNumber",
        "gid_number",
        "unixHomeDirectory",
        "unix_home_directory",
        "loginShell",
        "login_shell",
        "gecos",
        "samAccountName",
        "sam_account_name",
        "userPrincipalName",
        "user_principal_name",
        "upn",
        "accountExpires",
        "account_expires",
        "userWorkstations",
        "user_workstations",
        "logonHours",
        "logon_hours",
        "passwordNeverExpires",
        "password_never_expires",
        "cannotChangePassword",
        "cannot_change_password",
        "smartcardLogonRequired",
        "smartcard_logon_required",
        "accountNotDelegated",
        "account_not_delegated",
        "msTSAllowLogon",
        "ms_ts_allow_logon",
        "msTSProfilePath",
        "ms_ts_profile_path",
        "msTSHomeDirectory",
        "ms_ts_home_directory",
        "msTSHomeDrive",
        "ms_ts_home_drive",
        "msTSInitialProgram",
        "ms_ts_initial_program",
        "msTSWorkDirectory",
        "ms_ts_work_directory",
        "title",
        "department",
        "division",
        "company",
        "telephoneNumber",
        "telephone_number",
        "homePhone",
        "facsimileTelephoneNumber",
        "pager",
        "ipPhone",
        "mobile",
        "mobile_phone",
        "office",
        "physicalDeliveryOfficeName",
        "employeeID",
        "employee_id",
        "employeeNumber",
        "employee_number",
        "manager",
        "manager_dn",
        "profilePath",
        "profile_path",
        "scriptPath",
        "script_path",
        "homeDirectory",
        "home_directory",
        "homeDrive",
        "home_drive",
        "streetAddress",
        "street_address",
        "postalCode",
        "postal_code",
        "postOfficeBox",
        "post_office_box",
        "l",
        "city",
        "st",
        "state",
        "c",
        "country_alpha2",
        "co",
        "country",
        "countryCode",
        "country_numeric_code",
        "groupScope",
        "group_scope",
        "groupCategory",
        "group_category",
        "managedBy",
        "managed_by",
        "protectedFromAccidentalDeletion",
        "protected_from_accidental_deletion",
    }

    property_aliases = {
        "display_name": "displayName",
        "personal_title": "personalTitle",
        "preferred_language": "preferredLanguage",
        "notes": "info",
        "remarks": "info",
        "user_notes": "info",
        "uid_number": "uidNumber",
        "gid_number": "gidNumber",
        "unix_home_directory": "unixHomeDirectory",
        "login_shell": "loginShell",
        "operating_system": "operatingSystem",
        "operating_system_version":
            "operatingSystemVersion",
        "operating_system_service_pack":
            "operatingSystemServicePack",
        "telephone_number": "telephoneNumber",
        "mobile_phone": "mobile",
        "office": "physicalDeliveryOfficeName",
        "employee_id": "employeeID",
        "employee_number": "employeeNumber",
        "manager_dn": "manager",
        "profile_path": "profilePath",
        "script_path": "scriptPath",
        "home_directory": "homeDirectory",
        "home_drive": "homeDrive",
        "street_address": "streetAddress",
        "postal_code": "postalCode",
        "post_office_box": "postOfficeBox",
        "city": "l",
        "state": "st",
        "country_alpha2": "c",
        "country": "co",
        "country_numeric_code": "countryCode",
        "group_scope": "groupScope",
        "group_category": "groupCategory",
        "managed_by": "managedBy",
        "sam_account_name": "samAccountName",
        "user_principal_name": "userPrincipalName",
        "upn": "userPrincipalName",
        "account_expires": "accountExpires",
        "user_workstations": "userWorkstations",
        "logon_hours": "logonHours",
        "password_never_expires":
            "passwordNeverExpires",
        "cannot_change_password":
            "cannotChangePassword",
        "smartcard_logon_required":
            "smartcardLogonRequired",
        "account_not_delegated":
            "accountNotDelegated",
        "ms_ts_allow_logon":
            "msTSAllowLogon",
        "ms_ts_profile_path":
            "msTSProfilePath",
        "ms_ts_home_directory":
            "msTSHomeDirectory",
        "ms_ts_home_drive":
            "msTSHomeDrive",
        "ms_ts_initial_program":
            "msTSInitialProgram",
        "ms_ts_work_directory":
            "msTSWorkDirectory",
        "protected_from_accidental_deletion":
            "protectedFromAccidentalDeletion",
    }

    property_max_lengths = {
        "personalTitle": 64,
        "initials": 6,
        "preferredLanguage": 32767,
        "wWWHomePage": 2048,
        "telephoneNumber": 64,
        "homePhone": 64,
        "facsimileTelephoneNumber": 64,
        "pager": 64,
        "mobile": 64,
        "ipPhone": 64,
        "info": 1024,
        "unixHomeDirectory": 2048,
        "loginShell": 1024,
        "gecos": 10240,
        "postOfficeBox": 40,
        "co": 128,
    }

    normalized_properties = {}

    read_only_properties = {
        "directReports",
        "direct_reports",
    }

    for key, value in raw_properties.items():
        if key in read_only_properties:
            raise HTTPException(
                status_code=400,
                detail=(
                    "directReports est calculé automatiquement "
                    "par Active Directory et reste en lecture seule"
                ),
            )

        if key not in allowed_properties:
            raise HTTPException(
                status_code=400,
                detail=f"Attribut non autorisé : {key}",
            )

        normalized_key = property_aliases.get(
            key,
            key,
        )

        if normalized_key == (
            "protectedFromAccidentalDeletion"
        ):
            if not isinstance(value, bool):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "protectedFromAccidentalDeletion "
                        "doit être un booléen"
                    ),
                )

            normalized_properties[normalized_key] = value
            continue

        if normalized_key == "msTSAllowLogon":
            if value is None:
                normalized_properties[normalized_key] = None
                continue

            if not isinstance(value, bool):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "msTSAllowLogon doit être un booléen "
                        "JSON ou null pour effacer la valeur"
                    ),
                )

            normalized_properties[normalized_key] = value
            continue

        if normalized_key in {
            "passwordNeverExpires",
            "cannotChangePassword",
            "smartcardLogonRequired",
            "accountNotDelegated",
        }:
            if not isinstance(value, bool):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{normalized_key} "
                        "doit être un booléen JSON"
                    ),
                )

            normalized_properties[normalized_key] = value
            continue

        if normalized_key in {
            "msTSProfilePath",
            "msTSHomeDirectory",
            "msTSHomeDrive",
            "msTSInitialProgram",
            "msTSWorkDirectory",
        }:
            if isinstance(
                value,
                (list, tuple, set, dict),
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{normalized_key} doit contenir "
                        "une seule chaine de caracteres"
                    ),
                )

            if value is None:
                normalized_properties[normalized_key] = None
                continue

            normalized_value = clean_string(value)

            if (
                normalized_key == "msTSHomeDrive"
                and normalized_value
            ):
                normalized_value = normalized_value.upper()

                if not re.fullmatch(
                    r"[A-Z]:",
                    normalized_value,
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "msTSHomeDrive doit être une lettre "
                            "de lecteur suivie de deux-points, "
                            "par exemple R:"
                        ),
                    )

            if len(normalized_value) > 32767:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{normalized_key} est limite a "
                        "32767 caracteres par le schema AD"
                    ),
                )

            normalized_properties[normalized_key] = (
                normalized_value
            )
            continue

        if normalized_key in {
            "uidNumber",
            "gidNumber",
        }:
            if value is None:
                normalized_properties[normalized_key] = None
                continue

            if (
                isinstance(value, bool)
                or isinstance(
                    value,
                    (list, tuple, set, dict),
                )
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{normalized_key} doit etre un "
                        "entier JSON ou une chaine entiere"
                    ),
                )

            if isinstance(value, int):
                normalized_value = value
            elif isinstance(value, str):
                normalized_text = value.strip()

                if not normalized_text:
                    normalized_properties[normalized_key] = None
                    continue

                if not re.fullmatch(
                    r"-?\d+",
                    normalized_text,
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{normalized_key} doit etre "
                            "un entier Integer32"
                        ),
                    )

                normalized_value = int(normalized_text)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{normalized_key} doit etre "
                        "un entier Integer32"
                    ),
                )

            if not (
                -2147483648
                <= normalized_value
                <= 2147483647
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{normalized_key} doit etre compris "
                        "entre -2147483648 et 2147483647"
                    ),
                )

            normalized_properties[normalized_key] = (
                normalized_value
            )
            continue

        if normalized_key in {
            "personalTitle",
            "initials",
            "preferredLanguage",
            "info",
            "unixHomeDirectory",
            "loginShell",
            "gecos",
        }:
            if (
                value is not None
                and not isinstance(value, str)
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{normalized_key} doit contenir "
                        "une chaine de caracteres unique"
                    ),
                )

            normalized_value = clean_string(value)
            maximum_length = property_max_lengths[
                normalized_key
            ]

            if len(normalized_value) > maximum_length:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{normalized_key} est limite a "
                        f"{maximum_length} caracteres"
                    ),
                )

            normalized_properties[normalized_key] = (
                normalized_value
            )
            continue

        if (
            normalized_key == "postOfficeBox"
            and isinstance(
                value,
                (list, tuple, set, dict),
            )
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "postOfficeBox doit contenir une seule "
                    "valeur dans C1"
                ),
            )

        if normalized_key == "countryCode":
            if value is None:
                normalized_properties[normalized_key] = ""
                continue

            normalized_value = str(value).strip()

            if not normalized_value:
                normalized_properties[normalized_key] = ""
                continue

            if not normalized_value.isdigit():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "countryCode doit être un entier "
                        "compris entre 0 et 65535"
                    ),
                )

            numeric_code = int(normalized_value)

            if not 0 <= numeric_code <= 65535:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "countryCode doit être un entier "
                        "compris entre 0 et 65535"
                    ),
                )

            normalized_properties[normalized_key] = (
                numeric_code
            )
            continue

        if normalized_key == "userWorkstations":
            if isinstance(
                value,
                (list, tuple, set, dict),
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "userWorkstations doit être une liste "
                        "de noms NetBIOS séparés par des virgules"
                    ),
                )

            normalized_value = clean_string(value)

            if not normalized_value:
                normalized_properties[normalized_key] = ""
                continue

            workstation_names = []
            seen_names = set()

            for raw_name in re.split(
                r"[,;]",
                normalized_value,
            ):
                workstation_name = raw_name.strip().upper()

                if not workstation_name:
                    continue

                if (
                    len(workstation_name) > 15
                    or not re.fullmatch(
                        r"[A-Z0-9]"
                        r"(?:[A-Z0-9-]*[A-Z0-9])?",
                        workstation_name,
                    )
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Chaque station doit utiliser un nom "
                            "NetBIOS valide de 1 à 15 caractères"
                        ),
                    )

                if workstation_name not in seen_names:
                    workstation_names.append(workstation_name)
                    seen_names.add(workstation_name)

            normalized_value = ",".join(workstation_names)

            if len(normalized_value) > 1024:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "userWorkstations est limité à "
                        "1024 caractères par le schéma AD"
                    ),
                )

            normalized_properties[normalized_key] = (
                normalized_value
            )
            continue

        if normalized_key == "logonHours":
            if isinstance(
                value,
                (list, tuple, set, dict),
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "logonHours doit contenir 21 octets "
                        "hexadécimaux"
                    ),
                )

            normalized_value = clean_string(value)

            if not normalized_value:
                normalized_properties[normalized_key] = ""
                continue

            hour_tokens = [
                token
                for token in re.split(
                    r"[\s,;]+",
                    normalized_value,
                )
                if token
            ]

            if (
                len(hour_tokens) != 21
                or any(
                    not re.fullmatch(
                        r"[0-9A-Fa-f]{2}",
                        token,
                    )
                    for token in hour_tokens
                )
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "logonHours doit contenir exactement "
                        "21 octets hexadécimaux"
                    ),
                )

            normalized_properties[normalized_key] = " ".join(
                token.upper()
                for token in hour_tokens
            )
            continue

        if normalized_key == "userPrincipalName":
            try:
                normalized_properties[normalized_key] = (
                    validate_user_principal_name(value)
                )
            except ADAdminBadRequest as error:
                raise HTTPException(
                    status_code=400,
                    detail=str(error),
                ) from error

            continue

        if normalized_key == "accountExpires":
            normalized_value = clean_string(value)

            if not normalized_value:
                normalized_properties[normalized_key] = ""
                continue

            if not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}",
                normalized_value,
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "accountExpires doit utiliser le format "
                        "AAAA-MM-JJ"
                    ),
                )

            try:
                parsed_expiration = datetime.strptime(
                    normalized_value,
                    "%Y-%m-%d",
                )
            except ValueError as error:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "accountExpires contient une date invalide"
                    ),
                ) from error

            normalized_properties[normalized_key] = (
                parsed_expiration.strftime("%Y-%m-%d")
            )
            continue

        if value is None:
            if normalized_key in {
                "groupScope",
                "groupCategory",
                "samAccountName",
            }:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{normalized_key} "
                        "ne peut pas être vide"
                    ),
                )

            normalized_properties[normalized_key] = None
            continue

        normalized_value = clean_string(value)

        if (
            normalized_key == "homeDrive"
            and normalized_value
        ):
            normalized_value = normalized_value.upper()

            if not re.fullmatch(
                r"[A-Z]:",
                normalized_value,
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "homeDrive doit être une lettre "
                        "de lecteur suivie de deux-points, "
                        "par exemple H:"
                    ),
                )

        if normalized_key == "c":
            normalized_value = normalized_value.upper()

            if (
                normalized_value
                and not re.fullmatch(
                    r"[A-Z]{2}",
                    normalized_value,
                )
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "c doit être un code pays ISO "
                        "alpha-2"
                    ),
                )

        maximum_length = property_max_lengths.get(
            normalized_key
        )

        if (
            maximum_length is not None
            and len(normalized_value) > maximum_length
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{normalized_key} est limité à "
                    f"{maximum_length} caractères"
                ),
            )

        if normalized_key == "samAccountName":
            if not normalized_value:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "samAccountName ne peut pas être vide"
                    ),
                )

            if len(normalized_value) > 256:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "samAccountName est limité à "
                        "256 caractères par le schéma AD"
                    ),
                )

        if normalized_key == "groupScope":
            if normalized_value not in {
                "Global",
                "Universal",
                "DomainLocal",
            }:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "groupScope doit être Global, "
                        "Universal ou DomainLocal"
                    ),
                )

        if normalized_key == "groupCategory":
            if normalized_value not in {
                "Security",
                "Distribution",
            }:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "groupCategory doit être Security "
                        "ou Distribution"
                    ),
                )

        if (
            normalized_key in {
                "manager",
                "managedBy",
            }
            and normalized_value
        ):
            normalized_value = validate_dn(
                normalized_value,
                normalized_key,
            )

        normalized_properties[normalized_key] = (
            normalized_value
        )

    country_triplet_requested = (
        "c" in normalized_properties
        or "countryCode" in normalized_properties
    )

    if country_triplet_requested:
        required_country_keys = {
            "c",
            "co",
            "countryCode",
        }

        missing_country_keys = (
            required_country_keys
            - set(normalized_properties)
        )

        if missing_country_keys:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Le pays doit être envoyé avec c, "
                    "co et countryCode"
                ),
            )

        country_values = [
            normalized_properties["c"],
            normalized_properties["co"],
            normalized_properties["countryCode"],
        ]

        empty_states = [
            value is None or value == ""
            for value in country_values
        ]

        if any(empty_states) and not all(empty_states):
            raise HTTPException(
                status_code=400,
                detail=(
                    "c, co et countryCode doivent être "
                    "tous renseignés ou tous vidés"
                ),
            )

        if all(empty_states):
            normalized_properties.update({
                "c": "",
                "co": "",
                "countryCode": "",
            })

    return normalized_properties



def create_ldap_attribute_update_simulation_job(
    jobs_file: Path,
    payload: dict,
    agent_mode: object,
) -> tuple[dict, dict]:
    payload = payload or {}
    created_by = (
        clean_string(payload.get("created_by"))
        or "react-admin"
    )

    prepared = (
        prepare_ldap_attribute_update_simulation_payload(
            payload,
            agent_mode,
        )
    )

    job_id = str(uuid4())
    job_payload = {
        "action": prepared["action"],
        "object_identity": prepared["object_identity"],
        "object_class": prepared["object_class"],
        "changes": prepared["changes"],
        "validation_contract_version": (
            prepared["validation_contract_version"]
        ),
        "update_contract_version": (
            prepared["update_contract_version"]
        ),
        "execution_policy": prepared["execution_policy"],
        "simulation_job_authorized": True,
        "production_authorized": False,
        "execution_authorized": False,
    }

    job = {
        "id": job_id,
        "type": "ad_admin",
        "status": "pending",
        "created_at": utc_now_iso(),
        "created_by": created_by,
        "action": prepared["action"],
        "payload": job_payload,
        "claimed_at": None,
        "claimed_by": None,
        "completed_at": None,
        "success": None,
        "message": "Simulation LDAP en attente agent",
        "output": "",
        "result": None,
        "details": None,
    }

    jobs = load_json(jobs_file, [])
    jobs.append(job)
    save_json(jobs_file, jobs)

    attribute_names = [
        change["attribute_name"]
        for change in prepared["changes"]
    ]

    audit_event = {
        "action": "ldap_simulation_job_created",
        "request_id": job_id,
        "actor": created_by,
        "message": "Job LDAP de simulation créé",
        "details": {
            "job_id": job_id,
            "action": prepared["action"],
            "object_identity": prepared["object_identity"],
            "object_class": prepared["object_class"],
            "attribute_names": attribute_names,
            "change_count": len(attribute_names),
            "execution_policy": prepared["execution_policy"],
            "production_authorized": False,
        },
    }

    return {
        "message": "Job LDAP de simulation créé",
        "job": sanitize_job_value(job),
    }, audit_event


def create_ad_admin_job(jobs_file: Path, payload: dict) -> tuple[dict, dict]:
    payload = payload or {}

    action = clean_string(payload.get("action"))
    created_by = clean_string(payload.get("created_by")) or "react-admin"

    if action not in ALLOWED_ACTIONS:
        raise ADAdminBadRequest(f"Action AD Admin inconnue : {action}")

    job_payload = {}
    audit_details = {
        "action": action,
    }

    if action in {"enable_account", "disable_account", "unlock_account"}:
        object_dn = validate_dn(
            payload.get("object_dn")
            or payload.get("distinguished_name")
            or payload.get("dn"),
            "object_dn"
        )

        job_payload = {
            "object_dn": object_dn,
        }

        audit_details.update({
            "object_dn": object_dn,
        })

    elif action == "reset_password":
        object_dn = validate_dn(
            payload.get("object_dn")
            or payload.get("distinguished_name")
            or payload.get("dn"),
            "object_dn"
        )

        temporary_password = clean_string(
            payload.get("temporary_password")
            or payload.get("password")
            or payload.get("new_password")
        )

        if not temporary_password:
            raise ADAdminBadRequest("temporary_password est obligatoire")

        force_change_at_logon = payload.get("force_change_at_logon", True)
        unlock_after_reset = payload.get("unlock_after_reset", True)

        if isinstance(force_change_at_logon, str):
            force_change_at_logon = force_change_at_logon.strip().lower() not in {"0", "false", "no", "non"}

        if isinstance(unlock_after_reset, str):
            unlock_after_reset = unlock_after_reset.strip().lower() not in {"0", "false", "no", "non"}

        job_payload = {
            "object_dn": object_dn,
            "temporary_password": temporary_password,
            "force_change_at_logon": bool(force_change_at_logon),
            "unlock_after_reset": bool(unlock_after_reset),
        }

        audit_details.update({
            "object_dn": object_dn,
            "force_change_at_logon": bool(force_change_at_logon),
            "unlock_after_reset": bool(unlock_after_reset),
        })

    elif action in {"create_ou", "create_group"}:
        parent_dn = validate_dn(payload.get("parent_dn"), "parent_dn")
        name = validate_name(payload.get("name"), "name")
        description = clean_string(payload.get("description"))

        job_payload = {
            "parent_dn": parent_dn,
            "name": name,
            "description": description,
        }

        audit_details.update({
            "parent_dn": parent_dn,
            "name": name,
        })

        if action == "create_group":
            group_scope = clean_string(payload.get("group_scope")) or "Global"
            group_category = clean_string(payload.get("group_category")) or "Security"
            sam_account_name = clean_string(payload.get("sam_account_name")) or name

            if group_scope not in ["Global", "Universal", "DomainLocal"]:
                raise ADAdminBadRequest("group_scope doit être Global, Universal ou DomainLocal")

            if group_category not in ["Security", "Distribution"]:
                raise ADAdminBadRequest("group_category doit être Security ou Distribution")

            sam_account_name = validate_name(sam_account_name, "sam_account_name")

            job_payload.update({
                "sam_account_name": sam_account_name,
                "group_scope": group_scope,
                "group_category": group_category,
            })

            audit_details.update({
                "sam_account_name": sam_account_name,
                "group_scope": group_scope,
                "group_category": group_category,
            })

    elif action == "create_user":
        first_name = validate_name(
            payload.get("first_name")
            or payload.get("firstName")
            or payload.get("given_name")
            or payload.get("givenName"),
            "first_name"
        )

        last_name = validate_name(
            payload.get("last_name")
            or payload.get("lastName")
            or payload.get("surname")
            or payload.get("sn"),
            "last_name"
        )

        sam_account_name = validate_name(
            payload.get("sam_account_name")
            or payload.get("samAccountName")
            or payload.get("username")
            or payload.get("login"),
            "sam_account_name"
        )

        if len(sam_account_name) > 20:
            raise ADAdminBadRequest(
                "sam_account_name est limité à 20 caractères"
            )

        target_ou_dn = validate_dn(
            payload.get("target_ou_dn")
            or payload.get("targetOuDn")
            or payload.get("target_parent_dn")
            or payload.get("targetParentDn")
            or payload.get("ou_dn")
            or payload.get("ouDn"),
            "target_ou_dn"
        )

        domain_dns_name = get_dns_domain_from_dn(
            target_ou_dn
        )

        user_principal_name = clean_string(
            payload.get("user_principal_name")
            or payload.get("userPrincipalName")
            or payload.get("upn")
        )

        if not user_principal_name:
            if not domain_dns_name:
                raise ADAdminBadRequest(
                    "Impossible de déterminer le domaine UPN"
                )

            user_principal_name = (
                f"{sam_account_name}@{domain_dns_name}"
            )

        user_principal_name = (
            validate_user_principal_name(
                user_principal_name
            )
        )

        temporary_password = clean_string(
            payload.get("temporary_password")
            or payload.get("temporaryPassword")
            or payload.get("password")
        )

        if not temporary_password:
            raise ADAdminBadRequest(
                "temporary_password est obligatoire"
            )

        description = clean_string(
            payload.get("description") or ""
        )

        create_user_profile = (
            normalize_create_user_profile(
                payload
            )
        )

        enabled = normalize_bool(
            payload.get("enabled"),
            default=False,
        )

        force_change_at_logon = normalize_bool(
            payload.get(
                "force_change_at_logon",
                payload.get(
                    "change_password_at_logon"
                ),
            ),
            default=True,
        )

        job_payload = {
            "action": action,
            "first_name": first_name,
            "last_name": last_name,
            "sam_account_name": sam_account_name,
            "user_principal_name": user_principal_name,
            "target_ou_dn": target_ou_dn,
            "temporary_password": temporary_password,
            "description": description,
            "enabled": enabled,
            "force_change_at_logon": (
                force_change_at_logon
            ),
        }

        job_payload.update(
            create_user_profile
        )

        profile_fields = sorted(
            set(create_user_profile)
            | (
                {"description"}
                if description
                else set()
            )
        )

        audit_details.update({
            "target_ou_dn": target_ou_dn,
            "sam_account_name": sam_account_name,
            "user_principal_name": user_principal_name,
            "first_name": first_name,
            "last_name": last_name,
            "enabled": enabled,
            "force_change_at_logon": (
                force_change_at_logon
            ),
            "profile_fields": profile_fields,
        })

    elif action == "create_computer":
        name = validate_computer_name(
            payload.get("name")
            or payload.get("computer_name")
            or payload.get("computerName")
        )

        sam_account_name = f"{name}$"

        target_ou_dn = validate_computer_target_ou(
            payload.get("target_ou_dn")
            or payload.get("targetOuDn")
            or payload.get("parent_dn")
            or payload.get("parentDn")
        )

        description = clean_string(
            payload.get("description")
        )

        location = clean_string(
            payload.get("location")
            or payload.get("office")
            or payload.get("site")
        )

        if len(description) > 1024:
            raise ADAdminBadRequest(
                "La description ordinateur est limitée à 1024 caractères"
            )

        if len(location) > 128:
            raise ADAdminBadRequest(
                "L’emplacement ordinateur est limité à 128 caractères"
            )

        enabled = normalize_bool(
            payload.get("enabled"),
            default=False,
        )

        job_payload = {
            "action": action,
            "name": name,
            "sam_account_name": sam_account_name,
            "target_ou_dn": target_ou_dn,
            "description": description,
            "location": location,
            "enabled": enabled,
        }

        audit_details.update({
            "name": name,
            "sam_account_name": sam_account_name,
            "target_ou_dn": target_ou_dn,
            "enabled": enabled,
        })

    elif action == "update_object_properties":
        object_identity = clean_string(
            payload.get("object_identity")
            or payload.get("object_dn")
            or payload.get("distinguished_name")
            or payload.get("dn")
            or payload.get("sam_account_name")
            or payload.get("name")
        )

        raw_properties = (
            payload.get("properties") or {}
        )

        normalized_properties = (
            normalize_update_object_properties(
                raw_properties
            )
        )

        if not object_identity:
            raise HTTPException(status_code=400, detail="object_identity est obligatoire")

        if not normalized_properties:
            raise HTTPException(status_code=400, detail="Aucune propriété à modifier")

        job_payload = {
            "action": action,
            "object_identity": object_identity,
            "properties": normalized_properties,
        }

    elif action == "delete_object":
        object_identity = clean_string(
            payload.get("object_identity")
            or payload.get("object_dn")
            or payload.get("distinguished_name")
            or payload.get("dn")
            or payload.get("sam_account_name")
            or payload.get("name")
        )

        confirm_dn = validate_dn(
            payload.get("confirm_dn")
            or payload.get("confirmDn")
            or payload.get("confirmation_dn")
            or payload.get("confirmationDn"),
            "confirm_dn"
        )

        if not object_identity:
            raise ValueError("object_identity est obligatoire")

        job_payload = {
            "action": action,
            "object_identity": object_identity,
            "confirm_dn": confirm_dn,
        }

    elif action == "rename_object":
        object_identity = clean_string(
            payload.get("object_identity")
            or payload.get("object_dn")
            or payload.get("distinguished_name")
            or payload.get("dn")
            or payload.get("sam_account_name")
            or payload.get("name")
        )

        new_name = validate_name(
            payload.get("new_name")
            or payload.get("newName")
            or payload.get("target_name")
            or payload.get("targetName"),
            "new_name"
        )

        if not object_identity:
            raise ValueError("object_identity est obligatoire")

        job_payload = {
            "action": action,
            "object_identity": object_identity,
            "new_name": new_name,
        }

    elif action == "move_object":
        object_identity = clean_string(
            payload.get("object_identity")
            or payload.get("object_dn")
            or payload.get("distinguished_name")
            or payload.get("dn")
            or payload.get("sam_account_name")
            or payload.get("name")
        )

        target_parent_dn = validate_dn(
            payload.get("target_parent_dn")
            or payload.get("target_ou_dn")
            or payload.get("target_dn"),
            "target_parent_dn"
        )

        if not object_identity:
            raise ValueError("object_identity est obligatoire")

        job_payload = {
            "action": action,
            "object_identity": object_identity,
            "target_parent_dn": target_parent_dn,
        }

    elif action in {"add_group_member", "remove_group_member"}:
        group_identity = clean_string(
            payload.get("group_identity")
            or payload.get("group_dn")
            or payload.get("group_name")
            or payload.get("group")
        )

        member_identity = clean_string(
            payload.get("member_identity")
            or payload.get("member_dn")
            or payload.get("member_name")
            or payload.get("member")
            or payload.get("user_identity")
            or payload.get("username")
            or payload.get("sam_account_name")
        )

        if not group_identity:
            raise ADAdminBadRequest("group_identity est obligatoire")

        if not member_identity:
            raise ADAdminBadRequest("member_identity est obligatoire")

        job_payload = {
            "group_identity": group_identity,
            "member_identity": member_identity,
        }

        audit_details.update({
            "group_identity": group_identity,
            "member_identity": member_identity,
        })

    job_id = str(uuid4())

    job = {
        "id": job_id,
        "type": "ad_admin",
        "status": "pending",
        "created_at": utc_now_iso(),
        "created_by": created_by,
        "action": action,
        "payload": job_payload,
        "claimed_at": None,
        "claimed_by": None,
        "completed_at": None,
        "success": None,
        "message": "Action AD Admin en attente agent",
        "output": "",
        "result": None,
        "details": None,
    }

    jobs = load_json(jobs_file, [])
    jobs.append(job)
    save_json(jobs_file, jobs)

    audit_details["job_id"] = job_id

    audit_event = {
        "action": "ad_admin_job_created",
        "request_id": job_id,
        "actor": created_by,
        "message": f"Job AD Admin créé : {action}",
        "details": audit_details,
    }

    return {
        "message": "Job AD Admin créé",
        "job": sanitize_job_value(job),
    }, audit_event


def list_ad_admin_jobs(jobs_file: Path, limit: int = 100) -> dict:
    jobs = load_json(jobs_file, [])
    safe_limit = normalize_limit(limit, default=100)

    sorted_jobs = sorted(
        jobs,
        key=lambda job: job.get("created_at") or "",
        reverse=True,
    )

    selected = sorted_jobs[:safe_limit]

    return {
        "count": len(jobs),
        "returned": len(selected),
        "jobs": [
            sanitize_job_value(job)
            for job in selected
        ],
    }


def get_ad_admin_job(jobs_file: Path, job_id: str) -> dict:
    jobs = load_json(jobs_file, [])

    for job in jobs:
        if job.get("id") == job_id:
            return sanitize_job_value(job)

    raise ADAdminNotFound("Job AD Admin introuvable")


def get_pending_ad_admin_jobs(jobs_file: Path) -> dict:
    jobs = load_json(jobs_file, [])

    pending = [
        job for job in jobs
        if job.get("status") == "pending"
    ]

    return {
        "count": len(pending),
        "jobs": pending,
    }


def claim_ad_admin_job(jobs_file: Path, job_id: str, payload: dict) -> tuple[dict, dict]:
    jobs = load_json(jobs_file, [])
    payload = payload or {}

    for job in jobs:
        if job.get("id") == job_id:
            current_status = job.get("status")

            if current_status != "pending":
                raise ADAdminConflict(
                    f"Job AD Admin non disponible. Statut actuel : {current_status}"
                )

            agent_name = clean_string(payload.get("agent_name")) or "unknown-agent"

            job["status"] = "processing"
            job["claimed_at"] = utc_now_iso()
            job["claimed_by"] = agent_name
            job["message"] = "Action AD Admin en cours sur agent"

            save_json(jobs_file, jobs)

            audit_event = {
                "action": "ad_admin_job_claimed",
                "request_id": job_id,
                "actor": agent_name,
                "message": "Job AD Admin pris en charge par un agent",
                "details": {
                    "job_id": job_id,
                    "action": job.get("action"),
                    "status": "processing",
                },
            }

            return {
                "message": "Job AD Admin pris en charge",
                "job": job,
            }, audit_event

    raise ADAdminNotFound("Job AD Admin introuvable")


def submit_ad_admin_job_result(jobs_file: Path, job_id: str, payload: dict) -> tuple[dict, dict]:
    jobs = load_json(jobs_file, [])
    payload = payload or {}

    for job in jobs:
        if job.get("id") == job_id:
            success = bool(payload.get("success"))
            sensitive_values = collect_sensitive_values(job)

            job["status"] = "completed" if success else "failed"
            job["completed_at"] = utc_now_iso()
            job["success"] = success
            job["message"] = sanitize_job_value(
                payload.get("message")
                or (
                    "Action AD Admin terminée"
                    if success
                    else "Action AD Admin en erreur"
                ),
                sensitive_values,
            )
            job["output"] = sanitize_job_value(
                payload.get("output") or "",
                sensitive_values,
            )
            job["result"] = sanitize_job_value(
                payload.get("result"),
                sensitive_values,
            )
            job["details"] = sanitize_job_value(
                payload.get("details"),
                sensitive_values,
            )
            job["agent_name"] = clean_string(
                payload.get("agent_name")
            )

            redacted_secret_fields = (
                remove_sensitive_values_in_place(job)
            )

            save_json(jobs_file, jobs)

            audit_event = {
                "action": "ad_admin_job_completed" if success else "ad_admin_job_failed",
                "request_id": job_id,
                "actor": payload.get("agent_name") or "agent",
                "message": job["message"],
                "details": {
                    "job_id": job_id,
                    "action": job.get("action"),
                    "success": success,
                    "redacted_secret_fields": (
                        redacted_secret_fields
                    ),
                },
            }

            return {
                "message": "Résultat AD Admin enregistré",
                "job_id": job_id,
            }, audit_event

    raise ADAdminNotFound("Job AD Admin introuvable")
