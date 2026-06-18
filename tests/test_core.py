import unittest

from core.formatter import format_story_description
from core.jira_client import build_issue_fields
from core.models import validate_ai_response
from core.service import (
    JiraIssueContext,
    preview_story_issue_fields,
    preview_task_issue_fields,
)


class CoreModelTests(unittest.TestCase):
    def test_story_acceptance_criteria_string_is_normalized(self):
        data = validate_ai_response(
            "story",
            {
                "title": " Test Story ",
                "user_story": " As a user, I want value. ",
                "acceptance_criteria": "First criterion; Second criterion",
                "tasks": [{"title": " Build ", "description": " Do work "}],
            },
        )

        self.assertEqual(data["title"], "Test Story")
        self.assertEqual(
            data["acceptance_criteria"],
            ["First criterion", "Second criterion"],
        )
        self.assertEqual(data["tasks"][0]["description"], "Do work")

    def test_task_response_is_normalized(self):
        data = validate_ai_response(
            "task",
            {
                "title": " Task title ",
                "description": " Task description ",
                "subtasks": [{"title": " Sub ", "description": " Detail "}],
            },
        )

        self.assertEqual(data["title"], "Task title")
        self.assertEqual(data["subtasks"][0]["title"], "Sub")


class CoreFormattingTests(unittest.TestCase):
    def test_story_description_format(self):
        story_data = {
            "user_story": "As a user, I want value.",
            "acceptance_criteria": ["First", "Second"],
        }

        self.assertEqual(
            format_story_description(story_data),
            "As a user, I want value.\n\nAcceptance Criteria:\n- First\n- Second",
        )


class JiraPayloadTests(unittest.TestCase):
    def test_build_issue_fields_omits_empty_optional_fields(self):
        fields = build_issue_fields(
            project_key="MC",
            issue_type="Epic",
            summary="Title",
            description="Description",
        )

        self.assertNotIn("assignee", fields)
        self.assertNotIn("components", fields)
        self.assertNotIn("parent", fields)

    def test_preview_story_issue_fields(self):
        context = JiraIssueContext(
            project_key="MC",
            component_name="Cloud",
            assignee_account_id="abc123",
        )
        story_data = {
            "title": "Story title",
            "user_story": "As a user, I want value.",
            "acceptance_criteria": ["First"],
            "tasks": [{"title": "Build", "description": "Do work"}],
        }

        fields = preview_story_issue_fields(context, story_data, epic_key="MC-1")

        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0]["issuetype"]["name"], "Story")
        self.assertEqual(fields[0]["parent"]["key"], "MC-1")
        self.assertEqual(fields[1]["issuetype"]["name"], "Sub-task")
        self.assertEqual(fields[1]["parent"]["key"], "<created-story-key>")

    def test_preview_task_issue_fields(self):
        context = JiraIssueContext(project_key="MC")
        task_data = {
            "title": "Task title",
            "description": "Task description",
            "subtasks": [{"title": "Subtask", "description": "Subtask detail"}],
        }

        fields = preview_task_issue_fields(context, task_data, issue_type="Task")

        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0]["issuetype"]["name"], "Task")
        self.assertEqual(fields[1]["parent"]["key"], "<created-task-key>")


if __name__ == "__main__":
    unittest.main()
