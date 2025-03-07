import os
import json
from jira import JIRA
import openai

# ---------------------- CONFIGURATION ----------------------

# Prompt user for Jira Server and Project Key
JIRA_SERVER = input("Enter Jira Server URL (default: https://projectultron.atlassian.net): ").strip() or "https://projectultron.atlassian.net"
JIRA_PROJECT_KEY = input("Enter Jira Project Key (default: MC): ").strip() or "MC"

# Load environment variables
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate environment variables
if not JIRA_USERNAME or not JIRA_API_TOKEN or not OPENAI_API_KEY:
    print("\n❌ ERROR: Missing required environment variables. Ensure the following are set:")
    print("   - JIRA_USERNAME")
    print("   - JIRA_API_TOKEN")
    print("   - OPENAI_API_KEY")
    exit(1)

# Configure OpenAI Client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize Jira client
jira_options = {"server": JIRA_SERVER}
try:
    jira = JIRA(options=jira_options, basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN))
    user = jira.myself()
    print(f"\n✅ Authenticated as: {user['displayName']}")
except Exception as e:
    print(f"\n❌ ERROR: Jira authentication failed: {e}")
    exit(1)

# ---------------------- FUNCTIONS ----------------------

def create_epic(title, description):
    """Creates an Epic in Jira."""
    try:
        epic_issue = jira.create_issue(fields={
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": title,
            "description": description,
            "issuetype": {"name": "Epic"}
        })
        print(f"\n✅ Created Epic: {epic_issue.key}")
        return epic_issue.key
    except Exception as e:
        print(f"\n❌ Error creating epic: {e}")
        exit(1)

def get_user_story_inputs():
    """Prompts the user to enter user story topics (short keywords)."""
    print("\n🔹 Enter User Story Topics (one per line, blank to finish):")
    user_story_topics = []
    while True:
        story = input("➤ ").strip()
        if story == "":
            break
        user_story_topics.append(story)
    
    if not user_story_topics:
        print("\n❌ No user stories provided. Exiting.")
        exit(1)

    return user_story_topics

def generate_stories_and_tasks(epic_title, epic_description, user_story_topics):
    """Uses OpenAI to generate structured Jira stories and tasks."""
    formatted_topics = "\n".join([f"- {topic}" for topic in user_story_topics])
    
    prompt = f"""
    You are an AI Jira assistant.
    The Epic is titled: "{epic_title}"
    The Epic Description: "{epic_description}"
    
    The user has provided the following topics for user stories:
    {formatted_topics}

    Generate a detailed Jira-friendly output:
    - Convert each topic into a **proper user story** in the format:
      "As a <role>, I want <feature> so that <benefit>."
    - Provide **3 acceptance criteria** per story.
    - Generate **2 tasks** for each story, with a title and description.

    Output **only JSON** in the following format:
    [
      {{
        "title": "...",
        "user_story": "...",
        "acceptance_criteria": ["...", "...", "..."],
        "tasks": [
          {{"title": "...", "description": "..."}},
          {{"title": "...", "description": "..."}}
        ]
      }},
      ...
    ]
    """

    models = ["gpt-4o", "gpt-3.5-turbo"]  # Try GPT-4o first, then fallback
    for model in models:
        try:
            print(f"\n🔄 Trying OpenAI model: {model}...")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            # Extract AI response
            ai_response = response.choices[0].message.content.strip()

            # Ensure the response is **only JSON** and valid
            try:
                json_data = json.loads(ai_response)
                return json_data
            except json.JSONDecodeError:
                print("\n❌ Error: AI response was not valid JSON. OpenAI returned:")
                print(ai_response)
                continue  # Try next model if JSON parsing fails

        except openai.APIError as e:
            print(f"\n❌ OpenAI API Error (Model: {model}): {e}")
            continue  # Try next model if API call fails

    print("\n❌ AI-generated stories failed. Exiting.")
    return None

def create_story(epic_key, story_data):
    """Creates a story in Jira linked to the Epic."""
    try:
        story_fields = {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": story_data["title"],
            "description": (
                f"{story_data['user_story']}\n\n"
                "**Acceptance Criteria:**\n"
                + "\n".join([f"- {ac}" for ac in story_data["acceptance_criteria"]])
            ),
            "issuetype": {"name": "Story"},
            "parent": {"key": epic_key}
        }
        story_issue = jira.create_issue(fields=story_fields)
        print(f"  ✅ Created Story: {story_issue.key} - {story_data['title']}")
        return story_issue.key
    except Exception as e:
        print(f"  ❌ Error creating story: {e}")

def create_tasks(story_key, tasks):
    """Creates tasks under a given Story."""
    for task in tasks:
        try:
            task_fields = {
                "project": {"key": JIRA_PROJECT_KEY},
                "summary": task["title"],
                "description": task["description"],
                "issuetype": {"name": "Sub-task"},
                "parent": {"key": story_key}
            }
            task_issue = jira.create_issue(fields=task_fields)
            print(f"    ✅ Created Task: {task_issue.key} - {task['title']}")
        except Exception as e:
            print(f"    ❌ Error creating task: {e}")

# ---------------------- MAIN EXECUTION ----------------------

def main():
    # Prompt user for Epic details
    epic_title = input("\nEnter Epic Title: ").strip()
    epic_description = input("Enter Epic Description: ").strip()

    # Create Epic in Jira
    epic_key = create_epic(epic_title, epic_description)

    # Prompt user for User Story Topics
    user_story_topics = get_user_story_inputs()

    # Generate stories & tasks from AI
    stories = generate_stories_and_tasks(epic_title, epic_description, user_story_topics)
    if stories is None:
        exit(1)

    # Create Stories & Tasks
    for s in stories:
        story_key = create_story(epic_key, s)
        create_tasks(story_key, s["tasks"])

if __name__ == "__main__":
    main()

