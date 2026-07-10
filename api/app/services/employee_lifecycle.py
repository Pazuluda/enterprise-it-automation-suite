from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.storage import load_json, save_json
from app.utils.naming import generate_username, generate_email


class EmployeeLifecycleError(Exception):
    pass


class EmployeeLifecycleBadRequest(EmployeeLifecycleError):
    pass


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def dump_model(payload) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()

    if hasattr(payload, "dict"):
        return payload.dict()

    return dict(payload)


def create_onboarding_request(
    requests_file: Path,
    templates_file: Path,
    payload,
) -> tuple[dict, dict]:
    templates = load_json(templates_file, {"departments": {}})
    departments = templates.get("departments", {})

    if payload.department not in departments:
        raise EmployeeLifecycleBadRequest("Département inconnu")

    department_config = departments[payload.department]
    roles = department_config.get("roles", {})

    if payload.job_title not in roles:
        raise EmployeeLifecycleBadRequest("Poste inconnu pour ce département")

    default_groups = department_config.get("default_groups", [])
    role_groups = roles[payload.job_title].get("groups", [])
    manual_groups = payload.manual_groups

    all_groups = sorted(set(default_groups + role_groups + manual_groups))

    request_id = str(uuid4())
    username = generate_username(payload.first_name, payload.last_name)
    email = generate_email(payload.first_name, payload.last_name)

    request_data = {
        "id": request_id,
        "type": "onboarding",
        "status": "waiting_approval",
        "created_at": utc_now_iso(),
        "input": dump_model(payload),
        "ad_payload": {
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "display_name": f"{payload.first_name} {payload.last_name}",
            "username": username,
            "email": email,
            "department": payload.department,
            "job_title": payload.job_title,
            "manager": payload.manager,
            "start_date": payload.start_date,
            "ou": department_config.get("default_ou"),
            "groups": all_groups,
        },
        "agent_result": None,
    }

    requests = load_json(requests_file, [])
    requests.append(request_data)
    save_json(requests_file, requests)

    audit_event = {
        "action": "request_created",
        "request_id": request_id,
        "actor": "api",
        "message": f"Demande onboarding créée pour {payload.first_name} {payload.last_name}",
        "details": {
            "username": username,
            "department": payload.department,
            "job_title": payload.job_title,
        },
    }

    return {
        "message": "Demande créée",
        "request": request_data,
    }, audit_event


def create_offboarding_request(
    requests_file: Path,
    payload,
) -> tuple[dict, dict]:
    requests = load_json(requests_file, [])

    request_id = str(uuid4())
    now = utc_now_iso()

    offboarding_payload = {
        "username": payload.username,
        "display_name": payload.display_name,
        "department": payload.department,
        "manager": payload.manager,
        "end_date": payload.end_date,
        "disable_account": payload.disable_account,
        "remove_groups": payload.remove_groups,
        "move_to_ou": payload.move_to_ou,
        "convert_mailbox": payload.convert_mailbox,
        "forward_to": payload.forward_to,
        "comment": payload.comment,
    }

    request = {
        "id": request_id,
        "type": "offboarding",
        "status": "waiting_approval",
        "created_at": now,
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "rejected_by": None,
        "rejected_at": None,
        "processing_by": None,
        "processing_at": None,
        "completed_at": None,
        "failed_at": None,
        "payload": dump_model(payload),
        "ad_payload": offboarding_payload,
        "agent_result": None,
    }

    requests.append(request)
    save_json(requests_file, requests)

    audit_event = {
        "action": "offboarding_request_created",
        "request_id": request_id,
        "actor": "api",
        "message": f"Demande offboarding créée pour {payload.display_name}",
        "details": {
            "username": payload.username,
            "display_name": payload.display_name,
            "department": payload.department,
            "end_date": payload.end_date,
        },
    }

    return {
        "message": "Demande offboarding créée",
        "request": request,
    }, audit_event


def create_modification_request(
    requests_file: Path,
    payload,
) -> tuple[dict, dict]:
    requests = load_json(requests_file, [])

    request_id = str(uuid4())
    now = utc_now_iso()

    modification_payload = {
        "username": payload.username,
        "display_name": payload.display_name,
        "department": payload.new_department or payload.current_department,
        "job_title": payload.new_job_title or payload.current_job_title,
        "current_department": payload.current_department,
        "current_job_title": payload.current_job_title,
        "new_department": payload.new_department,
        "new_job_title": payload.new_job_title,
        "manager": payload.manager,
        "effective_date": payload.effective_date,
        "add_groups": payload.add_groups,
        "remove_groups": payload.remove_groups,
        "move_to_ou": payload.move_to_ou,
        "comment": payload.comment,
    }

    request = {
        "id": request_id,
        "type": "modification",
        "status": "waiting_approval",
        "created_at": now,
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "rejected_by": None,
        "rejected_at": None,
        "processing_by": None,
        "processing_at": None,
        "completed_at": None,
        "failed_at": None,
        "payload": modification_payload,
        "ad_payload": modification_payload,
        "agent_result": None,
    }

    requests.append(request)
    save_json(requests_file, requests)

    audit_event = {
        "action": "modification_request_created",
        "request_id": request_id,
        "actor": "api",
        "message": f"Demande modification créée pour {payload.display_name}",
        "details": {
            "username": payload.username,
            "display_name": payload.display_name,
            "current_department": payload.current_department,
            "current_job_title": payload.current_job_title,
            "new_department": payload.new_department,
            "new_job_title": payload.new_job_title,
            "add_groups": payload.add_groups,
            "remove_groups": payload.remove_groups,
        },
    }

    return {
        "message": "Demande modification créée",
        "request": request,
    }, audit_event
