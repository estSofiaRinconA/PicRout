"""
Lógica de negocio de verificación de ocurrencias – Paso 3.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from entities.user import User
from entities.routine import (
    Routine,
    RoutineOccurrence,
    STATUS_PENDING,
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
from ai.llm_vision import validate_photo_smart as validate_photo_evidence
from functions.streak import award_completion_points, evaluate_day_and_update_streak
from functions.storage_files import absolute_path
from App.config import get_settings

settings = get_settings()

# Umbral mínimo de aciertos en quiz para aprobar (60%)
QUIZ_PASS_THRESHOLD = 0.6
# Umbral de confianza de foto para aprobar
PHOTO_PASS_THRESHOLD = 0.5


def ensure_verification_method(routine: Routine) -> str:
    """
    Si la rutina aún no tiene método, lo calcula con el analyzer y lo guarda.
    """
    if routine.verification_method:
        return routine.verification_method

    result = analyze_routine(routine.name, routine.description)
    routine.verification_method = result.verification_method
    # Solo sobreescribe base_points si sigue en el default típico o es bajo
    if routine.base_points is None or routine.base_points <= 10:
        routine.base_points = result.base_points
    return routine.verification_method


def start_verification(
    db: Session,
    user: User,
    occurrence: RoutineOccurrence,
) -> VerificationAttempt:
    """
    Inicia (o reutiliza) un intento de verificación para la ocurrencia.
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

    method = ensure_verification_method(routine)
    db.commit()  # por si se actualizó method/points

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
        occurrence.status = STATUS_AWAITING
        db.commit()
        db.refresh(existing)
        return existing

    attempt = VerificationAttempt(
        occurrence_id=occurrence.id,
        user_id=user.id,
        routine_id=routine.id,
        method=method,
        status=ATTEMPT_PENDING,
    )

    if method == "quiz":
        questions = generate_quiz(routine.name, routine.description, num_questions=3)
        attempt.quiz_questions = questions
        attempt.status = ATTEMPT_IN_PROGRESS

    db.add(attempt)
    occurrence.status = STATUS_AWAITING
    db.commit()
    db.refresh(attempt)
    return attempt


def submit_photos(
    db: Session,
    user: User,
    attempt: VerificationAttempt,
    *,
    single_relative: str | None = None,
    before_relative: str | None = None,
    after_relative: str | None = None,
) -> VerificationAttempt:
    """
    Asocia fotos al intento, valida y cierra el intento (passed/failed).
    """
    if attempt.user_id != user.id:
        raise PermissionError("El intento no pertenece al usuario.")

    if attempt.status in (ATTEMPT_PASSED, ATTEMPT_FAILED):
        raise ValueError("Este intento ya fue cerrado.")

    routine = attempt.routine
    if routine is None:
        routine = db.query(Routine).filter(Routine.id == attempt.routine_id).first()
    routine_name = routine.name if routine else ""
    routine_description = routine.description if routine else None

    if attempt.method == "single_photo":
        if not single_relative:
            raise ValueError("Se requiere una foto para este método.")
        attempt.photo_single_path = single_relative
        result = validate_photo_evidence(
            "single_photo",
            single_path=str(absolute_path(single_relative)),
            routine_name=routine_name,
            routine_description=routine_description,
            max_size_mb=settings.MAX_PHOTO_SIZE_MB,
        )
    elif attempt.method == "before_after":
        if not before_relative or not after_relative:
            raise ValueError("Se requieren foto ANTES y foto DESPUÉS.")
        attempt.photo_before_path = before_relative
        attempt.photo_after_path = after_relative
        result = validate_photo_evidence(
            "before_after",
            before_path=str(absolute_path(before_relative)),
            after_path=str(absolute_path(after_relative)),
            routine_name=routine_name,
            routine_description=routine_description,
            max_size_mb=settings.MAX_PHOTO_SIZE_MB,
        )
    else:
        raise ValueError(f"El método '{attempt.method}' no acepta fotos.")

    attempt.confidence = result.confidence
    attempt.result_message = result.message
    # Razón completa: detalle del validador (+ umbral si aplica)
    base_reason = (result.details or result.message or "").strip()

    occurrence = attempt.occurrence
    if occurrence is None:
        occurrence = (
            db.query(RoutineOccurrence)
            .filter(RoutineOccurrence.id == attempt.occurrence_id)
            .first()
        )

    if result.accepted and result.confidence >= PHOTO_PASS_THRESHOLD:
        attempt.status = ATTEMPT_PASSED
        attempt.completed_at = datetime.now(timezone.utc)
        attempt.ai_reason = base_reason or (
            f"Evidencia fotográfica aceptada para «{routine_name}» "
            f"(confianza {int((result.confidence or 0) * 100)}%)."
        )
        if occurrence:
            occurrence.status = STATUS_COMPLETED
            award_completion_points(db, user, occurrence)
            attempt.points_awarded = occurrence.points_awarded
            evaluate_day_and_update_streak(db, user, occurrence.scheduled_date)
    else:
        attempt.status = ATTEMPT_FAILED
        attempt.completed_at = datetime.now(timezone.utc)
        if not result.accepted:
            attempt.ai_reason = base_reason or "La evidencia no fue aceptada."
            if not attempt.result_message:
                attempt.result_message = "Foto rechazada."
        else:
            # Archivo OK pero confianza por debajo del umbral
            attempt.result_message = (
                f"Foto rechazada: confianza insuficiente "
                f"({int((result.confidence or 0) * 100)}% < {int(PHOTO_PASS_THRESHOLD * 100)}%)."
            )
            attempt.ai_reason = (
                f"{base_reason} "
                f"Además, la confianza ({int((result.confidence or 0) * 100)}%) "
                f"está por debajo del mínimo requerido ({int(PHOTO_PASS_THRESHOLD * 100)}%)."
            ).strip()
        if occurrence and occurrence.status != STATUS_COMPLETED:
            occurrence.status = STATUS_INCOMPLETE

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
