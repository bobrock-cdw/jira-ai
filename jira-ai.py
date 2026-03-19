import os
import json
import sys
import threading
import time
from datetime import datetime
from jira import JIRA, JIRAError
from google import genai
from google.genai import types

# ====================== HARDCODED CONFIGURATION ======================
DEFAULT_GCP_PROJECT_ID = "cdw-gemini-cli-sbx" #
DEFAULT_GCP_LOCATION = "us-central1"
DEFAULT_JIRA_SERVER = "https://projectultron.atlassian.net"
DEFAULT_JIRA_PROJECT = "MC"
DEFAULT_JIRA_COMPONENT = "Cloud"
DEFAULT_JIRA_ASSIGNEE = "Bob Rock"
# ======================================================================

def get_initial_config():
    print("--- Professional Jira AI Assistant (Vertex AI) ---")
    server = input(f"Jira Server URL (default: {DEFAULT_JIRA_SERVER}): ").strip() or DEFAULT_JIRA_SERVER
    jira_project = input(f"Jira Project Key (default: {DEFAULT_JIRA_PROJECT}): ").strip() or DEFAULT_JIRA_PROJECT
    component = input(f"Jira Component (default: {DEFAULT_JIRA_COMPONENT}): ").strip() or DEFAULT_JIRA_COMPONENT
    assignee = input(f"Jira Assignee (default: {DEFAULT_JIRA_ASSIGNEE}): ").strip() or DEFAULT_JIRA_ASSIGNEE
    
    print("\n--- Google Cloud Configuration ---")
    gcp_project = input(f"GCP Project ID (default: {DEFAULT_GCP_PROJECT_ID}): ").strip() or DEFAULT_GCP_PROJECT_ID
    location = input(f"GCP Region (default: {DEFAULT_GCP_LOCATION}): ").strip() or DEFAULT_GCP_LOCATION
    
    print("\n--- Session Context ---")
    context = input("Enter Project/Tech Context: ").strip()
    
    return server, jira_project, component, assignee, gcp_project, location, context

(JIRA_SERVER, JIRA_PROJECT_KEY, JIRA_COMPONENT_NAME, JIRA_ASSIGNEE_USERNAME, 
 GCP_PROJECT_ID, GCP_LOCATION, PROJECT_CONTEXT) = get_initial_config()

JIRA_USER = os.getenv("JIRA_USERNAME")
JIRA_TOKEN = os.getenv("JIRA_API_TOKEN")

if not (JIRA_USER and JIRA_TOKEN):
    print("❌ Error: JIRA_USERNAME or JIRA_API_TOKEN not found."); sys.exit(1)

# Initialize Vertex AI
try:
    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    print(f"✅ Gemini Client initialized for: {GCP_PROJECT_ID}")
except Exception as e:
    print(f"❌ Vertex AI Initialization Failed: {e}"); sys.exit(1)

# ---------------------- HELPERS ----------------------
def log_deliberation(data):
    if not os.path.exists("logs"): os.makedirs("logs")
    filename = f"logs/deliberation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f: json.dump(data, f, indent=4)
    print(f"💾 Local log saved: {filename}")

def get_multiline_input(prompt):
    print(f"\n{prompt}")
    print("-" * 30 + "\nPASTE TEXT. Type 'DONE' on a new line and press Enter.\n" + "-" * 30)
    lines = []
    while True:
        line = sys.stdin.readline()
        if not line: break # Handle EOF
        if line.strip().upper() == "DONE": break
        lines.append(line)
    return "".join(lines).strip()

def spinner_task(stop_event):
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r{chars[i % len(chars)]} Experts are deliberating...")
        sys.stdout.flush(); time.sleep(0.1); i += 1
    sys.stdout.write("\r✅ Deliberation complete!                                     \n")

# ---------------------- JIRA CORE ----------------------
try:
    jira = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_USER, JIRA_TOKEN))
    print(f"✅ Authenticated to Jira: {jira.myself()['displayName']}")
    users = jira.search_users(query=JIRA_ASSIGNEE_USERNAME, maxResults=1)
    ASSIGNEE_ACCOUNT_ID = users[0].accountId if users else None
