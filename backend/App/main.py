from fastapi import FastAPI

app = FastAPI(
    title="PicRout API",
    description="API de PicRout - Seguimiento de hábitos con IA",
    version="0.1.0"
)

@app.get("/")
def root():
    return {
        "mensaje": "PicRout API funcionando correctamente",
        "version": "0.1.0",
        "estado": "ok"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}