import type {
  AssigneeResolveResponse,
  ConfigDefaultsResponse,
  EpicIssue,
  CreateIssuesResponse,
  IssueFieldsPreviewResponse,
  IssueType,
  JiraCreateSettings,
  JiraIssueSettings,
  StoryGenerationResult,
  TaskGenerationResult,
} from "./types";

const FALLBACK_API_BASE_URL = "http://localhost:8000";

export const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || FALLBACK_API_BASE_URL;

async function requestJson<T>(
  apiBaseUrl: string,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }

  return response.json() as Promise<T>;
}

export function health(apiBaseUrl: string): Promise<{ status: string }> {
  return requestJson(apiBaseUrl, "/health");
}

export function getConfigDefaults(apiBaseUrl: string): Promise<ConfigDefaultsResponse> {
  return requestJson(apiBaseUrl, "/config/defaults");
}

export function testGemini(apiBaseUrl: string): Promise<{ elapsed_seconds: number; response_text: string }> {
  return requestJson(apiBaseUrl, "/test-gemini", {
    method: "POST",
  });
}

export function resolveAssignee(
  apiBaseUrl: string,
  jiraServer: string,
  assigneeName: string,
): Promise<AssigneeResolveResponse> {
  return requestJson(apiBaseUrl, "/jira/resolve-assignee", {
    method: "POST",
    body: JSON.stringify({
      jira_server: jiraServer,
      assignee_name: assigneeName,
    }),
  });
}

export function generateStory(
  apiBaseUrl: string,
  projectContext: string,
  brief: string,
) {
  return requestJson<{ prompt_type: "story"; data: StoryGenerationResult }>(
    apiBaseUrl,
    "/generate/story",
    {
      method: "POST",
      body: JSON.stringify({
        project_context: projectContext,
        brief,
      }),
    },
  );
}

export function generateTask(
  apiBaseUrl: string,
  projectContext: string,
  brief: string,
) {
  return requestJson<{ prompt_type: "task"; data: TaskGenerationResult }>(
    apiBaseUrl,
    "/generate/task",
    {
      method: "POST",
      body: JSON.stringify({
        project_context: projectContext,
        brief,
      }),
    },
  );
}

export function previewEpic(
  apiBaseUrl: string,
  jira: JiraIssueSettings,
  epic: EpicIssue,
): Promise<IssueFieldsPreviewResponse> {
  return requestJson(apiBaseUrl, "/preview/epic", {
    method: "POST",
    body: JSON.stringify({
      jira,
      epic,
    }),
  });
}

export function previewStory(
  apiBaseUrl: string,
  jira: JiraIssueSettings,
  story: StoryGenerationResult,
  epicKey?: string,
): Promise<IssueFieldsPreviewResponse> {
  return requestJson(apiBaseUrl, "/preview/story", {
    method: "POST",
    body: JSON.stringify({
      jira,
      story,
      epic_key: epicKey || null,
    }),
  });
}

export function previewTask(
  apiBaseUrl: string,
  jira: JiraIssueSettings,
  task: TaskGenerationResult,
  issueType: IssueType,
  parentKey?: string,
): Promise<IssueFieldsPreviewResponse> {
  return requestJson(apiBaseUrl, "/preview/task", {
    method: "POST",
    body: JSON.stringify({
      jira,
      task,
      issue_type: issueType,
      parent_key: parentKey || null,
    }),
  });
}

export function createEpic(
  apiBaseUrl: string,
  jira: JiraCreateSettings,
  epic: EpicIssue,
): Promise<CreateIssuesResponse> {
  return requestJson(apiBaseUrl, "/create/epic", {
    method: "POST",
    body: JSON.stringify({
      jira,
      epic,
    }),
  });
}

export function createStory(
  apiBaseUrl: string,
  jira: JiraCreateSettings,
  story: StoryGenerationResult,
  epicKey?: string,
): Promise<CreateIssuesResponse> {
  return requestJson(apiBaseUrl, "/create/story", {
    method: "POST",
    body: JSON.stringify({
      jira,
      story,
      epic_key: epicKey || null,
    }),
  });
}

export function createTask(
  apiBaseUrl: string,
  jira: JiraCreateSettings,
  task: TaskGenerationResult,
  issueType: IssueType,
  parentKey?: string,
): Promise<CreateIssuesResponse> {
  return requestJson(apiBaseUrl, "/create/task", {
    method: "POST",
    body: JSON.stringify({
      jira,
      task,
      issue_type: issueType,
      parent_key: parentKey || null,
    }),
  });
}
