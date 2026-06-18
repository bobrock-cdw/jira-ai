import type {
  CreateIssuesResponse,
  IssueFieldsPreviewResponse,
  IssueType,
  JiraCreateSettings,
  JiraIssueSettings,
  StoryGenerationResult,
  TaskGenerationResult,
} from "./types";

export const DEFAULT_API_BASE_URL = "http://localhost:8000";

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

export function testGemini(
  apiBaseUrl: string,
  gcpProjectId: string,
  gcpLocation: string,
): Promise<{ elapsed_seconds: number; response_text: string }> {
  return requestJson(apiBaseUrl, "/test-gemini", {
    method: "POST",
    body: JSON.stringify({
      gcp_project_id: gcpProjectId,
      gcp_location: gcpLocation,
    }),
  });
}

export function generateStory(
  apiBaseUrl: string,
  projectContext: string,
  brief: string,
  gcpProjectId: string,
  gcpLocation: string,
) {
  return requestJson<{ prompt_type: "story"; data: StoryGenerationResult }>(
    apiBaseUrl,
    "/generate/story",
    {
      method: "POST",
      body: JSON.stringify({
        project_context: projectContext,
        brief,
        gcp_project_id: gcpProjectId,
        gcp_location: gcpLocation,
      }),
    },
  );
}

export function generateTask(
  apiBaseUrl: string,
  projectContext: string,
  brief: string,
  gcpProjectId: string,
  gcpLocation: string,
) {
  return requestJson<{ prompt_type: "task"; data: TaskGenerationResult }>(
    apiBaseUrl,
    "/generate/task",
    {
      method: "POST",
      body: JSON.stringify({
        project_context: projectContext,
        brief,
        gcp_project_id: gcpProjectId,
        gcp_location: gcpLocation,
      }),
    },
  );
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
