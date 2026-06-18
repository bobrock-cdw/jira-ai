/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_JIRA_SERVER?: string;
  readonly VITE_JIRA_PROJECT_KEY?: string;
  readonly VITE_JIRA_COMPONENT?: string;
  readonly VITE_JIRA_ASSIGNEE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
