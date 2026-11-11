"""
Lógica de negocio de verificación de ocurrencias – Paso 3.

Único método activo: quiz (verificación por fotos eliminada del proyecto).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from entities.user import User
from entities.routine import (
    Routine,
    RoutineOccurrence,
    STATUS_AWAITING,
    STATUS_COMPLETED,
    STATUS_INCOMPLETE,
)
from entities.verification import (
    VerificationAttempt,
    ATTEMPT_PENDING,
    ATTEMPT_IN_PROGRESS,
    ATTEMPT_PASSED,
    ATTEMPT_FAILED,
)
from ai.llm_analyzer import analyze_routine_smart as analyze_routine
from ai.llm_quiz import generate_quiz_smart as generate_quiz, grade_quiz
from functions.streak import award_completion_points, evaluate_day_and_update_streak

# Umbral mínimo de aciertos en quiz para aprobar (60%)
QUIZ_PASS_THRESHOLD = 0.6


def ensure_verification_method(routine: Routine) -> str:
    """
    Siempre usa quiz. Calcula y guarda puntos base si aún no están definidos.
    """
    if not routine.verification_method or routine.verification_method != "quiz":
        routine.verification_method = "quiz"

    if routine.base_points is None or routine.base_points <= 0:
        result = analyze_routine(routine.name, routine.description)
        routine.base_points = result.base_points

    return "quiz"


def start_verification(
    db: Session,
    user: User,
    occurrence: RoutineOccurrence,
) -> VerificationAttempt:
    """
    Inicia (o reutiliza) un intento de verificación por quiz para la ocurrencia.
    Pasa el estado de la ocurrencia a 'falta_verificacion'.
    """
    if occurrence.user_id != user.id:
        raise PermissionError("La ocurrencia no pertenece al usuario.")

    if occurrence.status == STATUS_COMPLETED:
        raise ValueError("Esta ocurrencia ya está completada.")

    routine = occurrence.routine
    if routine is None:
        routine = db.query(Routine).filter(Routine.id == occurrence.routine_id).first()
    if not routine:
        raise ValueError("Rutina asociada no encontrada.")

    ensure_verification_method(routine)
    db.commit()

    # Reutilizar intento abierto si existe
    existing = (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.occurrence_id == occurrence.id,
            VerificationAttempt.status.in_([ATTEMPT_PENDING, ATTEMPT_IN_PROGRESS]),
        )
        .order_by(VerificationAttempt.id.desc())
        .first()
    )
    if existing:
        # Si un intento antiguo quedó sin preguntas (p.ej. método foto), regenerar quiz
        if not existing.quiz_questions:
            existing.method = "quiz"
            existing.quiz_questions = generate_quiz(
                routine.name, routine.description, num_questions=3
            )
            existing.status = ATTEMPT_IN_PROGRESS
            db.commit()
            db.refresh(existing)
        occurrence.status = STATUS_AWAITING
        db.commit()
        db.refresh(existing)
        return existing

    questions = generate_quiz(routine.name, routine.description, num_questions=3)
    attempt = VerificationAttempt(
        occurrence_id=occurrence.id,
        user_id=user.id,
        routine_id=routine.id,
        method="quiz",
        status=ATTEMPT_IN_PROGRESS,
        quiz_questions=questions,
    )

    db.add(attempt)
    occurrence.status = STATUS_AWAITING
    db.commit()
    db.refresh(attempt)
    return attempt


def submit_quiz_answers(
    db: Session,
    user: User,
    attempt: VerificationAttempt,
    answers: dict,
) -> VerificationAttempt:
    """
    Califica el quiz y cierra el intento.
    """
    if attempt.user_id != user.id:
        raise PermissionError("El intento no pertenece al usuario.")

    if attempt.method != "quiz":
        raise ValueError("Este intento no es de tipo quiz.")

    if attempt.status in (ATTEMPT_PASSED, ATTEMPT_FAILED):
        raise ValueError("Este intento ya fue cerrado.")

    questions = attempt.quiz_questions or []
    if not questions:
        raise ValueError("No hay preguntas generadas para este intento.")

    score, correct, total = grade_quiz(questions, answers)
    attempt.quiz_answers = {str(k): v for k, v in answers.items()}
    attempt.quiz_score = score
    attempt.confidence = score
    pct = int(score * 100)
    threshold_pct = int(QUIZ_PASS_THRESHOLD * 100)
    attempt.result_message = (
        f"Respondiste {correct}/{total} correctamente ({pct}%)."
    )

    occurrence = attempt.occurrence
    if occurrence is None:
        occurrence = (
            db.query(RoutineOccurrence)
            .filter(RoutineOccurrence.id == attempt.occurrence_id)
            .first()
        )

    if score >= QUIZ_PASS_THRESHOLD:
        attempt.status = ATTEMPT_PASSED
        attempt.completed_at = datetime.now(timezone.utc)
        attempt.ai_reason = (
            f"Quiz aprobado porque acertaste {correct} de {total} preguntas ({pct}%), "
            f"igual o por encima del mínimo requerido ({threshold_pct}%)."
        )
        if occurrence:
            occurrence.status = STATUS_COMPLETED
            award_completion_points(db, user, occurrence)
            attempt.points_awarded = occurrence.points_awarded
            evaluate_day_and_update_streak(db, user, occurrence.scheduled_date)
    else:
        attempt.status = ATTEMPT_FAILED
        attempt.completed_at = datetime.now(timezone.utc)
        attempt.ai_reason = (
            f"Quiz no aprobado porque acertaste {correct} de {total} preguntas ({pct}%), "
            f"por debajo del mínimo requerido ({threshold_pct}%). "
            "Intenta de nuevo cuando la ocurrencia lo permita."
        )
        if occurrence and occurrence.status != STATUS_COMPLETED:
            occurrence.status = STATUS_INCOMPLETE

    db.commit()
    db.refresh(attempt)
    return attempt
