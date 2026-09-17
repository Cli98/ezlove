from uuid import UUID
from pydantic import BaseModel


class AiSuggestRequest(BaseModel):
    elder_id: UUID


class AiSuggestion(BaseModel):
    tag: str
    text: str


class AiSuggestResponse(BaseModel):
    suggestions: list[AiSuggestion]
