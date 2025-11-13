"""Recognition endpoints."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...schemas import RecognitionCreate, RecognitionRead
from ...services import recognition_service
from ...services.recognition_service import RecognitionRuleViolation

router = APIRouter(prefix="/recognitions", tags=["recognitions"])


@router.post(
    "",
    response_model=RecognitionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recognition",
    responses={
        201: {
            "description": "Recognition created",
            "content": {
                "application/json": {
                    "example": {
                        "recognition_id": "44444444-4444-4444-4444-444444444444",
                        "sender": {
                            "student_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                            "campus_uid": "S1001",
                            "display_name": "Alex Rao",
                            "email": "alex.rao@example.edu",
                        },
                        "receiver": {
                            "student_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                            "campus_uid": "S1002",
                            "display_name": "Bianca Liu",
                            "email": "bianca.liu@example.edu",
                        },
                        "credits_transferred": 30,
                        "message": "Thanks for leading the robotics workshop!",
                        "month_bucket": "2025-11-01",
                        "created_at": "2025-11-12T10:15:30+00:00",
                    }
                }
            },
        },
        400: {"description": "Business rule violation"},
        404: {"description": "Student not found"},
    },
)
def create_recognition(
    payload: RecognitionCreate,
    db: Session = Depends(get_db),
) -> RecognitionRead:
    """Transfer credits from one student to another.

    Example request body::

        {
            "sender_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "receiver_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "credits_transferred": 30,
            "message": "Thanks for leading the robotics workshop!"
        }
    """

    try:
        recognition = recognition_service.create_recognition(
            db,
            sender_id=payload.sender_id,
            receiver_id=payload.receiver_id,
            credits_transferred=payload.credits_transferred,
            message=payload.message,
        )
        db.commit()
        db.refresh(recognition)
        return recognition
    except RecognitionRuleViolation as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "",
    response_model=List[RecognitionRead],
    summary="List recognitions",
    responses={
        200: {
            "description": "Paged recognition list",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "recognition_id": "44444444-4444-4444-4444-444444444444",
                            "sender": {
                                "student_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                                "campus_uid": "S1001",
                                "display_name": "Alex Rao",
                                "email": "alex.rao@example.edu",
                            },
                            "receiver": {
                                "student_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                                "campus_uid": "S1002",
                                "display_name": "Bianca Liu",
                                "email": "bianca.liu@example.edu",
                            },
                            "credits_transferred": 30,
                            "message": "Thanks for leading the robotics workshop!",
                            "month_bucket": "2025-11-01",
                            "created_at": "2025-11-12T10:15:30+00:00",
                        }
                    ]
                }
            },
        }
    },
)
def list_recognitions(
    *,
    sender_id: Optional[UUID] = Query(None, description="Filter by sender UUID"),
    receiver_id: Optional[UUID] = Query(None, description="Filter by receiver UUID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Items to skip for pagination"),
    db: Session = Depends(get_db),
) -> List[RecognitionRead]:
    """Fetch recognitions with optional sender/receiver filters."""

    recognitions = recognition_service.list_recognitions(
        db,
        sender_id=sender_id,
        receiver_id=receiver_id,
        limit=limit,
        offset=offset,
    )
    return list(recognitions)
