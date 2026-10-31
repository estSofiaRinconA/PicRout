"""
Router de Rutinas + Rachas – Paso 2
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from storage.database import get_db
from entities.user import User
from entities.routine import (
    Routine,
    RoutineOccurrence,
    STATUS_COMPLETED,
    STATUS_PENDING,
)
from App.schemas.routine import (
    RoutineCreate,
    RoutineUpdate,
    RoutinePublic,
    OccurrencePublic,
    MarkStatusRequest,
    TodaySummary,
    StreakInfo,
)
from App.dependencies import get_current_user
from functions.streak import (
    ensure_today_occurrences,
    evaluate_day_and_update_streak,
    award_completion_points,
)

router = APIRouter(prefix="/routines", tags=["Rutinas"])


# ---------- Helpers ----------

def _days_to_str(days: list[int]) -> str:
    return ",".join(str(d) for d in sorted(set(days)))


def _days_to_list(days_str: str) -> list[int]:
    if not days_str or not days_str.strip():
        return []
    return [int(x.strip()) for x in days_str.split(",") if x.strip().isdigit()]


def _routine_public(r: Routine) -> RoutinePublic:
    return RoutinePublic(
        id=r.id,
        name=r.name,
        description=r.description,
        days_of_week=_days_to_list(r.days_of_week),
        scheduled_time=r.scheduled_time,
        duration_minutes=r.duration_minutes,
        base_points=r.base_points,
        verification_method=r.verification_method,
        is_active=r.is_active,
        created_at=r.created_at,
    )


def _occurrence_public(o: RoutineOccurrence) -> OccurrencePublic:
    routine = o.routine
    return OccurrencePublic(
        id=o.id,
        routine_id=o.routine_id,
        scheduled_date=o.scheduled_date,
        status=o.status,
        points_awarded=o.points_awarded,
        completed_at=o.completed_at,
        notes=o.notes,
        routine_name=routine.name if routine else None,
        routine_time=routine.scheduled_time if routine else None,
        base_points=routine.base_points if routine else None,
    )


# ---------- CRUD de plantillas ----------

@router.post("", response_model=RoutinePublic, status_code=status.HTTP_201_CREATED)
def create_routine(
    payload: RoutineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea una nueva rutina (plantilla) para el usuario autenticado."""
    routine = Routine(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        days_of_week=_days_to_str(payload.days_of_week),
        scheduled_time=payload.scheduled_time,
        duration_minutes=payload.duration_minutes,
        base_points=payload.base_points,
    )
    db.add(routine)
    db.commit()
    db.refresh(routine)
    return _routine_public(routine)


