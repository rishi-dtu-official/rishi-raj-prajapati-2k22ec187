"""Primary API router definition."""

from fastapi import APIRouter

from . import endorsements, leaderboard, recognitions, redemptions

api_router = APIRouter()

api_router.include_router(recognitions.router)
api_router.include_router(endorsements.router)
api_router.include_router(redemptions.router)
api_router.include_router(leaderboard.router)


@api_router.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Basic health probe endpoint."""
    return {"status": "ok"}
