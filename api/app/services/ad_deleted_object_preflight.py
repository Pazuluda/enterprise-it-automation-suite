from __future__ import annotations

from typing import Any


CLASS_POLICIES = {
    "user": "standard_controlled",
    "group": "standard_controlled",
    "computer": "standard_controlled",
    "contact": "standard_controlled",
    "organizationalUnit": "hierarchy_sensitive",
    "container": "hierarchy_sensitive",
    "dnsNode": "high_risk_manual_review",
    "dnsZone": "high_risk_manual_review",
}


def _clean(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def evaluate_deleted_object_preflight(
    item: dict[str, Any],
    *,
    recycle_bin_enabled: bool,
    requested_new_name: str | None = None,
    requested_target_path: str | None = None,
    target_parent_exists: bool | None = None,
    target_parent_deleted: bool | None = None,
    target_dn_exists: bool | None = None,
) -> dict[str, Any]:
    object_guid = _clean(
        item.get("object_guid")
    )

    object_class = _clean(
        item.get("object_class")
    )

    native_parent = _clean(
        item.get("last_known_parent")
    )

    native_rdn = _clean(
        item.get("last_known_rdn")
    )

    explicit_name = _clean(
        requested_new_name
    )

    explicit_target = _clean(
        requested_target_path
    )

    effective_name = (
        explicit_name
        or native_rdn
    )

    effective_target = (
        explicit_target
        or native_parent
    )

    class_policy = CLASS_POLICIES.get(
        object_class,
        "unknown_manual_review",
    )

    manual_review_required = (
        class_policy
        != "standard_controlled"
    )

    decision = "candidate_preflight"

    if not object_guid:
        decision = (
            "blocked_invalid_identity"
        )

    elif item.get("is_deleted") is not True:
        decision = (
            "blocked_not_deleted"
        )

    elif item.get("is_recycled") is True:
        decision = (
            "blocked_recycled"
        )

    elif not recycle_bin_enabled:
        decision = (
            "blocked_recycle_bin_disabled"
        )

    elif (
        not effective_target
        and not effective_name
    ):
        decision = (
            "needs_target_path_and_new_name"
        )

    elif not effective_target:
        decision = (
            "needs_target_path"
        )

    elif not effective_name:
        decision = (
            "needs_new_name"
        )

    elif (
        target_parent_deleted is True
    ):
        decision = (
            "needs_parent_restore_or_target_path"
        )

    elif (
        target_parent_exists is False
        and not explicit_target
    ):
        decision = (
            "needs_parent_restore_or_target_path"
        )

    elif target_parent_exists is False:
        decision = (
            "needs_target_path"
        )

    elif (
        target_parent_exists is None
        or target_parent_deleted is None
        or target_dn_exists is None
    ):
        decision = (
            "needs_live_revalidation"
        )

    elif target_dn_exists is True:
        decision = (
            "blocked_name_collision"
        )

    preflight_passed = (
        decision
        == "candidate_preflight"
    )

    return {
        "decision":
            decision,

        "object_guid":
            object_guid or None,

        "object_class":
            object_class or None,

        "class_policy":
            class_policy,

        "manual_review_required":
            manual_review_required,

        "effective_new_name":
            effective_name or None,

        "effective_target_path":
            effective_target or None,

        "used_explicit_new_name":
            bool(explicit_name),

        "used_explicit_target_path":
            bool(explicit_target),

        "preflight_passed":
            preflight_passed,

        "simulation_candidate":
            preflight_passed,

        "execution_authorized":
            False,

        "write_authorized":
            False,
    }
