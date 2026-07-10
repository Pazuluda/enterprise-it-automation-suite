from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.core.storage import load_json, save_json


class RequestActionError(Exception):
    pass


class RequestActionBadRequest(RequestActionError):
    pass


class RequestActionNotFound(RequestActionError):
    pass


class RequestActionConflict(RequestActionError):
    pass


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def reset_requests(requests_file: Path, data_dir: Path, confirm: str) -> tuple[dict, dict]:
    if confirm != "RESET":
        raise RequestActionBadRequest("Confirmation invalide. Utilise exactement RESET.")

    requests = load_json(requests_file, [])
    deleted_count = len(requests)
    backup_file = None

    if deleted_count > 0:
        backup_file = data_dir / f"requests.backup.{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        save_json(backup_file, requests)

    save_json(requests_file, [])

    audit_event = {
        "action": "requests_reset",
        "actor": "admin",
        "message": "Réinitialisation des demandes",
        "details": {
            "deleted_count": deleted_count,
            "backup_file": backup_file.name if backup_file else None,
        },
    }

    return {
        "message": "Demandes réinitialisées",
        "deleted_count": deleted_count,
        "backup_file": backup_file.name if backup_file else None,
    }, audit_event


def retry_request(requests_file: Path, request_id: str) -> tuple[dict, dict]:
    requests = load_json(requests_file, [])

    for request in requests:
        if request.get("id") == request_id:
            request["status"] = "pending"
            request["retried_at"] = utc_now_iso()
            request["completed_at"] = None
            request["agent_result"] = None

            save_json(requests_file, requests)

            audit_event = {
                "action": "request_retried",
                "request_id": request_id,
                "actor": "admin",
                "message": "Demande remise en attente",
                "details": {
                    "status": "pending",
                },
            }

            return {
                "message": "Demande remise en attente",
                "request_id": request_id,
                "status": "pending",
            }, audit_event

    raise RequestActionNotFound("Demande introuvable")


def approve_request(
    requests_file: Path,
    request_id: str,
    approved_by: str,
    comment: str | None,
) -> tuple[dict, dict]:
    requests = load_json(requests_file, [])

    for request in requests:
        if request.get("id") == request_id:
            current_status = request.get("status")

            if current_status != "waiting_approval":
                raise RequestActionConflict(
                    f"Demande non validable. Statut actuel : {current_status}"
                )

            request["status"] = "pending"
            request["approved"] = True
            request["approved_by"] = approved_by
            request["approved_at"] = utc_now_iso()
            request["approval_comment"] = comment

            save_json(requests_file, requests)

            audit_event = {
                "action": "request_approved",
                "request_id": request_id,
                "actor": approved_by,
                "message": "Demande validée",
                "details": {
                    "comment": comment,
                    "status": "pending",
                },
            }

            return {
                "message": "Demande validée",
                "request_id": request_id,
                "status": "pending",
            }, audit_event

    raise RequestActionNotFound("Demande introuvable")


def reject_request(
    requests_file: Path,
    request_id: str,
    rejected_by: str,
    comment: str | None,
) -> tuple[dict, dict]:
    requests = load_json(requests_file, [])

    for request in requests:
        if request.get("id") == request_id:
            current_status = request.get("status")

            if current_status not in ["waiting_approval", "pending"]:
                raise RequestActionConflict(
                    f"Demande non rejetable. Statut actuel : {current_status}"
                )

            request["status"] = "rejected"
            request["approved"] = False
            request["rejected_by"] = rejected_by
            request["rejected_at"] = utc_now_iso()
            request["rejection_comment"] = comment

            save_json(requests_file, requests)

            audit_event = {
                "action": "request_rejected",
                "request_id": request_id,
                "actor": rejected_by,
                "message": "Demande rejetée",
                "details": {
                    "comment": comment,
                    "status": "rejected",
                },
            }

            return {
                "message": "Demande rejetée",
                "request_id": request_id,
                "status": "rejected",
            }, audit_event

    raise RequestActionNotFound("Demande introuvable")
