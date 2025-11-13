"""Credit ledger model capturing balance movements."""

import enum
from datetime import datetime
from sqlalchemy import CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..core.database import Base


class CreditEventType(str, enum.Enum):
    """Ledger event classification."""

    RECOGNITION_SENT = "RECOGNITION_SENT"
    RECOGNITION_RECEIVED = "RECOGNITION_RECEIVED"
    REDEMPTION = "REDEMPTION"
    MONTHLY_RESET = "MONTHLY_RESET"
    CARRY_FORWARD = "CARRY_FORWARD"
    CARRY_FORWARD_EXPIRED = "CARRY_FORWARD_EXPIRED"


class CreditLedger(Base):
    """Immutable ledger of credit deltas for each student."""

    __tablename__ = "credit_ledger"
    __table_args__ = (
        CheckConstraint(
            "((event_type IN ('RECOGNITION_SENT', 'REDEMPTION', 'CARRY_FORWARD_EXPIRED') AND credits_delta < 0) "
            "OR (event_type IN ('RECOGNITION_RECEIVED', 'MONTHLY_RESET', 'CARRY_FORWARD') AND credits_delta > 0))",
            name="credit_ledger_delta_sign",
        ),
    )

    ledger_entry_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False)
    related_recognition = Column(UUID(as_uuid=True), ForeignKey("recognitions.recognition_id", ondelete="SET NULL"))
    related_redemption = Column(UUID(as_uuid=True), ForeignKey("redemptions.redemption_id", ondelete="SET NULL"))
    quota_snapshot_id = Column(UUID(as_uuid=True))
    event_type = Column(Enum(CreditEventType, name="credit_event_type"), nullable=False)
    credits_delta = Column(Integer, nullable=False)
    month_bucket = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="ledger_entries")
    recognition = relationship("Recognition", back_populates="ledger_entries")
    redemption = relationship("Redemption", back_populates="ledger_entries")
