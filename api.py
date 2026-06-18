from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import (
    DEFAULT_GCP_LOCATION,
    DEFAULT_GCP_PROJECT_ID,
    DEFAULT_JIRA_ASSIGNEE,
    DEFAULT_JIRA_COMPONENT,
    DEFAULT_JIRA_PROJECT,
    DEFAULT_JIRA_SERVER,
    GEMINI_MODEL,
    get_cors_origins,
    get_jira_credentials,
    get_jira_servers,
)
from core.gemini import (
    create_gemini_client,
    generate_ai_content,
    test_gemini_connection,
)
from core.models import StoryGenerationResult, TaskGenerationResult
from core.jira_client import create_jira_client, resolve_assignee_account_id
from core.service import (
    CreatedIssue,
    JiraIssueContext,
    create_epic,
    create_epic_plan,
    create_story_with_tasks,
    create_task_with_subtasks,
    preview_epic_issue_fields,
    preview_epic_plan_issue_fields,
    preview_story_issue_fields,
    preview_task_issue_fields,
)


app = FastAPI(
    title="Jira-AI API",
    description="Minimal FastAPI backend for AI-assisted Jira issue generation.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GeminiSettings(BaseModel):
    gcp_project_id: str = Field(default=DEFAULT_GCP_PROJECT_ID)
    gcp_location: str = Field(default=DEFAULT_GCP_LOCATION)


class GenerateRequest(BaseModel):
    project_context: str = ""
    brief: str


class GenerateResponse(BaseModel):
    prompt_type: Literal["epic", "story", "task"]
    data: dict


class GeminiTestResponse(BaseModel):
    elapsed_seconds: int
    response_text: str


class ConfigDefaultsResponse(BaseModel):
    gemini_model: str
    jira_server: str
    jira_servers: list[str]
    jira_project_key: str
    jira_component: str
    jira_assignee: str


class JiraIssueSettings(BaseModel):
    project_key: str
    component_name: str | None = None
    assignee_account_id: str | None = None


class JiraCreateSettings(JiraIssueSettings):
    jira_server: str = DEFAULT_JIRA_SERVER


class AssigneeResolveRequest(BaseModel):
    jira_server: str = DEFAULT_JIRA_SERVER
    assignee_name: str


class AssigneeResolveResponse(BaseModel):
    assignee_name: str
    account_id: str


class StoryPreviewRequest(BaseModel):
    jira: JiraIssueSettings
    story: StoryGenerationResult
    epic_key: str | None = None


class TaskPreviewRequest(BaseModel):
    jira: JiraIssueSettings
    task: TaskGenerationResult
    issue_type: Literal["Task", "Sub-task"] = "Task"
    parent_key: str | None = None


class IssueFieldsPreviewResponse(BaseModel):
    fields: list[dict]


class EpicIssue(BaseModel):
    title: str
    description: str


class EpicPlan(BaseModel):
    epic: EpicIssue
    stories: list[StoryGenerationResult] = Field(default_factory=list)


class EpicPreviewRequest(BaseModel):
    jira: JiraIssueSettings
    epic: EpicIssue


class EpicPlanPreviewRequest(BaseModel):
    jira: JiraIssueSettings
    plan: EpicPlan


class StoryCreateRequest(BaseModel):
    jira: JiraCreateSettings
    story: StoryGenerationResult
    epic_key: str | None = None


class EpicCreateRequest(BaseModel):
    jira: JiraCreateSettings
    epic: EpicIssue


class EpicPlanCreateRequest(BaseModel):
    jira: JiraCreateSettings
    plan: EpicPlan


class TaskCreateRequest(BaseModel):
    jira: JiraCreateSettings
    task: TaskGenerationResult
    issue_type: Literal["Task", "Sub-task"] = "Task"
    parent_key: str | None = None


class CreatedIssueResponse(BaseModel):
    issue_type: str
    key: str


class CreateIssuesResponse(BaseModel):
    created: list[CreatedIssueResponse]


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config/defaults")
def config_defaults() -> ConfigDefaultsResponse:
    return ConfigDefaultsResponse(
        gemini_model=GEMINI_MODEL,
        jira_server=DEFAULT_JIRA_SERVER,
        jira_servers=get_jira_servers(),
        jira_project_key=DEFAULT_JIRA_PROJECT,
        jira_component=DEFAULT_JIRA_COMPONENT,
        jira_assignee=DEFAULT_JIRA_ASSIGNEE,
    )


@app.post(
    "/test-gemini",
    responses={502: {"description": "Gemini connectivity test failed"}},
)
def test_gemini(settings: GeminiSettings | None = None) -> GeminiTestResponse:
    settings = settings or GeminiSettings()
    try:
        elapsed, response_text = test_gemini_connection(
            settings.gcp_project_id,
            settings.gcp_location,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return GeminiTestResponse(
        elapsed_seconds=elapsed,
        response_text=response_text,
    )


def generate_content(prompt_type: Literal["epic", "story", "task"], request: GenerateRequest) -> GenerateResponse:
    try:
        client = create_gemini_client(
            DEFAULT_GCP_PROJECT_ID,
            DEFAULT_GCP_LOCATION,
        )
        data = generate_ai_content(
            client=client,
            prompt_type=prompt_type,
            brief=request.brief,
            project_context=request.project_context,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return GenerateResponse(prompt_type=prompt_type, data=data)


@app.post(
    "/generate/epic",
    responses={502: {"description": "Epic plan generation failed"}},
)
def generate_epic(request: GenerateRequest) -> GenerateResponse:
    return generate_content("epic", request)


@app.post(
    "/generate/story",
    responses={502: {"description": "Story generation failed"}},
)
def generate_story(request: GenerateRequest) -> GenerateResponse:
    return generate_content("story", request)


@app.post(
    "/generate/task",
    responses={502: {"description": "Task generation failed"}},
)
def generate_task(request: GenerateRequest) -> GenerateResponse:
    return generate_content("task", request)


def build_issue_context(settings: JiraIssueSettings) -> JiraIssueContext:
    return JiraIssueContext(
        project_key=settings.project_key,
        component_name=settings.component_name,
        assignee_account_id=settings.assignee_account_id,
    )


def get_authenticated_jira_client_for_server(jira_server: str):
    credentials = get_jira_credentials()
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="JIRA_USERNAME or JIRA_API_TOKEN not found.",
        )
    return create_jira_client(jira_server, credentials)


def get_authenticated_jira_client(settings: JiraCreateSettings):
    return get_authenticated_jira_client_for_server(settings.jira_server)


def to_create_response(created: list[CreatedIssue]) -> CreateIssuesResponse:
    return CreateIssuesResponse(
        created=[
            CreatedIssueResponse(issue_type=issue.issue_type, key=issue.key)
            for issue in created
        ]
    )


@app.post(
    "/jira/resolve-assignee",
    responses={
        401: {"description": "Jira credentials are missing"},
        404: {"description": "Assignee was not found"},
        502: {"description": "Jira assignee lookup failed"},
    },
)
def resolve_assignee(request: AssigneeResolveRequest) -> AssigneeResolveResponse:
    try:
        jira_client = get_authenticated_jira_client_for_server(request.jira_server)
        account_id = resolve_assignee_account_id(jira_client, request.assignee_name)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not account_id:
        raise HTTPException(
            status_code=404,
            detail=f"Assignee not found: {request.assignee_name}",
        )
    return AssigneeResolveResponse(
        assignee_name=request.assignee_name,
        account_id=account_id,
    )


@app.post("/preview/story")
def preview_story(request: StoryPreviewRequest) -> IssueFieldsPreviewResponse:
    context = JiraIssueContext(
        project_key=request.jira.project_key,
        component_name=request.jira.component_name,
        assignee_account_id=request.jira.assignee_account_id,
    )
    fields = preview_story_issue_fields(
        context=context,
        story_data=request.story.model_dump(),
        epic_key=request.epic_key,
    )
    return IssueFieldsPreviewResponse(fields=fields)


@app.post("/preview/epic")
def preview_epic(request: EpicPreviewRequest) -> IssueFieldsPreviewResponse:
    context = JiraIssueContext(
        project_key=request.jira.project_key,
        component_name=request.jira.component_name,
        assignee_account_id=request.jira.assignee_account_id,
    )
    fields = preview_epic_issue_fields(
        context=context,
        title=request.epic.title,
        description=request.epic.description,
    )
    return IssueFieldsPreviewResponse(fields=fields)


@app.post("/preview/epic-plan")
def preview_epic_plan(request: EpicPlanPreviewRequest) -> IssueFieldsPreviewResponse:
    context = JiraIssueContext(
        project_key=request.jira.project_key,
        component_name=request.jira.component_name,
        assignee_account_id=request.jira.assignee_account_id,
    )
    fields = preview_epic_plan_issue_fields(
        context=context,
        plan_data=request.plan.model_dump(),
    )
    return IssueFieldsPreviewResponse(fields=fields)


@app.post("/preview/task")
def preview_task(request: TaskPreviewRequest) -> IssueFieldsPreviewResponse:
    context = JiraIssueContext(
        project_key=request.jira.project_key,
        component_name=request.jira.component_name,
        assignee_account_id=request.jira.assignee_account_id,
    )
    fields = preview_task_issue_fields(
        context=context,
        task_data=request.task.model_dump(),
        issue_type=request.issue_type,
        parent=request.parent_key,
    )
    return IssueFieldsPreviewResponse(fields=fields)


@app.post(
    "/create/epic",
    responses={
        401: {"description": "Jira credentials are missing"},
        502: {"description": "Jira Epic creation failed"},
    },
)
def create_epic_endpoint(request: EpicCreateRequest) -> CreateIssuesResponse:
    try:
        jira_client = get_authenticated_jira_client(request.jira)
        created = create_epic(
            jira_client=jira_client,
            context=build_issue_context(request.jira),
            title=request.epic.title,
            description=request.epic.description,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return to_create_response(created)


@app.post(
    "/create/epic-plan",
    responses={
        401: {"description": "Jira credentials are missing"},
        502: {"description": "Jira Epic plan creation failed"},
    },
)
def create_epic_plan_endpoint(request: EpicPlanCreateRequest) -> CreateIssuesResponse:
    try:
        jira_client = get_authenticated_jira_client(request.jira)
        created = create_epic_plan(
            jira_client=jira_client,
            context=build_issue_context(request.jira),
            plan_data=request.plan.model_dump(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return to_create_response(created)


@app.post(
    "/create/story",
    responses={
        401: {"description": "Jira credentials are missing"},
        502: {"description": "Jira Story creation failed"},
    },
)
def create_story(request: StoryCreateRequest) -> CreateIssuesResponse:
    try:
        jira_client = get_authenticated_jira_client(request.jira)
        created = create_story_with_tasks(
            jira_client=jira_client,
            context=build_issue_context(request.jira),
            story_data=request.story.model_dump(),
            epic_key=request.epic_key,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return to_create_response(created)


@app.post(
    "/create/task",
    responses={
        401: {"description": "Jira credentials are missing"},
        502: {"description": "Jira Task creation failed"},
    },
)
def create_task(request: TaskCreateRequest) -> CreateIssuesResponse:
    try:
        jira_client = get_authenticated_jira_client(request.jira)
        created = create_task_with_subtasks(
            jira_client=jira_client,
            context=build_issue_context(request.jira),
            task_data=request.task.model_dump(),
            issue_type=request.issue_type,
            parent=request.parent_key,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return to_create_response(created)
