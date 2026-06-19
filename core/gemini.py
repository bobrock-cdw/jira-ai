import json
import time
from threading import Thread
from typing import Callable

from google import genai
from google.genai import types

from core.config import GEMINI_MODEL, build_gemini_http_options
from core.models import validate_ai_response


ProgressCallback = Callable[[str], None]


def create_gemini_client(project_id: str, location: str):
    return genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
        http_options=build_gemini_http_options(),
    )


def format_gemini_error(exc: Exception) -> str:
    text = str(exc)
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
        return (
            f"{text}\n\n"
            "Vertex AI rate limit or quota hit. This is not a hang — the API is throttling requests.\n"
            "Wait a minute and retry, or check quotas in GCP Console → Vertex AI → Quotas."
        )
    return text


def build_prompt(prompt_type: str, project_context: str, brief: str) -> str:
    if prompt_type == "epic":
        return (
            "Act as an Expert Product Committee (PM, Architect, Lead Dev, QA). "
            f"Context: {project_context}. Epic brief: {brief}. "
            "Break the Epic into a small, reviewable implementation plan. Return ONLY JSON: "
            "{'epic': {'title', 'description'}, "
            "'stories': [{'title', 'user_story', 'acceptance_criteria', "
            "'tasks': [{'title', 'description'}]}]}"
        )
    if prompt_type == "story":
        return (
            "Act as an Expert Committee (PM, Dev, Architect, QA). "
            f"Context: {project_context}. Brief: {brief}. Return ONLY JSON: "
            "{'title', 'user_story', 'acceptance_criteria', 'tasks': [{'title', 'description'}]}"
        )
    if prompt_type == "task":
        return (
            "Act as a Lead Dev and Architect. "
            f"Context: {project_context}. Brief: {brief}. "
            "Return ONLY JSON: {'title', 'description', 'subtasks': [{'title', 'description'}]}"
        )
    raise ValueError(f"Unsupported prompt type: {prompt_type}")


def call_gemini(client, prompt: str):
    return client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )


def generate_ai_content(
    client,
    prompt_type: str,
    brief: str,
    project_context: str,
    progress_callback: ProgressCallback | None = None,
) -> dict | None:
    prompt = build_prompt(prompt_type, project_context, brief)
    result = {}
    error = {}

    def worker():
        try:
            result["response"] = call_gemini(client, prompt)
        except Exception as exc:
            error["exc"] = exc

    started_at = time.time()
    worker_thread = Thread(target=worker, daemon=True)
    worker_thread.start()

    while worker_thread.is_alive():
        if progress_callback:
            elapsed = int(time.time() - started_at)
            progress_callback(f"Waiting for Gemini... {elapsed}s")
        worker_thread.join(timeout=2)

    if error:
        raise RuntimeError(format_gemini_error(error["exc"])) from error["exc"]

    response = result.get("response")
    if not response or not response.text:
        raise ValueError("empty response from model")

    return validate_ai_response(prompt_type, json.loads(response.text))


def test_gemini_connection(project_id: str, location: str) -> tuple[int, str]:
    test_client = create_gemini_client(project_id, location)
    started = time.time()
    response = test_client.models.generate_content(
        model=GEMINI_MODEL,
        contents='Return JSON: {"status":"ok"}',
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    elapsed = int(time.time() - started)
    return elapsed, response.text
