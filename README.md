# Jira-AI: AI-Powered Jira Issue Creation

Jira-AI is an AI-assisted Jira issue creation tool that converts plain-language requirements into consistent, structured Jira work items and integrates directly with Jira using automated API access. It currently runs as an interactive CLI and uses Google Gemini on Vertex AI to generate Stories, Tasks, acceptance criteria, and child Sub-tasks after the user provides project context and a brief.

The tool keeps a human in control: Gemini generates a proposed draft, the user reviews it, and Jira issues are created only after explicit approval. Epics are currently created manually, while Stories and Tasks are AI-assisted.

## What It Does

- Creates Jira Epics manually from a title and description.
- Generates AI-assisted Stories with user story text, acceptance criteria, and implementation Sub-tasks.
- Generates AI-assisted Tasks with optional implementation Sub-tasks.
- Creates approved issues in Jira with project, component, assignee, and parent issue metadata.
- Logs generated AI output to `logs/deliberation_YYYYMMDD_HHMMSS.json`.
- Supports large input through macOS clipboard, file path, or terminal input.
- Validates and normalizes Gemini responses with Pydantic before the CLI uses them.

## Current Architecture

The project has been refactored so the reusable business logic lives in `core/`, while `jira-ai.py` remains the interactive CLI wrapper.

```text
jira-ai.py              # CLI prompts, menu flow, review/approve interaction
core/
  __init__.py
  config.py             # defaults, session config, credentials, Gemini HTTP options
  models.py             # Pydantic models for Gemini Story/Task responses
  gemini.py             # Gemini client, prompts, generation, connectivity test
  jira_client.py        # Jira client, assignee lookup, issue field construction
  formatter.py          # Jira description formatting
  service.py            # Story/Task creation workflows using core helpers
```

This structure prepares the project for a future FastAPI + React UI because the API can call the same `core/` functions that the CLI uses today.

## Requirements

- Python 3.8+
- Jira Cloud account with issue creation permissions
- Jira API token
- Google Cloud project with Vertex AI enabled
- GCP Application Default Credentials configured

Install the core dependencies:

```sh
pip install -r requirements.txt
```

Authenticate with Google Cloud:

```sh
gcloud auth application-default login
```

Set Jira credentials in your shell:

```sh
export JIRA_USERNAME=your.email@company.com
export JIRA_API_TOKEN=your-jira-api-token
```

Or copy `.env.example` to `.env` and fill in your local values:

```sh
cp .env.example .env
```

`.env` is ignored by git and can provide Jira credentials plus defaults for Jira server, project, component, assignee, GCP project, GCP location, and Gemini model.

## Running

Test Gemini connectivity without starting Jira setup:

```sh
python3 -u jira-ai.py --test-gemini
```

Or use the shortcut:

```sh
make test-gemini
```

Run the CLI:

```sh
python3 -u jira-ai.py
```

Or use:

```sh
make run-cli
```

At startup, the script prompts for:

- Jira server URL
- Jira project key
- Jira component
- Jira assignee display name
- GCP project ID
- GCP region
- Project/technical context

Then it authenticates to Jira, resolves the assignee account ID, and shows the main menu:

```text
1. Epic | 2. Story | 3. Task/SubTask | 4. Exit
```

## Testing

Run the lightweight automated test suite:

```sh
python3 -m unittest discover
```

Or use:

```sh
make test
```

Run syntax checks plus tests:

```sh
make check
```

Core tests use only the standard library test runner. API tests require the optional FastAPI dependencies from `requirements-api.txt`; they mock Jira creation helpers and do not create live Jira issues.

## Input Options

When the script asks for a brief or description, it offers three input methods:

- `c` — Clipboard, recommended for large documents on macOS using `pbpaste`
- `f` — File path, reads a local UTF-8 file
- `t` — Terminal input, reads until `DONE` is typed on its own line

Terminal input warns after `4096` characters. All input methods enforce a maximum brief size of `500,000` characters.

## AI Generation

Gemini generation uses:

- Model: `gemini-2.5-flash`
- Vertex AI mode
- JSON response mode
- Temperature: `0.2`
- 120-second HTTP timeout
- fast failure on rate-limit errors instead of silent long retry loops

Story responses are validated into this shape:

```json
{
  "title": "...",
  "user_story": "...",
  "acceptance_criteria": ["...", "..."],
  "tasks": [
    {"title": "...", "description": "..."}
  ]
}
```

Task responses are validated into this shape:

```json
{
  "title": "...",
  "description": "...",
  "subtasks": [
    {"title": "...", "description": "..."}
  ]
}
```

If Gemini returns `acceptance_criteria` as a single string, the Pydantic model normalizes it into a list before Jira issue creation.

## Jira Creation Flow

For Stories, the CLI:

1. Collects an optional Epic key.
2. Generates Story content with Gemini.
3. Logs and displays the generated JSON.
4. Lets the user create, retry, or cancel.
5. Creates the Story and generated Sub-tasks after approval.

For Tasks, the CLI:

1. Lets the user choose Task or Sub-task.
2. Collects an optional parent key.
3. Generates Task content with Gemini.
4. Logs and displays the generated JSON.
5. Creates the Task/Sub-task and any generated Sub-tasks after approval.

## Optional FastAPI Backend

The repo includes a minimal FastAPI backend skeleton in `api.py`. It reuses the same `core/` Gemini logic as the CLI and is intended as the starting point for a future React UI.

Install optional API dependencies:

```sh
pip install -r requirements-api.txt
```

Run the API:

```sh
uvicorn api:app --reload
```

Or use:

```sh
make run-api
```

Initial endpoints:

- `GET /health`
- `POST /test-gemini`
- `POST /generate/story`
- `POST /generate/task`
- `POST /preview/story`
- `POST /preview/task`
- `POST /create/story`
- `POST /create/task`

The preview endpoints return the Jira field payloads that would be sent to Jira, without creating any issues. The create endpoints use `JIRA_USERNAME` and `JIRA_API_TOKEN` from the server environment and create real Jira issues, so use the preview endpoints first when testing UI flows.

Detailed API request and response examples are documented in `docs/api-usage.md`.

For browser-based development, the API enables CORS for Vite's default localhost origins:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

Override this with a comma-separated `CORS_ORIGINS` value in `.env`.

## Future React Frontend

A React + Vite frontend plan is documented in `docs/react-frontend-plan.md`. Node.js is required before scaffolding and building the frontend.

## Notes and Limitations

- Epics are manual only; there is no AI-generated Epic-to-Story breakdown yet.
- Clipboard input currently uses macOS `pbpaste`.
- Assignee lookup uses the first Jira user match.
- `.env` support, dry-run mode, custom fields, and a FastAPI + React UI are planned future improvements.
- Deliberation logs are useful for debugging or audit history, but they are not required for the script to run.