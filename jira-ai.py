import os
import json
import sys
import subprocess
from datetime import datetime
from jira import JIRA

from core.config import (
    DEFAULT_GCP_LOCATION,
    DEFAULT_GCP_PROJECT_ID,
    DEFAULT_JIRA_ASSIGNEE,
    DEFAULT_JIRA_COMPONENT,
    DEFAULT_JIRA_PROJECT,
    DEFAULT_JIRA_SERVER,
    GEMINI_MODEL,
    LARGE_PASTE_WARNING_CHARS,
    MAX_BRIEF_CHARS,
    SessionConfig,
    get_jira_credentials,
)
from core.gemini import (
    create_gemini_client,
    generate_ai_content as core_generate_ai_content,
    test_gemini_connection,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

# Session globals set during startup()
JIRA_SERVER = None
JIRA_PROJECT_KEY = None
JIRA_COMPONENT_NAME = None
JIRA_ASSIGNEE_USERNAME = None
GCP_PROJECT_ID = None
GCP_LOCATION = None
PROJECT_CONTEXT = None
client = None
jira = None
ASSIGNEE_ACCOUNT_ID = None


def status(message):
    print(message, file=sys.stderr, flush=True)


def safe_input(prompt):
    """
    Prefer built-in input() for normal interactive prompts.
    Fall back to stdin.readline() only if input() raises unexpectedly.
    """
    try:
        return input(prompt)
    except EOFError:
        return ""
    except Exception:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            return ""
        return line.rstrip("\r\n")


def get_initial_config():
    print("--- Professional Jira AI Assistant (Vertex AI) ---")
    server = safe_input(f"Jira Server URL (default: {DEFAULT_JIRA_SERVER}): ").strip() or DEFAULT_JIRA_SERVER
    jira_project = safe_input(f"Jira Project Key (default: {DEFAULT_JIRA_PROJECT}): ").strip() or DEFAULT_JIRA_PROJECT
    component = safe_input(f"Jira Component (default: {DEFAULT_JIRA_COMPONENT}): ").strip() or DEFAULT_JIRA_COMPONENT
    assignee = safe_input(f"Jira Assignee (default: {DEFAULT_JIRA_ASSIGNEE}): ").strip() or DEFAULT_JIRA_ASSIGNEE

    print("\n--- Google Cloud Configuration ---")
    gcp_project = safe_input(f"GCP Project ID (default: {DEFAULT_GCP_PROJECT_ID}): ").strip() or DEFAULT_GCP_PROJECT_ID
    location = safe_input(f"GCP Region (default: {DEFAULT_GCP_LOCATION}): ").strip() or DEFAULT_GCP_LOCATION

    print("\n--- Session Context ---")
    context = safe_input("Enter Project/Tech Context: ").strip()

    return SessionConfig(
        jira_server=server,
        jira_project_key=jira_project,
        jira_component_name=component,
        jira_assignee_username=assignee,
        gcp_project_id=gcp_project,
        gcp_location=location,
        project_context=context,
    )


def startup():
    global JIRA_SERVER, JIRA_PROJECT_KEY, JIRA_COMPONENT_NAME, JIRA_ASSIGNEE_USERNAME
    global GCP_PROJECT_ID, GCP_LOCATION, PROJECT_CONTEXT
    global client, jira, ASSIGNEE_ACCOUNT_ID

    config = get_initial_config()
    JIRA_SERVER = config.jira_server
    JIRA_PROJECT_KEY = config.jira_project_key
    JIRA_COMPONENT_NAME = config.jira_component_name
    JIRA_ASSIGNEE_USERNAME = config.jira_assignee_username
    GCP_PROJECT_ID = config.gcp_project_id
    GCP_LOCATION = config.gcp_location
    PROJECT_CONTEXT = config.project_context

    jira_credentials = get_jira_credentials()
    if not jira_credentials:
        print("❌ Error: JIRA_USERNAME or JIRA_API_TOKEN not found.")
        sys.exit(1)

    status(f"Initializing Gemini client ({GCP_PROJECT_ID}, {GCP_LOCATION})...")
    try:
        client = create_gemini_client(GCP_PROJECT_ID, GCP_LOCATION)
        print(f"✅ Gemini Client initialized for: {GCP_PROJECT_ID} ({GCP_LOCATION})")
    except Exception as e:
        print(f"❌ Vertex AI Initialization Failed: {e}")
        sys.exit(1)

    status("Connecting to Jira...")
    try:
        jira = JIRA(
            server=JIRA_SERVER,
            basic_auth=(jira_credentials.username, jira_credentials.token),
        )
        print(f"✅ Authenticated to Jira: {jira.myself()['displayName']}")
        users = jira.search_users(query=JIRA_ASSIGNEE_USERNAME, maxResults=1)
        ASSIGNEE_ACCOUNT_ID = users[0].accountId if users else None
    except Exception as e:
        print(f"❌ Jira Setup Failed: {e}")
        sys.exit(1)


def log_deliberation(data):
    if not os.path.exists("logs"):
        os.makedirs("logs")
    filename = f"logs/deliberation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    print(f"💾 Local log saved: {filename}")


def _read_clipboard():
    try:
        text = subprocess.check_output(["pbpaste"], text=True)
    except Exception as e:
        print(f"❌ Failed to read clipboard via pbpaste: {e}", flush=True)
        return ""
    text = text.rstrip("\r\n")
    if text:
        print(f"✅ Loaded {len(text):,} characters from clipboard.", flush=True)
    else:
        print("⚠️ Clipboard is empty.", flush=True)
    return text


def _read_file_path():
    path = safe_input("File path: ").strip().strip("'\"")
    if not path:
        return ""
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            text = f.read()
        print(f"✅ Loaded {len(text):,} characters from {path}.", flush=True)
        return text.strip()
    except Exception as e:
        print(f"❌ Failed to read file: {e}", flush=True)
        return ""


def _read_terminal_lines():
    """Read pasted/typed text until DONE. No mid-read prints — they break large pastes."""
    print(
        "Paste or type your text, then type DONE on its own line and press Enter.",
        flush=True,
    )
    lines = []
    total_chars = 0
    warned_large_paste = False
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if line.strip().upper() == "DONE":
            break
        lines.append(line)
        total_chars += len(line)
        if not warned_large_paste and total_chars >= LARGE_PASTE_WARNING_CHARS:
            print(
                f"⚠️ Large input (~{total_chars:,} chars). "
                "For big documents, cancel (Ctrl+C) and retry with clipboard or file instead.",
                flush=True,
            )
            warned_large_paste = True
    return "".join(lines).strip()


def get_multiline_input(prompt):
    print(f"\n{prompt}")
    print("-" * 30, flush=True)
    print(
        "How do you want to provide the text?\n"
        "  [c] Clipboard — recommended for large documents (macOS)\n"
        "  [f] File path\n"
        "  [t] Type/paste in terminal — OK for short text only",
        flush=True,
    )
    method = safe_input("Choice [c/f/t] (default: c): ").strip().lower() or "c"

    if method in ("c", "clipboard"):
        text = _read_clipboard()
    elif method in ("f", "file"):
        text = _read_file_path()
    elif method in ("t", "terminal", "paste"):
        text = _read_terminal_lines()
    else:
        print("⚠️ Unknown choice; using clipboard.", flush=True)
        text = _read_clipboard()

    if len(text) > MAX_BRIEF_CHARS:
        print(
            f"❌ Input too large ({len(text):,} chars; max {MAX_BRIEF_CHARS:,}). "
            "Shorten the brief or split into multiple stories.",
            flush=True,
        )
        return ""

    if text:
        print(f"✅ Brief captured ({len(text):,} chars).", flush=True)
    return text


def generate_ai_content(prompt_type, brief):
    print(
        f"\n⏳ Generating with {GEMINI_MODEL} ({len(brief):,} char brief). "
        "Watch for progress below — usually 15–60s.",
        flush=True,
    )
    status(
        f"Calling {GEMINI_MODEL} via Vertex AI. Progress updates every 2s..."
    )

    try:
        data = core_generate_ai_content(
            client=client,
            prompt_type=prompt_type,
            brief=brief,
            project_context=PROJECT_CONTEXT,
            progress_callback=status,
        )
        status("Gemini responded.")
        return data
    except json.JSONDecodeError as exc:
        print(f"\n❌ Gemini Error: invalid JSON in response ({exc}).")
        return None
    except Exception as exc:
        print(f"\n❌ Gemini Error: {exc}")
        return None


def create_issue(issue_type, summary, description, parent=None):
    fields = {
        "project": {"key": JIRA_PROJECT_KEY},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
        "assignee": {"accountId": ASSIGNEE_ACCOUNT_ID} if ASSIGNEE_ACCOUNT_ID else None,
    }
    if JIRA_COMPONENT_NAME:
        fields["components"] = [{"name": JIRA_COMPONENT_NAME}]
    if parent:
        fields["parent"] = {"key": parent}

    try:
        issue = jira.create_issue(fields=fields)
        print(f"✅ Created {issue_type}: {issue.key}")
        return issue.key
    except Exception as e:
        print(f"❌ Creation Failed: {e}")
        return None


def test_gemini():
    project = os.getenv("GCP_PROJECT_ID", DEFAULT_GCP_PROJECT_ID)
    location = os.getenv("GCP_LOCATION", DEFAULT_GCP_LOCATION)
    status(f"Gemini connectivity test: project={project}, location={location}")

    try:
        status("Client created. Sending test prompt...")
        elapsed, response_text = test_gemini_connection(project, location)
        print(f"✅ Gemini OK in {elapsed}s: {response_text}")
    except Exception as e:
        print(f"❌ Gemini test failed: {e}")
        sys.exit(1)


def main():
    while True:
        print("\n1. Epic | 2. Story | 3. Task/SubTask | 4. Exit")
        choice = safe_input("Choice: ")

        if choice == "1":
            title = safe_input("Epic Title: ")
            desc = get_multiline_input("Epic Description")
            create_issue("Epic", title, desc)

        elif choice == "2":
            epic = safe_input("Epic Key (optional): ").strip() or None
            brief = get_multiline_input("Describe the Story requirement")
            if not brief:
                print("⚠️ No brief provided; skipping.")
                continue
            while True:
                data = generate_ai_content("story", brief)
                if not data:
                    break
                log_deliberation(data)
                print("\nPROPOSED CONTENT:\n", json.dumps(data, indent=2))
                action = safe_input("\n[y] Create, [r] Retry, [n] Cancel: ").lower().strip()
                if action == "y":
                    desc = f"{data['user_story']}\n\nAcceptance Criteria:\n- " + "\n- ".join(data["acceptance_criteria"])
                    key = create_issue("Story", data["title"], desc, epic)
                    if key:
                        for t in data["tasks"]:
                            create_issue("Sub-task", t["title"], t["description"], key)
                    break
                if action != "r":
                    break

        elif choice == "3":
            i_type = safe_input("Create Task or Sub-task? [task/subtask]: ").lower().strip()
            parent = safe_input("Parent Key (optional for Task): ").strip() or None
            brief = get_multiline_input(f"Describe the {i_type}")
            if not brief:
                print("⚠️ No brief provided; skipping.")
                continue
            while True:
                data = generate_ai_content("task", brief)
                if not data:
                    break
                log_deliberation(data)
                print("\nPROPOSED CONTENT:\n", json.dumps(data, indent=2))
                action = safe_input("\n[y] Create, [r] Retry, [n] Cancel: ").lower().strip()
                if action == "y":
                    key = create_issue(
                        "Task" if i_type == "task" else "Sub-task",
                        data["title"],
                        data["description"],
                        parent,
                    )
                    if key and i_type == "task" and "subtasks" in data:
                        for s in data["subtasks"]:
                            create_issue("Sub-task", s["title"], s["description"], key)
                    break
                if action != "r":
                    break
        elif choice == "4":
            break


if __name__ == "__main__":
    if "--test-gemini" in sys.argv:
        test_gemini()
    else:
        startup()
        main()
