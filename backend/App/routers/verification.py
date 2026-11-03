"""
Router de Verificación por IA – Paso 3

Flujo típico:
1. POST /verification/analyze          → previsualizar método + puntos (opcional)
2. POST /verification/{occurrence_id}/start
3a. Si single_photo / before_after:
      POST /verification/attempts/{attempt_id}/photo  (multipart)
3b. Si quiz:
      el start ya devuelve las preguntas
      POST /verification/attempts/{attempt_id}/quiz   (JSON con respuestas)
4. GET  /verification/attempts/{attempt_id}          → estado / resultado
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
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
    submit_photos,
    submit_quiz_answers,
)
from functions.storage_files import save_upload_image

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
        photo_single_path=attempt.photo_single_path,
        photo_before_path=attempt.photo_before_path,
        photo_after_path=attempt.photo_after_path,
        quiz_questions=quiz_public,
        quiz_score=attempt.quiz_score,
        confidence=attempt.confidence,
        result_message=attempt.result_message,
        reason=attempt.ai_reason,
        points_awarded=attempt.points_awarded,
        created_at=attempt.created_at,
        completed_at=attempt.completed_at,
    )


# ---------- Análisis previo (sin crear nada) ----------

@router.post("/analyze", response_model=AnalysisPreview)
def analyze_name_description(
    payload: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Analiza nombre + descripción y sugiere método de verificación y puntos.
    Útil en la UI al crear/editar una rutina (antes de guardar).
    """
    try:
        result = analyze_routine(payload.name, payload.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return AnalysisPreview(
        verification_method=result.verification_method,
        base_points=result.base_points,
        difficulty=result.difficulty,
        reason=result.reason,
        confidence=result.confidence,
    )


# ---------- Iniciar verificación de una ocurrencia ----------

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
    Inicia la verificación de una ocurrencia del día.
    - Asigna método si la rutina aún no lo tiene.
    - Si es quiz, genera las preguntas y las devuelve.
    - Cambia el estado de la ocurrencia a 'falta_verificacion'.
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


# ---------- Subir fotos ----------

@router.post(
    "/attempts/{attempt_id}/photo",
    response_model=VerificationResultResponse,
)
async def upload_photos(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    photo: UploadFile | None = File(None, description="Foto única (método single_photo)"),
    photo_before: UploadFile | None = File(None, description="Foto ANTES (before_after)"),
    photo_after: UploadFile | None = File(None, description="Foto DESPUÉS (before_after)"),
):
    """
    Sube la(s) foto(s) de evidencia y cierra el intento (passed/failed).
    - single_photo → campo `photo`
    - before_after → campos `photo_before` + `photo_after`
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

    single_rel = before_rel = after_rel = None

    try:
        if attempt.method == "single_photo":
            if not photo:
                raise HTTPException(
                    status_code=400,
                    detail="Debes enviar el campo 'photo' para verificación de foto única.",
                )
            single_rel = await save_upload_image(
                photo,
                user_id=current_user.id,
                occurrence_id=attempt.occurrence_id,
                kind="single",
            )
        elif attempt.method == "before_after":
            if not photo_before or not photo_after:
                raise HTTPException(
                    status_code=400,
                    detail="Debes enviar 'photo_before' y 'photo_after'.",
                )
            before_rel = await save_upload_image(
                photo_before,
                user_id=current_user.id,
                occurrence_id=attempt.occurrence_id,
                kind="before",
            )
            after_rel = await save_upload_image(
                photo_after,
                user_id=current_user.id,
                occurrence_id=attempt.occurrence_id,
                kind="after",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"El método '{attempt.method}' no acepta subida de fotos. Usa el endpoint de quiz.",
            )

        attempt = submit_photos(
            db,
            current_user,
            attempt,
            single_relative=single_rel,
            before_relative=before_rel,
            after_relative=after_rel,
        )
    except HTTPException:
        raise
    except (PermissionError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    occurrence = attempt.occurrence
    occ_status = occurrence.status if occurrence else "desconocido"

    msg = attempt.result_message or (
        "Verificación aprobada." if attempt.status == "passed" else "Verificación no aprobada."
    )
    return VerificationResultResponse(
        attempt=_to_public(attempt),
        occurrence_status=occ_status,
        current_streak=current_user.current_streak,
        points=current_user.points,
        message=msg,
        reason=attempt.ai_reason,
    )


# ---------- Responder quiz ----------

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


# ---------- Consultar intento ----------

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
