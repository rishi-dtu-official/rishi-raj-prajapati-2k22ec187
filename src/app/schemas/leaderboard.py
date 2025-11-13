"""Leaderboard response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class LeaderboardStudent(BaseModel):
    """Aggregated leaderboard entry."""

    student_id: UUID
    campus_uid: str
    display_name: str
    email: str
    total_credits_received: int = Field(..., ge=0)
    recognitions_received: int = Field(..., ge=0)
    endorsements_received: int = Field(..., ge=0)

    class Config:
        orm_mode = True
