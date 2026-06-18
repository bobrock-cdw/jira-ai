from dataclasses import dataclass
from typing import Any

from jira import JIRA

from core.formatter import format_story_description
from core.jira_client import build_issue_fields, create_issue


@dataclass(frozen=True)
class JiraIssueContext:
    project_key: str
    component_name: str | None = None
    assignee_account_id: str | None = None


@dataclass(frozen=True)
class CreatedIssue:
    issue_type: str
    key: str


def create_issue_from_context(
    jira_client: JIRA,
    context: JiraIssueContext,
    issue_type: str,
    summary: str,
    description: str,
    parent: str | None = None,
) -> CreatedIssue:
    fields = build_issue_fields(
        project_key=context.project_key,
        issue_type=issue_type,
        summary=summary,
        description=description,
        component_name=context.component_name,
        assignee_account_id=context.assignee_account_id,
        parent=parent,
    )
    key = create_issue(jira_client, fields)
    return CreatedIssue(issue_type=issue_type, key=key)


def create_story_with_tasks(
    jira_client: JIRA,
    context: JiraIssueContext,
    story_data: dict[str, Any],
    epic_key: str | None = None,
) -> list[CreatedIssue]:
    created = [
        create_issue_from_context(
            jira_client=jira_client,
            context=context,
            issue_type="Story",
            summary=story_data["title"],
            description=format_story_description(story_data),
            parent=epic_key,
        )
    ]
    story_key = created[0].key
    for task in story_data["tasks"]:
        created.append(
            create_issue_from_context(
                jira_client=jira_client,
                context=context,
                issue_type="Sub-task",
                summary=task["title"],
                description=task["description"],
                parent=story_key,
            )
        )
    return created


def create_task_with_subtasks(
    jira_client: JIRA,
    context: JiraIssueContext,
    task_data: dict[str, Any],
    issue_type: str,
    parent: str | None = None,
) -> list[CreatedIssue]:
    created = [
        create_issue_from_context(
            jira_client=jira_client,
            context=context,
            issue_type=issue_type,
            summary=task_data["title"],
            description=task_data["description"],
            parent=parent,
        )
    ]
    parent_key = created[0].key
    if issue_type == "Task":
        for subtask in task_data.get("subtasks", []):
            created.append(
                create_issue_from_context(
                    jira_client=jira_client,
                    context=context,
                    issue_type="Sub-task",
                    summary=subtask["title"],
                    description=subtask["description"],
                    parent=parent_key,
                )
            )
    return created
