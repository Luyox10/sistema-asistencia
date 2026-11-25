from fastapi import APIRouter

from .asistencias import router as asistencias_router
from .cursos import router as cursos_router
from .dashboard import router as dashboard_router
from .datasets import router as datasets_router
from .estudiantes import router as estudiantes_router
from .health import router as health_router
from .predicciones import router as predicciones_router

# Router raíz de la API.
router = APIRouter()
router.include_router(health_router)
router.include_router(dashboard_router)
router.include_router(estudiantes_router)
router.include_router(cursos_router)
router.include_router(asistencias_router)
router.include_router(predicciones_router)
router.include_router(datasets_router)
