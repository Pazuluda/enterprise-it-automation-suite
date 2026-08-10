from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from datetime import datetime
import json
import os

from app.core.config import BASE_DIR, DATA_DIR, TEMPLATES_FILE, REQUESTS_FILE, AUDIT_FILE
from app.core.security import (
    require_api_key,
    require_roles,
    require_roles_or_api_key,
)

from app.core.identity_update_security import (
    require_identity_update_roles,
)
from app.core.storage import load_json, save_json
from app.services.audit import write_audit_log
from app.services.identity_update import (
    IdentityUpdateRequestConflict,
    IdentityUpdateRequestError,
    IdentityUpdateStatusUnavailable,
    create_identity_update_source_check_request as
    service_create_identity_update_source_check_request,
    get_identity_update_status as
    service_get_identity_update_status,
)
from app.services.requests import (
    RequestNotFound,
    get_request_by_id as service_get_request_by_id,
    list_requests as service_list_requests,
)
from app.services.templates import (
    TemplatesNotFound,
    delete_department_template as service_delete_department_template,
    delete_role_template as service_delete_role_template,
    get_templates as service_get_templates,
    upsert_department_template as service_upsert_department_template,
    upsert_role_template as service_upsert_role_template,
)
from app.services.employee_lifecycle import (
    EmployeeLifecycleBadRequest,
    create_modification_request as service_create_modification_request,
    create_offboarding_request as service_create_offboarding_request,
    create_onboarding_request as service_create_onboarding_request,
)

from app.services.ad_jobs import (
    ADJobsBadRequest,
    ADJobsConflict,
    ADJobsNotFound,
    claim_ad_check_job as service_claim_ad_check_job,
    claim_ad_lookup_job as service_claim_ad_lookup_job,
    create_ad_check_job as service_create_ad_check_job,
    create_ad_lookup_job as service_create_ad_lookup_job,
    get_ad_check_job as service_get_ad_check_job,
    get_ad_lookup_job as service_get_ad_lookup_job,
    get_pending_ad_check_jobs as service_get_pending_ad_check_jobs,
    get_pending_ad_lookup_jobs as service_get_pending_ad_lookup_jobs,
    list_ad_check_jobs as service_list_ad_check_jobs,
    submit_ad_check_job_result as service_submit_ad_check_job_result,
    submit_ad_lookup_job_result as service_submit_ad_lookup_job_result,
)
from app.services.ad_deleted_object_restore_preflight import preflight_deleted_object_restore
from app.services.ad_deleted_object_restore_simulation_persistence import (
    DeletedObjectRestoreSimulationPersistenceError,
    create_deleted_object_restore_simulation_record as
    service_create_deleted_object_restore_simulation_record,
)
from app.services.ad_explorer import (
    ADExplorerBadRequest,
    ADExplorerConflict,
    ADExplorerNotFound,
    claim_ad_explorer_job as service_claim_ad_explorer_job,
    create_ad_explorer_job as service_create_ad_explorer_job,
    get_ad_explorer_job as service_get_ad_explorer_job,
    get_pending_ad_explorer_jobs as service_get_pending_ad_explorer_jobs,
    list_ad_explorer_jobs as service_list_ad_explorer_jobs,
    submit_ad_explorer_job_result as service_submit_ad_explorer_job_result,
)
from app.services.ad_snapshot import (
    ADSnapshotBadRequest,
    ADSnapshotNotFound,
    get_ad_snapshot as service_get_ad_snapshot,
    receive_ad_snapshot as service_receive_ad_snapshot,
)
from app.services.ad_admin import (
    ADAdminBadRequest,
    ADAdminConflict,
    ADAdminNotFound,
    claim_ad_admin_job as service_claim_ad_admin_job,
    create_ad_admin_job as service_create_ad_admin_job,
    create_ldap_attribute_update_simulation_job as service_create_ldap_attribute_update_simulation_job,
    get_ad_admin_job as service_get_ad_admin_job,
    get_pending_ad_admin_jobs as service_get_pending_ad_admin_jobs,
    list_ad_admin_jobs as service_list_ad_admin_jobs,
    submit_ad_admin_job_result as service_submit_ad_admin_job_result,
)

from app.services.ldap_attribute_validation import (
    validate_reviewed_ldap_attribute_request as
    service_validate_reviewed_ldap_attribute_request,
)
from app.services.ldap_attribute_update import (
    LDAPAttributeUpdateBadRequest,
    normalize_ldap_attribute_update_request as
    service_normalize_ldap_attribute_update_request,
)


from app.services.worker_status import (
    WorkerStatusBadRequest,
    get_worker_status as service_get_worker_status,
    get_worker_events as service_get_worker_events,
    receive_worker_heartbeat as service_receive_worker_heartbeat,
)
from app.services.agent_runtime import (
    AgentRuntimeBadRequest,
    AgentRuntimeConflict,
    AgentRuntimeNotFound,
    AgentRuntimeStorageError,
    claim_request as service_claim_request,
    get_agent_config as service_get_agent_config,
    get_agent_status as service_get_agent_status,
    get_default_agent_config as service_get_default_agent_config,
    get_pending_requests as service_get_pending_requests,
    receive_agent_heartbeat as service_receive_agent_heartbeat,
    submit_agent_result as service_submit_agent_result,
    update_agent_config as service_update_agent_config,
)
from app.models import OnboardingRequest, AgentResult, ResetRequestsPayload, ClaimRequestPayload, ApprovalPayload, DepartmentTemplatePayload, RoleTemplatePayload, OffboardingRequest, ModificationRequest, LDAPAttributeValidationPayload, LDAPAttributeUpdateValidationPayload



from app.models import (
    LDAPHabSenioritySimulationPayload,
)

from app.services.ldap_hab_seniority_simulation import (
    LDAPHabSimulationBadRequest,
    normalize_ldap_hab_simulation_request as
    service_normalize_ldap_hab_simulation_request,
)

from app.services.acl_delegation_prewrite_ticket import (
    AclDelegationPrewriteTicketConflict,
    AclDelegationPrewriteTicketError,
    create_acl_delegation_prewrite_ticket,
)

from app.services.acl_delegation_prewrite_runtime import (
    AclDelegationPrewriteRuntimeConflict,
    AclDelegationPrewriteRuntimeError,
    claim_acl_delegation_prewrite_ticket_for_agent,
    complete_acl_delegation_prewrite_ticket,
    list_pending_acl_delegation_prewrite_tickets,
)

from app.services.acl_delegation_prewrite_status import (
    AclDelegationPrewriteStatusError,
    AclDelegationPrewriteStatusNotFound,
    get_acl_delegation_prewrite_status,
)

from app.services.acl_delegation_write_identity_envelope import (
    AclDelegationWriteIdentityEnvelopeError,
    build_acl_delegation_write_identity_envelope,
)
from app.services.acl_delegation_write_claim import (
    AclDelegationWriteClaimConflict,
    AclDelegationWriteClaimError,
    claim_acl_delegation_write_intent,
)
from app.services.acl_delegation_write_replay import (
    AclDelegationWriteReplayStorageError,
)

from app.services.acl_delegation_production_confirmation import (
    AclDelegationProductionConfirmationConflict,
    AclDelegationProductionConfirmationError,
)

from app.services.acl_delegation_production_confirmation_persistence import (
    AclDelegationProductionConfirmationPersistenceConflict,
    AclDelegationProductionConfirmationPersistenceError,
    persist_acl_delegation_production_confirmation,
)

from app.services.acl_delegation_production_preparation import (
    AclDelegationProductionPreparationError,
    prepare_acl_delegation_production_evidence,
)

from app.services.ldap_hab_seniority_simulation_persistence import (
    LDAPHabSimulationPersistenceError,
    create_ldap_hab_simulation_job_record as
    service_create_ldap_hab_simulation_job_record,
)


# PACK B2.4 — Dépendances RBAC du portail
PORTAL_READ_ACCESS = require_roles(
    "Viewer",
    "Operator",
    "ADAdmin",
    "SecurityAdmin",
    "Auditor",
    "UltraAdmin",
)

OPERATOR_ACCESS = require_roles(
    "Operator",
    "UltraAdmin",
)

