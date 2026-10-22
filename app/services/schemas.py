import json

from pydantic import BaseModel, Field, ValidationError


class AIResponseError(Exception):
    pass


class AIFix(BaseModel):
    category: str = Field(max_length=100)
    line: int | None = None
    root_cause: str = Field(max_length=2000)
    beginner_explanation: str = Field(max_length=3000)
    why_fix_works: str = Field(max_length=3000)
    prevention_tips: list[str] = Field(max_length=10)
    changes: list[str] = Field(max_length=30)
    corrected_code: str = Field(max_length=100_000)
    verification_recommendations: list[str] = Field(max_length=10)


def parse_ai_response(text):
    """Turns the model's text into a checked AIFix, or raises AIResponseError."""
    if not isinstance(text, str) or not text.strip():
        raise AIResponseError("Empty answer")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise AIResponseError("No JSON found")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        raise AIResponseError("Invalid JSON")
    try:
        return AIFix.model_validate(data)
    except ValidationError:
        raise AIResponseError("JSON has the wrong shape")