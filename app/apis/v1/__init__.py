from fastapi import APIRouter

from app.apis.v1.auth_routers import auth_router
from app.apis.v1.challenge_routers import (
    challenge_categories_router,
    challenge_invitations_router,
    challenge_recommendations_router,
    challenge_summaries_router,
    challenge_verifications_router,
    challenges_router,
)
from app.apis.v1.chatbot_routers import chatbot_router
from app.apis.v1.files_routers import files_router
from app.apis.v1.health_routers import (
    health_records_router,
    health_reports_router,
    predictions_router,
)
from app.apis.v1.pet_routers import (
    attendance_router,
    inventory_router,
    pets_router,
    points_router,
    rewards_router,
    store_router,
)
from app.apis.v1.user_routers import user_router

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(user_router)
v1_routers.include_router(health_records_router)
v1_routers.include_router(health_reports_router)
v1_routers.include_router(predictions_router)
v1_routers.include_router(challenge_categories_router)
v1_routers.include_router(challenges_router)
v1_routers.include_router(challenge_invitations_router)
v1_routers.include_router(challenge_verifications_router)
v1_routers.include_router(challenge_summaries_router)
v1_routers.include_router(challenge_recommendations_router)
v1_routers.include_router(pets_router)
v1_routers.include_router(store_router)
v1_routers.include_router(inventory_router)
v1_routers.include_router(points_router)
v1_routers.include_router(attendance_router)
v1_routers.include_router(rewards_router)
v1_routers.include_router(chatbot_router)
v1_routers.include_router(files_router)
