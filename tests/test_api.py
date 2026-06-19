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

    def test_config_defaults_endpoint(self):
        response = self.client.get("/config/defaults")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()),
            {
                "gemini_model",
                "jira_server",
                "jira_servers",
                "jira_project_key",
                "jira_component",
                "jira_assignee",
            },
        )

    def test_cors_preflight_allows_vite_origin(self):
        response = self.client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:5173",
        )

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

    def test_preview_epic_endpoint(self):
        response = self.client.post(
            "/preview/epic",
            json={
                "jira": {
                    "project_key": "MC",
                    "component_name": "Cloud",
                },
                "epic": {
                    "title": "Epic title",
                    "description": "Epic description",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        fields = response.json()["fields"]
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0]["issuetype"]["name"], "Epic")
        self.assertEqual(fields[0]["summary"], "Epic title")

    def test_preview_epic_plan_endpoint(self):
        response = self.client.post(
            "/preview/epic-plan",
            json={
                "jira": {"project_key": "MC"},
                "plan": {
                    "epic": {
                        "title": "Epic title",
                        "description": "Epic description",
                    },
                    "stories": [
                        {
                            "title": "Story title",
                            "user_story": "As a user, I want value.",
                            "acceptance_criteria": ["First"],
                            "tasks": [{"title": "Build", "description": "Do work"}],
                        }
                    ],
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        fields = response.json()["fields"]
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[0]["issuetype"]["name"], "Epic")
        self.assertEqual(fields[1]["parent"]["key"], "<created-epic-key>")

    def test_create_task_endpoint_uses_mocked_jira_creation(self):
        from core.config import JiraCredentials
        from core.service import CreatedIssue

        original_get_credentials = self.api.get_jira_credentials
        original_create_client = self.api.create_jira_client
        original_create_task = self.api.create_task_with_subtasks
        self.addCleanup(setattr, self.api, "get_jira_credentials", original_get_credentials)
        self.addCleanup(setattr, self.api, "create_jira_client", original_create_client)
        self.addCleanup(setattr, self.api, "create_task_with_subtasks", original_create_task)

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

    def test_create_epic_endpoint_uses_mocked_jira_creation(self):
        from core.config import JiraCredentials
        from core.service import CreatedIssue

        original_get_credentials = self.api.get_jira_credentials
        original_create_client = self.api.create_jira_client
        original_create_epic = self.api.create_epic
        self.addCleanup(setattr, self.api, "get_jira_credentials", original_get_credentials)
        self.addCleanup(setattr, self.api, "create_jira_client", original_create_client)
        self.addCleanup(setattr, self.api, "create_epic", original_create_epic)

        self.api.get_jira_credentials = lambda: JiraCredentials(
            username="user",
            token="token",
        )
        self.api.create_jira_client = lambda server, credentials: object()
        self.api.create_epic = (
            lambda jira_client, context, title, description: [
                CreatedIssue(issue_type="Epic", key="MC-100")
            ]
        )

        response = self.client.post(
            "/create/epic",
            json={
                "jira": {"project_key": "MC"},
                "epic": {
                    "title": "Epic title",
                    "description": "Epic description",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"created": [{"issue_type": "Epic", "key": "MC-100"}]},
        )

    def test_create_epic_plan_endpoint_uses_mocked_jira_creation(self):
        from core.config import JiraCredentials
        from core.service import CreatedIssue

        original_get_credentials = self.api.get_jira_credentials
        original_create_client = self.api.create_jira_client
        original_create_epic_plan = self.api.create_epic_plan
        self.addCleanup(setattr, self.api, "get_jira_credentials", original_get_credentials)
        self.addCleanup(setattr, self.api, "create_jira_client", original_create_client)
        self.addCleanup(setattr, self.api, "create_epic_plan", original_create_epic_plan)

        self.api.get_jira_credentials = lambda: JiraCredentials(
            username="user",
            token="token",
        )
        self.api.create_jira_client = lambda server, credentials: object()
        self.api.create_epic_plan = (
            lambda jira_client, context, plan_data: [
                CreatedIssue(issue_type="Epic", key="MC-100"),
                CreatedIssue(issue_type="Story", key="MC-101"),
            ]
        )

        response = self.client.post(
            "/create/epic-plan",
            json={
                "jira": {"project_key": "MC"},
                "plan": {
                    "epic": {
                        "title": "Epic title",
                        "description": "Epic description",
                    },
                    "stories": [],
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "created": [
                    {"issue_type": "Epic", "key": "MC-100"},
                    {"issue_type": "Story", "key": "MC-101"},
                ]
            },
        )

    def test_resolve_assignee_endpoint_uses_mocked_jira_lookup(self):
        from core.config import JiraCredentials

        original_get_credentials = self.api.get_jira_credentials
        original_create_client = self.api.create_jira_client
        original_resolve_assignee = self.api.resolve_assignee_account_id
        self.addCleanup(setattr, self.api, "get_jira_credentials", original_get_credentials)
        self.addCleanup(setattr, self.api, "create_jira_client", original_create_client)
        self.addCleanup(
            setattr,
            self.api,
            "resolve_assignee_account_id",
            original_resolve_assignee,
        )

        jira_client = object()
        self.api.get_jira_credentials = lambda: JiraCredentials(
            username="user",
            token="token",
        )
        self.api.create_jira_client = lambda server, credentials: jira_client
        self.api.resolve_assignee_account_id = (
            lambda client, assignee_name: "account-123"
            if client is jira_client and assignee_name == "Bob Rock"
            else None
        )

        response = self.client.post(
            "/jira/resolve-assignee",
            json={
                "jira_server": "https://example.atlassian.net",
                "assignee_name": "Bob Rock",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"assignee_name": "Bob Rock", "account_id": "account-123"},
        )


if __name__ == "__main__":
    unittest.main()
