from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID, uuid4

from app.services.ad_deleted_object_restore_preflight import preflight_deleted_object_restore
from app.services.ad_deleted_object_restore_simulation import (
    DELETED_OBJECT_RESTORE_SIMULATION_CONTRACT_VERSION,
)
from app.services.ad_deleted_object_restore_simulation_persistence import (
    DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_CONTRACT_VERSION,
)

AD_DELETED_OBJECT_RESTORE_TICKET_CONTRACT_VERSION = "c9.5a4b-v1"
AD_DELETED_OBJECT_RESTORE_TICKET_TTL_SECONDS = 120
AD_DELETED_OBJECT_RESTORE_TICKET_LIVE_MAX_AGE_SECONDS = 120
AD_DELETED_OBJECT_RESTORE_TICKET_ENABLED = True
AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_TICKET_ROUTE_ENABLED = False
AD_DELETED_OBJECT_RESTORE_TICKET_JOB_CREATION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_CLAIM_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_RUNTIME_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_PRODUCTION_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_RESTORE_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_RESTORE_WHATIF_AUTHORIZED = False
AD_DELETED_OBJECT_RESTORE_TICKET_WRITE_PERFORMED = False


class AdDeletedObjectRestoreTicketError(ValueError):
    pass


@dataclass(frozen=True)
class AdDeletedObjectRestoreTicket:
    contract_version: str
    ticket_id: str
    ticket_digest: str
    state: str
    status: str
    source_simulation_job_id: str
    source_inventory_job_id: str
    source_live_job_id: str
    source_live_completed_at: str
    fresh_live_job_id: str
    fresh_live_sha256: str
    fresh_live_completed_at: str
    object_guid: str
    object_class: str
    class_policy: str
    effective_new_name: str
    effective_target_path: str
    issued_at: str
    expires_at: str
    one_shot_required: bool
    replay_consumed: bool
    persistence_enabled: bool
    route_enabled: bool
    job_creation_authorized: bool
    claim_authorized: bool
    runtime_authorized: bool
    production_authorized: bool
    restore_authorized: bool
    restore_whatif_authorized: bool
    write_performed: bool


