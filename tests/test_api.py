import unittest

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:
    TestClient = None


@unittest.skipIf(TestClient is None, "FastAPI test dependencies are not installed")
class ApiTests(unittest.TestCase):
    def setUp(self):
        import api

        self.api = api
        self.client = TestClient(api.app)

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_preview_story_endpoint(self):
        response = self.client.post(
            "/preview/story",
            json={
                "jira": {
                    "project_key": "MC",
                    "component_name": "Cloud",
                    "assignee_account_id": "abc123",
                },
                "epic_key": "MC-1",
                "story": {
                    "title": "Story title",
                    "user_story": "As a user, I want value.",
                    "acceptance_criteria": "First; Second",
                    "tasks": [{"title": "Build", "description": "Do work"}],
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        fields = response.json()["fields"]
        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0]["issuetype"]["name"], "Story")
        self.assertEqual(fields[1]["parent"]["key"], "<created-story-key>")

    def test_create_task_endpoint_uses_mocked_jira_creation(self):
        from core.config import JiraCredentials
        from core.service import CreatedIssue

        self.api.get_jira_credentials = lambda: JiraCredentials(
            username="user",
            token="token",
        )
        self.api.create_jira_client = lambda server, credentials: object()
        self.api.create_task_with_subtasks = (
            lambda jira_client, context, task_data, issue_type, parent=None: [
                CreatedIssue(issue_type=issue_type, key="MC-200")
            ]
        )

        response = self.client.post(
            "/create/task",
            json={
                "jira": {"project_key": "MC"},
                "issue_type": "Task",
                "task": {
                    "title": "Task title",
                    "description": "Task description",
                    "subtasks": [],
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"created": [{"issue_type": "Task", "key": "MC-200"}]},
        )


if __name__ == "__main__":
    unittest.main()
