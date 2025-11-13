"""Pydantic schemas for recognition endpoints."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StudentSummary(BaseModel):
    """Lightweight projection of student details."""

    student_id: UUID
    campus_uid: str
    display_name: str
    email: str

    class Config:
        orm_mode = True


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

    recognition_id: UUID
    sender: StudentSummary
    receiver: StudentSummary
    credits_transferred: int
    message: Optional[str]
    month_bucket: date
    created_at: datetime

    class Config:
        orm_mode = True