AD_ACCESS = require_roles(
    "ADAdmin",
    "UltraAdmin",
)

SECURITY_ACCESS = require_roles(
    "SecurityAdmin",
    "UltraAdmin",
)

AUDIT_ACCESS = require_roles(
    "Auditor",
    "UltraAdmin",
)

SECURITY_OR_API_KEY_ACCESS = require_roles_or_api_key(
    "SecurityAdmin",
    "UltraAdmin",
)

AGENT_MODE_READ_OR_API_KEY_ACCESS = require_roles_or_api_key(
    "ADAdmin",
    "SecurityAdmin",
    "UltraAdmin",
)


IDENTITY_UPDATE_STATUS_ACCESS = (
    require_identity_update_roles(
        "UltraAdmin",
    )
)


APP_VERSION = (BASE_DIR.parent / "VERSION").read_text(encoding="utf-8").strip()
if not APP_VERSION:
    raise RuntimeError("VERSION EITAS vide.")

app = FastAPI(
    title="Enterprise IT Automation Suite",
    description="API MVP pour gérer les arrivées utilisateurs et les demandes Active Directory.",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# STEP176_CORS_REACT_DEV
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://10.10.10.11:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://10.10.10.11:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

AGENT_STATUS_FILE = DATA_DIR / "agent-status.json"
WORKER_STATUS_FILE = DATA_DIR / "worker-status.json"
WORKER_EVENTS_FILE = DATA_DIR / "worker-events.jsonl"
AGENT_CONFIG_FILE = DATA_DIR / "agent-config.json"
AD_CHECK_JOBS_FILE = DATA_DIR / "ad-check-jobs.json"
AD_LOOKUP_JOBS_FILE = DATA_DIR / "ad-lookup-jobs.json"
AD_EXPLORER_JOBS_FILE = DATA_DIR / "ad-explorer-jobs.json"
AD_SNAPSHOT_FILE = DATA_DIR / "ad-snapshot.json"
AD_SNAPSHOT_EXPECTED_BASE_DN = os.getenv(
    "EITAS_AD_SNAPSHOT_BASE_DN",
    "OU=EITAS,DC=API,DC=LOCAL",
)
AD_SNAPSHOT_STALE_AFTER_SECONDS = max(
    3,
    int(os.getenv("EITAS_AD_SNAPSHOT_STALE_AFTER_SECONDS", "15")),
)
AD_DOMAIN_CATALOG_FILE = (
    DATA_DIR / "ad-domain-catalog.json"
)

AD_DOMAIN_CATALOG_EXPECTED_BASE_DN = os.getenv(
    "EITAS_AD_DOMAIN_CATALOG_BASE_DN",
    "DC=API,DC=LOCAL",
)

AD_DOMAIN_CATALOG_STALE_AFTER_SECONDS = max(
    5,
    int(
        os.getenv(
            "EITAS_AD_DOMAIN_CATALOG_STALE_AFTER_SECONDS",
            "30",
        )
    ),
)

AD_ADMIN_JOBS_FILE = DATA_DIR / "ad-admin-jobs.json"
ACL_DELEGATION_WRITE_REPLAY_FILE = (
    DATA_DIR / "acl-delegation-write-replay.json"
)

IDENTITY_UPDATE_STATUS_FILE = Path(
    os.getenv(
        "EITAS_IDENTITY_UPDATE_STATUS_FILE",
        "/var/lib/eitas/identity-update/status.json",
    )
).resolve()

IDENTITY_UPDATE_SOURCE_CHECK_REQUEST_FILE = Path(
    os.getenv(
        "EITAS_IDENTITY_UPDATE_SOURCE_CHECK_REQUEST_FILE",
        "/var/lib/eitas/identity-update/requests/upstream-check.json",
    )
).resolve()



@app.get("/app", include_in_schema=False)
@app.get("/app/{full_path:path}", include_in_schema=False)
def serve_react_app(full_path: str = ""):
    react_index = BASE_DIR / "static" / "app" / "index.html"

    if not react_index.exists():
        raise HTTPException(status_code=404, detail="React build introuvable")

    return FileResponse(react_index)


@app.get("/portal", include_in_schema=False)
@app.get("/portal/{full_path:path}", include_in_schema=False)
def serve_react_portal(full_path: str = ""):
    return serve_react_app(full_path)

@app.get("/docs-local", include_in_schema=False)
def docs_local():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enterprise IT Automation Suite - Docs</title>
        <link rel="stylesheet" type="text/css" href="/static/swagger/swagger-ui.css">
        <style>
            html, body {
                margin: 0;
                padding: 0;
                background: white;
            }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="/static/swagger/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {
                SwaggerUIBundle({
                    url: "/openapi.json",
                    dom_id: "#swagger-ui",
                    deepLinking: true,
                    layout: "BaseLayout"
                });
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/")
def root():
    return {
        "name": "Enterprise IT Automation Suite",
        "version": APP_VERSION,
        "status": "running"
    }


@app.get("/api/templates")
def get_templates(
    api_key: None = Depends(PORTAL_READ_ACCESS),
):
    return service_get_templates(TEMPLATES_FILE)


@app.post("/api/onboarding/request")
def create_onboarding_request(payload: OnboardingRequest, api_key: None = Depends(OPERATOR_ACCESS)):
    try:
        response, audit_event = service_create_onboarding_request(
            REQUESTS_FILE,
            TEMPLATES_FILE,
            payload,
        )
    except EmployeeLifecycleBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.get("/api/requests")
def list_requests(api_key: None = Depends(PORTAL_READ_ACCESS)):
    return service_list_requests(REQUESTS_FILE)


@app.get("/api/requests/{request_id}")
def get_request_by_id(request_id: str, api_key: None = Depends(PORTAL_READ_ACCESS)):
    try:
        return service_get_request_by_id(REQUESTS_FILE, request_id)
    except RequestNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/agent/config")
def get_agent_config(api_key: None = Depends(SECURITY_OR_API_KEY_ACCESS)):
    try:
        return service_get_agent_config(AGENT_CONFIG_FILE)
    except AgentRuntimeStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/agent/config")
def update_agent_config(payload: dict, api_key: None = Depends(SECURITY_OR_API_KEY_ACCESS)):
    try:
        response, audit_event = service_update_agent_config(AGENT_CONFIG_FILE, payload)
    except AgentRuntimeBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except AgentRuntimeStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if audit_event:
        write_audit_log(**audit_event)

    return response

@app.post("/api/agent/heartbeat")
def receive_agent_heartbeat(payload: dict, api_key: None = Depends(require_api_key)):
    return service_receive_agent_heartbeat(AGENT_STATUS_FILE, payload)

@app.get("/api/agent/status")
def get_agent_status(api_key: None = Depends(SECURITY_OR_API_KEY_ACCESS)):
    try:
        return service_get_agent_status(AGENT_STATUS_FILE)
    except AgentRuntimeStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/agent/worker-heartbeat")
def receive_worker_heartbeat(payload: dict = Body(...), api_key: None = Depends(require_api_key)):
    try:
        return service_receive_worker_heartbeat(WORKER_STATUS_FILE, payload, WORKER_EVENTS_FILE)
    except WorkerStatusBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/admin/worker-status")
def get_worker_status(api_key: None = Depends(SECURITY_ACCESS)):
    return service_get_worker_status(WORKER_STATUS_FILE, WORKER_EVENTS_FILE)


@app.get("/api/admin/worker-events")
def get_worker_events(limit: int = 100, api_key: None = Depends(SECURITY_ACCESS)):
    return service_get_worker_events(WORKER_EVENTS_FILE, limit=limit)

@app.get("/api/agent/pending")
def get_pending_requests(api_key: None = Depends(require_api_key)):
    return service_get_pending_requests(REQUESTS_FILE)

@app.post("/api/agent/claim/{request_id}")
def claim_request(request_id: str, payload: ClaimRequestPayload, api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_claim_request(
            REQUESTS_FILE,
            request_id,
            payload.agent_name or "unknown-agent",
        )
    except AgentRuntimeConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except AgentRuntimeNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response

@app.post("/api/agent/result/{request_id}")
def submit_agent_result(request_id: str, result: AgentResult, api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_submit_agent_result(
            REQUESTS_FILE,
            request_id,
            result.model_dump(),
        )
    except AgentRuntimeNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response

@app.post("/api/admin/requests/reset")
def reset_requests(payload: ResetRequestsPayload, api_key: None = Depends(OPERATOR_ACCESS)):
    if payload.confirm != "RESET":
        raise HTTPException(
            status_code=400,
            detail="Confirmation invalide. Utilise exactement RESET."
        )

    requests = load_json(REQUESTS_FILE, [])
    deleted_count = len(requests)
    backup_file = None

    if deleted_count > 0:
        backup_file = DATA_DIR / f"requests.backup.{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        save_json(backup_file, requests)

    save_json(REQUESTS_FILE, [])

    write_audit_log(
        action="requests_reset",
        actor="admin",
        message="Réinitialisation des demandes",
        details={
            "deleted_count": deleted_count,
            "backup_file": backup_file.name if backup_file else None
        }
    )

    return {
        "message": "Demandes réinitialisées",
        "deleted_count": deleted_count,
        "backup_file": backup_file.name if backup_file else None
    }


@app.post("/api/admin/requests/{request_id}/retry")
def retry_request(request_id: str, api_key: None = Depends(OPERATOR_ACCESS)):
    requests = load_json(REQUESTS_FILE, [])
    found = False

    for request in requests:
        if request.get("id") == request_id:
            found = True
            request["status"] = "pending"
            request["retried_at"] = datetime.utcnow().isoformat() + "Z"
            request["completed_at"] = None
            request["agent_result"] = None
            break

    if not found:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    save_json(REQUESTS_FILE, requests)

    write_audit_log(
        action="request_retried",
        request_id=request_id,
        actor="admin",
        message="Demande remise en attente",
        details={
            "status": "pending"
        }
    )

    return {
        "message": "Demande remise en attente",
        "request_id": request_id,
        "status": "pending"
    }


@app.post("/api/admin/requests/{request_id}/approve")
def approve_request(request_id: str, payload: ApprovalPayload, api_key: None = Depends(OPERATOR_ACCESS)):
    requests = load_json(REQUESTS_FILE, [])

    for request in requests:
        if request.get("id") == request_id:
            current_status = request.get("status")

            if current_status != "waiting_approval":
                raise HTTPException(
                    status_code=409,
                    detail=f"Demande non validable. Statut actuel : {current_status}"
                )

            request["status"] = "pending"
            request["approved"] = True
            request["approved_by"] = payload.approved_by
            request["approved_at"] = datetime.utcnow().isoformat() + "Z"
            request["approval_comment"] = payload.comment

            save_json(REQUESTS_FILE, requests)

            write_audit_log(
                action="request_approved",
                request_id=request_id,
                actor=payload.approved_by,
                message="Demande validée",
                details={
                    "comment": payload.comment,
                    "status": "pending"
                }
            )

            return {
                "message": "Demande validée",
                "request_id": request_id,
                "status": "pending"
            }

    raise HTTPException(status_code=404, detail="Demande introuvable")


@app.post("/api/admin/requests/{request_id}/reject")
def reject_request(request_id: str, payload: ApprovalPayload, api_key: None = Depends(OPERATOR_ACCESS)):
    requests = load_json(REQUESTS_FILE, [])

    for request in requests:
        if request.get("id") == request_id:
            current_status = request.get("status")

            if current_status not in ["waiting_approval", "pending"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Demande non rejetable. Statut actuel : {current_status}"
                )

            request["status"] = "rejected"
            request["approved"] = False
            request["rejected_by"] = payload.approved_by
            request["rejected_at"] = datetime.utcnow().isoformat() + "Z"
            request["rejection_comment"] = payload.comment

            save_json(REQUESTS_FILE, requests)

            write_audit_log(
                action="request_rejected",
                request_id=request_id,
                actor=payload.approved_by,
                message="Demande rejetée",
                details={
                    "comment": payload.comment,
                    "status": "rejected"
                }
            )

            return {
                "message": "Demande rejetée",
                "request_id": request_id,
                "status": "rejected"
            }

    raise HTTPException(status_code=404, detail="Demande introuvable")




def get_request_id_from_payload(value):
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        for key in ["id", "request_id"]:
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item.strip()

    return ""




@app.post("/api/ad-lookup/jobs")
def create_ad_lookup_job(payload: dict = Body(...), api_key: None = Depends(AD_ACCESS)):
    try:
        response, audit_event = service_create_ad_lookup_job(AD_LOOKUP_JOBS_FILE, payload)
    except ADJobsBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.get("/api/ad-lookup/jobs/{job_id}")
def get_ad_lookup_job(job_id: str, api_key: None = Depends(AD_ACCESS)):
    try:
        return service_get_ad_lookup_job(AD_LOOKUP_JOBS_FILE, job_id)
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/agent/ad-lookup/pending")
def get_pending_ad_lookup_jobs(api_key: None = Depends(require_api_key)):
    return service_get_pending_ad_lookup_jobs(AD_LOOKUP_JOBS_FILE)


@app.post("/api/agent/ad-lookup/claim/{job_id}")
def claim_ad_lookup_job(job_id: str, payload: dict = Body(default={}), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_claim_ad_lookup_job(AD_LOOKUP_JOBS_FILE, job_id, payload)
    except ADJobsConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.post("/api/agent/ad-lookup/result/{job_id}")
def submit_ad_lookup_job_result(job_id: str, payload: dict = Body(...), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_submit_ad_lookup_job_result(AD_LOOKUP_JOBS_FILE, job_id, payload)
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.post("/api/ad-check/jobs")
def create_ad_check_job(payload: dict = Body(...), api_key: None = Depends(AD_ACCESS)):
    try:
        response, audit_event = service_create_ad_check_job(
            AD_CHECK_JOBS_FILE,
            REQUESTS_FILE,
            payload,
        )
    except ADJobsBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.get("/api/ad-check/jobs")
def list_ad_check_jobs(limit: int = 200, api_key: None = Depends(AD_ACCESS)):
    return service_list_ad_check_jobs(AD_CHECK_JOBS_FILE, limit)


@app.get("/api/ad-check/jobs/{job_id}")
def get_ad_check_job(job_id: str, api_key: None = Depends(AD_ACCESS)):
    try:
        return service_get_ad_check_job(AD_CHECK_JOBS_FILE, job_id)
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/agent/ad-check/pending")
def get_pending_ad_check_jobs(api_key: None = Depends(require_api_key)):
    return service_get_pending_ad_check_jobs(AD_CHECK_JOBS_FILE)


@app.post("/api/agent/ad-check/claim/{job_id}")
def claim_ad_check_job(job_id: str, payload: dict = Body(default={}), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_claim_ad_check_job(AD_CHECK_JOBS_FILE, job_id, payload)
    except ADJobsConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.post("/api/agent/ad-check/result/{job_id}")
def submit_ad_check_job_result(job_id: str, payload: dict = Body(...), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_submit_ad_check_job_result(AD_CHECK_JOBS_FILE, job_id, payload)
    except ADJobsNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)
    return response


@app.post("/api/agent/ad-snapshot")
def receive_ad_snapshot(
    payload: dict = Body(...),
    api_key: None = Depends(require_api_key),
):
    try:
        return service_receive_ad_snapshot(
            AD_SNAPSHOT_FILE,
            payload,
            expected_base_dn=AD_SNAPSHOT_EXPECTED_BASE_DN,
        )
    except ADSnapshotBadRequest as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.get("/api/ad-snapshot")
def get_ad_snapshot(
    api_key: None = Depends(AD_ACCESS),
):
    try:
        return service_get_ad_snapshot(
            AD_SNAPSHOT_FILE,
            stale_after_seconds=AD_SNAPSHOT_STALE_AFTER_SECONDS,
        )
    except ADSnapshotNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@app.post(
    "/api/agent/ad-domain-catalog"
)
def receive_ad_domain_catalog(
    payload: dict = Body(...),
    api_key: None = Depends(
        require_api_key
    ),
):
    try:
        response = service_receive_ad_snapshot(
            AD_DOMAIN_CATALOG_FILE,
            payload,
            expected_base_dn=(
                AD_DOMAIN_CATALOG_EXPECTED_BASE_DN
            ),
        )

        response["message"] = (
            "Catalogue Active Directory "
            "du domaine enregistré."
        )

        return response

    except ADSnapshotBadRequest as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.get(
    "/api/ad-domain-catalog"
)
def get_ad_domain_catalog(
    api_key: None = Depends(AD_ACCESS),
):
    try:
        return service_get_ad_snapshot(
            AD_DOMAIN_CATALOG_FILE,
            stale_after_seconds=(
                AD_DOMAIN_CATALOG_STALE_AFTER_SECONDS
            ),
        )

    except ADSnapshotNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


def _c9_authenticated_actor(identity) -> str:
    if isinstance(identity, dict):
        for key in (
            "preferred_username",
            "username",
            "email",
            "sub",
        ):
            value = str(
                identity.get(key)
                or ""
            ).strip()

            if value:
                return value[:128]

    for attribute in (
        "preferred_username",
        "username",
        "email",
        "sub",
    ):
        value = str(
            getattr(
                identity,
                attribute,
                "",
            )
            or ""
        ).strip()

        if value:
            return value[:128]

    return "authenticated-ad-user"


@app.post(
    "/api/ad-explorer/deleted-objects/preflight"
)
def preflight_ad_deleted_object_restore(
    payload: dict = Body(...),
    api_key: None = Depends(AD_ACCESS),
):
    object_guid = str(
        payload.get("object_guid")
        or ""
    ).strip()

    requested_new_name = (
        payload.get("new_name")
    )

    requested_target_path = (
        payload.get("target_path")
    )

    live_job_id = (
        payload.get("live_job_id")
    )

    try:
        return preflight_deleted_object_restore(
            DATA_DIR
            / "ad-explorer-jobs.json",
            object_guid=object_guid,
            requested_new_name=(
                requested_new_name
            ),
            requested_target_path=(
                requested_target_path
            ),
            live_job_id=(
                live_job_id
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/ad-explorer/deleted-objects/"
    "restore-simulation/prepare"
)
def prepare_ad_deleted_object_restore_simulation(
    payload: dict = Body(...),
    identity=Depends(AD_ACCESS),
):
    config = (
        _eitas_agent_mode_load_config()
    )

    mode = (
        _eitas_agent_mode_normalize(
            config.get("mode")
            or config.get("Mode")
            or "Simulation"
        )
    )

    simulation_payload = dict(
        payload or {}
    )

    simulation_payload[
        "created_by"
    ] = _c9_authenticated_actor(
        identity
    )

    try:
        response, audit_event = (
            service_create_deleted_object_restore_simulation_record(
                AD_ADMIN_JOBS_FILE,
                AD_EXPLORER_JOBS_FILE,
                simulation_payload,
                agent_mode=mode,
            )
        )

    except DeletedObjectRestoreSimulationPersistenceError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    write_audit_log(
        **audit_event
    )

    return response


@app.post("/api/ad-explorer/jobs")
def create_ad_explorer_job(payload: dict = Body(...), api_key: None = Depends(AD_ACCESS)):
    try:
        response, audit_event = service_create_ad_explorer_job(AD_EXPLORER_JOBS_FILE, payload)
    except ADExplorerBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.get("/api/ad-explorer/jobs")
def list_ad_explorer_jobs(limit: int = 100, api_key: None = Depends(AD_ACCESS)):
    return service_list_ad_explorer_jobs(AD_EXPLORER_JOBS_FILE, limit)


@app.get("/api/ad-explorer/jobs/{job_id}")
def get_ad_explorer_job(job_id: str, api_key: None = Depends(AD_ACCESS)):
    try:
        return service_get_ad_explorer_job(AD_EXPLORER_JOBS_FILE, job_id)
    except ADExplorerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/agent/ad-explorer/pending")
def get_pending_ad_explorer_jobs(api_key: None = Depends(require_api_key)):
    return service_get_pending_ad_explorer_jobs(AD_EXPLORER_JOBS_FILE)


@app.post("/api/agent/ad-explorer/claim/{job_id}")
def claim_ad_explorer_job(job_id: str, payload: dict = Body(default={}), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_claim_ad_explorer_job(AD_EXPLORER_JOBS_FILE, job_id, payload)
    except ADExplorerConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ADExplorerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.post("/api/agent/ad-explorer/result/{job_id}")
def submit_ad_explorer_job_result(job_id: str, payload: dict = Body(...), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_submit_ad_explorer_job_result(AD_EXPLORER_JOBS_FILE, job_id, payload)
    except ADExplorerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.post("/api/ad-explorer/ldap/validate")
def validate_ldap_attribute_request(
    payload: LDAPAttributeValidationPayload,
    api_key: None = Depends(AD_ACCESS),
):
    return service_validate_reviewed_ldap_attribute_request(
        attribute_name=payload.attribute_name,
        object_class=payload.object_class,
        operation=payload.operation,
        value=payload.value,
    ).to_dict()



@app.post(
    "/api/ad-explorer/ldap/"
    "hab-seniority/validate"
)
def validate_ldap_hab_seniority_simulation_payload(
    payload: LDAPHabSenioritySimulationPayload,
    api_key: None = Depends(AD_ACCESS),
):
    config = _eitas_agent_mode_load_config()

    mode = _eitas_agent_mode_normalize(
        config.get("mode")
        or config.get("Mode")
        or "Simulation"
    )

    try:
        request = (
            service_normalize_ldap_hab_simulation_request(
                payload.model_dump(),
                mode,
            )
        )
    except LDAPHabSimulationBadRequest as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return request.to_dict()


@app.post(
    "/api/ad-explorer/ldap/"
    "hab-seniority/jobs"
)
def create_ldap_hab_seniority_simulation_job_api(
    payload: LDAPHabSenioritySimulationPayload,
    api_key: None = Depends(AD_ACCESS),
):
    config = _eitas_agent_mode_load_config()

    mode = _eitas_agent_mode_normalize(
        config.get("mode")
        or config.get("Mode")
        or "Simulation"
    )

    try:
        response, audit_event = (
            service_create_ldap_hab_simulation_job_record(
                AD_ADMIN_JOBS_FILE,
                payload.model_dump(),
                mode,
            )
        )
    except LDAPHabSimulationPersistenceError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    write_audit_log(**audit_event)

    return response


@app.post("/api/ad-explorer/ldap/update/validate")
def validate_ldap_attribute_update_payload(
    payload: LDAPAttributeUpdateValidationPayload,
    api_key: None = Depends(AD_ACCESS),
):
    try:
        return service_normalize_ldap_attribute_update_request(
            payload.model_dump()
        ).to_dict()
    except LDAPAttributeUpdateBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/ad-explorer/ldap/update/jobs")
def create_ldap_attribute_update_simulation_job_api(
    payload: LDAPAttributeUpdateValidationPayload,
    api_key: None = Depends(AD_ACCESS),
):
    config = _eitas_agent_mode_load_config()
    mode = _eitas_agent_mode_normalize(
        config.get("mode") or
        config.get("Mode") or
        "Simulation"
    )

    try:
        response, audit_event = (
            service_create_ldap_attribute_update_simulation_job(
                AD_ADMIN_JOBS_FILE,
                payload.model_dump(),
                mode,
            )
        )
    except LDAPAttributeUpdateBadRequest as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    write_audit_log(**audit_event)

    return response


@app.post(
    "/api/ad-admin/acl-delegation/production-preparation"
)
def prepare_acl_delegation_production_api(
    payload: dict = Body(...),
    identity=Depends(AD_ACCESS),
):
    try:
        preparation = (
            prepare_acl_delegation_production_evidence(
                ad_admin_jobs_file=(
                    AD_ADMIN_JOBS_FILE
                ),
                ad_explorer_jobs_file=(
                    AD_EXPLORER_JOBS_FILE
                ),
                payload=payload,
            )
        )

    except AclDelegationProductionPreparationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    actor_username = str(
        identity.username
        or identity.subject
        or ""
    ).strip()

    write_audit_log(
        action=(
            "acl_delegation_production_preparation_built"
        ),
        request_id=(
            preparation.evidence_digest
        ),
        actor=actor_username,
        message=(
            "Preparation Production ACL construite "
            "depuis les preuves serveur sans "
            "autorisation d'ecriture"
        ),
        details={
            "contract_version": (
                preparation.contract_version
            ),
            "state": preparation.state,

            "simulation_job_id": (
                preparation.simulation_job_id
            ),
            "security_descriptor_job_id": (
                preparation.security_descriptor_job_id
            ),

            "target_dn": (
                preparation.target_dn
            ),
            "target_object_guid": (
                preparation.target_object_guid
            ),

            "principal_sid": (
                preparation.principal_sid
            ),

            "dacl_sddl_sha256": (
                preparation.dacl_sddl_sha256
            ),
            "acl_fingerprint": (
                preparation.acl_fingerprint
            ),
            "evidence_digest": (
                preparation.evidence_digest
            ),

            "trusted_evidence_loaded": True,
            "binding_validated": True,
            "human_confirmation_validated": False,
            "replay_consumed": False,
            "claim_created": False,

            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    )

    return {
        "contract_version": (
            preparation.contract_version
        ),
        "state": preparation.state,

        "evidence": {
            "simulation_job_id": (
                preparation.simulation_job_id
            ),
            "security_descriptor_job_id": (
                preparation.security_descriptor_job_id
            ),
            "evidence_digest": (
                preparation.evidence_digest
            ),
            "trusted_source": (
                preparation.trusted_source
            ),
            "trusted_evidence_loaded": True,
            "binding_validated": True,
        },

        "target": {
            "dn": preparation.target_dn,
            "object_guid": (
                preparation.target_object_guid
            ),
        },

        "principal": {
            "identity": (
                preparation.principal_identity
            ),
            "dn": preparation.principal_dn,
            "sid": preparation.principal_sid,
        },

        "ace": {
            "access_control_type": (
                preparation.access_control_type
            ),
            "rights": list(
                preparation.rights
            ),
            "inheritance_type": (
                preparation.inheritance_type
            ),
            "object_type_guid": (
                preparation.object_type_guid
            ),
            "inherited_object_type_guid": (
                preparation.inherited_object_type_guid
            ),
        },

        "dacl": {
            "dacl_sddl_sha256": (
                preparation.dacl_sddl_sha256
            ),
            "acl_fingerprint": (
                preparation.acl_fingerprint
            ),
        },

        "freshness": {
            "simulation_completed_at": (
                preparation.simulation_completed_at
            ),
            "security_descriptor_completed_at": (
                preparation.security_descriptor_completed_at
            ),
            "simulation_age_seconds": (
                preparation.simulation_age_seconds
            ),
            "security_descriptor_age_seconds": (
                preparation.security_descriptor_age_seconds
            ),
        },

        "confirmation_requirements": {
            "confirm_object_dn": (
                preparation.required_confirm_object_dn
            ),
            "confirmation_phrase": (
                preparation.required_confirmation_phrase
            ),
            "human_confirmation_validated": False,
        },

        "anti_replay": {
            "replay_consumed": False,
            "claim_created": False,
        },

        "authorization": {
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }


@app.post(
    "/api/ad-admin/acl-delegation/write-intent/identity-envelope"
)
def create_acl_delegation_write_identity_envelope_api(
    payload: dict = Body(...),
    identity=Depends(AD_ACCESS),
):
    try:
        envelope = (
            build_acl_delegation_write_identity_envelope(
                identity=identity,
                ad_admin_jobs_file=AD_ADMIN_JOBS_FILE,
                ad_explorer_jobs_file=AD_EXPLORER_JOBS_FILE,
                intent_payload=payload,
            )
        )
    except AclDelegationWriteIdentityEnvelopeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    audit_event = {
        "action": (
            "acl_delegation_write_identity_envelope_built"
        ),
        "request_id": envelope.server_nonce,
        "actor": envelope.actor_username,
        "message": (
            "Enveloppe d'identite ACL preparee "
            "sans autorisation d'ecriture"
        ),
        "details": {
            "contract_version": envelope.contract_version,
            "actor_subject": envelope.actor_subject,
            "actor_username": envelope.actor_username,
            "actor_roles": list(envelope.actor_roles),
            "simulation_job_id": (
                envelope.simulation_job_id
            ),
            "security_descriptor_job_id": (
                envelope.security_descriptor_job_id
            ),
            "target_dn": envelope.target_dn,
            "target_object_guid": (
                envelope.target_object_guid
            ),
            "principal_sid": (
                envelope.principal_sid
            ),
            "evidence_digest": (
                envelope.evidence_digest
            ),
            "envelope_digest": (
                envelope.envelope_digest
            ),
            "replay_consumed": False,
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }

    write_audit_log(**audit_event)

    return {
        "contract_version": envelope.contract_version,
        "execution_policy": envelope.execution_policy,
        "server_nonce": envelope.server_nonce,
        "issued_at": envelope.issued_at,
        "expires_at": envelope.expires_at,
        "actor": {
            "auth_type": envelope.actor_auth_type,
            "subject": envelope.actor_subject,
            "username": envelope.actor_username,
            "roles": list(envelope.actor_roles),
            "issuer": envelope.actor_issuer,
            "azp": envelope.actor_azp,
            "audience": list(envelope.actor_audience),
            "jti": envelope.actor_jti,
        },
        "evidence": {
            "simulation_job_id": (
                envelope.simulation_job_id
            ),
            "security_descriptor_job_id": (
                envelope.security_descriptor_job_id
            ),
            "evidence_digest": (
                envelope.evidence_digest
            ),
        },
        "target": {
            "dn": envelope.target_dn,
            "object_guid": (
                envelope.target_object_guid
            ),
        },
        "principal": {
            "dn": envelope.principal_dn,
            "sid": envelope.principal_sid,
        },
        "ace": {
            "access_control_type": (
                envelope.access_control_type
            ),
            "rights": list(envelope.rights),
            "inheritance_type": (
                envelope.inheritance_type
            ),
            "object_type_guid": (
                envelope.object_type_guid
            ),
            "inherited_object_type_guid": (
                envelope.inherited_object_type_guid
            ),
        },
        "dacl": {
            "dacl_sddl_sha256": (
                envelope.dacl_sddl_sha256
            ),
            "acl_fingerprint": (
                envelope.acl_fingerprint
            ),
        },
        "anti_replay": {
            "consumed": False,
            "consumption_id": None,
            "consumption_required": True,
        },
        "envelope_digest": envelope.envelope_digest,
        "authorization": {
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }


@app.post(
    "/api/ad-admin/acl-delegation/write-intent/claim"
)
def claim_acl_delegation_write_intent_api(
    payload: dict = Body(...),
    identity=Depends(AD_ACCESS),
):
    try:
        claim = claim_acl_delegation_write_intent(
            identity=identity,
            ad_admin_jobs_file=AD_ADMIN_JOBS_FILE,
            ad_explorer_jobs_file=AD_EXPLORER_JOBS_FILE,
            replay_registry_file=(
                ACL_DELEGATION_WRITE_REPLAY_FILE
            ),
            intent_payload=payload,
        )

    except AclDelegationWriteClaimConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except AclDelegationWriteClaimError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except AclDelegationWriteReplayStorageError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Stockage de securite ACL indisponible"
            ),
        ) from exc

    audit_event = {
        "action": (
            "acl_delegation_write_claim_created"
        ),
        "request_id": claim.claim_id,
        "actor": claim.actor_username,
        "message": (
            "Claim ACL dormant cree sans "
            "autorisation d'ecriture"
        ),
        "details": {
            "contract_version": (
                claim.contract_version
            ),
            "state": claim.state,
            "claim_id": claim.claim_id,
            "consumption_id": (
                claim.consumption_id
            ),
            "actor_subject": (
                claim.actor_subject
            ),
            "actor_username": (
                claim.actor_username
            ),
            "actor_roles": list(
                claim.actor_roles
            ),
            "simulation_job_id": (
                claim.simulation_job_id
            ),
            "security_descriptor_job_id": (
                claim.security_descriptor_job_id
            ),
            "target_dn": claim.target_dn,
            "target_object_guid": (
                claim.target_object_guid
            ),
            "principal_sid": (
                claim.principal_sid
            ),
            "evidence_digest": (
                claim.evidence_digest
            ),
            "envelope_digest": (
                claim.envelope_digest
            ),
            "replay_consumed": True,
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }

    write_audit_log(**audit_event)

    return {
        "contract_version": (
            claim.contract_version
        ),
        "state": claim.state,
        "claim_id": claim.claim_id,
        "consumption_id": (
            claim.consumption_id
        ),
        "replay_consumed": True,

        "actor": {
            "subject": claim.actor_subject,
            "username": claim.actor_username,
            "roles": list(
                claim.actor_roles
            ),
            "issuer": claim.actor_issuer,
            "azp": claim.actor_azp,
        },

        "evidence": {
            "simulation_job_id": (
                claim.simulation_job_id
            ),
            "security_descriptor_job_id": (
                claim.security_descriptor_job_id
            ),
            "evidence_digest": (
                claim.evidence_digest
            ),
            "envelope_digest": (
                claim.envelope_digest
            ),
        },

        "target": {
            "dn": claim.target_dn,
            "object_guid": (
                claim.target_object_guid
            ),
        },

        "principal": {
            "dn": claim.principal_dn,
            "sid": claim.principal_sid,
        },

        "ace": {
            "access_control_type": (
                claim.access_control_type
            ),
            "rights": list(claim.rights),
            "inheritance_type": (
                claim.inheritance_type
            ),
            "object_type_guid": (
                claim.object_type_guid
            ),
            "inherited_object_type_guid": (
                claim.inherited_object_type_guid
            ),
        },

        "dacl": {
            "dacl_sddl_sha256": (
                claim.dacl_sddl_sha256
            ),
            "acl_fingerprint": (
                claim.acl_fingerprint
            ),
        },

        "authorization": {
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }


@app.post(
    "/api/ad-admin/acl-delegation/prewrite-ticket"
)
def create_acl_delegation_prewrite_ticket_api(
    payload: dict = Body(...),
    identity=Depends(AD_ACCESS),
):
    allowed_fields = {
        "claim_id",
    }

    unexpected_fields = sorted(
        set(payload)
        - allowed_fields
    )

    if unexpected_fields:
        raise HTTPException(
            status_code=400,
            detail=(
                "Champs ticket ACL interdits : "
                + ", ".join(
                    unexpected_fields
                )
            ),
        )

    claim_id = str(
        payload.get("claim_id")
        or ""
    ).strip()

    if not claim_id:
        raise HTTPException(
            status_code=400,
            detail="claim_id ACL obligatoire",
        )

    try:
        ticket = (
            create_acl_delegation_prewrite_ticket(
                replay_registry_file=(
                    ACL_DELEGATION_WRITE_REPLAY_FILE
                ),
                claim_id=claim_id,
            )
        )

    except AclDelegationPrewriteTicketConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except AclDelegationPrewriteTicketError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except AclDelegationWriteReplayStorageError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Stockage de securite ACL indisponible"
            ),
        ) from exc

    write_audit_log(
        action=(
            "acl_delegation_prewrite_ticket_created"
        ),
        request_id=ticket.ticket_id,
        actor=identity.username,
        message=(
            "Ticket ACL pre-write dormant cree "
            "sans autorisation d'ecriture"
        ),
        details={
            "contract_version": (
                ticket.contract_version
            ),
            "state": ticket.state,
            "ticket_id": ticket.ticket_id,
            "claim_id": ticket.claim_id,
            "consumption_id": (
                ticket.consumption_id
            ),
            "payload_digest": (
                ticket.payload_digest
            ),
            "actor_subject": (
                identity.subject
            ),
            "actor_username": (
                identity.username
            ),
            "prewrite_validation_runtime_authorized": (
                False
            ),
            "job_creation_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    )

    return {
        "contract_version": (
            ticket.contract_version
        ),
        "state": ticket.state,
        "ticket_id": ticket.ticket_id,
        "claim_id": ticket.claim_id,
        "consumption_id": (
            ticket.consumption_id
        ),
        "created_at": ticket.created_at,
        "expires_at": ticket.expires_at,
        "payload_digest": (
            ticket.payload_digest
        ),
        "authorization": {
            "prewrite_validation_runtime_authorized": (
                False
            ),
            "job_creation_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }


@app.post(
    "/api/ad-admin/acl-delegation/production-confirmation"
)
def confirm_acl_delegation_production_api(
    payload: dict = Body(...),
    identity=Depends(AD_ACCESS),
):
    allowed_fields = {
        "claim_id",
        "ticket_id",
        "execution_id",
        "confirm_object_dn",
        "confirmation_phrase",
    }

    unexpected_fields = sorted(
        set(payload)
        - allowed_fields
    )

    if unexpected_fields:
        raise HTTPException(
            status_code=400,
            detail=(
                "Champs confirmation ACL interdits : "
                + ", ".join(
                    unexpected_fields
                )
            ),
        )

    required = {
        key: str(
            payload.get(key)
            or ""
        ).strip()
        for key in allowed_fields
    }

    missing = sorted(
        key
        for key, value in required.items()
        if not value
    )

    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                "Champs confirmation ACL obligatoires : "
                + ", ".join(
                    missing
                )
            ),
        )

    try:
        confirmation = (
            persist_acl_delegation_production_confirmation(
                identity=identity,
                replay_registry_file=(
                    ACL_DELEGATION_WRITE_REPLAY_FILE
                ),
                claim_id=required[
                    "claim_id"
                ],
                ticket_id=required[
                    "ticket_id"
                ],
                execution_id=required[
                    "execution_id"
                ],
                confirm_object_dn=required[
                    "confirm_object_dn"
                ],
                confirmation_phrase=required[
                    "confirmation_phrase"
                ],
            )
        )

    except (
        AclDelegationProductionConfirmationConflict,
        AclDelegationProductionConfirmationPersistenceConflict,
    ) as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except (
        AclDelegationProductionConfirmationError,
        AclDelegationProductionConfirmationPersistenceError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except AclDelegationWriteReplayStorageError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Stockage de securite ACL indisponible"
            ),
        ) from exc

    write_audit_log(
        action=(
            "acl_delegation_production_confirmation_consumed"
        ),
        request_id=(
            confirmation.confirmation_id
        ),
        actor=confirmation.actor_username,
        message=(
            "Confirmation Production ACL validee "
            "et consommee sans autorisation d'ecriture"
        ),
        details={
            "contract_version": (
                confirmation.contract_version
            ),
            "state": confirmation.state,
            "source_state": (
                confirmation.source_state
            ),

            "confirmation_id": (
                confirmation.confirmation_id
            ),
            "confirmation_digest": (
                confirmation.confirmation_digest
            ),
            "confirmation_created_at": (
                confirmation.confirmation_created_at
            ),

            "claim_id": confirmation.claim_id,
            "ticket_id": confirmation.ticket_id,
            "execution_id": (
                confirmation.execution_id
            ),

            "actor_subject": (
                confirmation.actor_subject
            ),
            "actor_username": (
                confirmation.actor_username
            ),

            "target_dn": (
                confirmation.target_dn
            ),
            "target_object_guid": (
                confirmation.target_object_guid
            ),
            "principal_sid": (
                confirmation.principal_sid
            ),

            "dacl_sddl_sha256": (
                confirmation.dacl_sddl_sha256
            ),
            "acl_fingerprint": (
                confirmation.acl_fingerprint
            ),

            "confirmation_validated": True,
            "confirmation_consumed": True,

            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    )

    return {
        "contract_version": (
            confirmation.contract_version
        ),
        "state": confirmation.state,
        "source_state": (
            confirmation.source_state
        ),

        "confirmation_id": (
            confirmation.confirmation_id
        ),
        "confirmation_digest": (
            confirmation.confirmation_digest
        ),
        "confirmation_created_at": (
            confirmation.confirmation_created_at
        ),

        "claim_id": confirmation.claim_id,
        "ticket_id": confirmation.ticket_id,
        "execution_id": (
            confirmation.execution_id
        ),

        "actor": {
            "subject": (
                confirmation.actor_subject
            ),
            "username": (
                confirmation.actor_username
            ),
        },

        "target": {
            "dn": confirmation.target_dn,
            "object_guid": (
                confirmation.target_object_guid
            ),
        },

        "principal": {
            "sid": confirmation.principal_sid,
        },

        "dacl": {
            "dacl_sddl_sha256": (
                confirmation.dacl_sddl_sha256
            ),
            "acl_fingerprint": (
                confirmation.acl_fingerprint
            ),
        },

        "confirmation": {
            "validated": True,
            "consumed": True,
        },

        "authorization": {
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }


@app.get(
    "/api/ad-admin/acl-delegation/prewrite-status/{ticket_id}"
)
def get_acl_delegation_prewrite_status_api(
    ticket_id: str,
    identity=Depends(AD_ACCESS),
):
    actor_subject = str(
        identity.subject
        or ""
    ).strip()

    if not actor_subject:
        raise HTTPException(
            status_code=403,
            detail="Identite OIDC ACL invalide",
        )

    try:
        status = (
            get_acl_delegation_prewrite_status(
                replay_registry_file=(
                    ACL_DELEGATION_WRITE_REPLAY_FILE
                ),
                ticket_id=ticket_id,
                actor_subject=actor_subject,
            )
        )

    except AclDelegationPrewriteStatusNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail="Statut ACL pre-write introuvable",
        ) from exc

    except AclDelegationPrewriteStatusError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except AclDelegationWriteReplayStorageError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Stockage de securite ACL indisponible"
            ),
        ) from exc

    return {
        "contract_version": (
            status.contract_version
        ),
        "state": status.state,

        "ticket_id": status.ticket_id,
        "claim_id": status.claim_id,
        "execution_id": (
            status.execution_id
        ),

        "created_at": status.created_at,
        "expires_at": status.expires_at,
        "claimed_at": status.claimed_at,
        "completed_at": status.completed_at,

        "success": status.success,

        "validation": {
            "worker_validation_in_progress": (
                status.worker_validation_in_progress
            ),
            "completed": (
                status.validation_completed
            ),
            "confirmation_ready": (
                status.confirmation_ready
            ),
        },

        "authorization": {
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }


@app.get(
    "/api/agent/acl-delegation/prewrite/pending"
)
def get_pending_acl_delegation_prewrite_tickets(
    api_key: None = Depends(require_api_key),
):
    try:
        return (
            list_pending_acl_delegation_prewrite_tickets(
                replay_registry_file=(
                    ACL_DELEGATION_WRITE_REPLAY_FILE
                ),
            )
        )

    except (
        AclDelegationPrewriteRuntimeError,
        AclDelegationWriteReplayStorageError,
    ) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Etat ACL pre-write indisponible"
            ),
        ) from exc


@app.post(
    "/api/agent/acl-delegation/prewrite/claim/{ticket_id}"
)
def claim_acl_delegation_prewrite_ticket_api(
    ticket_id: str,
    payload: dict = Body(...),
    api_key: None = Depends(require_api_key),
):
    allowed_fields = {
        "agent_name",
    }

    unexpected_fields = sorted(
        set(payload)
        - allowed_fields
    )

    if unexpected_fields:
        raise HTTPException(
            status_code=400,
            detail=(
                "Champs claim ACL agent interdits : "
                + ", ".join(
                    unexpected_fields
                )
            ),
        )

    agent_name = str(
        payload.get("agent_name")
        or ""
    ).strip()

    if not agent_name:
        raise HTTPException(
            status_code=400,
            detail="agent_name ACL obligatoire",
        )

    try:
        execution = (
            claim_acl_delegation_prewrite_ticket_for_agent(
                replay_registry_file=(
                    ACL_DELEGATION_WRITE_REPLAY_FILE
                ),
                ticket_id=ticket_id,
                agent_name=agent_name,
            )
        )

    except AclDelegationPrewriteRuntimeConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except AclDelegationPrewriteRuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except AclDelegationWriteReplayStorageError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Stockage de securite ACL indisponible"
            ),
        ) from exc

    write_audit_log(
        action=(
            "acl_delegation_prewrite_agent_claimed"
        ),
        request_id=execution.execution_id,
        actor=agent_name,
        message=(
            "Ticket ACL pre-write pris "
            "par l'agent de validation"
        ),
        details={
            "contract_version": (
                execution.contract_version
            ),
            "state": execution.state,
            "ticket_id": execution.ticket_id,
            "execution_id": (
                execution.execution_id
            ),
            "claim_id": execution.claim_id,
            "consumption_id": (
                execution.consumption_id
            ),
            "payload_digest": (
                execution.payload_digest
            ),
            "prewrite_validation_runtime_authorized": True,
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    )

    return {
        "contract_version": (
            execution.contract_version
        ),
        "state": execution.state,
        "ticket_id": execution.ticket_id,
        "execution_id": (
            execution.execution_id
        ),
        "claim_id": execution.claim_id,
        "consumption_id": (
            execution.consumption_id
        ),
        "claimed_at": execution.claimed_at,
        "claimed_by": execution.claimed_by,
        "expires_at": execution.expires_at,
        "payload_digest": (
            execution.payload_digest
        ),

        # Payload is returned only to the API-key
        # authenticated Windows validation worker.
        "payload": execution.payload,

        "authorization": {
            "prewrite_validation_runtime_authorized": True,
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }


@app.post(
    "/api/agent/acl-delegation/prewrite/result/{ticket_id}"
)
def submit_acl_delegation_prewrite_result_api(
    ticket_id: str,
    payload: dict = Body(...),
    api_key: None = Depends(require_api_key),
):
    allowed_fields = {
        "execution_id",
        "agent_name",
        "success",
        "result",
        "message",
    }

    unexpected_fields = sorted(
        set(payload)
        - allowed_fields
    )

    if unexpected_fields:
        raise HTTPException(
            status_code=400,
            detail=(
                "Champs resultat ACL agent interdits : "
                + ", ".join(
                    unexpected_fields
                )
            ),
        )

    execution_id = str(
        payload.get("execution_id")
        or ""
    ).strip()

    agent_name = str(
        payload.get("agent_name")
        or ""
    ).strip()

    if not execution_id:
        raise HTTPException(
            status_code=400,
            detail="execution_id ACL obligatoire",
        )

    if not agent_name:
        raise HTTPException(
            status_code=400,
            detail="agent_name ACL obligatoire",
        )

    success = payload.get("success")

    if success is not True and success is not False:
        raise HTTPException(
            status_code=400,
            detail="success ACL doit etre booleen",
        )

    try:
        completion = (
            complete_acl_delegation_prewrite_ticket(
                replay_registry_file=(
                    ACL_DELEGATION_WRITE_REPLAY_FILE
                ),
                ticket_id=ticket_id,
                execution_id=execution_id,
                agent_name=agent_name,
                success=success,
                result=payload.get("result"),
                message=str(
                    payload.get("message")
                    or ""
                ),
            )
        )

    except AclDelegationPrewriteRuntimeConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except AclDelegationPrewriteRuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except AclDelegationWriteReplayStorageError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Stockage de securite ACL indisponible"
            ),
        ) from exc

    write_audit_log(
        action=(
            "acl_delegation_prewrite_agent_completed"
            if completion.success
            else
            "acl_delegation_prewrite_agent_failed"
        ),
        request_id=completion.execution_id,
        actor=agent_name,
        message=(
            "Validation ACL pre-write terminee"
            if completion.success
            else
            "Validation ACL pre-write refusee"
        ),
        details={
            "contract_version": (
                completion.contract_version
            ),
            "state": completion.state,
            "ticket_id": completion.ticket_id,
            "execution_id": (
                completion.execution_id
            ),
            "success": completion.success,
            "prewrite_validation_runtime_authorized": False,
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    )

    return {
        "contract_version": (
            completion.contract_version
        ),
        "state": completion.state,
        "ticket_id": completion.ticket_id,
        "execution_id": (
            completion.execution_id
        ),
        "completed_at": (
            completion.completed_at
        ),
        "success": completion.success,
        "authorization": {
            "prewrite_validation_runtime_authorized": False,
            "job_creation_authorized": False,
            "runtime_authorized": False,
            "production_authorized": False,
            "ad_write_authorized": False,
        },
    }


@app.post("/api/ad-admin/jobs")
def create_ad_admin_job(payload: dict = Body(...), api_key: None = Depends(AD_ACCESS)):
    try:
        response, audit_event = service_create_ad_admin_job(AD_ADMIN_JOBS_FILE, payload)
    except ADAdminBadRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.get("/api/ad-admin/jobs")
def list_ad_admin_jobs(limit: int = 100, api_key: None = Depends(AD_ACCESS)):
    return service_list_ad_admin_jobs(AD_ADMIN_JOBS_FILE, limit)


@app.get("/api/ad-admin/jobs/{job_id}")
def get_ad_admin_job(job_id: str, api_key: None = Depends(AD_ACCESS)):
    try:
        return service_get_ad_admin_job(AD_ADMIN_JOBS_FILE, job_id)
    except ADAdminNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/agent/ad-admin/pending")
def get_pending_ad_admin_jobs(api_key: None = Depends(require_api_key)):
    return service_get_pending_ad_admin_jobs(AD_ADMIN_JOBS_FILE)


@app.post("/api/agent/ad-admin/claim/{job_id}")
def claim_ad_admin_job(job_id: str, payload: dict = Body(default={}), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_claim_ad_admin_job(AD_ADMIN_JOBS_FILE, job_id, payload)
    except ADAdminConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ADAdminNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.post("/api/agent/ad-admin/result/{job_id}")
def submit_ad_admin_job_result(job_id: str, payload: dict = Body(...), api_key: None = Depends(require_api_key)):
    try:
        response, audit_event = service_submit_ad_admin_job_result(AD_ADMIN_JOBS_FILE, job_id, payload)
    except ADAdminNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.get("/api/identity-update/status")
def get_identity_update_status(
    _identity=Depends(
        IDENTITY_UPDATE_STATUS_ACCESS
    ),
):
    try:
        return service_get_identity_update_status(
            IDENTITY_UPDATE_STATUS_FILE
        )
    except IdentityUpdateStatusUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/identity-update/source-check",
    status_code=202,
)
def request_identity_update_source_check(
    identity=Depends(
        IDENTITY_UPDATE_STATUS_ACCESS
    ),
):
    try:
        response = (
            service_create_identity_update_source_check_request(
                IDENTITY_UPDATE_SOURCE_CHECK_REQUEST_FILE,
                identity.username,
            )
        )
    except IdentityUpdateRequestConflict as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except IdentityUpdateRequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    write_audit_log(
        "identity_update_source_check_requested",
        actor=identity.username,
        details={
            "request_id": response["request_id"],
            "action": response["action"],
        },
        message=(
            "Vérification de la source upstream demandée"
        ),
    )

    return response


@app.get("/api/audit-logs")
def list_audit_logs(limit: int = 50, api_key: None = Depends(AUDIT_ACCESS)):
    if not AUDIT_FILE.exists():
        return {
            "count": 0,
            "logs": []
        }

    lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    selected_lines = lines[-limit:]

    logs = []
    for line in selected_lines:
        try:
            logs.append(json.loads(line))
        except json.JSONDecodeError:
            logs.append({
                "error": "invalid_log_line",
                "raw": line
            })

    return {
        "count": len(logs),
        "logs": logs
    }


@app.get("/api/admin/templates")
def admin_get_templates(api_key: None = Depends(SECURITY_ACCESS)):
    return service_get_templates(TEMPLATES_FILE)


@app.post("/api/admin/templates/departments")
def upsert_department_template(payload: DepartmentTemplatePayload, api_key: None = Depends(SECURITY_ACCESS)):
    response, audit_event = service_upsert_department_template(
        TEMPLATES_FILE,
        payload.name,
        payload.default_ou,
        payload.default_groups,
    )

    write_audit_log(**audit_event)

    return response


@app.delete("/api/admin/templates/departments/{department_name}")
def delete_department_template(department_name: str, api_key: None = Depends(SECURITY_ACCESS)):
    try:
        response, audit_event = service_delete_department_template(TEMPLATES_FILE, department_name)
    except TemplatesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.post("/api/admin/templates/departments/{department_name}/roles")
def upsert_role_template(department_name: str, payload: RoleTemplatePayload, api_key: None = Depends(SECURITY_ACCESS)):
    try:
        response, audit_event = service_upsert_role_template(
            TEMPLATES_FILE,
            department_name,
            payload.name,
            payload.groups,
        )
    except TemplatesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.delete("/api/admin/templates/departments/{department_name}/roles/{role_name}")
def delete_role_template(department_name: str, role_name: str, api_key: None = Depends(SECURITY_ACCESS)):
    try:
        response, audit_event = service_delete_role_template(
            TEMPLATES_FILE,
            department_name,
            role_name,
        )
    except TemplatesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    write_audit_log(**audit_event)

    return response


@app.post("/api/offboarding/request")
def create_offboarding_request(payload: OffboardingRequest, api_key: None = Depends(OPERATOR_ACCESS)):
    response, audit_event = service_create_offboarding_request(
        REQUESTS_FILE,
        payload,
    )

    write_audit_log(**audit_event)

    return response


@app.post("/api/modification/request")
def create_modification_request(payload: ModificationRequest, api_key: None = Depends(OPERATOR_ACCESS)):
    response, audit_event = service_create_modification_request(
        REQUESTS_FILE,
        payload,
    )

    write_audit_log(**audit_event)

    return response


# STEP176_AGENT_MODE_COMPAT_ROUTES
def _eitas_agent_mode_config_file():
    if "AGENT_CONFIG_FILE" in globals():
        return AGENT_CONFIG_FILE

    if "DATA_DIR" in globals():
        return DATA_DIR / "agent_config.json"

    return Path(__file__).resolve().parent.parent / "data" / "agent_config.json"


def _eitas_agent_mode_load_config():
    path = _eitas_agent_mode_config_file()

    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            if isinstance(data, dict):
                return data
    except Exception:
        return {}

    return {}


def _eitas_agent_mode_save_config(config):
    path = _eitas_agent_mode_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)


def _eitas_agent_mode_normalize(value):
    text = str(value or "Simulation").strip().lower()

    if text in {"production", "prod", "reel", "réel", "real"}:
        return "Production"

    return "Simulation"


@app.get("/api/agent/mode")
def eitas_get_agent_mode_compat(
    api_key: None = Depends(
        AGENT_MODE_READ_OR_API_KEY_ACCESS
    ),
):
    config = _eitas_agent_mode_load_config()
    mode = _eitas_agent_mode_normalize(
        config.get("mode") or
        config.get("Mode") or
        "Simulation"
    )

    return {
        "mode": mode,
        "source": "agent_config"
    }


@app.post("/api/admin/agent/mode")
def eitas_update_agent_mode_compat(
    payload: dict = Body(...),
    api_key: None = Depends(SECURITY_ACCESS),
):
    wanted_mode = _eitas_agent_mode_normalize(payload.get("mode") if isinstance(payload, dict) else None)
    updated_by = payload.get("updated_by") if isinstance(payload, dict) else None

    config = _eitas_agent_mode_load_config()
    config["mode"] = wanted_mode
    config["Mode"] = wanted_mode
    config["updated_by"] = updated_by or "react-admin"
    config["updated_at"] = now_iso() if "now_iso" in globals() else ""

    _eitas_agent_mode_save_config(config)

    if "write_audit_log" in globals():
        try:
            write_audit_log(
                "agent_mode_updated",
                actor=updated_by or "react-admin",
                details={"mode": wanted_mode},
                message=f"Mode agent mis à jour : {wanted_mode}"
            )
        except Exception:
            pass

    return {
        "mode": wanted_mode,
        "message": f"Mode agent mis à jour : {wanted_mode}"
    }
