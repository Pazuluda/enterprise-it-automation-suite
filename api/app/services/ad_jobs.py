from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.storage import load_json, save_json


class ADJobsError(Exception):
    pass


class ADJobsBadRequest(ADJobsError):
    pass


class ADJobsNotFound(ADJobsError):
    pass


class ADJobsConflict(ADJobsError):
    pass


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_request_id_from_payload(value) -> str:
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        for key in ["id", "request_id"]:
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()

    return ""


def create_ad_lookup_job(jobs_file: Path, payload: dict) -> tuple[dict, dict]:
    query = (
        payload.get("query")
        or payload.get("username")
        or payload.get("sam_account_name")
        or payload.get("sam")
        or ""
    )

    query = str(query).strip()
    created_by = payload.get("created_by") or "react-admin"

    if not query:
        raise ADJobsBadRequest("query est obligatoire")

    job_id = str(uuid4())

    job = {
        "id": job_id,
        "type": "ad_lookup",
        "status": "pending",
        "created_at": utc_now_iso(),
        "created_by": created_by,
        "query": query,
        "claimed_at": None,
        "claimed_by": None,
        "completed_at": None,
        "success": None,
        "message": "Recherche AD en attente agent",
        "output": "",
        "result": None,
        "details": None,
    }

    jobs = load_json(jobs_file, [])
    jobs.append(job)
    save_json(jobs_file, jobs)

    audit_event = {
        "action": "ad_lookup_job_created",
        "request_id": job_id,
        "actor": created_by,
        "message": f"Recherche AD créée pour {query}",
        "details": {
            "job_id": job_id,
            "query": query,
        },
    }

    return {
        "message": "Recherche AD créée",
        "job": job,
    }, audit_event


def get_ad_lookup_job(jobs_file: Path, job_id: str) -> dict:
    jobs = load_json(jobs_file, [])

    for job in jobs:
        if job.get("id") == job_id:
            return job

    raise ADJobsNotFound("Job recherche AD introuvable")


def get_pending_ad_lookup_jobs(jobs_file: Path) -> dict:
    jobs = load_json(jobs_file, [])

    pending = [
        job for job in jobs
        if job.get("status") == "pending"
    ]

    return {
        "count": len(pending),
        "jobs": pending,
    }


def claim_ad_lookup_job(jobs_file: Path, job_id: str, payload: dict) -> tuple[dict, dict]:
    jobs = load_json(jobs_file, [])

    for job in jobs:
        if job.get("id") == job_id:
            current_status = job.get("status")

            if current_status != "pending":
                raise ADJobsConflict(
                    f"Job recherche AD non disponible. Statut actuel : {current_status}"
                )

            agent_name = payload.get("agent_name") or "unknown-agent"

            job["status"] = "processing"
            job["claimed_at"] = utc_now_iso()
            job["claimed_by"] = agent_name
            job["message"] = "Recherche AD en cours sur agent"

            save_json(jobs_file, jobs)

            audit_event = {
                "action": "ad_lookup_job_claimed",
                "request_id": job_id,
                "actor": agent_name,
                "message": "Recherche AD prise en charge par un agent",
                "details": {
                    "job_id": job_id,
                    "query": job.get("query"),
                    "status": "processing",
                },
            }

            return {
                "message": "Job recherche AD pris en charge",
                "job": job,
            }, audit_event

    raise ADJobsNotFound("Job recherche AD introuvable")


def submit_ad_lookup_job_result(jobs_file: Path, job_id: str, payload: dict) -> tuple[dict, dict]:
    jobs = load_json(jobs_file, [])

    for job in jobs:
        if job.get("id") == job_id:
            success = bool(payload.get("success"))

            job["status"] = "completed" if success else "failed"
            job["completed_at"] = utc_now_iso()
            job["success"] = success
            job["message"] = payload.get("message") or ("Recherche AD terminée" if success else "Recherche AD en erreur")
            job["output"] = payload.get("output") or ""
            job["result"] = payload.get("result")
            job["details"] = payload.get("details")
            job["agent_name"] = payload.get("agent_name")

            save_json(jobs_file, jobs)

            audit_event = {
                "action": "ad_lookup_job_completed" if success else "ad_lookup_job_failed",
                "request_id": job_id,
                "actor": payload.get("agent_name") or "agent",
                "message": job["message"],
                "details": {
                    "job_id": job_id,
                    "query": job.get("query"),
                    "found": (job.get("result") or {}).get("found"),
                },
            }

            return {
                "message": "Résultat recherche AD enregistré",
                "job_id": job_id,
            }, audit_event

    raise ADJobsNotFound("Job recherche AD introuvable")


