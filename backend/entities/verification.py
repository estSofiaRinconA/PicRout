"""
Modelos de verificación de rutinas – Paso 3.

Un VerificationAttempt representa un intento de verificar una ocurrencia
mediante quiz (método único activo).
"""

from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Text,
    Float,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.database import Base


def utcnow():
    return datetime.now(timezone.utc)


ATTEMPT_PENDING = "pending"
ATTEMPT_IN_PROGRESS = "in_progress"
ATTEMPT_PASSED = "passed"
ATTEMPT_FAILED = "failed"
ATTEMPT_EXPIRED = "expired"

VALID_ATTEMPT_STATUSES = {
    ATTEMPT_PENDING,
    ATTEMPT_IN_PROGRESS,
    ATTEMPT_PASSED,
    ATTEMPT_FAILED,
    ATTEMPT_EXPIRED,
}


class VerificationAttempt(Base):
    """
    Intento de verificación de una ocurrencia diaria (solo quiz).
    """

    __tablename__ = "verification_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    occurrence_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("routine_occurrences.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    routine_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("routines.id"), nullable=False, index=True
    )

    # Único método activo: quiz
    method: Mapped[str] = mapped_column(String(30), nullable=False, default="quiz")

    status: Mapped[str] = mapped_column(
        String(20), default=ATTEMPT_PENDING, server_default=ATTEMPT_PENDING
    )

    # Quiz: lista de preguntas + respuestas del usuario
    quiz_questions: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    quiz_answers: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    quiz_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    points_awarded: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    occurrence = relationship("RoutineOccurrence", backref="verification_attempts")
    user = relationship("User", backref="verification_attempts")
    routine = relationship("Routine", backref="verification_attempts")

    def __repr__(self) -> str:
        return (
            f"<VerificationAttempt id={self.id} method={self.method} "
            f"status={self.status} occurrence={self.occurrence_id}>"
        )
