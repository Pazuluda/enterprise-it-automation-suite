from __future__ import annotations
from fastapi import HTTPException

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.storage import load_json, save_json


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
    "add_group_member",
    "remove_group_member",
    "move_object",
    "rename_object",
    "delete_object",
    "update_object_properties",
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

    if action in {"create_ou", "create_group"}:
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

        target_ou_dn = validate_dn(
            payload.get("target_ou_dn")
            or payload.get("targetOuDn")
            or payload.get("target_parent_dn")
            or payload.get("targetParentDn")
            or payload.get("ou_dn")
            or payload.get("ouDn"),
            "target_ou_dn"
        )

        temporary_password = clean_string(
            payload.get("temporary_password")
            or payload.get("temporaryPassword")
            or payload.get("password")
        )

        description = clean_string(payload.get("description") or "")
        enabled = bool(payload.get("enabled", True))

        if not temporary_password:
            raise ADAdminBadRequest("temporary_password est obligatoire")

        job_payload = {
            "action": action,
            "first_name": first_name,
            "last_name": last_name,
            "sam_account_name": sam_account_name,
            "target_ou_dn": target_ou_dn,
            "temporary_password": temporary_password,
            "description": description,
            "enabled": enabled,
        }

        audit_details.update({
            "target_ou_dn": target_ou_dn,
            "sam_account_name": sam_account_name,
            "first_name": first_name,
            "last_name": last_name,
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

        raw_properties = payload.get("properties") or {}

        if not isinstance(raw_properties, dict):
            raise HTTPException(status_code=400, detail="properties doit être un objet JSON")

        allowed_properties = {
            "description",
            "displayName",
            "display_name",
            "mail",
            "title",
            "department",
            "company",
            "telephoneNumber",
            "telephone_number",
            "office",
            "physicalDeliveryOfficeName",
        }

        normalized_properties = {}

        property_aliases = {
            "display_name": "displayName",
            "telephone_number": "telephoneNumber",
            "office": "physicalDeliveryOfficeName",
        }

        for key, value in raw_properties.items():
            if key not in allowed_properties:
                raise HTTPException(status_code=400, detail=f"Attribut non autorisé : {key}")

            normalized_key = property_aliases.get(key, key)

            if value is None:
                normalized_properties[normalized_key] = None
            else:
                normalized_properties[normalized_key] = clean_string(str(value))

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
        "job": job,
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
        "jobs": selected,
    }


def get_ad_admin_job(jobs_file: Path, job_id: str) -> dict:
    jobs = load_json(jobs_file, [])

    for job in jobs:
        if job.get("id") == job_id:
            return job

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

            job["status"] = "completed" if success else "failed"
            job["completed_at"] = utc_now_iso()
            job["success"] = success
            job["message"] = payload.get("message") or ("Action AD Admin terminée" if success else "Action AD Admin en erreur")
            job["output"] = payload.get("output") or ""
            job["result"] = payload.get("result")
            job["details"] = payload.get("details")
            job["agent_name"] = payload.get("agent_name")

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
                },
            }

            return {
                "message": "Résultat AD Admin enregistré",
                "job_id": job_id,
            }, audit_event

    raise ADAdminNotFound("Job AD Admin introuvable")
