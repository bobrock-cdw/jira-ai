from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.config import DEFAULT_GCP_LOCATION, DEFAULT_GCP_PROJECT_ID
from core.gemini import (
    create_gemini_client,
    generate_ai_content,
    test_gemini_connection,
)


app = FastAPI(
    title="Jira-AI API",
    description="Minimal FastAPI backend for AI-assisted Jira issue generation.",
    version="0.1.0",
)


class GeminiSettings(BaseModel):
    gcp_project_id: str = Field(default=DEFAULT_GCP_PROJECT_ID)
    gcp_location: str = Field(default=DEFAULT_GCP_LOCATION)


class GenerateRequest(GeminiSettings):
    project_context: str = ""
    brief: str


class GenerateResponse(BaseModel):
    prompt_type: Literal["story", "task"]
    data: dict


class GeminiTestResponse(BaseModel):
    elapsed_seconds: int
    response_text: str


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/test-gemini",
    responses={502: {"description": "Gemini connectivity test failed"}},
)
def test_gemini(settings: GeminiSettings) -> GeminiTestResponse:
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


def generate_content(prompt_type: Literal["story", "task"], request: GenerateRequest) -> GenerateResponse:
    try:
        client = create_gemini_client(
            request.gcp_project_id,
            request.gcp_location,
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
