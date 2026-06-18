from typing import Any

from pydantic import BaseModel, Field, field_validator


def _clean_string(value: Any) -> str:
    return str(value).strip()


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")
        if "\n" in normalized:
            parts = normalized.split("\n")
        elif ";" in normalized:
            parts = normalized.split(";")
        else:
            parts = [normalized]
        return [
            part.strip().lstrip("-•*0123456789. ").strip()
            for part in parts
            if part.strip()
        ]
    if isinstance(value, list):
        return [_clean_string(item) for item in value if _clean_string(item)]
    return [_clean_string(value)]


class GeneratedTask(BaseModel):
    title: str
    description: str

    @field_validator("title", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        return _clean_string(value)


class StoryGenerationResult(BaseModel):
    title: str
    user_story: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    tasks: list[GeneratedTask] = Field(default_factory=list)

    @field_validator("title", "user_story", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        return _clean_string(value)

    @field_validator("acceptance_criteria", mode="before")
    @classmethod
    def normalize_acceptance_criteria(cls, value: Any) -> list[str]:
        return _normalize_string_list(value)


class TaskGenerationResult(BaseModel):
    title: str
    description: str
    subtasks: list[GeneratedTask] = Field(default_factory=list)

    @field_validator("title", "description", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        return _clean_string(value)


def validate_ai_response(prompt_type: str, data: dict[str, Any]) -> dict[str, Any]:
    if prompt_type == "story":
        return StoryGenerationResult.model_validate(data).model_dump()
    if prompt_type == "task":
        return TaskGenerationResult.model_validate(data).model_dump()
    raise ValueError(f"Unsupported prompt type: {prompt_type}")
