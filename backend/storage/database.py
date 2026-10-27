"""
Configuración de la base de datos (SQLAlchemy).
SQLite en desarrollo → PostgreSQL en producción (cambiar DATABASE_URL).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from App.config import get_settings

settings = get_settings()

# check_same_thread=False es necesario para SQLite con FastAPI
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
)

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

    Base.metadata.create_all(bind=engine)
