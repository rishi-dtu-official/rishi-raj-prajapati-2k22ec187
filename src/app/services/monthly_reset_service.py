"""Scheduled credit reset logic."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import CreditEventType, CreditLedger, MonthlyQuota, Student
from ..utils.datetime import month_bucket, previous_month_bucket


def run_monthly_reset(session: Session, *, current_time: datetime | None = None) -> dict[str, int]:
    """Apply monthly credit reset with carry-forward cap.

    Returns summary statistics useful for logging/testing.
    """

    now_utc = current_time.astimezone(timezone.utc) if current_time else datetime.now(timezone.utc)
    now_naive = now_utc.replace(tzinfo=None)
    current_bucket = month_bucket(now_utc)
    prior_bucket = previous_month_bucket(current_bucket)

    summary = {
        "students_processed": 0,
        "carry_forward_total": 0,
        "expired_total": 0,
    }

    student_ids = session.execute(select(Student.student_id)).scalars().all()

    for student_id in student_ids:
        # Avoid double-processing if this month's quota already reset
        current_quota_stmt = (
            select(MonthlyQuota)
            .where(MonthlyQuota.student_id == student_id, MonthlyQuota.month_bucket == current_bucket)
            .with_for_update(of=MonthlyQuota, skip_locked=True)
        )
        current_quota = session.execute(current_quota_stmt).scalar_one_or_none()

        if current_quota and current_quota.reset_at and current_quota.reset_at.date() >= current_bucket:
            continue

        # Calculate unused credits from the prior month (monthly alloc + carry - sends)
        unused_stmt = select(func.coalesce(func.sum(CreditLedger.credits_delta), 0)).where(
            CreditLedger.student_id == student_id,
            CreditLedger.month_bucket == prior_bucket,
            CreditLedger.event_type.in_(
                [
                    CreditEventType.MONTHLY_RESET,
                    CreditEventType.CARRY_FORWARD,
                    CreditEventType.RECOGNITION_SENT,
                ]
            ),
        )
        unused = session.execute(unused_stmt).scalar_one()
        if unused < 0:
            unused = 0

        carry_forward = min(unused, 50)
        expired_amount = unused - carry_forward

        # Mark previous month's quota as processed
        previous_quota_stmt = (
            select(MonthlyQuota)
            .where(MonthlyQuota.student_id == student_id, MonthlyQuota.month_bucket == prior_bucket)
            .with_for_update(of=MonthlyQuota, skip_locked=True)
        )
        previous_quota = session.execute(previous_quota_stmt).scalar_one_or_none()
        if previous_quota:
            previous_quota.carry_forward_applied = True
            previous_quota.updated_at = now_naive

        if current_quota is None:
            current_quota = MonthlyQuota(student_id=student_id, month_bucket=current_bucket)
            session.add(current_quota)

        current_quota.send_limit = 100
        current_quota.credits_sent = 0
        current_quota.carry_forward_credits = carry_forward
        current_quota.carry_forward_applied = carry_forward > 0
        current_quota.reset_at = now_naive
        current_quota.updated_at = now_naive

        # Ensure a baseline reset entry exists for the new month
        reset_exists_stmt = (
            select(CreditLedger.ledger_entry_id)
            .where(
                CreditLedger.student_id == student_id,
                CreditLedger.month_bucket == current_bucket,
                CreditLedger.event_type == CreditEventType.MONTHLY_RESET,
            )
            .limit(1)
        )
        if session.execute(reset_exists_stmt).scalar_one_or_none() is None:
            session.add(
                CreditLedger(
                    student_id=student_id,
                    event_type=CreditEventType.MONTHLY_RESET,
                    credits_delta=100,
                    month_bucket=current_bucket,
                )
            )

        if unused > 0:
            session.add(
                CreditLedger(
                    student_id=student_id,
                    event_type=CreditEventType.CARRY_FORWARD_EXPIRED,
                    credits_delta=-unused,
                    month_bucket=current_bucket,
                )
            )
        if carry_forward > 0:
            session.add(
                CreditLedger(
                    student_id=student_id,
                    event_type=CreditEventType.CARRY_FORWARD,
                    credits_delta=carry_forward,
                    month_bucket=current_bucket,
                )
            )

        summary["students_processed"] += 1
        summary["carry_forward_total"] += carry_forward
        summary["expired_total"] += expired_amount

    return summary
