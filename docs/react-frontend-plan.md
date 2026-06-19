# React Frontend Plan

## Goal

Build a React + Vite frontend that lets users generate, preview, edit, and create Jira Stories and Tasks through the FastAPI backend in `api.py`.

The frontend should not duplicate business logic. It should call the API endpoints, display returned data clearly, let users edit generated content, and require explicit approval before calling Jira creation endpoints.

## Prerequisites

Install Node.js before scaffolding the frontend:

```sh
node --version
npm --version
```

If those commands are unavailable, install Node.js with your preferred package manager or from the official installer.

## Initial Structure

```text
frontend/
  package.json
  index.html
  vite.config.ts
  tsconfig.json
  src/
    App.tsx
    api.ts
    types.ts
    main.tsx
    styles.css
```

## API Endpoints Used

See `docs/api-usage.md` for request and response examples.

- `GET /health` — verify backend is running.
- `POST /test-gemini` — verify Vertex AI/Gemini connectivity.
- `POST /generate/story` — generate Story JSON from context and brief.
- `POST /generate/task` — generate Task JSON from context and brief.
- `POST /preview/story` — preview Jira payloads for Story plus Sub-tasks.
- `POST /preview/task` — preview Jira payloads for Task/Sub-task.
- `POST /create/story` — create approved Story plus Sub-tasks in Jira.
- `POST /create/task` — create approved Task/Sub-task in Jira.

## MVP Screens

### 1. Settings Panel

Fields:

- API base URL, default `http://localhost:8000`
- GCP project ID
- GCP location
- Jira server URL
- Jira project key
- Jira component
- Jira assignee account ID
- Project context

Actions:

- Test backend health
- Test Gemini

### 2. Generate Work Item

Fields:

- Issue workflow: Story or Task
- Parent Epic key for Story, optional
- Parent key for Task/Sub-task, optional
- Large brief text area

Actions:

- Generate
- Retry
- Clear

### 3. Review and Edit

For Story:

- Title
- User story
- Acceptance criteria
- Generated implementation tasks

For Task:

- Title
- Description
- Generated subtasks

Actions:

- Preview Jira payload
- Create in Jira

### 4. Results

Display:

- Created issue type
- Created Jira key
- Clickable Jira URL

## Safety Rules

- Always call preview before create.
- Show a clear warning before calling `/create/story` or `/create/task`.
- Do not store Jira API tokens in browser local storage.
- Use server-side environment variables for Jira credentials.
- Treat create endpoints as real production actions.

## Implementation Order

1. Scaffold Vite React app.
2. Add API client functions in `src/api.ts`.
3. Add shared TypeScript types in `src/types.ts`.
4. Build settings and health/Gemini test panel.
5. Build generate form for Story and Task.
6. Build editable review panels.
7. Build preview payload display.
8. Add create actions and results panel.
9. Add basic error handling and loading states.
10. Update README with frontend run instructions.

## Scaffold Commands

After Node.js is installed:

```sh
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm run dev
```

The backend should run separately:

```sh
uvicorn api:app --reload
```
