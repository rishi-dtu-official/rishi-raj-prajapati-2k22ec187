"""Endpoints for recognition endorsements."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...schemas import EndorsementCreate, EndorsementRead
from ...services import endorsement_service
from ...services.endorsement_service import EndorsementRuleViolation

router = APIRouter(prefix="/endorsements", tags=["endorsements"])


@router.post(
    "",
    response_model=EndorsementRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an endorsement",
    responses={
        201: {
            "description": "Endorsement created",
            "content": {
                "application/json": {
                    "example": {
                        "endorsement_id": "66666666-6666-6666-6666-666666666666",
                        "recognition_id": "44444444-4444-4444-4444-444444444444",
                        "endorser": {
                            "student_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                            "campus_uid": "S1003",
                            "display_name": "Carlos Menon",
                            "email": "carlos.menon@example.edu",
                        },
                        "created_at": "2025-11-12T12:05:30+00:00"
                    }
                }
            },
        },
        400: {"description": "Business rule violation"},
        404: {"description": "Recognition or student not found"},
    },
)
def create_endorsement(
    payload: EndorsementCreate,
    db: Session = Depends(get_db),
) -> EndorsementRead:
    """Register an endorsement for a recognition.

    Example request body::

        {
            "recognition_id": "44444444-4444-4444-4444-444444444444",
            "endorser_id": "cccccccc-cccc-cccc-cccc-cccccccccccc"
        }
    """

    try:
        endorsement = endorsement_service.create_endorsement(
            db,
            recognition_id=payload.recognition_id,
            endorser_id=payload.endorser_id,
        )
        db.commit()
        db.refresh(endorsement)
        return endorsement
    except EndorsementRuleViolation as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "",
    response_model=List[EndorsementRead],
    summary="List endorsements for a recognition",
    responses={
        200: {
            "description": "Endorsements for recognition",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "endorsement_id": "66666666-6666-6666-6666-666666666666",
                            "recognition_id": "44444444-4444-4444-4444-444444444444",
                            "endorser": {
                                "student_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                                "campus_uid": "S1003",
                                "display_name": "Carlos Menon",
                                "email": "carlos.menon@example.edu"
                            },
                            "created_at": "2025-11-12T12:05:30+00:00"
                        }
                    ]
                }
            },
        }
    },
)
def list_endorsements(
    *,
    recognition_id: UUID = Query(..., description="Recognition to fetch endorsements for"),
    limit: int = Query(50, ge=1, le=100, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Items to skip for pagination"),
    db: Session = Depends(get_db),
) -> List[EndorsementRead]:
    """Return endorsements scoped to a recognition."""

    endorsements = endorsement_service.list_endorsements(
        db,
        recognition_id=recognition_id,
        limit=limit,
        offset=offset,
    )
    return list(endorsements)
