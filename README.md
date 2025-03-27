# 🚀 Jira-AI: AI-Powered Jira Issue Creation

## 📌 Overview
Jira-AI is a Python-based automation tool that leverages OpenAI to create Jira issues effortlessly. It converts a few user-provided keywords into structured Agile issues—Epics, Stories, and Tasks—with comprehensive acceptance criteria and adaptive task breakdowns, all while following Jira best practices. With flexible workflows, you can choose to create issues with or without Epics, add tasks to new or existing Stories, or even generate standalone Tasks.

## 🔹 Features
- **Flexible Issue Creation**: Choose the workflow that fits your needs—Epics, Stories, or standalone Tasks.
- **Epic Mode**: Create an Epic and automatically generate related Stories (with comprehensive acceptance criteria) and Tasks linked to that Epic.
- **Story Mode**: Create a new Story with generated Tasks or add additional subtasks to an existing Story.
- **Task Mode**: Generate and create standalone Tasks without any parent issue.
- **Dynamic Acceptance Criteria**: AI generates a comprehensive set of acceptance criteria tailored to each user story.
- **Adaptive Task Breakdown**: AI determines and creates as many tasks as needed for proper implementation.
- **Jira Integration**: Issues are automatically created in Jira using your provided credentials.

## 🛠️ Requirements
### ✅ Software & Dependencies
- **Python** 3.8+
- **pip** package manager
- **Jira Cloud Account** with issue creation permissions
- **OpenAI API Key** (requires ChatGPT credits)
- **Jira API Token**

### ✅ Python Packages
Install the required dependencies:
```sh
pip install jira openai python-dotenv
```
✅ **Authentication Setup**  
Create a `.env` file in the project root to store authentication details:

```ini
JIRA_SERVER=https://yourcompany.atlassian.net
JIRA_USERNAME=your.email@company.com
JIRA_API_TOKEN=your-jira-api-token
OPENAI_API_KEY=your-openai-api-key
```
Note: The script will prompt for these if no .env is found.

Note: You must have Jira permissions to create issues.