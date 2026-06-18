export type PromptType = "story" | "task";
export type IssueType = "Task" | "Sub-task";

export interface JiraIssueSettings {
  project_key: string;
  component_name?: string;
  assignee_account_id?: string;
}

export interface JiraCreateSettings extends JiraIssueSettings {
  jira_server: string;
}

export interface GeneratedTask {
  title: string;
  description: string;
}

export interface StoryGenerationResult {
  title: string;
  user_story: string;
  acceptance_criteria: string[];
  tasks: GeneratedTask[];
}

export interface TaskGenerationResult {
  title: string;
  description: string;
  subtasks: GeneratedTask[];
}

export interface GenerateResponse<T> {
  prompt_type: PromptType;
  data: T;
}

export interface IssueFieldsPreviewResponse {
  fields: Record<string, unknown>[];
}

export interface CreatedIssue {
  issue_type: string;
  key: string;
}

export interface CreateIssuesResponse {
  created: CreatedIssue[];
}

export interface ConfigDefaultsResponse {
  gcp_project_id: string;
  gcp_location: string;
  gemini_model: string;
  jira_server: string;
  jira_project_key: string;
  jira_component: string;
  jira_assignee: string;
}
