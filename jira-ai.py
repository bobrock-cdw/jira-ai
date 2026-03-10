import os
import json
import sys
from jira import JIRA, JIRAError
import openai

# ---------------------- CONFIGURATION ----------------------
def get_initial_config():
    print("--- Jira AI Configuration ---")
    server = input("Jira Server URL (default: https://projectultron.atlassian.net): ").strip() or "https://projectultron.atlassian.net"
    project = input("Jira Project Key (default: MC): ").strip() or "MC"
    component = input("Jira Component (default: Cloud): ").strip() or "Cloud"
    assignee = input("Jira Assignee Display Name (default: Bob Rock): ").strip() or "Bob Rock"
    context = input("\nEnter Project Context (e.g., 'Inscape GCP Reporting') [Optional]: ").strip()
    return server, project, component, assignee, context

JIRA_SERVER, JIRA_PROJECT_KEY, JIRA_COMPONENT_NAME, JIRA_ASSIGNEE_USERNAME, PROJECT_CONTEXT = get_initial_config()

JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not (JIRA_USERNAME and JIRA_API_TOKEN and OPENAI_API_KEY):
    print("\n❌ Missing environment variables. Please set JIRA_USERNAME, JIRA_API_TOKEN, and OPENAI_API_KEY.")
    sys.exit(1)

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ---------------------- HELPERS ----------------------
def get_multiline_input(prompt):
    """Allows pasting large blocks of text. Ends on Ctrl-D (Unix) or Ctrl-Z (Win)."""
    print(f"\n{prompt}")
    print("-" * 30)
    print("PASTE TEXT BELOW. To finish, press ENTER and then CTRL-D (on Mac/Linux) or CTRL-Z (on Windows).")
    print("-" * 30)
    try:
        content = sys.stdin.read()
        return content.strip()
    except EOFError:
        return ""

def get_account_id(jira_client, username):
    try:
        users = jira_client.search_users(query=username, maxResults=1)
        if users:
            print(f"✅ Found user '{users[0].displayName}' with accountId.")
            return users[0].accountId
        return None
    except Exception as e:
        print(f"❌ Error finding Jira user: {e}")
        return None

# Authenticate
try:
    jira = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))
    print(f"\n✅ Authenticated as: {jira.myself()['displayName']}")
    ASSIGNEE_ACCOUNT_ID = get_account_id(jira, JIRA_ASSIGNEE_USERNAME)
except Exception as e:
    print(f"\n❌ Jira authentication failed: {e}")
    sys.exit(1)

# ---------------------- OPENAI EXPERT COMMITTEE ----------------------
def generate_json(prompt, retries=3):
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            ai_response = response.choices[0].message.content.strip()
            if ai_response.startswith("```json"):
                ai_response = ai_response[7:-3].strip()
            return json.loads(ai_response)
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed. Retrying...")
    return None

def generate_story_and_tasks(brief):
    prompt = f"""
    Act as a Committee of Experts (Senior TPM, Cloud Architect, Software Developer, QA Lead).
    Project Context: {PROJECT_CONTEXT if PROJECT_CONTEXT else "General Development"}
    Input: "{brief}"

    Return JSON:
    - "title": Technical summary.
    - "user_story": "As a [role], I want [feature] so that [benefit]".
    - "acceptance_criteria": List of measurable requirements.
    - "tasks": List of objects with "title" and "description".
    """
    return generate_json(prompt)

def generate_task_and_subtasks(brief):
    prompt = f"""
    Act as a Lead Software Developer and Cloud Architect.
    Project Context: {PROJECT_CONTEXT if PROJECT_CONTEXT else "General Development"}
    Input: "{brief}"

    Return JSON:
    - "title": Task name.
    - "description": Detailed scope.
    - "subtasks": List of objects with "title" and "description".
    """
    return generate_json(prompt)

# ---------------------- REVIEW & JIRA OPS ----------------------
def review_content(data):
    print("\n" + "="*50)
    print("📋 PROPOSED JIRA CONTENT")
    print("="*50)
    print(json.dumps(data, indent=4))
    print("="*50)
    return input("\n[y] Accept, [r] Regenerate, [n] Cancel: ").lower().strip()

def create_issue(issue_type, summary, description, parent=None, assignee_id=None):
    fields = {
        "project": {"key": JIRA_PROJECT_KEY},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type}
    }
    if JIRA_COMPONENT_NAME:
        fields["components"] = [{"name": JIRA_COMPONENT_NAME}]
    if assignee_id:
        fields["assignee"] = {"accountId": assignee_id}
    if parent:
        fields["parent"] = {"key": parent}
    
    try:
        issue = jira.create_issue(fields=fields)
        print(f"✅ Created {issue_type}: {issue.key}")
        return issue.key
    except Exception as e:
        print(f"❌ Creation failed: {e}")
        return None

# ---------------------- MAIN ----------------------
def main():
    while True:
        print("\n1. Epic | 2. Story | 3. Task | 4. Exit")
        choice = input("Choice: ")

        if choice == '1':
            title = input("Epic Title: ")
            desc = get_multiline_input("Epic Description")
            create_issue("Epic", title, desc, assignee_id=ASSIGNEE_ACCOUNT_ID)

        elif choice == '2':
            epic_key = input("Epic Key (optional): ").strip() or None
            brief = get_multiline_input("Describe the story (pasted text supported)")
            while True:
                data = generate_story_and_tasks(brief)
                if not data or review_content(data) != 'y': break
                
                full_desc = f"{data['user_story']}\n\nAcceptance Criteria:\n- " + "\n- ".join(data['acceptance_criteria'])
                key = create_issue("Story", data['title'], full_desc, epic_key, ASSIGNEE_ACCOUNT_ID)
                if key:
                    for t in data['tasks']:
                        create_issue("Sub-task", t['title'], t['description'], key, ASSIGNEE_ACCOUNT_ID)
                break

        elif choice == '3':
            task_type = input("Create Task or Sub-task? [task/subtask]: ").lower().strip()
            parent_key = input("Parent Key (optional for Task): ").strip() or None
            brief = get_multiline_input(f"Describe the {task_type}")
            while True:
                data = generate_task_and_subtasks(brief)
                if not data or review_content(data) != 'y': break
                
                key = create_issue("Task" if task_type == 'task' else "Sub-task", data['title'], data['description'], parent_key, ASSIGNEE_ACCOUNT_ID)
                if key and task_type == 'task':
                    for s in data['subtasks']:
                        create_issue("Sub-task", s['title'], s['description'], key, ASSIGNEE_ACCOUNT_ID)
                break

        elif choice == '4':
            break

if __name__ == "__main__":
    main()