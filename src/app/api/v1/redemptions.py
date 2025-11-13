"""Endpoints for credit redemptions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...schemas import RedemptionCreate, RedemptionReceipt
from ...services import redemption_service
from ...services.redemption_service import RedemptionRuleViolation

router = APIRouter(prefix="/redemptions", tags=["redemptions"])


@router.post(
    "",
    response_model=RedemptionReceipt,
    status_code=status.HTTP_201_CREATED,
    summary="Redeem credits",
    responses={
        201: {
            "description": "Redemption completed",
            "content": {
                "application/json": {
                    "example": {
                        "redemption": {
                            "redemption_id": "88888888-8888-8888-8888-888888888888",
                            "student": {
                                "student_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                                "campus_uid": "S1002",
                                "display_name": "Bianca Liu",
                                "email": "bianca.liu@example.edu"
                            },
                            "credits_redeemed": 40,
                            "voucher_value": 200,
                            "status": "ISSUED",
                            "created_at": "2025-11-12T14:30:00+00:00"
                        },
                        "available_balance": 35
                    }
                }
            },
        },
        400: {"description": "Business rule violation"},
        404: {"description": "Student not found"},
    },
)
def redeem_credits(
    payload: RedemptionCreate,
    db: Session = Depends(get_db),
) -> RedemptionReceipt:
    """Redeem available credits for vouchers.

    Example request body::

        {
            "student_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "credits_redeemed": 40
        }
    """

    try:
        redemption, remaining_balance = redemption_service.redeem(
            db,
            student_id=payload.student_id,
            credits_redeemed=payload.credits_redeemed,
        )
        db.commit()
        db.refresh(redemption)
        return RedemptionReceipt(redemption=redemption, available_balance=remaining_balance)
    except RedemptionRuleViolation as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
