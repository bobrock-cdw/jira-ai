import os
import json
import sys
from jira import JIRA, JIRAError
import openai

# ---------------------- CONFIGURATION ----------------------
JIRA_SERVER = input("Jira Server URL (default: https://projectultron.atlassian.net): ").strip() or "https://projectultron.atlassian.net"
JIRA_PROJECT_KEY = input("Jira Project Key (default: MC): ").strip() or "MC"
JIRA_COMPONENT_NAME = input("Jira Component (default: Cloud): ").strip() or "Cloud"
JIRA_ASSIGNEE_USERNAME = input("Jira Assignee Username or Display Name (default: Bob Rock): ").strip() or "Bob Rock"

# Session-wide project context (e.g., 'Inscape Google Workspace Reporting')
PROJECT_CONTEXT = input("\nEnter Project Context (e.g., 'GCP Data Pipeline', 'Mobile App') [Optional]: ").strip()

JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not (JIRA_USERNAME and JIRA_API_TOKEN and OPENAI_API_KEY):
    print("\n❌ Missing required environment variables: JIRA_USERNAME, JIRA_API_TOKEN, and OPENAI_API_KEY.")
    sys.exit(1)

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ---------------------- JIRA HELPER FUNCTIONS ----------------------
def get_account_id(jira_client, username):
    try:
        users = jira_client.search_users(query=username, maxResults=1)
        if users:
            print(f"✅ Found user '{users[0].displayName}' with accountId.")
            return users[0].accountId
        else:
            print(f"⚠️ User '{username}' not found. Issues will be unassigned.")
            return None
    except JIRAError as e:
        print(f"❌ Jira search error: {e.text}")
        return None

try:
    jira = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))
    print(f"\n✅ Authenticated as: {jira.myself()['displayName']}")
    ASSIGNEE_ACCOUNT_ID = get_account_id(jira, JIRA_ASSIGNEE_USERNAME)
except Exception as e:
    print(f"\n❌ Jira authentication failed: {e}")
    sys.exit(1)

# ---------------------- OPENAI / EXPERT PROMPTS ----------------------
def generate_json(prompt, retries=3):
    models = ["gpt-4o", "gpt-3.5-turbo"]
    for model in models:
        for attempt in range(retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                ai_response = response.choices[0].message.content.strip()
                if ai_response.startswith("```json"):
                    ai_response = ai_response[7:-3].strip()
                return json.loads(ai_response)
            except Exception as e:
                print(f"⚠️ {model} attempt {attempt+1} failed. Retrying...")
    return None

def generate_story_and_tasks(title):
    prompt = f"""
    Act as a Committee of Experts collaborating on a Jira Story:
    1. **Senior Technical PM**: Defines user value and INVEST-compliant story structure.
    2. **Cloud Architect**: Defines infrastructure (Terraform, IAM, Cloud Run) and security.
    3. **Software Developer**: Defines implementation logic, code structure, and library usage.
    4. **QA Lead**: Defines edge cases, validation, and testing requirements.

    Project Context: {PROJECT_CONTEXT if PROJECT_CONTEXT else "General Software Development"}
    Input Brief: "{title}"

    Generate a JSON object with:
    - "title": Concise technical summary.
    - "user_story": "As a [role], I want [feature] so that [benefit]".
    - "acceptance_criteria": List of measurable requirements (functional, technical, and architectural).
    - "tasks": List of objects with "title" and "description" (specific steps for the developer/architect).

    Respond only with valid JSON.
    """
    return generate_json(prompt)

def generate_task_and_subtasks(title):
    prompt = f"""
    Act as a Software Developer and Cloud Architect defining a technical Task.
    Project Context: {PROJECT_CONTEXT if PROJECT_CONTEXT else "General Software Development"}
    Brief: "{title}"

    Generate a JSON object with:
    - "title": Task name.
    - "description": Detailed technical scope.
    - "subtasks": List of objects with "title" and "description" (granular coding and infra steps).

    Respond only with valid JSON.
    """
    return generate_json(prompt)

# ---------------------- REVIEW LOOP ----------------------
def review_content(data):
    print("\n" + "="*50)
    print("📋 PROPOSED JIRA CONTENT")
    print("="*50)
    print(json.dumps(data, indent=4))
    print("="*50)
    return input("\n[y] Accept & Create, [r] Regenerate/Retry, [n] Cancel/Main Menu: ").lower().strip()

# ---------------------- JIRA CREATION ----------------------
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
        print(f"❌ Failed to create {issue_type}: {e}")
        return None

def create_subtasks(parent_key, subtasks, assignee_id=None):
    for st in subtasks:
        create_issue("Sub-task", st.get("title"), st.get("description"), parent_key, assignee_id)

# ---------------------- MAIN EXECUTION ----------------------
def main():
    while True:
        print("\n" + "="*30)
        choice = input("Options:\n1. Epic\n2. Story\n3. Task/Subtask\n4. Exit\nChoose (1-4): ")
        
        if choice == '1':
            title = input("Epic Title: ").strip()
            desc = input("Epic Description: ").strip()
            create_issue("Epic", title, desc, assignee_id=ASSIGNEE_ACCOUNT_ID)

        elif choice == '2':
            epic_key = input("Epic Key (optional): ").strip() or None
            desc = input("Describe your story: ").strip()
            while True:
                data = generate_story_and_tasks(desc)
                if not data: break
                rev = review_content(data)
                if rev == 'y':
                    full_desc = f"{data['user_story']}\n\nAcceptance Criteria:\n- " +  "\n- ".join(data['acceptance_criteria'])
                    key = create_issue("Story", data['title'], full_desc, epic_key, ASSIGNEE_ACCOUNT_ID)
                    if key: create_subtasks(key, data['tasks'], ASSIGNEE_ACCOUNT_ID)
                    break
                elif rev == 'n': break

        elif choice == '3':
            task_type = input("Create Task or Sub-task? [task/subtask]: ").lower().strip()
            parent_key = input("Parent Key (optional for Task, required for Sub-task): ").strip() or None
            desc = input(f"Describe the {task_type}: ").strip()
            while True:
                data = generate_task_and_subtasks(desc)
                if not data: break
                rev = review_content(data)
                if rev == 'y':
                    key = create_issue("Task" if task_type == 'task' else "Sub-task", data['title'], data['description'], parent_key, ASSIGNEE_ACCOUNT_ID)
                    if key and task_type == 'task': create_subtasks(key, data['subtasks'], ASSIGNEE_ACCOUNT_ID)
                    break
                elif rev == 'n': break

        elif choice == '4':
            print("👋 Exiting.")
            break

if __name__ == "__main__":
    main()