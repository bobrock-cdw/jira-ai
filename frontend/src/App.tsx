import { useState } from "react";
import {
  DEFAULT_API_BASE_URL,
  createStory,
  createTask,
  generateStory,
  generateTask,
  health,
  previewStory,
  previewTask,
  testGemini,
} from "./api";
import type {
  CreateIssuesResponse,
  IssueFieldsPreviewResponse,
  IssueType,
  JiraCreateSettings,
  JiraIssueSettings,
  StoryGenerationResult,
  TaskGenerationResult,
} from "./types";

const DEFAULT_GCP_PROJECT = "cdw-gemini-cli-sbx";
const DEFAULT_GCP_LOCATION = "us-central1";

type Workflow = "story" | "task";

function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [gcpProjectId, setGcpProjectId] = useState(DEFAULT_GCP_PROJECT);
  const [gcpLocation, setGcpLocation] = useState(DEFAULT_GCP_LOCATION);
  const [jiraServer, setJiraServer] = useState("https://projectultron.atlassian.net");
  const [projectKey, setProjectKey] = useState("MC");
  const [componentName, setComponentName] = useState("Cloud");
  const [assigneeAccountId, setAssigneeAccountId] = useState("");
  const [projectContext, setProjectContext] = useState("");
  const [workflow, setWorkflow] = useState<Workflow>("story");
  const [issueType, setIssueType] = useState<IssueType>("Task");
  const [parentKey, setParentKey] = useState("");
  const [brief, setBrief] = useState("");
  const [story, setStory] = useState<StoryGenerationResult | null>(null);
  const [task, setTask] = useState<TaskGenerationResult | null>(null);
  const [preview, setPreview] = useState<IssueFieldsPreviewResponse | null>(null);
  const [created, setCreated] = useState<CreateIssuesResponse | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const jiraSettings: JiraIssueSettings = {
    project_key: projectKey,
    component_name: componentName || undefined,
    assignee_account_id: assigneeAccountId || undefined,
  };

  const jiraCreateSettings: JiraCreateSettings = {
    ...jiraSettings,
    jira_server: jiraServer,
  };

  async function runAction(action: () => Promise<void>) {
    setLoading(true);
    setMessage("");
    try {
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }

  async function handleHealth() {
    await runAction(async () => {
      const result = await health(apiBaseUrl);
      setMessage(`Backend status: ${result.status}`);
    });
  }

  async function handleTestGemini() {
    await runAction(async () => {
      const result = await testGemini(apiBaseUrl, gcpProjectId, gcpLocation);
      setMessage(`Gemini OK in ${result.elapsed_seconds}s: ${result.response_text}`);
    });
  }

  async function handleGenerate() {
    await runAction(async () => {
      setPreview(null);
      setCreated(null);
      if (workflow === "story") {
        const result = await generateStory(
          apiBaseUrl,
          projectContext,
          brief,
          gcpProjectId,
          gcpLocation,
        );
        setStory(result.data);
        setTask(null);
      } else {
        const result = await generateTask(
          apiBaseUrl,
          projectContext,
          brief,
          gcpProjectId,
          gcpLocation,
        );
        setTask(result.data);
        setStory(null);
      }
    });
  }

  async function handlePreview() {
    await runAction(async () => {
      if (workflow === "story" && story) {
        setPreview(await previewStory(apiBaseUrl, jiraSettings, story, parentKey));
      }
      if (workflow === "task" && task) {
        setPreview(await previewTask(apiBaseUrl, jiraSettings, task, issueType, parentKey));
      }
    });
  }

  async function handleCreate() {
    const confirmed = window.confirm(
      "This will create real Jira issues. Continue?",
    );
    if (!confirmed) return;
    await runAction(async () => {
      if (workflow === "story" && story) {
        setCreated(await createStory(apiBaseUrl, jiraCreateSettings, story, parentKey));
      }
      if (workflow === "task" && task) {
        setCreated(await createTask(apiBaseUrl, jiraCreateSettings, task, issueType, parentKey));
      }
    });
  }

  return (
    <main className="app-shell">
      <header>
        <h1>Jira-AI</h1>
        <p>Generate, preview, and create structured Jira work items.</p>
      </header>

      <section className="grid">
        <div className="card">
          <h2>Settings</h2>
          <label>
            API URL
            <input value={apiBaseUrl} onChange={(e) => setApiBaseUrl(e.target.value)} />
          </label>
          <label>
            GCP Project
            <input value={gcpProjectId} onChange={(e) => setGcpProjectId(e.target.value)} />
          </label>
          <label>
            GCP Location
            <input value={gcpLocation} onChange={(e) => setGcpLocation(e.target.value)} />
          </label>
          <label>
            Jira Server
            <input value={jiraServer} onChange={(e) => setJiraServer(e.target.value)} />
          </label>
          <label>
            Jira Project Key
            <input value={projectKey} onChange={(e) => setProjectKey(e.target.value)} />
          </label>
          <label>
            Component
            <input value={componentName} onChange={(e) => setComponentName(e.target.value)} />
          </label>
          <label>
            Assignee Account ID
            <input value={assigneeAccountId} onChange={(e) => setAssigneeAccountId(e.target.value)} />
          </label>
          <div className="button-row">
            <button onClick={handleHealth} disabled={loading}>Test Backend</button>
            <button onClick={handleTestGemini} disabled={loading}>Test Gemini</button>
          </div>
        </div>

        <div className="card">
          <h2>Generate</h2>
          <label>
            Workflow
            <select value={workflow} onChange={(e) => setWorkflow(e.target.value as Workflow)}>
              <option value="story">Story</option>
              <option value="task">Task</option>
            </select>
          </label>
          {workflow === "task" && (
            <label>
              Issue Type
              <select value={issueType} onChange={(e) => setIssueType(e.target.value as IssueType)}>
                <option value="Task">Task</option>
                <option value="Sub-task">Sub-task</option>
              </select>
            </label>
          )}
          <label>
            Parent Key
            <input value={parentKey} onChange={(e) => setParentKey(e.target.value)} />
          </label>
          <label>
            Project Context
            <textarea value={projectContext} onChange={(e) => setProjectContext(e.target.value)} />
          </label>
          <label>
            Brief
            <textarea value={brief} onChange={(e) => setBrief(e.target.value)} />
          </label>
          <button onClick={handleGenerate} disabled={loading || !brief}>Generate</button>
        </div>
      </section>

      <section className="card">
        <h2>Review</h2>
        {workflow === "story" && story && (
          <StoryEditor story={story} onChange={setStory} />
        )}
        {workflow === "task" && task && (
          <TaskEditor task={task} onChange={setTask} />
        )}
        <div className="button-row">
          <button onClick={handlePreview} disabled={loading || (!story && !task)}>
            Preview Jira Payload
          </button>
          <button onClick={handleCreate} disabled={loading || !preview}>
            Create in Jira
          </button>
        </div>
      </section>

      {message && <pre className="message">{message}</pre>}
      {preview && <JsonPanel title="Preview Payloads" value={preview} />}
      {created && <JsonPanel title="Created Issues" value={created} />}
    </main>
  );
}

