"""Pydantic schemas for endorsement endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from .recognition import StudentSummary


class EndorsementCreate(BaseModel):
    """Request payload to endorse a recognition."""

    recognition_id: UUID
    endorser_id: UUID


class EndorsementRead(BaseModel):
    """Response payload representing an endorsement."""

    endorsement_id: UUID
    recognition_id: UUID
    endorser: StudentSummary
    created_at: datetime

    class Config:
        orm_mode = True
