from __future__ import annotations

from dataclasses import asdict, dataclass


LDAP_SUPPORTED_VALUE_TYPES = frozenset({
    "single_text",
    "boolean",
    "integer32",
    "integer64",
})

_INTEGER_BOUNDS = {
    "integer32": (
        -2147483648,
        2147483647,
    ),
    "integer64": (
        -9223372036854775808,
        9223372036854775807,
    ),
}


@dataclass(frozen=True)
class LDAPValueNormalizationResult:
    valid: bool
    normalized_value: str | int | bool | None
    errors: tuple[dict[str, str], ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["errors"] = [
            dict(item)
            for item in self.errors
        ]
        return payload


def _error(
    code: str,
    message: str,
) -> dict[str, str]:
    return {
        "code": code,
        "message": message,
    }


def normalize_ldap_typed_value(
    *,
    value_type: str,
    value: object,
    minimum_length: int = 0,
    maximum_length: int | None = None,
    minimum_value: int | None = None,
    maximum_value: int | None = None,
) -> LDAPValueNormalizationResult:
    errors: list[dict[str, str]] = []
    normalized_value: str | int | bool | None = None

    if value_type not in LDAP_SUPPORTED_VALUE_TYPES:
        errors.append(
            _error(
                "unsupported_value_type",
                "Type de valeur LDAP non pris en charge.",
            )
        )

    elif value_type == "single_text":
        if not isinstance(value, str):
            errors.append(
                _error(
                    "invalid_value_type",
                    "Valeur texte obligatoire.",
                )
            )
        else:
            normalized_value = value.strip()

            if not normalized_value:
                errors.append(
                    _error(
                        "empty_set_value",
                        "La valeur texte ne peut pas être vide.",
                    )
                )

            if any(
                char in normalized_value
                for char in (
                    "\x00",
                    "\r",
                    "\n",
                )
            ):
                errors.append(
                    _error(
                        "forbidden_control_character",
                        "Caractère de contrôle interdit.",
                    )
                )

            if len(normalized_value) < minimum_length:
                errors.append(
                    _error(
                        "value_too_short",
                        "Valeur trop courte.",
                    )
                )

            if (
                maximum_length is not None
                and len(normalized_value) > maximum_length
            ):
                errors.append(
                    _error(
                        "value_too_long",
                        "Valeur trop longue.",
                    )
                )

    elif value_type == "boolean":
        if type(value) is not bool:
            errors.append(
                _error(
                    "invalid_value_type",
                    "Valeur booléenne obligatoire.",
                )
            )
        else:
            normalized_value = value

    else:
        if type(value) is not int:
            errors.append(
                _error(
                    "invalid_value_type",
                    "Valeur entière obligatoire.",
                )
            )
        else:
            normalized_value = value
            hard_minimum, hard_maximum = (
                _INTEGER_BOUNDS[value_type]
            )

            effective_minimum = (
                hard_minimum
                if minimum_value is None
                else max(
                    hard_minimum,
                    minimum_value,
                )
            )

            effective_maximum = (
                hard_maximum
                if maximum_value is None
                else min(
                    hard_maximum,
                    maximum_value,
                )
            )

            if effective_minimum > effective_maximum:
                errors.append(
                    _error(
                        "invalid_numeric_bounds",
                        "Bornes numériques incohérentes.",
                    )
                )
            else:
                if value < effective_minimum:
                    errors.append(
                        _error(
                            "value_below_minimum",
                            "Valeur inférieure au minimum.",
                        )
                    )

                if value > effective_maximum:
                    errors.append(
                        _error(
                            "value_above_maximum",
                            "Valeur supérieure au maximum.",
                        )
                    )

    return LDAPValueNormalizationResult(
        valid=not errors,
        normalized_value=normalized_value,
        errors=tuple(errors),
    )
