from fastapi import APIRouter

from ..config import settings
from ..database import check_connection, get_table_columns

router = APIRouter(tags=["health"])

EXPECTED_TABLES = ["estudiantes", "cursos", "sesiones", "asistencias", "predicciones"]


@router.get("/health/database")
def health_database():
    """Comprueba la conexión con TiDB y la existencia de las cinco tablas."""
    try:
        check_connection()
    except Exception as exc:
        return {"status": "error", "detalle": str(exc)}

    tables = {t: get_table_columns(t) for t in EXPECTED_TABLES}
    missing = [t for t, cols in tables.items() if cols is None]

    return {
        "status": "ok" if not missing else "incompleto",
        "host": settings.TIDB_HOST,
        "database": settings.TIDB_DATABASE,
        "tablas_faltantes": missing,
        "tablas": tables,
    }
