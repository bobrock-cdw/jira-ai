# FastAPI Usage Examples

These examples assume the backend is running locally:

```sh
uvicorn api:app --reload
```

Base URL:

```text
http://localhost:8000
```

## Recommended Frontend Flow

1. Call `GET /health` to confirm the backend is available.
2. Call `GET /config/defaults` to prefill non-secret backend defaults.
3. Call `POST /jira/resolve-assignee` to turn an assignee display name into a Jira account ID.
4. Call `POST /test-gemini` from the settings screen to confirm Vertex AI access.
5. Call `POST /generate/story` or `POST /generate/task` to generate AI content.
6. Let the user edit the generated content in the React UI.
7. Call `POST /preview/story` or `POST /preview/task` to show the exact Jira payloads.
8. Require explicit user confirmation.
9. Call `POST /create/story` or `POST /create/task` to create real Jira issues.

Use preview endpoints before create endpoints. The create endpoints call Jira and create real issues.

## Health Check

```sh
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

## Config Defaults

```sh
curl http://localhost:8000/config/defaults
```

Example response:

```json
{
  "gcp_project_id": "your-gcp-project-id",
  "gcp_location": "us-central1",
  "gemini_model": "gemini-2.5-flash",
  "jira_server": "https://yourcompany.atlassian.net",
  "jira_project_key": "MC",
  "jira_component": "Cloud",
  "jira_assignee": "Your Name"
}
```

## Resolve Jira Assignee

This endpoint uses server-side Jira credentials from `JIRA_USERNAME` and `JIRA_API_TOKEN`.

```sh
curl -X POST http://localhost:8000/jira/resolve-assignee \
  -H "Content-Type: application/json" \
  -d '{
    "jira_server": "https://yourcompany.atlassian.net",
    "assignee_name": "Your Name"
  }'
```

Example response:

```json
{
  "assignee_name": "Your Name",
  "account_id": "abc123"
}
```

## Test Gemini

```sh
curl -X POST http://localhost:8000/test-gemini \
  -H "Content-Type: application/json" \
  -d '{}'
```

Example response:

```json
{
  "elapsed_seconds": 1,
  "response_text": "{\"status\":\"ok\"}"
}
```

## Generate Story

```sh
curl -X POST http://localhost:8000/generate/story \
  -H "Content-Type: application/json" \
  -d '{
    "project_context": "Python CLI and FastAPI app for Jira automation",
    "brief": "Create a login audit trail for administrator actions"
  }'
```

Example response shape:

```json
{
  "prompt_type": "story",
  "data": {
    "title": "Create Administrator Login Audit Trail",
    "user_story": "As an administrator...",
    "acceptance_criteria": ["..."],
    "tasks": [
      {
        "title": "Implement audit event persistence",
        "description": "..."
      }
    ]
  }
}
```

## Generate Task

```sh
curl -X POST http://localhost:8000/generate/task \
  -H "Content-Type: application/json" \
  -d '{
    "project_context": "Python CLI and FastAPI app for Jira automation",
    "brief": "Add backend validation for Jira payload preview requests"
  }'
```

## Preview Story Payloads

```sh
curl -X POST http://localhost:8000/preview/story \
  -H "Content-Type: application/json" \
  -d '{
    "jira": {
      "project_key": "MC",
      "component_name": "Cloud",
      "assignee_account_id": "abc123"
    },
    "epic_key": "MC-100",
    "story": {
      "title": "Create Administrator Login Audit Trail",
      "user_story": "As an administrator, I want login actions to be audited.",
      "acceptance_criteria": ["Audit event is stored", "Audit event includes actor and timestamp"],
      "tasks": [
        {
          "title": "Implement audit persistence",
          "description": "Create backend storage for login audit events."
        }
      ]
    }
  }'
```

Example response shape:

```json
{
  "fields": [
    {
      "project": {"key": "MC"},
      "summary": "Create Administrator Login Audit Trail",
      "description": "As an administrator...",
      "issuetype": {"name": "Story"},
      "assignee": {"accountId": "abc123"},
      "components": [{"name": "Cloud"}],
      "parent": {"key": "MC-100"}
    },
    {
      "project": {"key": "MC"},
      "summary": "Implement audit persistence",
      "description": "Create backend storage for login audit events.",
      "issuetype": {"name": "Sub-task"},
      "assignee": {"accountId": "abc123"},
      "components": [{"name": "Cloud"}],
      "parent": {"key": "<created-story-key>"}
    }
  ]
}
```

## Preview Task Payloads

```sh
curl -X POST http://localhost:8000/preview/task \
  -H "Content-Type: application/json" \
  -d '{
    "jira": {
      "project_key": "MC"
    },
    "issue_type": "Task",
    "task": {
      "title": "Add payload validation",
      "description": "Validate API preview requests before building Jira payloads.",
      "subtasks": [
        {
          "title": "Add request validation tests",
          "description": "Cover missing and malformed preview inputs."
        }
      ]
    }
  }'
```

## Create Story

This endpoint creates real Jira issues. Ensure `JIRA_USERNAME` and `JIRA_API_TOKEN` are set in the backend environment first.

```sh
curl -X POST http://localhost:8000/create/story \
  -H "Content-Type: application/json" \
  -d '{
    "jira": {
      "jira_server": "https://yourcompany.atlassian.net",
      "project_key": "MC",
      "component_name": "Cloud",
      "assignee_account_id": "abc123"
    },
    "epic_key": "MC-100",
    "story": {
      "title": "Create Administrator Login Audit Trail",
      "user_story": "As an administrator, I want login actions to be audited.",
      "acceptance_criteria": ["Audit event is stored"],
      "tasks": []
    }
  }'
```

Example response:

```json
{
  "created": [
    {
      "issue_type": "Story",
      "key": "MC-123"
    }
  ]
}
```

## Create Task

This endpoint creates real Jira issues. Use `/preview/task` first.

```sh
curl -X POST http://localhost:8000/create/task \
  -H "Content-Type: application/json" \
  -d '{
    "jira": {
      "jira_server": "https://yourcompany.atlassian.net",
      "project_key": "MC"
    },
    "issue_type": "Task",
    "task": {
      "title": "Add payload validation",
      "description": "Validate API preview requests before building Jira payloads.",
      "subtasks": []
    }
  }'
```

## Browser Development Notes

The backend allows the default Vite origins:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

Override them with:

```ini
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```
