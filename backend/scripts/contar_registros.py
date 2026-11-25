"""Verifica la conexión con TiDB, comprueba las cinco tablas y cuenta registros.

Uso (desde backend/):
    .\\venv\\Scripts\\python.exe scripts\\contar_registros.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import check_connection, engine, get_table_columns  # noqa: E402

EXPECTED_TABLES = ["estudiantes", "cursos", "sesiones", "asistencias", "predicciones"]


def main() -> int:
    print(f"Conectando a {settings.TIDB_HOST}:{settings.TIDB_PORT}/{settings.TIDB_DATABASE} ...")
    try:
        check_connection()
    except Exception as exc:
        print(f"ERROR de conexión: {exc}")
        return 1
    print("Conexión OK\n")

    with engine.connect() as conn:
        for table in EXPECTED_TABLES:
            cols = get_table_columns(table)
            if cols is None:
                print(f"{table}: NO EXISTE")
                continue
            count = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            col_desc = ", ".join(
                f"{c['nombre']}:{c['tipo']}" + (" (PK)" if c["pk"] else "") for c in cols
            )
            print(f"{table}: {count} registros")
            print(f"    columnas: {col_desc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
