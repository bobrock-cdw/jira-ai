from typing import Any

from jira import JIRA

from core.config import JiraCredentials


def create_jira_client(server: str, credentials: JiraCredentials) -> JIRA:
    return JIRA(
        server=server,
        basic_auth=(credentials.username, credentials.token),
    )


def get_current_user_display_name(jira_client: JIRA) -> str:
    return jira_client.myself()["displayName"]


def resolve_assignee_account_id(jira_client: JIRA, assignee_name: str) -> str | None:
    users = jira_client.search_users(query=assignee_name, maxResults=1)
    return users[0].accountId if users else None


def list_projects(jira_client: JIRA) -> list[dict[str, str]]:
    return [
        {
            "key": project.key,
            "name": project.name,
        }
        for project in jira_client.projects()
    ]


def list_components(jira_client: JIRA, project_key: str) -> list[dict[str, str]]:
    return [
        {
            "id": str(component.id),
            "name": component.name,
        }
        for component in jira_client.project_components(project_key)
    ]


def list_labels(jira_client: JIRA) -> list[str]:
    if hasattr(jira_client, "labels"):
        return sorted(str(label) for label in jira_client.labels())

    response = jira_client._session.get(f"{jira_client._options['server']}/rest/api/3/label")
    response.raise_for_status()
    data = response.json()
    values = data.get("values", [])
    return sorted(str(label) for label in values)


def build_issue_fields(
    project_key: str,
    issue_type: str,
    summary: str,
    description: str,
    component_name: str | None = None,
    assignee_account_id: str | None = None,
    labels: list[str] | None = None,
    parent: str | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "project": {"key": project_key},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
    }
    if assignee_account_id:
        fields["assignee"] = {"accountId": assignee_account_id}
    if component_name:
        fields["components"] = [{"name": component_name}]
    if labels:
        fields["labels"] = labels
    if parent:
        fields["parent"] = {"key": parent}
    return fields


def create_issue(jira_client: JIRA, fields: dict[str, Any]) -> str:
    issue = jira_client.create_issue(fields=fields)
    return issue.key
