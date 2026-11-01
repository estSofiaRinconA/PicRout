"""
Modelos de verificación de rutinas – Paso 3.

Un VerificationAttempt representa un intento de verificar una ocurrencia
mediante foto única, foto antes/después o quiz.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Boolean,
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


# Estados del intento de verificación
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
    Intento de verificación de una ocurrencia diaria.
    Guarda método, evidencias (rutas de fotos), quiz y resultado.
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

    # single_photo | before_after | quiz
    method: Mapped[str] = mapped_column(String(30), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default=ATTEMPT_PENDING, server_default=ATTEMPT_PENDING
    )

    # Fotos (rutas relativas dentro de STORAGE_PATH)
    photo_before_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_after_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_single_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Quiz: lista de preguntas + respuestas del usuario
    # Estructura: [{"id": 1, "question": "...", "options": [...], "correct_index": 0}, ...]
    quiz_questions: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    # Respuestas del usuario: {"0": 1, "1": 0, ...}  (índice de opción elegida)
    quiz_answers: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    quiz_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0 – 1.0

    # Resultado del análisis (visión / heurística)
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
