"""Leaderboard endpoint."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...schemas import LeaderboardStudent
from ...services import leaderboard_service

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get(
    "",
    response_model=List[LeaderboardStudent],
    summary="Top credit recipients",
    responses={
        200: {
            "description": "Leaderboard entries ordered by credits received",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "student_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                            "campus_uid": "S1002",
                            "display_name": "Bianca Liu",
                            "email": "bianca.liu@example.edu",
                            "total_credits_received": 80,
                            "recognitions_received": 3,
                            "endorsements_received": 5
                        }
                    ]
                }
            },
        }
    },
)
def get_leaderboard(
    limit: int = Query(10, ge=1, le=100, description="Number of top students to return"),
    db: Session = Depends(get_db),
) -> List[LeaderboardStudent]:
    """Return ranked list of students based on credits received."""

    entries = leaderboard_service.top_recipients(db, limit=limit)
    response: List[LeaderboardStudent] = []
    for student, total_credits, recognitions_count, endorsements in entries:
        response.append(
            LeaderboardStudent(
                student_id=student.student_id,
                campus_uid=student.campus_uid,
                display_name=student.display_name,
                email=student.email,
                total_credits_received=int(total_credits or 0),
                recognitions_received=int(recognitions_count or 0),
                endorsements_received=int(endorsements or 0),
            )
        )
    return response