function StoryEditor({
  story,
  onChange,
}: {
  story: StoryGenerationResult;
  onChange: (story: StoryGenerationResult) => void;
}) {
  return (
    <div className="editor-grid">
      <label>
        Title
        <input value={story.title} onChange={(e) => onChange({ ...story, title: e.target.value })} />
      </label>
      <label>
        User Story
        <textarea value={story.user_story} onChange={(e) => onChange({ ...story, user_story: e.target.value })} />
      </label>
      <label>
        Acceptance Criteria (one per line)
        <textarea
          value={story.acceptance_criteria.join("\n")}
          onChange={(e) => onChange({ ...story, acceptance_criteria: e.target.value.split("\n").filter(Boolean) })}
        />
      </label>
    </div>
  );
}

function TaskEditor({
  task,
  onChange,
}: {
  task: TaskGenerationResult;
  onChange: (task: TaskGenerationResult) => void;
}) {
  return (
    <div className="editor-grid">
      <label>
        Title
        <input value={task.title} onChange={(e) => onChange({ ...task, title: e.target.value })} />
      </label>
      <label>
        Description
        <textarea value={task.description} onChange={(e) => onChange({ ...task, description: e.target.value })} />
      </label>
    </div>
  );
}

function JsonPanel({ title, value }: { title: string; value: unknown }) {
  return (
    <section className="card">
      <h2>{title}</h2>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </section>
  );
}

export default App;
