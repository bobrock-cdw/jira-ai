import os
from dataclasses import dataclass

from google.genai import types

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


if load_dotenv:
    load_dotenv()


DEFAULT_GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "cdw-gemini-cli-sbx")
DEFAULT_GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
DEFAULT_JIRA_SERVER = os.getenv("JIRA_SERVER", "https://projectultron.atlassian.net")
DEFAULT_JIRA_PROJECT = os.getenv("JIRA_PROJECT_KEY", os.getenv("JIRA_PROJECT", "MC"))
DEFAULT_JIRA_COMPONENT = os.getenv("JIRA_COMPONENT", "Cloud")
DEFAULT_JIRA_ASSIGNEE = os.getenv("JIRA_ASSIGNEE", "Bob Rock")
LARGE_PASTE_WARNING_CHARS = 4096
MAX_BRIEF_CHARS = 500_000
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_REQUEST_TIMEOUT_MS = 120_000
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


@dataclass(frozen=True)
class SessionConfig:
    jira_server: str
    jira_project_key: str
    jira_component_name: str
    jira_assignee_username: str
    gcp_project_id: str
    gcp_location: str
    project_context: str


@dataclass(frozen=True)
class JiraCredentials:
    username: str
    token: str


def get_jira_credentials() -> JiraCredentials | None:
    username = os.getenv("JIRA_USERNAME")
    token = os.getenv("JIRA_API_TOKEN")
    if not (username and token):
        return None
    return JiraCredentials(username=username, token=token)


def get_cors_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS")
    if not raw_origins:
        return list(DEFAULT_CORS_ORIGINS)
    return [
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip()
    ]


def build_gemini_http_options() -> types.HttpOptions:
    return types.HttpOptions(
        timeout=GEMINI_REQUEST_TIMEOUT_MS,
        # Fail fast on quota/rate limits instead of retrying silently for minutes.
        retry_options=types.HttpRetryOptions(
            attempts=2,
            http_status_codes=[500, 502, 503, 504],
        ),
    )
