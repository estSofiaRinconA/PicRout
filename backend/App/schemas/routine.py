"""
Schemas Pydantic para Rutinas y ocurrencias diarias – Paso 2.
"""

from datetime import date, time, datetime
from pydantic import BaseModel, Field, field_validator


class RoutineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(None, max_length=1000)
    # Lista de días: 0=Lunes … 6=Domingo
    days_of_week: list[int] = Field(..., min_length=1, description="Ej: [0, 2, 4] = Lun, Mié, Vie")
    scheduled_time: time = Field(..., description="Hora HH:MM, ej. 09:00")
    duration_minutes: int | None = Field(None, ge=1, le=24 * 60)
    base_points: int = Field(10, ge=1, le=100)

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        cleaned = sorted(set(v))
        for d in cleaned:
            if d < 0 or d > 6:
                raise ValueError("Los días deben estar entre 0 (Lunes) y 6 (Domingo)")
        if not cleaned:
            raise ValueError("Debes indicar al menos un día")
        return cleaned


class RoutineUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=1000)
    days_of_week: list[int] | None = None
    scheduled_time: time | None = None
    duration_minutes: int | None = Field(None, ge=1, le=24 * 60)
    base_points: int | None = Field(None, ge=1, le=100)
    is_active: bool | None = None

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        cleaned = sorted(set(v))
        for d in cleaned:
            if d < 0 or d > 6:
                raise ValueError("Los días deben estar entre 0 (Lunes) y 6 (Domingo)")
        if not cleaned:
            raise ValueError("Debes indicar al menos un día")
        return cleaned


class RoutinePublic(BaseModel):
    id: int
    name: str
    description: str | None = None
    days_of_week: list[int]
    scheduled_time: time
    duration_minutes: int | None = None
    base_points: int
    verification_method: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OccurrencePublic(BaseModel):
    id: int
    routine_id: int
    scheduled_date: date
    status: str
    points_awarded: int
    completed_at: datetime | None = None
    notes: str | None = None
    # Datos de la plantilla para mostrar en la app
    routine_name: str | None = None
    routine_time: time | None = None
    base_points: int | None = None

    model_config = {"from_attributes": True}


class MarkStatusRequest(BaseModel):
    """Cambiar estado de una ocurrencia (antes de integrar la IA de verificación)."""

    status: str = Field(
        ...,
        description="pendiente | falta_verificacion | completada | incompleta | perdida",
    )
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {
            "pendiente",
            "falta_verificacion",
            "completada",
            "incompleta",
            "perdida",
        }
        if v not in allowed:
            raise ValueError(f"Estado inválido. Usa uno de: {', '.join(sorted(allowed))}")
        return v


class TodaySummary(BaseModel):
    date: date
    total: int
    completed: int
    pending: int
    awaiting_verification: int
    missed: int
    all_completed: bool
    current_streak: int
    occurrences: list[OccurrencePublic]


class StreakInfo(BaseModel):
    current_streak: int
    longest_streak: int
    points: int
    message: str
