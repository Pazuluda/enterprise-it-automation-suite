from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.storage import load_json, save_json


class ADExplorerError(Exception):
    pass


class ADExplorerBadRequest(ADExplorerError):
    pass


class ADExplorerNotFound(ADExplorerError):
    pass


class ADExplorerConflict(ADExplorerError):
    pass


ALLOWED_ACTIONS = {
    "list_ous",
    "list_ou_tree",
    "list_groups",
    "search_users",
    "get_user",
    "get_group_members",
}


QUERY_REQUIRED_ACTIONS = {
    "get_user",
    "get_group_members",
}


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def normalize_limit(value, default: int = 200) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = default

    return max(1, min(limit, 1000))


def create_ad_explorer_job(jobs_file: Path, payload: dict) -> tuple[dict, dict]:
    payload = payload or {}

    action = str(payload.get("action") or "").strip()
    query = str(payload.get("query") or "").strip()
    base_dn = str(payload.get("base_dn") or "").strip()
    created_by = payload.get("created_by") or "react-admin"

    if not action:
        raise ADExplorerBadRequest("action est obligatoire")

    if action not in ALLOWED_ACTIONS:
        raise ADExplorerBadRequest(f"Action AD Explorer inconnue : {action}")

    if action in QUERY_REQUIRED_ACTIONS and not query:
        raise ADExplorerBadRequest("query est obligatoire pour cette action")

    filters = payload.get("filters")
    if not isinstance(filters, dict):
        filters = {}

    job_id = str(uuid4())

    job = {
        "id": job_id,
        "type": "ad_explorer",
        "status": "pending",
        "created_at": utc_now_iso(),
        "created_by": created_by,
        "action": action,
        "query": query,
        "base_dn": base_dn,
        "limit": normalize_limit(payload.get("limit")),
        "recursive": bool(payload.get("recursive")),
        "include_disabled": bool(payload.get("include_disabled", True)),
        "filters": filters,
        "claimed_at": None,
        "claimed_by": None,
        "completed_at": None,
        "success": None,
        "message": "Exploration AD en attente agent",
        "output": "",
        "result": None,
        "details": None,
    }

    jobs = load_json(jobs_file, [])
    jobs.append(job)
    save_json(jobs_file, jobs)

    audit_event = {
        "action": "ad_explorer_job_created",
        "request_id": job_id,
        "actor": created_by,
        "message": f"Exploration AD créée : {action}",
        "details": {
            "job_id": job_id,
            "action": action,
            "query": query,
            "base_dn": base_dn,
            "limit": job["limit"],
        },
    }

    return {
        "message": "Exploration AD créée",
        "job": job,
    }, audit_event


def list_ad_explorer_jobs(jobs_file: Path, limit: int = 100) -> dict:
    jobs = load_json(jobs_file, [])
    safe_limit = normalize_limit(limit, default=100)

    sorted_jobs = sorted(
        jobs,
        key=lambda job: job.get("created_at") or "",
        reverse=True,
    )

    selected_jobs = sorted_jobs[:safe_limit]

    return {
        "count": len(jobs),
        "returned": len(selected_jobs),
        "jobs": selected_jobs,
    }


def get_ad_explorer_job(jobs_file: Path, job_id: str) -> dict:
    jobs = load_json(jobs_file, [])

    for job in jobs:
        if job.get("id") == job_id:
            return job

    raise ADExplorerNotFound("Job explorateur AD introuvable")


def get_pending_ad_explorer_jobs(jobs_file: Path) -> dict:
    jobs = load_json(jobs_file, [])

    pending = [
        job for job in jobs
        if job.get("status") == "pending"
    ]

    return {
        "count": len(pending),
        "jobs": pending,
    }


def claim_ad_explorer_job(jobs_file: Path, job_id: str, payload: dict) -> tuple[dict, dict]:
    jobs = load_json(jobs_file, [])
    payload = payload or {}

    for job in jobs:
        if job.get("id") == job_id:
            current_status = job.get("status")

            if current_status != "pending":
                raise ADExplorerConflict(
                    f"Job explorateur AD non disponible. Statut actuel : {current_status}"
                )

            agent_name = payload.get("agent_name") or "unknown-agent"

            job["status"] = "processing"
            job["claimed_at"] = utc_now_iso()
            job["claimed_by"] = agent_name
            job["message"] = "Exploration AD en cours sur agent"

            save_json(jobs_file, jobs)

            audit_event = {
                "action": "ad_explorer_job_claimed",
                "request_id": job_id,
                "actor": agent_name,
                "message": "Exploration AD prise en charge par un agent",
                "details": {
                    "job_id": job_id,
                    "action": job.get("action"),
                    "query": job.get("query"),
                    "status": "processing",
                },
            }

            return {
                "message": "Job explorateur AD pris en charge",
                "job": job,
            }, audit_event

    raise ADExplorerNotFound("Job explorateur AD introuvable")


def submit_ad_explorer_job_result(jobs_file: Path, job_id: str, payload: dict) -> tuple[dict, dict]:
    jobs = load_json(jobs_file, [])
    payload = payload or {}

    for job in jobs:
        if job.get("id") == job_id:
            success = bool(payload.get("success"))

            job["status"] = "completed" if success else "failed"
            job["completed_at"] = utc_now_iso()
            job["success"] = success
            job["message"] = payload.get("message") or ("Exploration AD terminée" if success else "Exploration AD en erreur")
            job["output"] = payload.get("output") or ""
            job["result"] = payload.get("result")
            job["details"] = payload.get("details")
            job["agent_name"] = payload.get("agent_name")

            save_json(jobs_file, jobs)

            result = job.get("result") or {}
            items = result.get("items") if isinstance(result, dict) else None

            audit_event = {
                "action": "ad_explorer_job_completed" if success else "ad_explorer_job_failed",
                "request_id": job_id,
                "actor": payload.get("agent_name") or "agent",
                "message": job["message"],
                "details": {
                    "job_id": job_id,
                    "action": job.get("action"),
                    "query": job.get("query"),
                    "count": len(items) if isinstance(items, list) else None,
                },
            }

            return {
                "message": "Résultat explorateur AD enregistré",
                "job_id": job_id,
            }, audit_event

    raise ADExplorerNotFound("Job explorateur AD introuvable")
