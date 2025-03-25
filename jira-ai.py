import os
import json
import sys
from jira import JIRA
import openai

# ---------------------- CONFIGURATION ----------------------
# Prompt user for Jira Server URL and Project Key
JIRA_SERVER = input("Enter Jira Server URL (default: https://projectultron.atlassian.net): ").strip() or "https://projectultron.atlassian.net"
JIRA_PROJECT_KEY = input("Enter Jira Project Key (default: MC): ").strip() or "MC"

# Load required environment variables
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not (JIRA_USERNAME and JIRA_API_TOKEN and OPENAI_API_KEY):
    print("\n❌ ERROR: Missing one or more required environment variables (JIRA_USERNAME, JIRA_API_TOKEN, OPENAI_API_KEY).")
    sys.exit(1)

# Configure OpenAI API
openai.api_key = OPENAI_API_KEY

# Initialize Jira client
jira_options = {"server": JIRA_SERVER}
try:
    jira = JIRA(options=jira_options, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))
    user = jira.myself()
    print(f"\n✅ Authenticated as: {user['displayName']}")
except Exception as e:
    print(f"\n❌ ERROR: Jira authentication failed: {e}")
    sys.exit(1)

# ---------------------- OPENAI FUNCTIONS ----------------------
def generate_json(prompt):
    """
    Uses OpenAI to generate a JSON output based on the provided prompt.
    It tries a list of models until valid JSON is returned.
    """
    models = ["gpt-4o", "gpt-3.5-turbo"]
    for model in models:
        try:
            print(f"\n🔄 Trying OpenAI model: {model}...")
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            ai_response = response.choices[0].message.content.strip()
            try:
                data = json.loads(ai_response)
                return data
            except json.JSONDecodeError:
                print("\n❌ Error: AI response was not valid JSON. Response:")
                print(ai_response)
                continue
        except openai.APIError as e:
            print(f"\n❌ OpenAI API Error (Model: {model}): {e}")
            continue
    print("\n❌ AI generation failed. Exiting.")
    sys.exit(1)

def generate_story_and_tasks(story_title, story_description, topics):
    """
    Generates a story with acceptance criteria and tasks based on the provided topics.
    """
    topics_str = "\n".join([f"- {topic}" for topic in topics])
    prompt = f"""
You are an AI Jira assistant.
The Story is titled: "{story_title}"
The Story Description: "{story_description}"

The user has provided the following topics:
{topics_str}

Generate a detailed Jira-friendly output for this story:
- Write a complete user story.
- Provide a comprehensive set of acceptance criteria.
- Generate a list of tasks (each with a title and description) as needed.

Output only JSON in the following format:
{{
  "title": "{story_title}",
  "user_story": "...",
  "acceptance_criteria": ["...", "...", ...],
  "tasks": [
    {{"title": "...", "description": "..."}},
    ...
  ]
}}
    """
    return generate_json(prompt)

def generate_tasks_from_topics(topics):
    """
    Generates tasks or subtasks based on the provided topics.
    """
    topics_str = "\n".join([f"- {topic}" for topic in topics])
    prompt = f"""
You are an AI Jira assistant.
Generate a list of tasks based on the following topics:
{topics_str}
For each topic, generate a task with a title and description.
Output only JSON in the following format:
[
  {{"title": "...", "description": "..."}},
  ...
]
    """
    return generate_json(prompt)

# ---------------------- JIRA ISSUE CREATION ----------------------
def create_epic(title, description):
    """
    Creates an Epic issue in Jira.
    """
    try:
        epic = jira.create_issue(fields={
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": title,
            "description": description,
            "issuetype": {"name": "Epic"}
        })
        print(f"\n✅ Created Epic: {epic.key}")
        return epic.key
    except Exception as e:
        print(f"\n❌ Error creating Epic: {e}")
        sys.exit(1)

def create_story(parent_key, story_data):
    """
    Creates a Story in Jira.
    If a parent_key (Epic or other Story) is provided, the story is linked accordingly.
    """
    fields = {
        "project": {"key": JIRA_PROJECT_KEY},
        "summary": story_data["title"],
        "description": story_data["user_story"] + "\n\n**Acceptance Criteria:**\n" +
                       "\n".join(f"- {ac}" for ac in story_data["acceptance_criteria"]),
        "issuetype": {"name": "Story"}
    }
    if parent_key:
        fields["parent"] = {"key": parent_key}
    try:
        story = jira.create_issue(fields=fields)
        print(f"\n✅ Created Story: {story.key} - {story_data['title']}")
        return story.key
    except Exception as e:
        print(f"\n❌ Error creating Story: {e}")
        sys.exit(1)

