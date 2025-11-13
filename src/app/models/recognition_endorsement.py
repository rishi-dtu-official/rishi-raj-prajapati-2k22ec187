"""Recognition endorsement model."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..core.database import Base


class RecognitionEndorsement(Base):
    """Represents a student's endorsement on a recognition."""

    __tablename__ = "recognition_endorsements"
    __table_args__ = (
        UniqueConstraint("recognition_id", "endorser_id", name="recognition_endorsements_unique"),
    )

    endorsement_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recognition_id = Column(UUID(as_uuid=True), ForeignKey("recognitions.recognition_id", ondelete="RESTRICT"), nullable=False)
    endorser_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    recognition = relationship("Recognition", back_populates="endorsements")
    endorser = relationship("Student", back_populates="endorsements")
