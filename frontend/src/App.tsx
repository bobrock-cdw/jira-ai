import { useState } from "react";
import {
  DEFAULT_API_BASE_URL,
  createEpic,
  createStory,
  createTask,
  generateStory,
  generateTask,
  getConfigDefaults,
  health,
  previewEpic,
  previewStory,
  previewTask,
  resolveAssignee,
  testGemini,
} from "./api";
import type {
  CreateIssuesResponse,
  EpicIssue,
  GeneratedTask,
  IssueFieldsPreviewResponse,
  IssueType,
  JiraCreateSettings,
  JiraIssueSettings,
  StoryGenerationResult,
  TaskGenerationResult,
} from "./types";

const DEFAULT_JIRA_SERVER = import.meta.env.VITE_JIRA_SERVER || "";
const DEFAULT_JIRA_PROJECT_KEY = import.meta.env.VITE_JIRA_PROJECT_KEY || "";
const DEFAULT_JIRA_COMPONENT = import.meta.env.VITE_JIRA_COMPONENT || "";
const DEFAULT_JIRA_ASSIGNEE = import.meta.env.VITE_JIRA_ASSIGNEE || "";

type Workflow = "epic" | "story" | "task";

function canPreview(
  workflow: Workflow,
  epic: EpicIssue,
  story: StoryGenerationResult | null,
  task: TaskGenerationResult | null,
) {
  if (workflow === "epic") return Boolean(epic.title && epic.description);
  if (workflow === "story") return Boolean(story);
  return Boolean(task);
}

