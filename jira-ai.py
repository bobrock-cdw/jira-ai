import os
import json
import sys
from jira import JIRA
import openai

# ---------------------- CONFIGURATION ----------------------
JIRA_SERVER = input("Enter Jira Server URL (default: https://projectultron.atlassian.net): ").strip() or "https://projectultron.atlassian.net"
JIRA_PROJECT_KEY = input("Enter Jira Project Key (default: MC): ").strip() or "MC"

JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not (JIRA_USERNAME and JIRA_API_TOKEN and OPENAI_API_KEY):
    print("\n❌ ERROR: Missing required environment variables.")
    sys.exit(1)

openai.api_key = OPENAI_API_KEY
client = openai.OpenAI(api_key=OPENAI_API_KEY)

try:
    jira = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))
    user = jira.myself()
    print(f"\n✅ Authenticated as: {user['displayName']}")
except Exception as e:
    print(f"\n❌ ERROR: Jira authentication failed: {e}")
    sys.exit(1)

# ---------------------- OPENAI FUNCTIONS ----------------------
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
                try:
                    return json.loads(ai_response)
                except json.JSONDecodeError as e:
                    print(f"\n⚠️ JSON decode error: {e}")
                    print(f"🔍 Raw response: {ai_response}\nRetrying...({attempt+1}/{retries})")
            except Exception as e:
                print(f"\n⚠️ OpenAI API error: {e}\nRetrying...({attempt+1}/{retries})")
        print(f"⚠️ Model {model} failed, switching model.")
    print("\n❌ AI generation failed. Exiting.")
    sys.exit(1)

def generate_story_and_tasks(story_title, story_description):
    prompt = f"""
You are an expert Jira Product Owner assistant.

Given these details, generate a professional Jira user story with acceptance criteria and tasks.

Respond strictly with JSON in this format:
{{
  "title": "<Clear professional story title>",
  "user_story": "As a <role>, I want <feature>, so that <benefit>.",
  "acceptance_criteria": [
    "Acceptance criterion 1",
    "Acceptance criterion 2"
  ],
  "tasks": [
    {{"title": "Task title", "description": "Detailed task description"}},
    {{"title": "Task title", "description": "Detailed task description"}}
  ]
}}

Details provided:
- Title: "{story_title}"
- Description: "{story_description}"
"""
    return generate_json(prompt)

# ---------------------- JIRA ISSUE CREATION ----------------------
def create_epic(title, description):
    epic = jira.create_issue(fields={
        "project": {"key": JIRA_PROJECT_KEY},
        "summary": title,
        "description": description,
        "issuetype": {"name": "Epic"}
    })
    print(f"\n✅ Created Epic: {epic.key}")
    return epic.key

def create_story(parent_key, story_data):
    fields = {
        "project": {"key": JIRA_PROJECT_KEY},
        "summary": story_data["title"],
        "description": f"{story_data['user_story']}\n\nAcceptance Criteria:\n" +
                       "\n".join(f"- {ac}" for ac in story_data["acceptance_criteria"]),
        "issuetype": {"name": "Story"}
    }
    if parent_key:
        fields["parent"] = {"key": parent_key}
    story = jira.create_issue(fields=fields)
    print(f"\n✅ Created Story: {story.key}")
    return story.key

def create_subtasks(parent_story_key, tasks):
    for task in tasks:
        subtask = jira.create_issue(fields={
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": task["title"],
            "description": task["description"],
            "issuetype": {"name": "Sub-task"},
            "parent": {"key": parent_story_key}
        })
        print(f"✅ Created Subtask: {subtask.key}")

# ---------------------- CONFIRMATION STEP ----------------------
def confirm_and_create(issue_type, data, parent_key=None):
    print(f"\n📌 Proposed {issue_type}:")
    print(json.dumps(data, indent=2))

    confirm = input("\n🔔 Create these issues in Jira? [Y/N]: ").lower()
    if confirm != 'y':
        print("🚫 Operation cancelled.")
        sys.exit(0)

    if issue_type == "Epic":
        return create_epic(data['title'], data['description'])
    elif issue_type == "Story":
        story_key = create_story(parent_key, data)
        create_subtasks(story_key, data['tasks'])

# ---------------------- MAIN EXECUTION ----------------------
def main():
    while True:
        print("\nOptions:\n1. Create Epic\n2. Create Story\n3. Exit")
        choice = input("Choose (1-3): ").strip()

        if choice == '1':
            title = input("Epic Title: ").strip()
            desc = input("Epic Description: ").strip()
            confirm_and_create("Epic", {"title": title, "description": desc})

        elif choice == '2':
            epic_key = input("Epic Key (optional): ").strip()
            title = input("Story Title: ").strip()
            desc = input("Story Description: ").strip()
            story_data = generate_story_and_tasks(title, desc)
            confirm_and_create("Story", story_data, epic_key or None)

        elif choice == '3':
            print("👋 Exiting.")
            break
        else:
            print("❌ Invalid choice, try again.")

if __name__ == "__main__":
    main()
