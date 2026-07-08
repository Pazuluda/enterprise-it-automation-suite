from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    first_name: str
    last_name: str
    department: str
    job_title: str
    manager: str | None = None
    start_date: str
    manual_groups: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    success: bool
    message: str
    details: dict = Field(default_factory=dict)


class ResetRequestsPayload(BaseModel):
    confirm: str


class ClaimRequestPayload(BaseModel):
    agent_name: str | None = None


class ApprovalPayload(BaseModel):
    approved_by: str
    comment: str | None = None


class DepartmentTemplatePayload(BaseModel):
    name: str
    default_ou: str
    default_groups: list[str] = Field(default_factory=list)


class RoleTemplatePayload(BaseModel):
    name: str
    groups: list[str] = Field(default_factory=list)
