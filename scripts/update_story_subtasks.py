#!/usr/bin/env python3
import argparse
import sys
from textwrap import dedent

from core.config import DEFAULT_JIRA_SERVER, get_jira_credentials
from core.jira_client import create_jira_client


def parse_args():
    parser = argparse.ArgumentParser(
        description="Add acceptance-criteria evidence comments to all subtasks under a Jira Story.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually update Jira. Without this flag, the script runs as a dry run.",
    )
    parser.add_argument(
        "--story",
        help="Story key to update, for example MC-123. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--jira-server",
        default=DEFAULT_JIRA_SERVER,
        help=f"Jira server URL. Defaults to JIRA_SERVER or {DEFAULT_JIRA_SERVER}.",
    )
    return parser.parse_args()


def require_credentials():
    credentials = get_jira_credentials()
    if not credentials:
        print("Missing JIRA_USERNAME or JIRA_API_TOKEN in your environment or .env file.")
        sys.exit(1)
    return credentials


def prompt_multiline(prompt: str) -> str:
    print(prompt)
    print("Enter text. Type DONE on its own line when finished.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "DONE":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def extract_acceptance_criteria(description: str | None) -> list[str]:
    if not description:
        return []

    lines = description.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    criteria = []
    in_section = False

    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower()
        if "acceptance criteria" in lowered:
            in_section = True
            continue
        if in_section and stripped.endswith(":") and criteria:
            break
        if in_section and stripped:
            cleaned = stripped.lstrip("-*•0123456789. ").strip()
            if cleaned:
                criteria.append(cleaned)

    return criteria


def format_comment(story_key: str, story_summary: str, criteria: list[str], evidence: str) -> str:
    criteria_text = "\n".join(f"- {criterion}" for criterion in criteria)
    if not criteria_text:
        criteria_text = "- No acceptance criteria section was detected on the Story."

    return dedent(
        f"""
        Acceptance Criteria Evidence Update

        Story: {story_key} - {story_summary}

        Acceptance Criteria Reviewed:
        {criteria_text}

        Evidence / Work Completed:
        {evidence}
        """
    ).strip()


def collect_subtask_comments(story_key: str, story_summary: str, criteria: list[str], subtasks) -> list[tuple[str, str, str]]:
    comments = []
    for index, subtask in enumerate(subtasks, start=1):
        print(f"\nSubtask {index}/{len(subtasks)}: {subtask.key} - {subtask.fields.summary}")
        evidence = prompt_multiline(
            "Describe the evidence for this specific subtask. Leave blank and type DONE to skip this subtask."
        )
        if not evidence:
            print(f"Skipping {subtask.key}; no evidence provided.")
            continue
        comments.append(
            (
                subtask.key,
                subtask.fields.summary,
                format_comment(story_key, story_summary, criteria, evidence),
            )
        )
    return comments


def main():
    args = parse_args()
    credentials = require_credentials()
    jira_client = create_jira_client(args.jira_server, credentials)

    story_key = args.story or input("Story key: ").strip()
    if not story_key:
        print("No Story key provided.")
        sys.exit(1)

    story = jira_client.issue(story_key)
    story_summary = story.fields.summary
    story_description = story.fields.description
    subtasks = getattr(story.fields, "subtasks", [])
    criteria = extract_acceptance_criteria(story_description)

    print(f"\nStory: {story_key} - {story_summary}")
    print(f"Subtasks found: {len(subtasks)}")
    if criteria:
        print("\nAcceptance criteria found:")
        for criterion in criteria:
            print(f"- {criterion}")
    else:
        print("\nNo acceptance criteria section was detected on the Story.")

    if not subtasks:
        print("No subtasks found; nothing to update.")
        return

    comments = collect_subtask_comments(story_key, story_summary, criteria, subtasks)
    if not comments:
        print("No subtask evidence provided; nothing to update.")
        return

    print("\nComments prepared:")
    for subtask_key, subtask_summary, comment in comments:
        print("\n" + "=" * 72)
        print(f"{subtask_key}: {subtask_summary}")
        print("-" * 72)
        print(comment)
    print("=" * 72)

    if not args.apply:
        print("\nDRY RUN: no Jira subtasks were updated. Re-run with --apply to add these comments.")
        for subtask_key, subtask_summary, _ in comments:
            print(f"Would update {subtask_key}: {subtask_summary}")
        return

    confirm = input("\nType UPDATE to add these comments to the listed subtasks: ").strip()
    if confirm != "UPDATE":
        print("Cancelled.")
        return

    for subtask_key, subtask_summary, comment in comments:
        jira_client.add_comment(subtask_key, comment)
        print(f"Updated {subtask_key}: {subtask_summary}")

    print("\nDone.")


if __name__ == "__main__":
    main()
