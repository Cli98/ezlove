from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import User
from app.schemas.ai import AiSuggestRequest, AiSuggestResponse, AiSuggestion
from app.services.ai_content import generate_suggestions

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/suggest", response_model=AiSuggestResponse)
async def suggest(req: AiSuggestRequest, user: User = Depends(get_current_user)):
    raw = await generate_suggestions()
    suggestions = [AiSuggestion(tag=s["tag"], text=s["text"]) for s in raw]
    return AiSuggestResponse(suggestions=suggestions)
