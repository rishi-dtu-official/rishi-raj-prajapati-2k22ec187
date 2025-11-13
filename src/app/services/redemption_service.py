"""Domain logic for student redemptions."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import CreditEventType, CreditLedger, Redemption, RedemptionStatus, Student
from ..utils.datetime import month_bucket


class RedemptionRuleViolation(Exception):
    """Raised when redemption rules are violated."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _ensure_student(session: Session, student_id: UUID) -> Student:
    stmt = select(Student).where(Student.student_id == student_id)
    student = session.execute(stmt).scalar_one_or_none()
    if student is None:
        raise RedemptionRuleViolation(f"Student {student_id} not found", status_code=404)
    return student


def _redeemable_balance(session: Session, student_id: UUID) -> int:
    received_stmt = select(func.coalesce(func.sum(CreditLedger.credits_delta), 0)).where(
        CreditLedger.student_id == student_id,
        CreditLedger.event_type.in_([
            CreditEventType.RECOGNITION_RECEIVED,
            CreditEventType.CARRY_FORWARD,
        ]),
    )
    received_total = session.execute(received_stmt).scalar_one()

    redeemed_stmt = select(func.coalesce(func.sum(CreditLedger.credits_delta), 0)).where(
        CreditLedger.student_id == student_id,
        CreditLedger.event_type.in_([
            CreditEventType.REDEMPTION,
            CreditEventType.CARRY_FORWARD_EXPIRED,
        ]),
    )
    redeemed_total = session.execute(redeemed_stmt).scalar_one()

    return received_total + redeemed_total


def redeem(
    session: Session,
    *,
    student_id: UUID,
    credits_redeemed: int,
) -> tuple[Redemption, int]:
    """Execute redemption and return record along with remaining balance."""

    student = _ensure_student(session, student_id)

    redeemable = _redeemable_balance(session, student.student_id)
    if redeemable <= 0:
        raise RedemptionRuleViolation("No redeemable credits available.")

    if credits_redeemed > redeemable:
        raise RedemptionRuleViolation(
            f"Requested credits exceed redeemable balance ({redeemable} credits)."
        )

    now = datetime.now(timezone.utc)
    bucket = month_bucket(now)

    redemption = Redemption(
        student=student,
        credits_redeemed=credits_redeemed,
        status=RedemptionStatus.ISSUED,
        fulfilled_at=now,
    )
    session.add(redemption)
    session.flush()

    ledger_entry = CreditLedger(
        student_id=student.student_id,
        related_redemption=redemption.redemption_id,
        event_type=CreditEventType.REDEMPTION,
        credits_delta=-credits_redeemed,
        month_bucket=bucket,
    )
    session.add(ledger_entry)
    session.flush()

    session.refresh(redemption)

    remaining_balance = redeemable - credits_redeemed
    return redemption, remaining_balance