from app.services.ad_deleted_object_preflight import (
    CLASS_POLICIES,
    evaluate_deleted_object_preflight,
)


def base_item(**updates):
    item = {
        "object_guid":
            "11111111-2222-3333-4444-555555555555",

        "object_class":
            "user",

        "is_deleted":
            True,

        "is_recycled":
            False,

        "last_known_parent":
            "OU=Users,DC=API,DC=LOCAL",

        "last_known_rdn":
            "CN=Deleted User",
    }

    item.update(updates)

    return item


def evaluate(
    item=None,
    **kwargs,
):
    return evaluate_deleted_object_preflight(
        item or base_item(),
        recycle_bin_enabled=kwargs.pop(
            "recycle_bin_enabled",
            True,
        ),
        **kwargs,
    )


def test_missing_guid_is_blocked():
    result = evaluate(
        base_item(
            object_guid="",
        )
    )

    assert (
        result["decision"]
        == "blocked_invalid_identity"
    )


def test_non_deleted_object_is_blocked():
    result = evaluate(
        base_item(
            is_deleted=False,
        )
    )

    assert (
        result["decision"]
        == "blocked_not_deleted"
    )


def test_recycled_object_is_always_blocked():
    result = evaluate(
        base_item(
            is_recycled=True,
        ),
        recycle_bin_enabled=True,
    )

    assert (
        result["decision"]
        == "blocked_recycled"
    )

    assert (
        result["simulation_candidate"]
        is False
    )


def test_disabled_recycle_bin_blocks_non_recycled_object():
    result = evaluate(
        recycle_bin_enabled=False,
    )

    assert (
        result["decision"]
        == "blocked_recycle_bin_disabled"
    )


def test_missing_parent_and_name_requires_both():
    result = evaluate(
        base_item(
            last_known_parent="",
            last_known_rdn="",
        )
    )

    assert (
        result["decision"]
        == "needs_target_path_and_new_name"
    )


def test_missing_parent_requires_target_path():
    result = evaluate(
        base_item(
            last_known_parent="",
        )
    )

    assert (
        result["decision"]
        == "needs_target_path"
    )


def test_missing_rdn_requires_new_name():
    result = evaluate(
        base_item(
            last_known_rdn="",
        )
    )

    assert (
        result["decision"]
        == "needs_new_name"
    )


def test_deleted_historical_parent_requires_alternative():
    result = evaluate(
        target_parent_exists=False,
        target_parent_deleted=True,
    )

    assert (
        result["decision"]
        == "needs_parent_restore_or_target_path"
    )


def test_target_collision_is_blocked():
    result = evaluate(
        target_parent_exists=True,
        target_parent_deleted=False,
        target_dn_exists=True,
    )

    assert (
        result["decision"]
        == "blocked_name_collision"
    )


def test_valid_metadata_reaches_preflight_candidate_only():
    result = evaluate(
        target_parent_exists=True,
        target_parent_deleted=False,
        target_dn_exists=False,
    )

    assert (
        result["decision"]
        == "candidate_preflight"
    )

    assert (
        result["preflight_passed"]
        is True
    )

    assert (
        result["simulation_candidate"]
        is True
    )

    assert (
        result["execution_authorized"]
        is False
    )

    assert (
        result["write_authorized"]
        is False
    )


def test_explicit_name_and_target_replace_missing_metadata():
    result = evaluate(
        base_item(
            last_known_parent="",
            last_known_rdn="",
        ),
        requested_new_name=(
            "Recovered User"
        ),
        requested_target_path=(
            "OU=Recovery,DC=API,DC=LOCAL"
        ),
        target_parent_exists=True,
        target_parent_deleted=False,
        target_dn_exists=False,
    )

    assert (
        result["decision"]
        == "candidate_preflight"
    )

    assert (
        result["used_explicit_new_name"]
        is True
    )

    assert (
        result["used_explicit_target_path"]
        is True
    )


def test_explicit_missing_target_is_not_accepted():
    result = evaluate(
        requested_target_path=(
            "OU=Missing,DC=API,DC=LOCAL"
        ),
        target_parent_exists=False,
        target_parent_deleted=False,
        target_dn_exists=False,
    )

    assert (
        result["decision"]
        == "needs_target_path"
    )


def test_dns_objects_require_manual_review():
    result = evaluate(
        base_item(
            object_class="dnsNode",
        ),
        target_parent_exists=True,
        target_parent_deleted=False,
        target_dn_exists=False,
    )

    assert (
        result["class_policy"]
        == "high_risk_manual_review"
    )

    assert (
        result["manual_review_required"]
        is True
    )

    assert (
        result["execution_authorized"]
        is False
    )


def test_ou_objects_are_hierarchy_sensitive():
    result = evaluate(
        base_item(
            object_class="organizationalUnit",
        ),
        target_parent_exists=True,
        target_parent_deleted=False,
        target_dn_exists=False,
    )

    assert (
        result["class_policy"]
        == "hierarchy_sensitive"
    )

    assert (
        result["manual_review_required"]
        is True
    )


def test_class_policy_contains_expected_native_classes():
    assert CLASS_POLICIES == {
        "user":
            "standard_controlled",

        "group":
            "standard_controlled",

        "computer":
            "standard_controlled",

        "contact":
            "standard_controlled",

        "organizationalUnit":
            "hierarchy_sensitive",

        "container":
            "hierarchy_sensitive",

        "dnsNode":
            "high_risk_manual_review",

        "dnsZone":
            "high_risk_manual_review",
    }


def test_unknown_live_state_never_becomes_candidate():
    result = evaluate()

    assert (
        result["decision"]
        == "needs_live_revalidation"
    )

    assert (
        result["preflight_passed"]
        is False
    )

    assert (
        result["simulation_candidate"]
        is False
    )

    assert (
        result["execution_authorized"]
        is False
    )

    assert (
        result["write_authorized"]
        is False
    )


def test_partial_live_state_never_becomes_candidate():
    result = evaluate(
        target_parent_exists=True,
        target_parent_deleted=False,
        target_dn_exists=None,
    )

    assert (
        result["decision"]
        == "needs_live_revalidation"
    )

    assert (
        result["simulation_candidate"]
        is False
    )



def test_missing_parent_decision_does_not_require_collision_probe():
    result = evaluate(
        target_parent_exists=False,
        target_parent_deleted=False,
        target_dn_exists=None,
    )

    assert (
        result["decision"]
        == "needs_parent_restore_or_target_path"
    )

    assert (
        result["simulation_candidate"]
        is False
    )

    assert (
        result["execution_authorized"]
        is False
    )

    assert (
        result["write_authorized"]
        is False
    )
