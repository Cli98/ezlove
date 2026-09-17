from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.relations import router as relations_router
from app.api.v1.moments import router as moments_router
from app.api.v1.elders import router as elders_router
from app.api.v1.ai import router as ai_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.upload import router as upload_router
from app.api.v1.community_auth import router as community_auth_router
from app.api.v1.community import router as community_router
from app.api.v1.alert_rules import router as alert_rules_router
from app.api.v1.canteen import router as canteen_router
from app.api.v1.community_events import router as events_router
from app.api.v1.poster import router as poster_router
from app.api.v1.agent import router as agent_router
from app.api.v1.export import router as export_router
from app.api.v1.volunteer import router as volunteer_router
from app.api.v1.points import router as points_router
from app.api.v1.ai_media import router as ai_media_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(relations_router)
api_router.include_router(moments_router)
api_router.include_router(elders_router)
api_router.include_router(ai_router)
api_router.include_router(alerts_router)
api_router.include_router(upload_router)
api_router.include_router(community_auth_router)
api_router.include_router(community_router)
api_router.include_router(alert_rules_router)
api_router.include_router(canteen_router)
api_router.include_router(events_router)
api_router.include_router(poster_router)
api_router.include_router(agent_router)
api_router.include_router(export_router)
api_router.include_router(volunteer_router)
api_router.include_router(points_router)
api_router.include_router(ai_media_router)