function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [jiraServer, setJiraServer] = useState(DEFAULT_JIRA_SERVER);
  const [jiraServers, setJiraServers] = useState(
    DEFAULT_JIRA_SERVER ? [DEFAULT_JIRA_SERVER] : [],
  );
  const [projectKey, setProjectKey] = useState(DEFAULT_JIRA_PROJECT_KEY);
  const [componentName, setComponentName] = useState(DEFAULT_JIRA_COMPONENT);
  const [assigneeName, setAssigneeName] = useState(DEFAULT_JIRA_ASSIGNEE);
  const [assigneeAccountId, setAssigneeAccountId] = useState("");
  const [projectContext, setProjectContext] = useState("");
  const [workflow, setWorkflow] = useState<Workflow>("story");
  const [issueType, setIssueType] = useState<IssueType>("Task");
  const [parentKey, setParentKey] = useState("");
  const [brief, setBrief] = useState("");
  const [epic, setEpic] = useState<EpicIssue>({ title: "", description: "" });
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

  async function handleLoadDefaults() {
    await runAction(async () => {
      const defaults = await getConfigDefaults(apiBaseUrl);
      setJiraServer(defaults.jira_server);
      setJiraServers(defaults.jira_servers);
      setProjectKey(defaults.jira_project_key);
      setComponentName(defaults.jira_component);
      setAssigneeName(defaults.jira_assignee);
      setMessage("Loaded backend defaults.");
    });
  }

  async function handleResolveAssignee() {
    await runAction(async () => {
      const result = await resolveAssignee(apiBaseUrl, jiraServer, assigneeName);
      setAssigneeAccountId(result.account_id);
      setMessage(`Resolved ${result.assignee_name} to ${result.account_id}.`);
    });
  }

  async function handleTestGemini() {
    await runAction(async () => {
      const result = await testGemini(apiBaseUrl);
      setMessage(`Gemini OK in ${result.elapsed_seconds}s: ${result.response_text}`);
    });
  }

  function handleWorkflowChange(nextWorkflow: Workflow) {
    setWorkflow(nextWorkflow);
    setPreview(null);
    setCreated(null);
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
        );
        setStory(result.data);
        setTask(null);
      } else {
        const result = await generateTask(
          apiBaseUrl,
          projectContext,
          brief,
        );
        setTask(result.data);
        setStory(null);
      }
    });
  }

  async function handlePreview() {
    await runAction(async () => {
      if (workflow === "epic") {
        setPreview(await previewEpic(apiBaseUrl, jiraSettings, epic));
      }
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
      if (workflow === "epic") {
        setCreated(await createEpic(apiBaseUrl, jiraCreateSettings, epic));
      }
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
            Jira Server
            <select value={jiraServer} onChange={(e) => setJiraServer(e.target.value)}>
              {jiraServers.length === 0 && <option value="">Load backend defaults</option>}
              {jiraServers.map((server) => (
                <option key={server} value={server}>{server}</option>
              ))}
            </select>
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
            Assignee Name
            <input value={assigneeName} onChange={(e) => setAssigneeName(e.target.value)} />
          </label>
          <label>
            Assignee Account ID
            <input value={assigneeAccountId} onChange={(e) => setAssigneeAccountId(e.target.value)} />
          </label>
          <div className="button-row">
            <button onClick={handleLoadDefaults} disabled={loading}>Load Backend Defaults</button>
            <button onClick={handleResolveAssignee} disabled={loading || !jiraServer || !assigneeName}>
              Resolve Assignee
            </button>
            <button onClick={handleHealth} disabled={loading}>Test Backend</button>
            <button onClick={handleTestGemini} disabled={loading}>Test Gemini</button>
          </div>
        </div>

        <div className="card">
          <h2>Generate</h2>
          <label>
            Workflow
            <select value={workflow} onChange={(e) => handleWorkflowChange(e.target.value as Workflow)}>
              <option value="epic">Epic</option>
              <option value="story">Story</option>
              <option value="task">Task</option>
            </select>
          </label>
          {workflow === "epic" && (
            <>
              <label>
                Epic Title
                <input
                  value={epic.title}
                  onChange={(e) => setEpic({ ...epic, title: e.target.value })}
                />
              </label>
              <label>
                Epic Description
                <textarea
                  value={epic.description}
                  onChange={(e) => setEpic({ ...epic, description: e.target.value })}
                />
              </label>
            </>
          )}
          {workflow === "task" && (
            <label>
              Issue Type
              <select value={issueType} onChange={(e) => setIssueType(e.target.value as IssueType)}>
                <option value="Task">Task</option>
                <option value="Sub-task">Sub-task</option>
              </select>
            </label>
          )}
          {workflow !== "epic" && (
            <>
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
            </>
          )}
        </div>
      </section>

      <section className="card">
        <h2>Review</h2>
        {workflow === "epic" && (
          <EpicEditor epic={epic} onChange={setEpic} />
        )}
        {workflow === "story" && story && (
          <StoryEditor story={story} onChange={setStory} />
        )}
        {workflow === "task" && task && (
          <TaskEditor task={task} onChange={setTask} />
        )}
        <div className="button-row">
          <button onClick={handlePreview} disabled={loading || !canPreview(workflow, epic, story, task)}>
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

function EpicEditor({
  epic,
  onChange,
}: {
  epic: EpicIssue;
  onChange: (epic: EpicIssue) => void;
}) {
  return (
    <div className="editor-grid">
      <label>
        Title
        <input value={epic.title} onChange={(e) => onChange({ ...epic, title: e.target.value })} />
      </label>
      <label>
        Description
        <textarea value={epic.description} onChange={(e) => onChange({ ...epic, description: e.target.value })} />
      </label>
    </div>
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
      <ChildItemEditor
        items={story.tasks}
        label="Implementation Tasks"
        onChange={(tasks) => onChange({ ...story, tasks })}
      />
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
      <ChildItemEditor
        items={task.subtasks}
        label="Sub-tasks"
        onChange={(subtasks) => onChange({ ...task, subtasks })}
      />
    </div>
  );
}

function ChildItemEditor({
  items,
  label,
  onChange,
}: {
  items: GeneratedTask[];
  label: string;
  onChange: (items: GeneratedTask[]) => void;
}) {
  function updateItem(index: number, patch: Partial<GeneratedTask>) {
    onChange(items.map((item, itemIndex) => (
      itemIndex === index ? { ...item, ...patch } : item
    )));
  }

  function removeItem(index: number) {
    onChange(items.filter((_, itemIndex) => itemIndex !== index));
  }

  function addItem() {
    onChange([...items, { title: "", description: "" }]);
  }

  return (
    <section className="child-editor">
      <div className="section-heading">
        <h3>{label}</h3>
        <button type="button" onClick={addItem}>Add</button>
      </div>
      {items.length === 0 && <p className="empty-state">No child items yet.</p>}
      {items.map((item, index) => (
        <div className="child-item" key={index}>
          <label>
            Title
            <input
              value={item.title}
              onChange={(e) => updateItem(index, { title: e.target.value })}
            />
          </label>
          <label>
            Description
            <textarea
              value={item.description}
              onChange={(e) => updateItem(index, { description: e.target.value })}
            />
          </label>
          <button type="button" onClick={() => removeItem(index)}>Remove</button>
        </div>
      ))}
    </section>
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
