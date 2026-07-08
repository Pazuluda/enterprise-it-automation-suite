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


class OffboardingRequest(BaseModel):
    username: str
    display_name: str
    department: str | None = None
    manager: str | None = None
    end_date: str
    disable_account: bool = True
    remove_groups: bool = True
    move_to_ou: str | None = "OU=Disabled Users,DC=lab,DC=local"
    convert_mailbox: bool = False
    forward_to: str | None = None
    comment: str | None = None



class ModificationRequest(BaseModel):
    username: str
    display_name: str
    current_department: str | None = None
    current_job_title: str | None = None
    new_department: str | None = None
    new_job_title: str | None = None
    manager: str | None = None
    effective_date: str
    add_groups: list[str] = Field(default_factory=list)
    remove_groups: list[str] = Field(default_factory=list)
    move_to_ou: str | None = None
    comment: str | None = None
