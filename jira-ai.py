import os
import json
import sys
from jira import JIRA
import openai

# ---------------------- CONFIGURATION ----------------------
JIRA_SERVER = input("Jira Server URL (default: https://projectultron.atlassian.net): ") or "https://projectultron.atlassian.net"
JIRA_PROJECT_KEY = input("Jira Project Key (default: MC): ") or "MC"

JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not (JIRA_USERNAME and JIRA_API_TOKEN and OPENAI_API_KEY):
    print("\n❌ Missing required environment variables.")
    sys.exit(1)

openai.api_key = OPENAI_API_KEY
client = openai.OpenAI(api_key=OPENAI_API_KEY)

try:
    jira = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))
    print(f"\n✅ Authenticated as: {jira.myself()['displayName']}")
except Exception as e:
    print(f"\n❌ Jira authentication failed: {e}")
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
                return json.loads(ai_response)
            except Exception as e:
                print(f"\n⚠️ Error: {e}\nRetrying...({attempt+1}/{retries})")
        print(f"⚠️ Model {model} failed, switching...")
    print("\n❌ AI generation failed. Exiting.")
    sys.exit(1)

def generate_story_and_tasks(title):
    prompt = f"""
    Generate Jira story JSON from this short description: "{title}"
    Include "title", "user_story", "acceptance_criteria", and "tasks".
    Respond only with valid JSON.
    """
    return generate_json(prompt)

def generate_task_and_subtasks(title):
    prompt = f"""
    Generate Jira task JSON with subtasks from: "{title}"
    Include "title", "description", and "subtasks".
    Respond only with valid JSON.
    """
    return generate_json(prompt)

# ---------------------- JIRA CREATION FUNCTIONS ----------------------
def create_issue(issue_type, summary, description, parent=None):
    fields = {
        "project": {"key": JIRA_PROJECT_KEY},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type}
    }
    if parent:
        fields["parent"] = {"key": parent}
    issue = jira.create_issue(fields=fields)
    print(f"✅ Created {issue_type}: {issue.key}")
    return issue.key

def create_subtasks(parent_key, subtasks):
    for st in subtasks:
        create_issue("Sub-task", st["title"], st["description"], parent_key)

# ---------------------- MAIN EXECUTION ----------------------
def main():
    while True:
        choice = input("\nOptions:\n1. Epic\n2. Story\n3. Task/Subtask\n4. Exit\nChoose (1-4): ")

        if choice == '1':
            title = input("Epic Title: ")
            desc = input("Epic Description: ")
            create_issue("Epic", title, desc)

        elif choice == '2':
            epic_key = input("Epic Key (optional): ") or None
            method = input("Content source [manual/ai]: ").lower()
            if method == 'manual':
                title = input("Story Title: ")
                user_story = input("User Story: ")
                ac = input("Acceptance Criteria (comma-separated): ").split(",")
                tasks_raw = input("Tasks (title:description; separate tasks by semicolon): ")
                tasks = [{"title": t.split(":")[0].strip(), "description": t.split(":")[1].strip()} for t in tasks_raw.split(";")]

                story_data = {
                    "title": title,
                    "user_story": user_story,
                    "acceptance_criteria": [a.strip() for a in ac],
                    "tasks": tasks
                }
            else:
                desc = input("Give me a few words to describe your story: ")
                story_data = generate_story_and_tasks(desc)

            story_key = create_issue("Story", story_data["title"],
                                     story_data["user_story"] + "\nAcceptance Criteria:\n" +
                                     "\n".join(f"- {c}" for c in story_data["acceptance_criteria"]),
                                     epic_key)
            create_subtasks(story_key, story_data["tasks"])

        elif choice == '3':
            task_type = input("Task or Sub-task? [task/subtask]: ").lower()
            parent_key = input("Parent Key (Story for task, Task for subtask): ")
            method = input("Content source [manual/ai]: ").lower()

            if method == 'manual':
                title = input("Title: ")
                desc = input("Description: ")

                if task_type == 'task':
                    task_key = create_issue("Task", title, desc, parent_key)
                    add_subs = input("Add subtasks? [y/n]: ").lower()
                    if add_subs == 'y':
                        subs_raw = input("Subtasks (title:description; separate by semicolon): ")
                        subtasks = [{"title": s.split(":")[0].strip(), "description": s.split(":")[1].strip()} for s in subs_raw.split(";")]
                        create_subtasks(task_key, subtasks)
                else:
                    create_issue("Sub-task", title, desc, parent_key)

            else:
                desc = input("Give me a few words to describe your task: ")
                task_data = generate_task_and_subtasks(desc)

                task_key = create_issue("Task", task_data["title"], task_data["description"], parent_key)
                create_subtasks(task_key, task_data["subtasks"])

        elif choice == '4':
            print("👋 Exiting.")
            break
        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    main()
