"""Recognition model representing credit transfers."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..core.database import Base


class Recognition(Base):
    """Recognition entry capturing sender, receiver, and credit amount."""

    __tablename__ = "recognitions"
    __table_args__ = (
        CheckConstraint("sender_id <> receiver_id", name="recognitions_sender_receiver_check"),
    )

    recognition_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False)
    credits_transferred = Column(Integer, nullable=False)
    message = Column(String)
    month_bucket = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    endorsement_count = Column(Integer, nullable=False, default=0)
    recognition_count = Column(Integer, nullable=False, default=1)

    sender = relationship("Student", foreign_keys=[sender_id], back_populates="recognitions_sent")
    receiver = relationship("Student", foreign_keys=[receiver_id], back_populates="recognitions_received")
    ledger_entries = relationship("CreditLedger", back_populates="recognition")
    endorsements = relationship("RecognitionEndorsement", back_populates="recognition")
