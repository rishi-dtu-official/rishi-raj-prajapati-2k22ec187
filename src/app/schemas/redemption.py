"""Pydantic schemas for redemption workflows."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .recognition import StudentSummary


class RedemptionCreate(BaseModel):
    """Incoming payload for redeeming credits."""

    student_id: UUID
    credits_redeemed: int = Field(..., gt=0, description="Number of credits to redeem.")


class RedemptionRead(BaseModel):
    """Represents a redemption record."""

    redemption_id: UUID
    student: StudentSummary
    credits_redeemed: int
    voucher_value: int
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


class RedemptionReceipt(BaseModel):
    """Response returned after processing a redemption."""

    redemption: RedemptionRead
    available_balance: int = Field(..., description="Redeemable balance after this redemption.")