@router.get("", response_model=list[RoutinePublic])
def list_routines(
    active_only: bool = Query(True, description="Solo rutinas activas"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista las rutinas del usuario."""
    q = db.query(Routine).filter(Routine.user_id == current_user.id)
    if active_only:
        q = q.filter(Routine.is_active == True)  # noqa: E712
    routines = q.order_by(Routine.scheduled_time).all()
    return [_routine_public(r) for r in routines]


@router.get("/today", response_model=TodaySummary)
def get_today(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve las ocurrencias de hoy (las crea si aún no existen)
    y un resumen de cumplimiento + racha actual.
    """
    today = date.today()
    occurrences = ensure_today_occurrences(db, current_user, today)

    for o in occurrences:
        _ = o.routine

    completed = sum(1 for o in occurrences if o.status == STATUS_COMPLETED)
    pending = sum(1 for o in occurrences if o.status == STATUS_PENDING)
    awaiting = sum(1 for o in occurrences if o.status == "falta_verificacion")
    missed = sum(1 for o in occurrences if o.status == "perdida")
    total = len(occurrences)
    all_completed = total > 0 and completed == total

    return TodaySummary(
        date=today,
        total=total,
        completed=completed,
        pending=pending,
        awaiting_verification=awaiting,
        missed=missed,
        all_completed=all_completed,
        current_streak=current_user.current_streak,
        occurrences=[_occurrence_public(o) for o in occurrences],
    )


@router.get("/streak", response_model=StreakInfo)
def get_streak(
    current_user: User = Depends(get_current_user),
):
    """Información de racha y puntos del usuario."""
    msg = (
        f"Llevas {current_user.current_streak} día(s) de racha."
        if current_user.current_streak > 0
        else "Aún no tienes racha. Completa todas las rutinas de hoy para empezar."
    )
    return StreakInfo(
        current_streak=current_user.current_streak,
        longest_streak=current_user.longest_streak,
        points=current_user.points,
        message=msg,
    )


@router.get("/{routine_id}", response_model=RoutinePublic)
def get_routine(
    routine_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    routine = (
        db.query(Routine)
        .filter(Routine.id == routine_id, Routine.user_id == current_user.id)
        .first()
    )
    if not routine:
        raise HTTPException(status_code=404, detail="Rutina no encontrada")
    return _routine_public(routine)


@router.put("/{routine_id}", response_model=RoutinePublic)
def update_routine(
    routine_id: int,
    payload: RoutineUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    routine = (
        db.query(Routine)
        .filter(Routine.id == routine_id, Routine.user_id == current_user.id)
        .first()
    )
    if not routine:
        raise HTTPException(status_code=404, detail="Rutina no encontrada")

    data = payload.model_dump(exclude_unset=True)
    if "days_of_week" in data and data["days_of_week"] is not None:
        data["days_of_week"] = _days_to_str(data["days_of_week"])
    if "name" in data and data["name"]:
        data["name"] = data["name"].strip()
    if "description" in data and data["description"]:
        data["description"] = data["description"].strip()

    for field, value in data.items():
        setattr(routine, field, value)
    routine.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(routine)
    return _routine_public(routine)


@router.delete("/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_routine(
    routine_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Desactiva la rutina (soft delete)."""
    routine = (
        db.query(Routine)
        .filter(Routine.id == routine_id, Routine.user_id == current_user.id)
        .first()
    )
    if not routine:
        raise HTTPException(status_code=404, detail="Rutina no encontrada")
    routine.is_active = False
    routine.updated_at = datetime.now(timezone.utc)
    db.commit()
    return None


# ---------- Ocurrencias / estados ----------

@router.patch("/occurrences/{occurrence_id}/status", response_model=OccurrencePublic)
def mark_occurrence_status(
    occurrence_id: int,
    payload: MarkStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cambia el estado de una ocurrencia del día.
    Cuando se marca como 'completada' otorga los puntos base.
    Si todas las del día quedan completadas, actualiza la racha.
    """
    occ = (
        db.query(RoutineOccurrence)
        .filter(
            RoutineOccurrence.id == occurrence_id,
            RoutineOccurrence.user_id == current_user.id,
        )
        .first()
    )
    if not occ:
        raise HTTPException(status_code=404, detail="Ocurrencia no encontrada")

    occ.status = payload.status
    if payload.notes is not None:
        occ.notes = payload.notes
    occ.updated_at = datetime.now(timezone.utc)

    if payload.status == STATUS_COMPLETED:
        _ = occ.routine
        award_completion_points(db, current_user, occ)
        evaluate_day_and_update_streak(db, current_user, occ.scheduled_date)
    else:
        db.commit()
        db.refresh(occ)

    db.refresh(occ)
    _ = occ.routine
    return _occurrence_public(occ)


@router.post("/evaluate-today", response_model=StreakInfo)
def evaluate_today(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fuerza la evaluación del día (útil al final del día o tras marcar varias).
    Actualiza racha y puntos si corresponde.
    """
    result = evaluate_day_and_update_streak(db, current_user, date.today())
    db.refresh(current_user)
    return StreakInfo(
        current_streak=current_user.current_streak,
        longest_streak=current_user.longest_streak,
        points=current_user.points,
        message=result["message"],
    )
