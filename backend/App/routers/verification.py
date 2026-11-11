"""
Router de Verificación por IA – Paso 3

Único método activo: quiz.

Flujo:
1. POST /verification/analyze              → previsualizar puntos (método siempre quiz)
2. POST /verification/{occurrence_id}/start → inicia intento y devuelve preguntas
3. POST /verification/attempts/{id}/quiz    → envía respuestas y cierra el intento
4. GET  /verification/attempts/{id}         → estado / resultado
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from storage.database import get_db
from entities.user import User
from entities.routine import RoutineOccurrence
from entities.verification import VerificationAttempt
from App.dependencies import get_current_user
from App.schemas.verification import (
    AnalyzeRequest,
    AnalysisPreview,
    VerificationAttemptPublic,
    QuizQuestionPublic,
    QuizSubmitRequest,
    VerificationResultResponse,
)
from ai.llm_analyzer import analyze_routine_smart as analyze_routine
from functions.verification_service import (
    start_verification,
    submit_quiz_answers,
)

router = APIRouter(prefix="/verification", tags=["Verificación IA"])


def _to_public(attempt: VerificationAttempt) -> VerificationAttemptPublic:
    quiz_public = None
    if attempt.quiz_questions:
        quiz_public = [
            QuizQuestionPublic(
                id=q["id"],
                question=q["question"],
                options=q["options"],
            )
            for q in attempt.quiz_questions
        ]

    return VerificationAttemptPublic(
        id=attempt.id,
        occurrence_id=attempt.occurrence_id,
        routine_id=attempt.routine_id,
        method=attempt.method,
        status=attempt.status,
        quiz_questions=quiz_public,
        quiz_score=attempt.quiz_score,
        confidence=attempt.confidence,
        result_message=attempt.result_message,
        reason=attempt.ai_reason,
        points_awarded=attempt.points_awarded,
        created_at=attempt.created_at,
        completed_at=attempt.completed_at,
    )


@router.post("/analyze", response_model=AnalysisPreview)
def analyze_name_description(
    payload: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Analiza nombre + descripción y sugiere puntos / dificultad.
    El método de verificación es siempre quiz.
    """
    try:
        result = analyze_routine(payload.name, payload.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AnalysisPreview(
        verification_method="quiz",
        base_points=result.base_points,
        difficulty=result.difficulty,
        reason=result.reason,
        confidence=result.confidence,
    )


@router.post(
    "/{occurrence_id}/start",
    response_model=VerificationAttemptPublic,
    status_code=status.HTTP_201_CREATED,
)
def start(
    occurrence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Inicia la verificación por quiz de una ocurrencia del día.
    Genera las preguntas y cambia el estado a 'falta_verificacion'.
    """
    occurrence = (
        db.query(RoutineOccurrence)
        .filter(
            RoutineOccurrence.id == occurrence_id,
            RoutineOccurrence.user_id == current_user.id,
        )
        .first()
    )
    if not occurrence:
        raise HTTPException(status_code=404, detail="Ocurrencia no encontrada")

    try:
        attempt = start_verification(db, current_user, occurrence)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _to_public(attempt)


@router.post(
    "/attempts/{attempt_id}/quiz",
    response_model=VerificationResultResponse,
)
def submit_quiz(
    attempt_id: int,
    payload: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Envía las respuestas del quiz y cierra el intento.
    Body ejemplo: { "answers": { "0": 1, "1": 0, "2": 2 } }
    """
    attempt = (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.id == attempt_id,
            VerificationAttempt.user_id == current_user.id,
        )
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Intento de verificación no encontrado")

    try:
        attempt = submit_quiz_answers(db, current_user, attempt, payload.answers)
    except (PermissionError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    occurrence = attempt.occurrence
    occ_status = occurrence.status if occurrence else "desconocido"
    msg = attempt.result_message or ""
    return VerificationResultResponse(
        attempt=_to_public(attempt),
        occurrence_status=occ_status,
        current_streak=current_user.current_streak,
        points=current_user.points,
        message=msg,
        reason=attempt.ai_reason,
    )


@router.get("/attempts/{attempt_id}", response_model=VerificationAttemptPublic)
def get_attempt(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve el estado actual de un intento de verificación."""
    attempt = (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.id == attempt_id,
            VerificationAttempt.user_id == current_user.id,
        )
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Intento de verificación no encontrado")
    return _to_public(attempt)
