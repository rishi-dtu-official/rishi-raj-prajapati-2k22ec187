"""Monthly quota tracking model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..core.database import Base


class MonthlyQuota(Base):
    """Tracks monthly sending allowance and carry-forward state."""

    __tablename__ = "monthly_quota"
    __table_args__ = (
        UniqueConstraint("student_id", "month_bucket", name="monthly_quota_unique"),
        CheckConstraint("credits_sent >= 0", name="monthly_quota_credits_sent_positive"),
        CheckConstraint("send_limit >= 0", name="monthly_quota_send_limit_positive"),
        CheckConstraint("carry_forward_credits >= 0", name="monthly_quota_carry_forward_positive"),
        CheckConstraint("carry_forward_credits <= 50", name="monthly_quota_carry_forward_cap"),
    )

    quota_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    month_bucket = Column(Date, nullable=False)
    credits_sent = Column(Integer, nullable=False, default=0)
    send_limit = Column(Integer, nullable=False, default=100)
    carry_forward_applied = Column(Boolean, nullable=False, default=False)
    carry_forward_credits = Column(Integer, nullable=False, default=0)
    reset_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="quota_records")
