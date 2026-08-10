from pathlib import Path

import pytest

from app.services.acl_delegation_write_intent import (
    ACL_DELEGATION_WRITE_CONFIRMATION_PHRASE,
    AclDelegationWriteIntentBadRequest,
    normalize_acl_delegation_write_intent,
)


TARGET_DN = (
    "OU=test,OU=Users,OU=EITAS,"
    "DC=API,DC=LOCAL"
)

SIMULATION_JOB_ID = (
    "0359e373-70b2-47a0-b785-f7cb80967ac4"
)

SECURITY_DESCRIPTOR_JOB_ID = (
    "deebe24c-a62e-4b03-9f92-546d38a984df"
)

ACL_FINGERPRINT = (
    "768e3666597dd8390a77eaaf13284dd4"
    "7f9cb7d1b43432db2a712b9ee8e9b56a"
)


def make_payload(**overrides):
    payload = {
        "action": "apply_acl_delegation",
        "mode": "Production",
        "object_dn": TARGET_DN,
        "principal_identity": "GG_IT_Admin",
        "access_control_type": "Allow",
        "rights": [
            "ReadProperty",
            "WriteProperty",
        ],
        "inheritance_type": "Descendents",
        "object_type_guid": None,
        "inherited_object_type_guid": None,
        "simulation_job_id": SIMULATION_JOB_ID,
        "security_descriptor_job_id": (
            SECURITY_DESCRIPTOR_JOB_ID
        ),
        "expected_acl_fingerprint": ACL_FINGERPRINT,
        "confirm_object_dn": TARGET_DN,
        "confirmation_phrase": (
            ACL_DELEGATION_WRITE_CONFIRMATION_PHRASE
        ),
    }

    payload.update(overrides)

    return payload


def test_c8_4a1_normalizes_dormant_write_intent():
    intent = normalize_acl_delegation_write_intent(
        make_payload()
    )

    assert intent.action == "apply_acl_delegation"
    assert intent.mode == "Production"

    assert intent.object_dn == TARGET_DN

    assert intent.principal_identity == (
        "GG_IT_Admin"
    )

    assert intent.rights == (
        "ReadProperty",
        "WriteProperty",
    )

    assert intent.inheritance_type == (
        "Descendents"
    )

    assert intent.simulation_job_id == (
        SIMULATION_JOB_ID
    )

    assert intent.security_descriptor_job_id == (
        SECURITY_DESCRIPTOR_JOB_ID
    )

    assert intent.expected_acl_fingerprint == (
        ACL_FINGERPRINT
    )

    assert intent.execution_policy == (
        "controlled_write_dormant"
    )

    assert intent.job_creation_authorized is False
    assert intent.runtime_authorized is False
    assert intent.production_authorized is False
    assert intent.ad_write_authorized is False


def test_c8_4a1_requires_explicit_production_intent():
    with pytest.raises(
        AclDelegationWriteIntentBadRequest
    ):
        normalize_acl_delegation_write_intent(
            make_payload(
                mode="Simulation",
            )
        )


@pytest.mark.parametrize(
    "right",
    [
        "GenericAll",
        "WriteDacl",
        "WriteOwner",
        "AccessSystemSecurity",
    ],
)
def test_c8_4a1_rejects_dangerous_rights(
    right,
):
    with pytest.raises(
        AclDelegationWriteIntentBadRequest
    ):
        normalize_acl_delegation_write_intent(
            make_payload(
                rights=[right],
            )
        )


def test_c8_4a1_rejects_deny():
    with pytest.raises(
        AclDelegationWriteIntentBadRequest
    ):
        normalize_acl_delegation_write_intent(
            make_payload(
                access_control_type="Deny",
            )
        )


def test_c8_4a1_requires_matching_confirmation_dn():
    with pytest.raises(
        AclDelegationWriteIntentBadRequest
    ):
        normalize_acl_delegation_write_intent(
            make_payload(
                confirm_object_dn=(
                    "OU=Other,OU=Users,OU=EITAS,"
                    "DC=API,DC=LOCAL"
                ),
            )
        )


def test_c8_4a1_requires_confirmation_phrase():
    with pytest.raises(
        AclDelegationWriteIntentBadRequest
    ):
        normalize_acl_delegation_write_intent(
            make_payload(
                confirmation_phrase="YES",
            )
        )


@pytest.mark.parametrize(
    "field,value",
    [
        (
            "simulation_job_id",
            "not-a-uuid",
        ),
        (
            "security_descriptor_job_id",
            "not-a-uuid",
        ),
        (
            "expected_acl_fingerprint",
            "1234",
        ),
    ],
)
def test_c8_4a1_requires_simulation_binding(
    field,
    value,
):
    with pytest.raises(
        AclDelegationWriteIntentBadRequest
    ):
        normalize_acl_delegation_write_intent(
            make_payload(
                **{
                    field: value,
                }
            )
        )



def test_c8_4a1_remains_completely_dormant():
    admin_source = Path(
        "api/app/services/ad_admin.py"
    ).read_text(
        encoding="utf-8"
    )

    main_source = Path(
        "api/main.py"
    ).read_text(
        encoding="utf-8"
    )

    worker_source = Path(
        "agent-windows/modules/EitasAdAdmin.ps1"
    ).read_text(
        encoding="utf-8"
    )

    frontend_source = Path(
        "frontend/src/features/"
        "active-directory/"
        "AdExplorerPage.jsx"
    ).read_text(
        encoding="utf-8"
    )

    # C8.4D introduces one structural dormant intent
    # in React. It is evidence only and must remain
    # absent from generic backend/worker execution.
    assert "apply_acl_delegation" not in admin_source
    assert "apply_acl_delegation" not in main_source
    assert "apply_acl_delegation" not in worker_source

    assert (
        'action: "apply_acl_delegation"'
        in frontend_source
    )

    assert (
        'mode: "Production"'
        in frontend_source
    )

    assert (
        "production_preparation_dormant"
        in frontend_source
    )



def test_c8_4a1_contains_no_acl_write_primitive():
    source = Path(
        "api/app/services/"
        "acl_delegation_write_intent.py"
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "Set-Acl",
        "SetAccessRule",
        "AddAccessRule",
        "RemoveAccessRule",
        "ResetAccessRule",
        "SetOwner",
        "ActiveDirectoryAccessRule",
    )

    for token in forbidden:
        assert token not in source
