"""
Modelos de Rutinas e instancias diarias (ocurrencias) – Paso 2.
"""

from datetime import datetime, date, time, timezone
from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    Date,
    Time,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# Estados posibles de una ocurrencia del día
STATUS_PENDING = "pendiente"
STATUS_AWAITING = "falta_verificacion"
STATUS_COMPLETED = "completada"
STATUS_INCOMPLETE = "incompleta"
STATUS_MISSED = "perdida"

VALID_STATUSES = {
    STATUS_PENDING,
    STATUS_AWAITING,
    STATUS_COMPLETED,
    STATUS_INCOMPLETE,
    STATUS_MISSED,
}

# Días de la semana: 0 = Lunes … 6 = Domingo
WEEKDAY_NAMES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


class Routine(Base):
    """
    Plantilla de rutina creada por el usuario.
    Define qué días y a qué hora debe realizarse.
    """

    __tablename__ = "routines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Días en que se realiza: "0,2,4" = Lunes, Miércoles, Viernes
    days_of_week: Mapped[str] = mapped_column(String(20), nullable=False)

    # Hora programada (ej. 09:00)
    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Duración opcional en minutos (ej. 60)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Puntos base (la IA podrá ajustarlos en el Paso 3)
    base_points: Mapped[int] = mapped_column(Integer, default=10, server_default="10")

    # Método de verificación (lo definirá la IA en el siguiente paso)
    # single_photo | before_after | quiz | none
    verification_method: Mapped[str | None] = mapped_column(String(30), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user = relationship("User", backref="routines")
    occurrences = relationship(
        "RoutineOccurrence",
        back_populates="routine",
        cascade="all, delete-orphan",
    )

    def weekday_list(self) -> list[int]:
        """Devuelve lista de enteros 0-6 a partir de days_of_week."""
        if not self.days_of_week or not self.days_of_week.strip():
            return []
        return [int(x.strip()) for x in self.days_of_week.split(",") if x.strip().isdigit()]

    def applies_on(self, d: date) -> bool:
        """¿Esta rutina aplica el día de la semana de la fecha d?"""
        # Python: Monday=0 … Sunday=6 → coincide con nuestro esquema
        return d.weekday() in self.weekday_list()

    def __repr__(self) -> str:
        return f"<Routine id={self.id} name={self.name!r}>"


class RoutineOccurrence(Base):
    """
    Instancia de una rutina en un día concreto.
    Guarda el estado de cumplimiento de ese día.
    """

    __tablename__ = "routine_occurrences"
    __table_args__ = (
        UniqueConstraint("routine_id", "scheduled_date", name="uq_routine_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    routine_id: Mapped[int] = mapped_column(Integer, ForeignKey("routines.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default=STATUS_PENDING, server_default=STATUS_PENDING)

    points_awarded: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    routine = relationship("Routine", back_populates="occurrences")
    user = relationship("User", backref="routine_occurrences")

    def __repr__(self) -> str:
        return f"<Occurrence routine={self.routine_id} date={self.scheduled_date} status={self.status}>"
