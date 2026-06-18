import os
from dataclasses import dataclass

from google.genai import types


DEFAULT_GCP_PROJECT_ID = "cdw-gemini-cli-sbx"
DEFAULT_GCP_LOCATION = "us-central1"
DEFAULT_JIRA_SERVER = "https://projectultron.atlassian.net"
DEFAULT_JIRA_PROJECT = "MC"
DEFAULT_JIRA_COMPONENT = "Cloud"
DEFAULT_JIRA_ASSIGNEE = "Bob Rock"
LARGE_PASTE_WARNING_CHARS = 4096
MAX_BRIEF_CHARS = 500_000
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_REQUEST_TIMEOUT_MS = 120_000


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


def build_gemini_http_options() -> types.HttpOptions:
    return types.HttpOptions(
        timeout=GEMINI_REQUEST_TIMEOUT_MS,
        # Fail fast on quota/rate limits instead of retrying silently for minutes.
        retry_options=types.HttpRetryOptions(
            attempts=2,
            http_status_codes=[500, 502, 503, 504],
        ),
    )