def _clean(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _uuid(v: Any, field: str) -> str:
    try:
        return str(UUID(_clean(v)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise AdDeletedObjectRestoreTicketError(f"{field} invalid") from exc


def _ts(v: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(_clean(v).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdDeletedObjectRestoreTicketError(f"{field} invalid") from exc
    if parsed.tzinfo is None:
        raise AdDeletedObjectRestoreTicketError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _sha(v: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(v), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _fail_if(condition: bool, message: str) -> None:
    if condition:
        raise AdDeletedObjectRestoreTicketError(message)


def _global_gate() -> None:
    _fail_if(any((
        AD_DELETED_OBJECT_RESTORE_TICKET_PERSISTENCE_ENABLED,
        AD_DELETED_OBJECT_RESTORE_TICKET_ROUTE_ENABLED,
        AD_DELETED_OBJECT_RESTORE_TICKET_JOB_CREATION_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_CLAIM_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_RUNTIME_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_PRODUCTION_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_RESTORE_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_RESTORE_WHATIF_AUTHORIZED,
        AD_DELETED_OBJECT_RESTORE_TICKET_WRITE_PERFORMED,
    )), "dangerous restore ticket capability enabled")


def _jobs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("jobs") or data.get("items") or []
    _fail_if(not isinstance(data, list), "deleted-object job storage invalid")
    return [x for x in data if isinstance(x, dict)]


def assert_ad_deleted_object_restore_ticket_invariants(ticket: AdDeletedObjectRestoreTicket) -> None:
    _fail_if(not AD_DELETED_OBJECT_RESTORE_TICKET_ENABLED, "restore ticket contract disabled")
    _global_gate()
    _fail_if(ticket.contract_version != AD_DELETED_OBJECT_RESTORE_TICKET_CONTRACT_VERSION, "ticket contract mismatch")
    _uuid(ticket.ticket_id, "ticket_id")
    _uuid(ticket.object_guid, "object_guid")
    _fail_if(ticket.state != "restore_ticket_dormant" or ticket.status != "dormant", "ticket must remain dormant")
    _fail_if(ticket.one_shot_required is not True or ticket.replay_consumed is not False, "ticket one-shot invariant failed")
    for field in ("persistence_enabled", "route_enabled", "job_creation_authorized", "claim_authorized", "runtime_authorized", "production_authorized", "restore_authorized", "restore_whatif_authorized", "write_performed"):
        _fail_if(getattr(ticket, field) is not False, f"unsafe ticket flag: {field}")
    issued, expires = _ts(ticket.issued_at, "issued_at"), _ts(ticket.expires_at, "expires_at")
    _fail_if((expires - issued).total_seconds() != AD_DELETED_OBJECT_RESTORE_TICKET_TTL_SECONDS, "ticket TTL mismatch")
    payload = asdict(ticket)
    digest = payload.pop("ticket_digest")
    _fail_if(digest != _sha(payload), "ticket digest mismatch")


def build_ad_deleted_object_restore_ticket(
    *,
    deleted_object_jobs_path: Path,
    source_simulation_job: Mapping[str, Any],
    expected_simulation_job_id: str,
    fresh_live_job_id: str,
    current_mode: str,
    now: datetime | None = None,
) -> AdDeletedObjectRestoreTicket:
    _fail_if(not AD_DELETED_OBJECT_RESTORE_TICKET_ENABLED, "restore ticket contract disabled")
    _global_gate()
    _fail_if(current_mode != "Simulation", "restore ticket preparation is Simulation-only")
    _fail_if(not isinstance(source_simulation_job, Mapping), "source simulation job invalid")

    source_id = _uuid(source_simulation_job.get("id"), "source simulation job id")
    _fail_if(source_id != _uuid(expected_simulation_job_id, "expected simulation job id"), "source simulation job id mismatch")
    _fail_if(source_simulation_job.get("type") != "ad_admin", "source simulation job type invalid")
    _fail_if(source_simulation_job.get("status") != "prepared", "source simulation job not prepared")
    _fail_if(source_simulation_job.get("action") != "simulate_deleted_object_restore", "source simulation action invalid")
    _fail_if(source_simulation_job.get("claimed_at") is not None or source_simulation_job.get("claimed_by") is not None, "source simulation job already claimed")
    _fail_if(source_simulation_job.get("result") is not None, "source simulation result must be empty")

    p = source_simulation_job.get("payload")
    _fail_if(not isinstance(p, Mapping), "source simulation payload invalid")
    _fail_if(p.get("contract_version") != DELETED_OBJECT_RESTORE_SIMULATION_CONTRACT_VERSION, "source simulation contract mismatch")
    _fail_if(p.get("persistence_contract_version") != DELETED_OBJECT_RESTORE_SIMULATION_PERSISTENCE_CONTRACT_VERSION, "source simulation persistence contract mismatch")
    _fail_if(p.get("mode") != "Simulation" or p.get("policy_decision") != "candidate_preflight" or p.get("class_policy") != "standard_controlled", "source simulation policy invalid")
    for field in ("preflight_passed", "simulation_candidate", "simulation_job_authorized", "simulation_job_persistence_authorized"):
        _fail_if(p.get(field) is not True, f"source simulation missing {field}")
    for field in ("worker_claim_authorized", "worker_runtime_authorized", "production_authorized", "restore_cmdlet_authorized", "restore_whatif_authorized", "execution_authorized", "write_authorized", "restore_implemented", "restore_performed"):
        _fail_if(p.get(field) is not False, f"unsafe source simulation flag: {field}")
    _fail_if(p.get("manual_review_required") is not False, "source simulation manual review required")

    guid = _uuid(p.get("object_guid"), "object_guid")
    name, target = _clean(p.get("effective_new_name")), _clean(p.get("effective_target_path"))
    _fail_if(not name or not target, "source simulation target binding incomplete")
    source_live_id = _uuid(p.get("live_job_id"), "source_live_job_id")
    source_live_at = _ts(p.get("live_job_completed_at"), "source_live_completed_at")
    inventory_id = _uuid(p.get("source_inventory_job_id"), "source_inventory_job_id")
    object_class, class_policy = _clean(p.get("object_class")), _clean(p.get("class_policy"))
    fresh_id = _uuid(fresh_live_job_id, "fresh_live_job_id")

    try:
        preflight = preflight_deleted_object_restore(
            deleted_object_jobs_path,
            object_guid=guid,
            requested_new_name=name,
            requested_target_path=target,
            live_job_id=fresh_id,
            live_revalidation_max_age_seconds=AD_DELETED_OBJECT_RESTORE_TICKET_LIVE_MAX_AGE_SECONDS,
        )
    except ValueError as exc:
        raise AdDeletedObjectRestoreTicketError(str(exc)) from exc

    policy = preflight.get("policy") or {}
    _fail_if(
        preflight.get("read_only") is not True
        or preflight.get("live_revalidation_performed") is not True
        or preflight.get("restore_implemented") is not False
        or preflight.get("execution_authorized") is not False
        or preflight.get("write_authorized") is not False
        or policy.get("decision") != "candidate_preflight"
        or policy.get("preflight_passed") is not True
        or policy.get("simulation_candidate") is not True,
        "fresh preflight is not safe",
    )
    _fail_if(_clean(policy.get("effective_new_name")) != name, "fresh preflight new name mismatch")
    _fail_if(_clean(policy.get("effective_target_path")) != target, "fresh preflight target mismatch")
    _fail_if(_clean(policy.get("object_class")) != object_class, "fresh preflight class mismatch")

    matches = [j for j in _jobs(deleted_object_jobs_path) if _clean(j.get("id")) == fresh_id]
    _fail_if(len(matches) != 1, "fresh live job not found")
    fresh = matches[0]
    fresh_at = _ts(fresh.get("completed_at"), "fresh_live_completed_at")
    _fail_if(fresh_at <= source_live_at, "fresh live revalidation is not newer than source Simulation")
    fresh_result = fresh.get("result")
    _fail_if(not isinstance(fresh_result, Mapping), "fresh live result invalid")

    current = datetime.now(timezone.utc) if now is None else now
    _fail_if(current.tzinfo is None, "now must be timezone-aware")
    current = current.astimezone(timezone.utc)
    payload = {
        "contract_version": AD_DELETED_OBJECT_RESTORE_TICKET_CONTRACT_VERSION,
        "ticket_id": str(uuid4()),
        "state": "restore_ticket_dormant",
        "status": "dormant",
        "source_simulation_job_id": source_id,
        "source_inventory_job_id": inventory_id,
        "source_live_job_id": source_live_id,
        "source_live_completed_at": source_live_at.isoformat(),
        "fresh_live_job_id": fresh_id,
        "fresh_live_sha256": _sha(dict(fresh_result)),
        "fresh_live_completed_at": fresh_at.isoformat(),
        "object_guid": guid,
        "object_class": object_class,
        "class_policy": class_policy,
        "effective_new_name": name,
        "effective_target_path": target,
        "issued_at": current.isoformat(),
        "expires_at": (current + timedelta(seconds=AD_DELETED_OBJECT_RESTORE_TICKET_TTL_SECONDS)).isoformat(),
        "one_shot_required": True,
        "replay_consumed": False,
        "persistence_enabled": False,
        "route_enabled": False,
        "job_creation_authorized": False,
        "claim_authorized": False,
        "runtime_authorized": False,
        "production_authorized": False,
        "restore_authorized": False,
        "restore_whatif_authorized": False,
        "write_performed": False,
    }
    ticket = AdDeletedObjectRestoreTicket(ticket_digest=_sha(payload), **payload)
    assert_ad_deleted_object_restore_ticket_invariants(ticket)
    return ticket


__all__ = [
    "AD_DELETED_OBJECT_RESTORE_TICKET_CONTRACT_VERSION",
    "AD_DELETED_OBJECT_RESTORE_TICKET_TTL_SECONDS",
    "AD_DELETED_OBJECT_RESTORE_TICKET_LIVE_MAX_AGE_SECONDS",
    "AdDeletedObjectRestoreTicket",
    "AdDeletedObjectRestoreTicketError",
    "assert_ad_deleted_object_restore_ticket_invariants",
    "build_ad_deleted_object_restore_ticket",
]
