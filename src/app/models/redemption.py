"""Redemption domain model."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, Computed, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..core.database import Base


class RedemptionStatus(str, enum.Enum):
    """Possible redemption states."""

    PENDING = "PENDING"
    ISSUED = "ISSUED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Redemption(Base):
    """Represents vouchers created from redeemed credits."""

    __tablename__ = "redemptions"

    redemption_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False)
    credits_redeemed = Column(Integer, nullable=False)
    voucher_value = Column(Integer, Computed("credits_redeemed * 5"), nullable=False)
    status = Column(SAEnum(RedemptionStatus, name="redemption_status"), nullable=False, default=RedemptionStatus.PENDING)
    reference_code = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    fulfilled_at = Column(DateTime)
    issued_by = Column(String)

    student = relationship("Student", back_populates="redemptions")
    ledger_entries = relationship("CreditLedger", back_populates="redemption")
