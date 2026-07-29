# Controlled LDAP attribute policy for EITAS C2.
#
# This module mirrors the validated C1 property policy while keeping the
# generic LDAP editor non-authorizing. The LDAP schema catalog is metadata,
# not an authorization source.

from __future__ import annotations

from dataclasses import asdict, dataclass
from types import MappingProxyType


LDAP_ATTRIBUTE_POLICY_VERSION = "c2.2b.1"
LDAP_ATTRIBUTE_POLICY_DEFAULT = "deny"
LDAP_SCHEMA_CATALOG_IS_AUTHORIZATION = False
LDAP_GENERIC_EDITOR_WRITES_ENABLED = False


C1_EDITABLE_INPUT_KEYS = frozenset(('account_expires',
 'accountExpires',
 'c',
 'city',
 'co',
 'company',
 'country',
 'country_alpha2',
 'country_numeric_code',
 'countryCode',
 'department',
 'description',
 'display_name',
 'displayName',
 'division',
 'employee_id',
 'employee_number',
 'employeeID',
 'employeeNumber',
 'facsimileTelephoneNumber',
 'givenName',
 'group_category',
 'group_scope',
 'groupCategory',
 'groupScope',
 'home_directory',
 'home_drive',
 'homeDirectory',
 'homeDrive',
 'homePhone',
 'info',
 'initials',
 'ipPhone',
 'l',
 'location',
 'logon_hours',
 'logonHours',
 'mail',
 'managed_by',
 'managedBy',
 'manager',
 'manager_dn',
 'mobile',
 'mobile_phone',
 'office',
 'operating_system',
 'operating_system_service_pack',
 'operating_system_version',
 'operatingSystem',
 'operatingSystemServicePack',
 'operatingSystemVersion',
 'pager',
 'physicalDeliveryOfficeName',
 'post_office_box',
 'postal_code',
 'postalCode',
 'postOfficeBox',
 'profile_path',
 'profilePath',
 'protected_from_accidental_deletion',
 'protectedFromAccidentalDeletion',
 'sam_account_name',
 'samAccountName',
 'script_path',
 'scriptPath',
 'sn',
 'st',
 'state',
 'street_address',
 'streetAddress',
 'telephone_number',
 'telephoneNumber',
 'title',
 'upn',
 'user_principal_name',
 'user_workstations',
 'userPrincipalName',
 'userWorkstations',
 'wWWHomePage'))
C1_EDITABLE_ALIASES = MappingProxyType({'account_expires': 'accountExpires',
 'city': 'l',
 'country': 'co',
 'country_alpha2': 'c',
 'country_numeric_code': 'countryCode',
 'display_name': 'displayName',
 'employee_id': 'employeeID',
 'employee_number': 'employeeNumber',
 'group_category': 'groupCategory',
 'group_scope': 'groupScope',
 'home_directory': 'homeDirectory',
 'home_drive': 'homeDrive',
 'logon_hours': 'logonHours',
 'managed_by': 'managedBy',
 'manager_dn': 'manager',
 'mobile_phone': 'mobile',
 'office': 'physicalDeliveryOfficeName',
 'operating_system': 'operatingSystem',
 'operating_system_service_pack': 'operatingSystemServicePack',
 'operating_system_version': 'operatingSystemVersion',
 'post_office_box': 'postOfficeBox',
 'postal_code': 'postalCode',
 'profile_path': 'profilePath',
 'protected_from_accidental_deletion': 'protectedFromAccidentalDeletion',
 'sam_account_name': 'samAccountName',
 'script_path': 'scriptPath',
 'state': 'st',
 'street_address': 'streetAddress',
 'telephone_number': 'telephoneNumber',
 'upn': 'userPrincipalName',
 'user_principal_name': 'userPrincipalName',
 'user_workstations': 'userWorkstations'})
