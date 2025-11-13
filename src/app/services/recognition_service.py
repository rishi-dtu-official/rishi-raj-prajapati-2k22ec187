"""Domain logic for recognition workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, joinedload

from ..models import CreditEventType, CreditLedger, MonthlyQuota, Recognition, Student
from ..utils.datetime import month_bucket


class RecognitionRuleViolation(Exception):
    """Raised when business constraints are violated."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _ensure_student(session: Session, student_id: UUID) -> Student:
    try:
        stmt = select(Student).where(Student.student_id == student_id)
        return session.execute(stmt).scalar_one()
    except NoResultFound as exc:  # pragma: no cover - defensive branch
        raise RecognitionRuleViolation(f"Student {student_id} not found", status_code=404) from exc


def _ensure_monthly_context(session: Session, student_id: UUID, bucket) -> MonthlyQuota:
    quota_stmt = (
        select(MonthlyQuota)
        .where(MonthlyQuota.student_id == student_id, MonthlyQuota.month_bucket == bucket)
        .with_for_update(nowait=False)
    )
    quota = session.execute(quota_stmt).scalar_one_or_none()

    if quota is None:
        quota = MonthlyQuota(student_id=student_id, month_bucket=bucket)
        session.add(quota)
        session.flush()

    reset_exists = (
        session.query(CreditLedger)
        .filter(
            CreditLedger.student_id == student_id,
            CreditLedger.month_bucket == bucket,
            CreditLedger.event_type == CreditEventType.MONTHLY_RESET,
        )
        .first()
    )
    if reset_exists is None:
        session.add(
            CreditLedger(
                student_id=student_id,
                event_type=CreditEventType.MONTHLY_RESET,
                credits_delta=100,
                month_bucket=bucket,
            )
        )
        session.flush()

    return quota


def _current_balance(session: Session, student_id: UUID) -> int:
    balance_query = select(func.coalesce(func.sum(CreditLedger.credits_delta), 0)).where(
        CreditLedger.student_id == student_id
    )
    return session.execute(balance_query).scalar_one()


def create_recognition(
    session: Session,
    *,
    sender_id: UUID,
    receiver_id: UUID,
    credits_transferred: int,
    message: Optional[str] = None,
) -> Recognition:
    """Create a recognition entry enforcing all business rules."""

    if sender_id == receiver_id:
        raise RecognitionRuleViolation("Students cannot recognize themselves.")

    now = datetime.now(timezone.utc)
    bucket = month_bucket(now)

    sender = _ensure_student(session, sender_id)
    receiver = _ensure_student(session, receiver_id)

    sender_quota = _ensure_monthly_context(session, sender.student_id, bucket)
    _ensure_monthly_context(session, receiver.student_id, bucket)

    if sender_quota.credits_sent + credits_transferred > sender_quota.send_limit:
        remaining = max(sender_quota.send_limit - sender_quota.credits_sent, 0)
        raise RecognitionRuleViolation(
            f"Monthly sending limit exceeded. Remaining credits for month: {remaining}."
        )

    available = _current_balance(session, sender.student_id)
    if available < credits_transferred:
        raise RecognitionRuleViolation(
            "Insufficient balance to send the requested credits.",
        )

    recognition = Recognition(
        sender=sender,
        receiver=receiver,
        credits_transferred=credits_transferred,
        message=message,
        month_bucket=bucket,
    )
    session.add(recognition)
    session.flush()  # Assign recognition_id before creating ledger entries

    sender_quota.credits_sent += credits_transferred
    sender_quota.updated_at = now

    session.add_all(
        [
            CreditLedger(
                student_id=sender.student_id,
                related_recognition=recognition.recognition_id,
                event_type=CreditEventType.RECOGNITION_SENT,
                credits_delta=-credits_transferred,
                month_bucket=bucket,
            ),
            CreditLedger(
                student_id=receiver.student_id,
                related_recognition=recognition.recognition_id,
                event_type=CreditEventType.RECOGNITION_RECEIVED,
                credits_delta=credits_transferred,
                month_bucket=bucket,
            ),
        ]
    )

    session.refresh(recognition)
    return recognition


def list_recognitions(
    session: Session,
    *,
    sender_id: Optional[UUID] = None,
    receiver_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Recognition]:
    """Retrieve recognitions with optional filters."""

    stmt = (
        select(Recognition)
        .options(
            joinedload(Recognition.sender),
            joinedload(Recognition.receiver),
        )
        .order_by(Recognition.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if sender_id:
        stmt = stmt.where(Recognition.sender_id == sender_id)
    if receiver_id:
        stmt = stmt.where(Recognition.receiver_id == receiver_id)

    results = session.execute(stmt).scalars().all()
    return results
