"""Student domain model."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..core.database import Base


class Student(Base):
    """Represents a campus user participating in Boostly."""

    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("campus_uid", name="students_campus_uid_unique"),
        UniqueConstraint("email", name="students_email_unique"),
    )

    student_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campus_uid = Column(String, nullable=False)
    email = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    recognitions_sent = relationship(
        "Recognition",
        foreign_keys="Recognition.sender_id",
        back_populates="sender",
    )
    recognitions_received = relationship(
        "Recognition",
        foreign_keys="Recognition.receiver_id",
        back_populates="receiver",
    )
    quota_records = relationship("MonthlyQuota", back_populates="student")
    ledger_entries = relationship("CreditLedger", back_populates="student")
    endorsements = relationship("RecognitionEndorsement", back_populates="endorser")
    redemptions = relationship("Redemption", back_populates="student")
