from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from App.config import get_settings
from storage.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (si se necesita)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend de PicRout - Seguimiento de hábitos con verificación por IA",
    lifespan=lifespan,
)

# CORS (necesario para el cliente Android y futuras versiones HTML)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción se restringirá
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "message": "PicRout API funcionando correctamente",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Routers
from App.routers import auth, routines  # noqa: E402

app.include_router(auth.router)
app.include_router(routines.router)

# Aquí se incluirán los routers de las siguientes fases:
# from App.routers import verification, points, store, social, notifications, admin
# ... etc
