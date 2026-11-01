"""
Schemas Pydantic para verificación de rutinas – Paso 3.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator


class AnalysisPreview(BaseModel):
    """Resultado del análisis de nombre + descripción (sin crear rutina)."""

    verification_method: str
    base_points: int
    difficulty: str
    reason: str
    confidence: float


class AnalyzeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(None, max_length=1000)


class QuizQuestionPublic(BaseModel):
    id: int
    question: str
    options: list[str]
    # correct_index NO se expone al cliente


class VerificationAttemptPublic(BaseModel):
    id: int
    occurrence_id: int
    routine_id: int
    method: str
    status: str  # pending | in_progress | passed | failed | expired
    # Fotos (rutas relativas; el cliente puede construir URL si se sirven estáticos)
    photo_single_path: str | None = None
    photo_before_path: str | None = None
    photo_after_path: str | None = None
    # Quiz: solo preguntas + opciones (sin respuesta correcta)
    quiz_questions: list[QuizQuestionPublic] | None = None
    quiz_score: float | None = None
    confidence: float | None = None
    result_message: str | None = None
    points_awarded: int = 0
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class QuizSubmitRequest(BaseModel):
    """
    Respuestas del usuario.
    Clave = id de pregunta (str o int), valor = índice de la opción elegida (0-based).
    Ejemplo: {"0": 1, "1": 0, "2": 2}
    """

    answers: dict[str, int] = Field(..., description="Mapa pregunta_id → índice de opción")

    @field_validator("answers")
    @classmethod
    def non_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("Debes enviar al menos una respuesta")
        return {str(k): int(val) for k, val in v.items()}


class VerificationResultResponse(BaseModel):
    attempt: VerificationAttemptPublic
    occurrence_status: str
    current_streak: int
    points: int
    message: str