C1_EDITABLE_CANONICAL_PROPERTIES = frozenset(('accountExpires',
 'c',
 'co',
 'company',
 'countryCode',
 'department',
 'description',
 'displayName',
 'division',
 'employeeID',
 'employeeNumber',
 'facsimileTelephoneNumber',
 'givenName',
 'groupCategory',
 'groupScope',
 'homeDirectory',
 'homeDrive',
 'homePhone',
 'info',
 'initials',
 'ipPhone',
 'l',
 'location',
 'logonHours',
 'mail',
 'managedBy',
 'manager',
 'mobile',
 'operatingSystem',
 'operatingSystemServicePack',
 'operatingSystemVersion',
 'pager',
 'physicalDeliveryOfficeName',
 'postalCode',
 'postOfficeBox',
 'profilePath',
 'protectedFromAccidentalDeletion',
 'samAccountName',
 'scriptPath',
 'sn',
 'st',
 'streetAddress',
 'telephoneNumber',
 'title',
 'userPrincipalName',
 'userWorkstations',
 'wWWHomePage'))
C1_READ_ONLY_CANONICAL_PROPERTIES = frozenset(('directReports',))
C1_READ_ONLY_ALIASES = MappingProxyType({'direct_reports': 'directReports'})
C1_VISIBLE_CANONICAL_PROPERTIES = frozenset(('accountExpires',
 'c',
 'co',
 'company',
 'countryCode',
 'department',
 'description',
 'directReports',
 'displayName',
 'division',
 'employeeID',
 'employeeNumber',
 'facsimileTelephoneNumber',
 'givenName',
 'groupCategory',
 'groupScope',
 'homeDirectory',
 'homeDrive',
 'homePhone',
 'info',
 'initials',
 'ipPhone',
 'l',
 'location',
 'logonHours',
 'mail',
 'managedBy',
 'manager',
 'mobile',
 'operatingSystem',
 'operatingSystemServicePack',
 'operatingSystemVersion',
 'pager',
 'physicalDeliveryOfficeName',
 'postalCode',
 'postOfficeBox',
 'profilePath',
 'protectedFromAccidentalDeletion',
 'samAccountName',
 'scriptPath',
 'sn',
 'st',
 'streetAddress',
 'telephoneNumber',
 'title',
 'userPrincipalName',
 'userWorkstations',
 'wWWHomePage'))
C1_PROPERTY_MAX_LENGTHS = MappingProxyType({'co': 128,
 'facsimileTelephoneNumber': 64,
 'homePhone': 64,
 'info': 1024,
 'initials': 6,
 'ipPhone': 64,
 'mobile': 64,
 'pager': 64,
 'postOfficeBox': 40,
 'telephoneNumber': 64,
 'wWWHomePage': 2048})


class LDAPAttributePolicyError(ValueError):
    pass


@dataclass(frozen=True)
class LDAPAttributePolicyDecision:
    requested_name: str
    canonical_name: str
    category: str
    known: bool
    visible: bool
    c1_property_editor_editable: bool
    generic_ldap_editor_editable: bool
    generic_ldap_editor_read_only: bool
    denied: bool
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _build_request_index() -> MappingProxyType:
    index: dict[str, str] = {}

    editable_requests = {
        name: C1_EDITABLE_ALIASES.get(name, name)
        for name in C1_EDITABLE_INPUT_KEYS
    }

    read_only_requests = {
        name: C1_READ_ONLY_ALIASES.get(name, name)
        for name in (
            set(C1_READ_ONLY_CANONICAL_PROPERTIES)
            | set(C1_READ_ONLY_ALIASES)
        )
    }

    for requested_name, canonical_name in (
        editable_requests | read_only_requests
    ).items():
        folded = requested_name.casefold()
        previous = index.get(folded)

        if previous is not None and previous != canonical_name:
            raise RuntimeError(
                "Collision de politique LDAP pour "
                f"{requested_name!r}: {previous!r} / {canonical_name!r}"
            )

        index[folded] = canonical_name

    return MappingProxyType(index)


_REQUEST_TO_CANONICAL = _build_request_index()


def normalize_ldap_attribute_name(value: object) -> tuple[str, str]:
    if not isinstance(value, str):
        raise LDAPAttributePolicyError(
            "Le nom d'attribut LDAP doit etre une chaine."
        )

    requested_name = value.strip()

    if not requested_name:
        raise LDAPAttributePolicyError(
            "Le nom d'attribut LDAP est obligatoire."
        )

    canonical_name = _REQUEST_TO_CANONICAL.get(
        requested_name.casefold(),
        requested_name,
    )

    return requested_name, canonical_name


