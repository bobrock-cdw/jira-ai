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


def build_issue_fields_from_context(
    context: JiraIssueContext,
    issue_type: str,
    summary: str,
    description: str,
    parent: str | None = None,
) -> dict[str, Any]:
    return build_issue_fields(
        project_key=context.project_key,
        issue_type=issue_type,
        summary=summary,
        description=description,
        component_name=context.component_name,
        assignee_account_id=context.assignee_account_id,
        parent=parent,
    )


def create_issue_from_context(
    jira_client: JIRA,
    context: JiraIssueContext,
    issue_type: str,
    summary: str,
    description: str,
    parent: str | None = None,
) -> CreatedIssue:
    fields = build_issue_fields_from_context(
        context=context,
        issue_type=issue_type,
        summary=summary,
        description=description,
        parent=parent,
    )
    key = create_issue(jira_client, fields)
    return CreatedIssue(issue_type=issue_type, key=key)


def preview_story_issue_fields(
    context: JiraIssueContext,
    story_data: dict[str, Any],
    epic_key: str | None = None,
) -> list[dict[str, Any]]:
    story_fields = build_issue_fields_from_context(
        context=context,
        issue_type="Story",
        summary=story_data["title"],
        description=format_story_description(story_data),
        parent=epic_key,
    )
    subtask_fields = [
        build_issue_fields_from_context(
            context=context,
            issue_type="Sub-task",
            summary=task["title"],
            description=task["description"],
            parent="<created-story-key>",
        )
        for task in story_data["tasks"]
    ]
    return [story_fields, *subtask_fields]


def preview_epic_issue_fields(
    context: JiraIssueContext,
    title: str,
    description: str,
) -> list[dict[str, Any]]:
    return [
        build_issue_fields_from_context(
            context=context,
            issue_type="Epic",
            summary=title,
            description=description,
        )
    ]


def preview_epic_plan_issue_fields(
    context: JiraIssueContext,
    plan_data: dict[str, Any],
) -> list[dict[str, Any]]:
    fields = preview_epic_issue_fields(
        context=context,
        title=plan_data["epic"]["title"],
        description=plan_data["epic"]["description"],
    )
    for story in plan_data.get("stories", []):
        story_fields = preview_story_issue_fields(
            context=context,
            story_data=story,
            epic_key="<created-epic-key>",
        )
        fields.extend(story_fields)
    return fields


def preview_task_issue_fields(
    context: JiraIssueContext,
    task_data: dict[str, Any],
    issue_type: str,
    parent: str | None = None,
) -> list[dict[str, Any]]:
    task_fields = build_issue_fields_from_context(
        context=context,
        issue_type=issue_type,
        summary=task_data["title"],
        description=task_data["description"],
        parent=parent,
    )
    fields = [task_fields]
    if issue_type == "Task":
        fields.extend(
            build_issue_fields_from_context(
                context=context,
                issue_type="Sub-task",
                summary=subtask["title"],
                description=subtask["description"],
                parent="<created-task-key>",
            )
            for subtask in task_data.get("subtasks", [])
        )
    return fields


def create_epic(
    jira_client: JIRA,
    context: JiraIssueContext,
    title: str,
    description: str,
) -> list[CreatedIssue]:
    return [
        create_issue_from_context(
            jira_client=jira_client,
            context=context,
            issue_type="Epic",
            summary=title,
            description=description,
        )
    ]


def create_epic_plan(
    jira_client: JIRA,
    context: JiraIssueContext,
    plan_data: dict[str, Any],
) -> list[CreatedIssue]:
    created = create_epic(
        jira_client=jira_client,
        context=context,
        title=plan_data["epic"]["title"],
        description=plan_data["epic"]["description"],
    )
    epic_key = created[0].key
    for story in plan_data.get("stories", []):
        created.extend(
            create_story_with_tasks(
                jira_client=jira_client,
                context=context,
                story_data=story,
                epic_key=epic_key,
            )
        )
    return created


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
