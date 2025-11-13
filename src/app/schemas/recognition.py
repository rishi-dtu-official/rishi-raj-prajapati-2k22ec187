"""Pydantic schemas for recognition endpoints."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class StudentSummary(BaseModel):
    """Lightweight projection of student details."""

    model_config = ConfigDict(from_attributes=True)

    student_id: UUID
    campus_uid: str
    display_name: str
    email: str


class RecognitionCreate(BaseModel):
    """Request body for creating a recognition."""

    sender_id: UUID
    receiver_id: UUID
    credits_transferred: int = Field(
        ...,
        gt=0,
        le=100,
        description="Credits to transfer to the receiver.",
    )
    message: Optional[str] = Field(None, max_length=280)


class RecognitionRead(BaseModel):
    """Recognition response payload."""

    model_config = ConfigDict(from_attributes=True)

    recognition_id: UUID
    sender: StudentSummary
    receiver: StudentSummary
    credits_transferred: int
    message: Optional[str]
    month_bucket: date
    created_at: datetime