def create_ad_check_job(
    jobs_file: Path,
    requests_file: Path,
    payload: dict,
) -> tuple[dict, dict]:
    request_ids = payload.get("request_ids") or payload.get("ids") or []
    created_by = payload.get("created_by") or "react-admin"

    if not isinstance(request_ids, list):
        raise ADJobsBadRequest("request_ids doit être une liste")

    normalized_ids = []
    for item in request_ids:
        request_id = get_request_id_from_payload(item)
        if request_id and request_id not in normalized_ids:
            normalized_ids.append(request_id)

    if not normalized_ids:
        raise ADJobsBadRequest("Aucune demande sélectionnée")

    requests = load_json(requests_file, [])
    selected_requests = [
        request for request in requests
        if request.get("id") in normalized_ids
    ]

    if not selected_requests:
        raise ADJobsNotFound("Aucune demande correspondante trouvée")

    found_ids = {request.get("id") for request in selected_requests}
    missing_ids = [
        request_id for request_id in normalized_ids
        if request_id not in found_ids
    ]

    job_id = str(uuid4())
    now = utc_now_iso()

    job = {
        "id": job_id,
        "type": "ad_check",
        "status": "pending",
        "created_at": now,
        "created_by": created_by,
        "requested_count": len(normalized_ids),
        "selected_count": len(selected_requests),
        "missing_request_ids": missing_ids,
        "request_ids": normalized_ids,
        "requests": selected_requests,
        "claimed_at": None,
        "claimed_by": None,
        "completed_at": None,
        "success": None,
        "message": "Contrôle AD en attente agent",
        "output": "",
        "summary": None,
        "details": None,
    }

    jobs = load_json(jobs_file, [])
    jobs.append(job)
    save_json(jobs_file, jobs)

    audit_event = {
        "action": "ad_check_job_created",
        "request_id": job_id,
        "actor": created_by,
        "message": f"Contrôle AD créé pour {len(selected_requests)} demande(s)",
        "details": {
            "job_id": job_id,
            "request_ids": normalized_ids,
            "selected_count": len(selected_requests),
            "missing_request_ids": missing_ids,
        },
    }

    return {
        "message": "Contrôle AD créé",
        "job": job,
    }, audit_event


def list_ad_check_jobs(jobs_file: Path, limit: int = 200) -> dict:
    jobs = load_json(jobs_file, [])

    try:
        safe_limit = int(limit)
    except (TypeError, ValueError):
        safe_limit = 200

    safe_limit = max(1, min(safe_limit, 1000))

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


def get_ad_check_job(jobs_file: Path, job_id: str) -> dict:
    jobs = load_json(jobs_file, [])

    for job in jobs:
        if job.get("id") == job_id:
            return job

    raise ADJobsNotFound("Job contrôle AD introuvable")


def get_pending_ad_check_jobs(jobs_file: Path) -> dict:
    jobs = load_json(jobs_file, [])

    pending = [
        job for job in jobs
        if job.get("status") == "pending"
    ]

    return {
        "count": len(pending),
        "jobs": pending,
    }


def claim_ad_check_job(jobs_file: Path, job_id: str, payload: dict) -> tuple[dict, dict]:
    jobs = load_json(jobs_file, [])

    for job in jobs:
        if job.get("id") == job_id:
            current_status = job.get("status")

            if current_status != "pending":
                raise ADJobsConflict(
                    f"Job contrôle AD non disponible. Statut actuel : {current_status}"
                )

            agent_name = payload.get("agent_name") or "unknown-agent"

            job["status"] = "processing"
            job["claimed_at"] = utc_now_iso()
            job["claimed_by"] = agent_name
            job["message"] = "Contrôle AD en cours sur agent"

            save_json(jobs_file, jobs)

            audit_event = {
                "action": "ad_check_job_claimed",
                "request_id": job_id,
                "actor": agent_name,
                "message": "Contrôle AD pris en charge par un agent",
                "details": {
                    "job_id": job_id,
                    "status": "processing",
                },
            }

            return {
                "message": "Job contrôle AD pris en charge",
                "job": job,
            }, audit_event

    raise ADJobsNotFound("Job contrôle AD introuvable")


def submit_ad_check_job_result(jobs_file: Path, job_id: str, payload: dict) -> tuple[dict, dict]:
    jobs = load_json(jobs_file, [])

    for job in jobs:
        if job.get("id") == job_id:
            success = bool(payload.get("success"))

            job["status"] = "completed" if success else "failed"
            job["completed_at"] = utc_now_iso()
            job["success"] = success
            job["message"] = payload.get("message") or ("Contrôle AD terminé" if success else "Contrôle AD en erreur")
            job["output"] = payload.get("output") or ""
            job["summary"] = payload.get("summary")
            job["details"] = payload.get("details")
            job["agent_name"] = payload.get("agent_name")

            save_json(jobs_file, jobs)

            audit_event = {
                "action": "ad_check_job_completed" if success else "ad_check_job_failed",
                "request_id": job_id,
                "actor": payload.get("agent_name") or "agent",
                "message": job["message"],
                "details": {
                    "job_id": job_id,
                    "summary": job.get("summary"),
                },
            }

            return {
                "message": "Résultat contrôle AD enregistré",
                "job_id": job_id,
            }, audit_event

    raise ADJobsNotFound("Job contrôle AD introuvable")