except Exception as e:
    print(f"❌ Jira Setup Failed: {e}"); sys.exit(1)

# ---------------------- AI CORE (GEMINI) ----------------------
def generate_ai_content(prompt_type, brief):
    stop_event = threading.Event()
    spinner_thread = threading.Thread(target=spinner_task, args=(stop_event,))
    spinner_thread.start()
    
    prompts = {
        "story": f"Act as an Expert Committee (PM, Dev, Architect, QA). Context: {PROJECT_CONTEXT}. Brief: {brief}. Return ONLY JSON: {{'title', 'user_story', 'acceptance_criteria', 'tasks': [{{'title', 'description'}}]}}",
        "task": f"Act as a Lead Dev and Architect. Context: {PROJECT_CONTEXT}. Brief: {brief}. Return ONLY JSON: {{'title', 'description', 'subtasks': [{{'title', 'description'}}]}}"
    }

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompts[prompt_type],
            config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0.2)
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"\n❌ Gemini Error: {e}"); return None
    finally:
        stop_event.set(); spinner_thread.join()

# ---------------------- JIRA OPERATIONS ----------------------
def create_issue(issue_type, summary, description, parent=None):
    fields = {
        "project": {"key": JIRA_PROJECT_KEY},
        "summary": summary, "description": description, "issuetype": {"name": issue_type},
        "assignee": {"accountId": ASSIGNEE_ACCOUNT_ID} if ASSIGNEE_ACCOUNT_ID else None
    }
    if JIRA_COMPONENT_NAME: fields["components"] = [{"name": JIRA_COMPONENT_NAME}]
    if parent: fields["parent"] = {"key": parent}
    
    try:
        issue = jira.create_issue(fields=fields)
        print(f"✅ Created {issue_type}: {issue.key}"); return issue.key
    except Exception as e:
        print(f"❌ Creation Failed: {e}"); return None

# ---------------------- MAIN ----------------------
def main():
    while True:
        print("\n1. Epic | 2. Story | 3. Task/SubTask | 4. Exit")
        choice = input("Choice: ")
        
        if choice == '1':
            title = input("Epic Title: ")
            desc = get_multiline_input("Epic Description")
            create_issue("Epic", title, desc)

        elif choice == '2':
            epic = input("Epic Key (optional): ").strip() or None
            brief = get_multiline_input("Describe the Story requirement")
            while True:
                data = generate_ai_content("story", brief)
                if not data: break
                log_deliberation(data)
                print("\nPROPOSED CONTENT:\n", json.dumps(data, indent=2))
                action = input("\n[y] Create, [r] Retry, [n] Cancel: ").lower().strip()
                if action == 'y':
                    desc = f"{data['user_story']}\n\nAcceptance Criteria:\n- " + "\n- ".join(data['acceptance_criteria'])
                    key = create_issue("Story", data['title'], desc, epic)
                    if key:
                        for t in data['tasks']: create_issue("Sub-task", t['title'], t['description'], key)
                    break
                elif action != 'r': break

        elif choice == '3':
            i_type = input("Create Task or Sub-task? [task/subtask]: ").lower().strip()
            parent = input("Parent Key (optional for Task): ").strip() or None
            brief = get_multiline_input(f"Describe the {i_type}")
            while True:
                data = generate_ai_content("task", brief)
                if not data: break
                log_deliberation(data)
                print("\nPROPOSED CONTENT:\n", json.dumps(data, indent=2))
                action = input("\n[y] Create, [r] Retry, [n] Cancel: ").lower().strip()
                if action == 'y':
                    key = create_issue("Task" if i_type == 'task' else "Sub-task", data['title'], data['description'], parent)
                    if key and i_type == 'task' and 'subtasks' in data:
                        for s in data['subtasks']: create_issue("Sub-task", s['title'], s['description'], key)
                    break
                elif action != 'r': break
        elif choice == '4': break

if __name__ == "__main__":
    main()