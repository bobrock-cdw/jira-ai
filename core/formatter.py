from typing import Any


def format_story_description(story_data: dict[str, Any]) -> str:
    acceptance_criteria = "\n- ".join(story_data["acceptance_criteria"])
    return f"{story_data['user_story']}\n\nAcceptance Criteria:\n- {acceptance_criteria}"
