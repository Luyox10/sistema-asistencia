from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import check_connection
from .routes import router as api_router

app = FastAPI(
    title="Sistema de Predicción de Asistencia Estudiantil",
    description="API con modelo LSTM para predecir asistencia estudiantil",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {"mensaje": "API de predicción de asistencia", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    """Verifica la conexión con TiDB."""
    try:
        check_connection()
        return {"status": "ok", "database": "conectada"}
    except Exception as exc:
        return {"status": "error", "database": str(exc)}
