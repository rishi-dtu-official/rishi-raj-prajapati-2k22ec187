"""Leaderboard aggregation services."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Recognition, Student


def top_recipients(session: Session, *, limit: int = 10) -> Sequence[tuple]:
    """Return leaderboard entries ordered by credits received and student id."""

    limit = max(1, min(limit, 100))

    total_credits = func.coalesce(func.sum(Recognition.credits_transferred), 0).label("total_credits")
    recognitions_count = func.coalesce(func.count(Recognition.recognition_id), 0).label("recognition_count")
    endorsements = func.coalesce(func.sum(Recognition.endorsement_count), 0).label("endorsement_count")

    stmt = (
        select(
            Student,
            total_credits,
            recognitions_count,
            endorsements,
        )
        .outerjoin(Recognition, Recognition.receiver_id == Student.student_id)
        .group_by(Student.student_id)
        .order_by(total_credits.desc(), Student.student_id.asc())
        .limit(limit)
    )

    return session.execute(stmt).all()
