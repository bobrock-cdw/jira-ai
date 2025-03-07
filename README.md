# 🚀 Jira-AI: AI-Powered Jira Issue Creation

## 📌 Overview
Jira-AI is a Python-based automation tool that leverages OpenAI to create Jira issues (Epics, Stories, Tasks, Acceptance Criteria) with minimal user input. The script intelligently expands a few user-provided keywords into structured Agile stories, complete with acceptance criteria and tasks, following Jira best practices.

## 🔹 Features
- **Epic Creation**: Users provide an Epic title and description.
- **Story Generation**: Users input brief story topics, and AI converts them into complete user stories.
- **Acceptance Criteria Automation**: AI generates 3+ acceptance criteria for each story.
- **Task Breakdown**: AI creates implementation tasks per story.
- **Jira Integration**: Issues are automatically created in Jira.

## 🛠️ Requirements
### ✅ **Software & Dependencies**
- **Python** 3.8+
- **pip** package manager
- **Jira Cloud Account** with issue creation permissions
- **OpenAI API Key** (requires ChatGPT credits)
- **Jira API Token**

### ✅ **Python Packages**
Install the required dependencies:
```sh
pip install jira openai python-dotenv
```

### ✅ **Authentication Setup**
Create a `.env` file in the project root to store authentication details:
```ini
JIRA_SERVER=https://yourcompany.atlassian.net
JIRA_USERNAME=your.email@company.com
JIRA_API_TOKEN=your-jira-api-token
OPENAI_API_KEY=your-openai-api-key
```
> **Note:** The script will prompt for these if no .env is found.

> **Note:** You must have Jira permissions to create issues.

## 🔹 Usage
Run the script:
```sh
python3 jira-ai.py
```
### 📌 Input Process
1. **Enter Jira Server & Project Information** (or use defaults from `.env`)
2. **Enter Epic Title & Description**
3. **Enter Story Topics**
   - Each line should contain a few words describing a user story.
   - A blank line signals the end of story input.
4. **AI Automatically Generates**:
   - Structured user stories using best Agile practices.
   - Acceptance criteria for each story.
   - Relevant tasks for each story.
5. **Jira Issues are Created Automatically**

### 📌 Example Workflow
#### **User Inputs**
```
Enter Epic Title: My Thing
Enter Epic Description: I want to build the thing

🔹 Enter Story Topics (one per line, blank to finish):
➤ Story one for building my thing
➤ Story two for building my thing
➤ Story three for building my thing

```
#### **AI-Generated Output**
**Epic: My Thing** ✅ Created in Jira

**Story 1: Story one for building my thing** ✅
```
As a user, I want to build this thing by starting with this.
```
✅ **Acceptance Criteria:**
- Users can access the thing.
- Users receive an error message for incorrect login credentials when accessing the thing with bad creds
- Users get locked out after 5 failed login attempts to access the thing

✅ **Tasks:**
- **Develop Login Page UI** – Implement frontend UI for login.
- **Integrate Authentication Backend** – Secure login functionality.

✔️ **Story & Tasks Created in Jira**

### Example Jira Epic that was created using this script
https://projectultron.atlassian.net/browse/MC-204?atlOrigin=eyJpIjoiZTkyNWQ0ZmUwMDA3NGEwYmE5YjQ1NzUyNTRjOTQ3NDkiLCJwIjoiaiJ9

## 📌 License
This project is licensed under the MIT License.

## 📌 Contributing
Feel free to submit issues or open a pull request to improve this tool!

---
🚀 **Jira-AI**: Streamline Agile Workflows with AI! 🚀

