"""
Lógica de rachas y puntos diarios – Paso 2.

Regla del proyecto:
- Para mantener/incrementar la racha hay que completar TODAS las rutinas del día.
- Cuanto mayor sea la racha, más puntos bonus por día.
"""

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from entities.user import User
from entities.routine import (
    Routine,
    RoutineOccurrence,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_AWAITING,
    STATUS_MISSED,
    STATUS_INCOMPLETE,
)


def ensure_today_occurrences(db: Session, user: User, today: date | None = None) -> list[RoutineOccurrence]:
    """
    Crea (si no existen) las ocurrencias del día para todas las rutinas activas
    que aplican a hoy. Devuelve la lista de ocurrencias de hoy.
    """
    if today is None:
        today = date.today()

    routines = (
        db.query(Routine)
        .filter(Routine.user_id == user.id, Routine.is_active == True)  # noqa: E712
        .all()
    )

    existing = {
        o.routine_id: o
        for o in db.query(RoutineOccurrence)
        .filter(
            RoutineOccurrence.user_id == user.id,
            RoutineOccurrence.scheduled_date == today,
        )
        .all()
    }

    created = False
    for routine in routines:
        if not routine.applies_on(today):
            continue
        if routine.id in existing:
            continue
        occ = RoutineOccurrence(
            routine_id=routine.id,
            user_id=user.id,
            scheduled_date=today,
            status=STATUS_PENDING,
        )
        db.add(occ)
        created = True

    if created:
        db.commit()

    occurrences = (
        db.query(RoutineOccurrence)
        .filter(
            RoutineOccurrence.user_id == user.id,
            RoutineOccurrence.scheduled_date == today,
        )
        .all()
    )
    return occurrences


def evaluate_day_and_update_streak(
    db: Session,
    user: User,
    day: date | None = None,
) -> dict:
    """
    Evalúa el estado del día:
    - Si hay ocurrencias y TODAS están 'completada' → incrementa racha y suma bonus.
    - Si alguna está 'perdida' y no quedan pendientes → puede romper racha.
    - Si aún hay pendientes del día actual → no toca la racha.

    Idempotente: solo procesa el bonus de racha una vez por día (last_streak_date).
    """
    if day is None:
        day = date.today()

    occurrences = ensure_today_occurrences(db, user, day)
    if not occurrences:
        return {
            "all_completed": True,
            "streak_changed": False,
            "current_streak": user.current_streak,
            "points_awarded_today": 0,
            "message": "No hay rutinas programadas para hoy.",
        }

    statuses = [o.status for o in occurrences]
    all_completed = all(s == STATUS_COMPLETED for s in statuses)
    any_missed = any(s == STATUS_MISSED for s in statuses)
    any_pending = any(s in (STATUS_PENDING, STATUS_AWAITING, STATUS_INCOMPLETE) for s in statuses)

    points_today = sum(o.points_awarded for o in occurrences)
    streak_changed = False
    message = ""

    if all_completed:
        # Idempotencia: solo incrementar racha y bonus si aún no se procesó este día
        if user.last_streak_date == day:
            message = f"Día ya contabilizado. Racha actual: {user.current_streak} días."
        else:
            previous = user.current_streak
            user.current_streak = previous + 1
            if user.current_streak > user.longest_streak:
                user.longest_streak = user.current_streak
            user.last_streak_date = day

            # Bonus por racha: +2 puntos por cada día de racha (tope 50)
            streak_bonus = min(user.current_streak * 2, 50)
            user.points += streak_bonus
            points_today += streak_bonus
            streak_changed = True
            message = (
                f"¡Día completado! Racha: {user.current_streak} días. "
                f"Bonus de racha: +{streak_bonus} puntos."
            )
            db.commit()
            db.refresh(user)

    elif any_missed and not any_pending:
        if user.current_streak > 0:
            user.current_streak = 0
            streak_changed = True
            message = "Se rompió la racha: hubo rutinas perdidas."
            db.commit()
            db.refresh(user)
        else:
            message = "Hay rutinas perdidas. La racha sigue en 0."

    else:
        message = "Aún hay rutinas pendientes o en verificación."

    return {
        "all_completed": all_completed,
        "streak_changed": streak_changed,
        "current_streak": user.current_streak,
        "longest_streak": user.longest_streak,
        "points": user.points,
        "points_awarded_today": points_today,
        "message": message,
    }


def award_completion_points(db: Session, user: User, occurrence: RoutineOccurrence) -> int:
    """
    Al marcar una ocurrencia como completada, otorga los puntos base de la rutina
    (si aún no se habían otorgado).
    """
    if occurrence.status != STATUS_COMPLETED:
        return 0
    if occurrence.points_awarded > 0:
        return occurrence.points_awarded

    routine = occurrence.routine
    if routine is None:
        routine = db.query(Routine).filter(Routine.id == occurrence.routine_id).first()

    points = routine.base_points if routine else 10
    occurrence.points_awarded = points
    occurrence.completed_at = datetime.now(timezone.utc)
    user.points += points
    db.commit()
    db.refresh(user)
    db.refresh(occurrence)
    return points