def create_subtasks(parent_story_key, tasks):
    """
    Creates subtasks under a given Story.
    """
    for task in tasks:
        try:
            task_fields = {
                "project": {"key": JIRA_PROJECT_KEY},
                "summary": task["title"],
                "description": task["description"],
                "issuetype": {"name": "Sub-task"},
                "parent": {"key": parent_story_key}
            }
            subtask = jira.create_issue(fields=task_fields)
            print(f"  ✅ Created Subtask: {subtask.key} - {task['title']}")
        except Exception as e:
            print(f"  ❌ Error creating Subtask: {e}")

def create_standalone_task(task):
    """
    Creates a standalone Task in Jira (not a subtask).
    """
    try:
        task_fields = {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": task["title"],
            "description": task["description"],
            "issuetype": {"name": "Task"}
        }
        created_task = jira.create_issue(fields=task_fields)
        print(f"✅ Created Standalone Task: {created_task.key} - {task['title']}")
    except Exception as e:
        print(f"❌ Error creating Standalone Task: {e}")

# ---------------------- MAIN EXECUTION ----------------------
def main():
    print("\nSelect a workflow option:")
    print("1. Create Epic with Stories and Tasks")
    print("2. Create a New Story or Add Tasks to an Existing Story")
    print("3. Create Standalone Tasks")
    option = input("Enter option (1, 2, or 3): ").strip()

    if option == "1":
        # Option 1: Epic with Stories & Tasks
        epic_title = input("\nEnter Epic Title: ").strip()
        epic_description = input("Enter Epic Description: ").strip()
        epic_key = create_epic(epic_title, epic_description)

        print("\nEnter User Story Topics (one per line, blank line to finish):")
        topics = []
        while True:
            topic = input("➤ ").strip()
            if topic == "":
                break
            topics.append(topic)
        if not topics:
            print("\n❌ No topics provided. Exiting.")
            sys.exit(1)

        # For each topic, generate a story and its tasks and link them to the Epic.
        for topic in topics:
            print(f"\nGenerating story for topic: {topic}")
            story_title = topic
            story_description = f"Story for topic: {topic} in Epic {epic_title}."
            story_data = generate_story_and_tasks(story_title, story_description, [topic])
            story_key = create_story(epic_key, story_data)
            create_subtasks(story_key, story_data.get("tasks", []))

    elif option == "2":
        # Option 2: Story Mode (create new story or add tasks to existing story)
        sub_option = input("\nEnter 'new' to create a new Story or 'existing' to add tasks to an existing Story: ").strip().lower()
        if sub_option == "new":
            story_title = input("Enter Story Title: ").strip()
            story_description = input("Enter Story Description: ").strip()
            print("\nEnter topics for generating tasks (one per line, blank line to finish):")
            topics = []
            while True:
                topic = input("➤ ").strip()
                if topic == "":
                    break
                topics.append(topic)
            if not topics:
                print("\n❌ No topics provided. Exiting.")
                sys.exit(1)
            story_data = generate_story_and_tasks(story_title, story_description, topics)
            story_key = create_story(None, story_data)
            create_subtasks(story_key, story_data.get("tasks", []))
        elif sub_option == "existing":
            existing_story_key = input("Enter existing Story key: ").strip()
            print("\nEnter topics for generating additional subtasks (one per line, blank line to finish):")
            topics = []
            while True:
                topic = input("➤ ").strip()
                if topic == "":
                    break
                topics.append(topic)
            if not topics:
                print("\n❌ No topics provided. Exiting.")
                sys.exit(1)
            tasks = generate_tasks_from_topics(topics)
            create_subtasks(existing_story_key, tasks)
        else:
            print("\n❌ Invalid sub-option. Exiting.")
            sys.exit(1)

    elif option == "3":
        # Option 3: Standalone Tasks
        print("\nEnter topics for generating standalone tasks (one per line, blank line to finish):")
        topics = []
        while True:
            topic = input("➤ ").strip()
            if topic == "":
                break
            topics.append(topic)
        if not topics:
            print("\n❌ No topics provided. Exiting.")
            sys.exit(1)
        tasks = generate_tasks_from_topics(topics)
        for task in tasks:
            create_standalone_task(task)
    else:
        print("\n❌ Invalid option selected. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
