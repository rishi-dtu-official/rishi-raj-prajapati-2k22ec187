"""Leaderboard response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class LeaderboardStudent(BaseModel):
    """Aggregated leaderboard entry."""

    model_config = ConfigDict(from_attributes=True)

    student_id: UUID
    campus_uid: str
    display_name: str
    email: str
    total_credits_received: int = Field(..., ge=0)
    recognitions_received: int = Field(..., ge=0)
    endorsements_received: int = Field(..., ge=0)
