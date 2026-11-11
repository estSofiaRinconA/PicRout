"""
Configuración de la base de datos (SQLAlchemy).

- Desarrollo local: SQLite (por defecto) → sqlite:///./app_routines.db
- Producción / equipo: PostgreSQL en Supabase → DATABASE_URL en .env

Ejemplo Supabase (URI de conexión, modo Session / Transaction pooler):
  postgresql+psycopg2://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
o conexión directa:
  postgresql+psycopg2://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from App.config import get_settings

settings = get_settings()

# check_same_thread=False es necesario para SQLite con FastAPI
connect_args = {}
engine_kwargs: dict = {"echo": settings.DEBUG}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine_kwargs["connect_args"] = connect_args
else:
    # Postgres / Supabase: pool razonable para API pequeña
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependencia de FastAPI: entrega una sesión de BD y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crea todas las tablas. Llamar al arrancar la aplicación."""
    # Importar modelos para que se registren en Base.metadata
    from entities.user import User, PasswordOTP  # noqa: F401
    from entities.routine import Routine, RoutineOccurrence  # noqa: F401
    from entities.verification import VerificationAttempt  # noqa: F401

    Base.metadata.create_all(bind=engine)
