"""Domain logic for recognition endorsements."""

from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import Recognition, RecognitionEndorsement, Student


class EndorsementRuleViolation(Exception):
    """Raised when endorsement rules are not met."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _ensure_student(session: Session, student_id: UUID) -> Student:
    stmt = select(Student).where(Student.student_id == student_id)
    student = session.execute(stmt).scalar_one_or_none()
    if student is None:
        raise EndorsementRuleViolation(f"Student {student_id} not found", status_code=404)
    return student


def _ensure_recognition(session: Session, recognition_id: UUID) -> Recognition:
    stmt = select(Recognition).options(joinedload(Recognition.receiver), joinedload(Recognition.sender)).where(
        Recognition.recognition_id == recognition_id
    )
    recognition = session.execute(stmt).scalar_one_or_none()
    if recognition is None:
        raise EndorsementRuleViolation(f"Recognition {recognition_id} not found", status_code=404)
    return recognition


def create_endorsement(
    session: Session,
    *,
    recognition_id: UUID,
    endorser_id: UUID,
) -> RecognitionEndorsement:
    """Insert a new endorsement ensuring uniqueness."""

    recognition = _ensure_recognition(session, recognition_id)
    endorser = _ensure_student(session, endorser_id)

    existing_stmt = select(RecognitionEndorsement).where(
        RecognitionEndorsement.recognition_id == recognition.recognition_id,
        RecognitionEndorsement.endorser_id == endorser.student_id,
    )
    existing = session.execute(existing_stmt).scalar_one_or_none()
    if existing is not None:
        raise EndorsementRuleViolation("Student has already endorsed this recognition.")

    endorsement = RecognitionEndorsement(
        recognition=recognition,
        endorser=endorser,
    )
    session.add(endorsement)
    recognition.endorsement_count += 1
    session.flush()
    session.refresh(endorsement)
    return endorsement


def list_endorsements(
    session: Session,
    *,
    recognition_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[RecognitionEndorsement]:
    """Return endorsements for a recognition."""

    _ensure_recognition(session, recognition_id)

    stmt = (
        select(RecognitionEndorsement)
        .options(joinedload(RecognitionEndorsement.endorser))
        .where(RecognitionEndorsement.recognition_id == recognition_id)
        .order_by(RecognitionEndorsement.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    results = session.execute(stmt).scalars().all()
    return results