def resolve_ldap_attribute_policy(
    attribute_name: object,
) -> LDAPAttributePolicyDecision:
    requested_name, canonical_name = normalize_ldap_attribute_name(
        attribute_name
    )

    if canonical_name in C1_EDITABLE_CANONICAL_PROPERTIES:
        return LDAPAttributePolicyDecision(
            requested_name=requested_name,
            canonical_name=canonical_name,
            category="c1_editable_generic_read_only",
            known=True,
            visible=True,
            c1_property_editor_editable=True,
            generic_ldap_editor_editable=False,
            generic_ldap_editor_read_only=True,
            denied=False,
            reason=(
                "Attribut gere par l'editeur de proprietes C1; "
                "lecture seule dans l'editeur LDAP generique."
            ),
        )

    if canonical_name in C1_READ_ONLY_CANONICAL_PROPERTIES:
        return LDAPAttributePolicyDecision(
            requested_name=requested_name,
            canonical_name=canonical_name,
            category="c1_read_only",
            known=True,
            visible=True,
            c1_property_editor_editable=False,
            generic_ldap_editor_editable=False,
            generic_ldap_editor_read_only=True,
            denied=False,
            reason="Attribut C1 visible mais gere en lecture seule.",
        )

    return LDAPAttributePolicyDecision(
        requested_name=requested_name,
        canonical_name=canonical_name,
        category="deny",
        known=False,
        visible=False,
        c1_property_editor_editable=False,
        generic_ldap_editor_editable=False,
        generic_ldap_editor_read_only=False,
        denied=True,
        reason=(
            "Attribut absent de la politique controlee; refus par defaut."
        ),
    )


def get_c1_visible_ldap_policy_catalog() -> list[dict]:
    return [
        resolve_ldap_attribute_policy(attribute_name).to_dict()
        for attribute_name in sorted(
            C1_VISIBLE_CANONICAL_PROPERTIES,
            key=str.casefold,
        )
    ]


def assert_ldap_attribute_policy_invariants() -> None:
    if LDAP_ATTRIBUTE_POLICY_DEFAULT != "deny":
        raise RuntimeError(
            "La politique LDAP par defaut doit rester deny."
        )

    if LDAP_SCHEMA_CATALOG_IS_AUTHORIZATION:
        raise RuntimeError(
            "Le catalogue LDAP ne peut pas devenir une autorisation."
        )

    if LDAP_GENERIC_EDITOR_WRITES_ENABLED:
        raise RuntimeError(
            "Les ecritures de l'editeur LDAP generique "
            "ne sont pas encore autorisees."
        )

    if (
        C1_EDITABLE_CANONICAL_PROPERTIES
        & C1_READ_ONLY_CANONICAL_PROPERTIES
    ):
        raise RuntimeError(
            "Les attributs C1 modifiables et lecture seule se chevauchent."
        )

    expected_visible = (
        C1_EDITABLE_CANONICAL_PROPERTIES
        | C1_READ_ONLY_CANONICAL_PROPERTIES
    )

    if C1_VISIBLE_CANONICAL_PROPERTIES != expected_visible:
        raise RuntimeError(
            "La liste visible C1 ne correspond pas aux ensembles controles."
        )

    for requested_name in C1_EDITABLE_INPUT_KEYS:
        decision = resolve_ldap_attribute_policy(requested_name)

        if (
            decision.canonical_name
            not in C1_EDITABLE_CANONICAL_PROPERTIES
        ):
            raise RuntimeError(
                f"Entree C1 non resolue: {requested_name}"
            )

        if decision.generic_ldap_editor_editable:
            raise RuntimeError(
                "Une entree C1 autorise une ecriture LDAP generique."
            )

    for alias, canonical_name in C1_READ_ONLY_ALIASES.items():
        decision = resolve_ldap_attribute_policy(alias)

        if decision.canonical_name != canonical_name:
            raise RuntimeError(
                f"Alias lecture seule non resolu: {alias}"
            )


assert_ldap_attribute_policy_invariants()
