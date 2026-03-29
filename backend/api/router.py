from fastapi import APIRouter

from api.audio_briefing import router as audio_briefing_router
from api.health import router as health_router
from api.incidents import router as incidents_router
from api.official_alerts import router as official_alerts_router
from api.submissions import router as submissions_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(audio_briefing_router)
api_router.include_router(incidents_router)
api_router.include_router(official_alerts_router)
api_router.include_router(submissions_router)
