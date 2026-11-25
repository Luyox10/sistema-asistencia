"""Importación segura del CSV de asistencias a TiDB.

Flujo:
1. Lee y valida el CSV (columnas, tipos, duplicados, valores inválidos, fechas).
2. Comprueba que las cinco tablas existen.
3. Verifica claves foráneas: los student_id / course_id / session_id del CSV
   deben existir en sus tablas padre. Si las tablas padre están vacías se
   insertan filas sintéticas claramente identificadas (prefijo SINTETICO-).
4. Crea la tabla temporal staging_asistencias, carga el CSV en ella y copia a
   asistencias solo los registros (student_id, session_id) que no existen.
5. La tabla staging se elimina al terminar.

Uso (desde backend/):
    .\\venv\\Scripts\\python.exe scripts\\importar_csv.py
    .\\venv\\Scripts\\python.exe scripts\\importar_csv.py --solo-validar
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from app.database import engine  # noqa: E402

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "dataset_asistencia_prueba.csv"
EXPECTED_COLS = ["student_id", "course_id", "session_id", "session_date", "attendance_status"]
EXPECTED_TABLES = ["estudiantes", "cursos", "sesiones", "asistencias", "predicciones"]
STAGING_TABLE = "staging_asistencias"
DEDUP_COLS = ["student_id", "session_id"]


def validar_csv(path: Path) -> pd.DataFrame:
    """Valida el CSV y devuelve el DataFrame limpio. Aborta si hay errores."""
    if not path.exists():
        sys.exit(f"ERROR: no existe el archivo {path}")

    df = pd.read_csv(path, dtype=str).fillna("")
    print(f"Filas leídas: {len(df)}")

    # 1. Columnas exactas
    cols = list(df.columns)
    if cols != EXPECTED_COLS:
        sys.exit(f"ERROR: columnas {cols} != esperadas {EXPECTED_COLS}")
    print("Columnas: OK")

    # 2. Identificadores no vacíos
    for col in ["student_id", "course_id", "session_id"]:
        vacios = int((df[col].str.strip() == "").sum())
        if vacios:
            sys.exit(f"ERROR: {vacios} valores vacíos en {col}")
    print("Identificadores: OK (sin vacíos)")

    # 3. attendance_status ∈ {0, 1}
    invalidos = df[~df["attendance_status"].isin(["0", "1"])]
    if len(invalidos):
        sys.exit(f"ERROR: {len(invalidos)} valores inválidos en attendance_status:\n{invalidos}")
    df["attendance_status"] = df["attendance_status"].astype(int)
    print("attendance_status: OK (solo 0/1)")

    # 4. Fechas válidas
    fechas = pd.to_datetime(df["session_date"], format="%Y-%m-%d", errors="coerce")
    if fechas.isna().any():
        malas = df.loc[fechas.isna(), "session_date"].unique()
        sys.exit(f"ERROR: fechas inválidas: {list(malas)}")
    df["session_date"] = fechas.dt.date
    print(f"session_date: OK ({df['session_date'].min()} a {df['session_date'].max()})")

    # 5. Duplicados por (student_id, session_id)
    dup = df.duplicated(subset=DEDUP_COLS, keep=False)
    if dup.any():
        sys.exit(f"ERROR: {int(dup.sum())} filas duplicadas por {DEDUP_COLS}")
    print("Duplicados (student_id, session_id): ninguno")

    print(
        f"Resumen: {df.student_id.nunique()} estudiantes, "
        f"{df.course_id.nunique()} cursos, {df.session_id.nunique()} sesiones\n"
    )
    return df


def columnas_de(conn, tabla: str) -> list[str]:
    return [c["name"] for c in inspect(conn).get_columns(tabla)]


def crear_staging(conn) -> None:
    conn.execute(
        text(
            f"""
            CREATE TEMPORARY TABLE {STAGING_TABLE} (
                student_id VARCHAR(64) NOT NULL,
                course_id VARCHAR(64) NOT NULL,
                session_id VARCHAR(64) NOT NULL,
                session_date DATE NOT NULL,
                attendance_status TINYINT NOT NULL,
                PRIMARY KEY (student_id, session_id)
            )
            """
        )
    )


def asegurar_padres(conn, df: pd.DataFrame) -> None:
    """Inserta filas sintéticas en las tablas padre solo si están vacías.

    Si las tablas padre tienen datos, se exige que todos los ids del CSV
    existan (integridad referencial).
    """
    mapa = {
        "estudiantes": ("student_id", sorted(df.student_id.unique())),
        "cursos": ("course_id", sorted(df.course_id.unique())),
        "sesiones": ("session_id", sorted(df.session_id.unique())),
    }
    for tabla, (col_csv, ids) in mapa.items():
        cols = columnas_de(conn, tabla)
        # Columna que guarda el identificador: coincide con el nombre del CSV
        # o es la PK de la tabla.
        col_id = col_csv if col_csv in cols else cols[0]
        n = conn.execute(text(f"SELECT COUNT(*) FROM `{tabla}`")).scalar()
        if n == 0:
            print(f"{tabla}: vacía -> insertando {len(ids)} filas SINTÉTICAS")
            nombre_col = next(
                (c for c in cols if "nombre" in c.lower() or "name" in c.lower()), None
            )
            rows = []
            for i in ids:
                row = {col_id: i}
                if nombre_col:
                    row[nombre_col] = f"SINTETICO-{i}"
                rows.append(row)
            conn.execute(
                text(
                    f"INSERT INTO `{tabla}` ({', '.join(rows[0].keys())}) "
                    f"VALUES ({', '.join(':' + k for k in rows[0].keys())})"
                ),
                rows,
            )
        else:
            existentes = {
                r[0]
                for r in conn.execute(text(f"SELECT `{col_id}` FROM `{tabla}`")).fetchall()
            }
            faltantes = [i for i in ids if i not in existentes]
            if faltantes:
                sys.exit(
                    f"ERROR: {tabla} tiene datos pero faltan {len(faltantes)} ids "
                    f"del CSV, p. ej. {faltantes[:5]}. Cárgalos primero."
                )
            print(f"{tabla}: {n} registros, todos los ids del CSV existen")


def importar(df: pd.DataFrame) -> None:
    insp = inspect(engine)
    missing = [t for t in EXPECTED_TABLES if not insp.has_table(t)]
    if missing:
        sys.exit(f"ERROR: faltan tablas en la BD: {missing}")

    cols_asist = columnas_de(engine.connect(), "asistencias")
    cols_comunes = [c for c in EXPECTED_COLS if c in cols_asist]
    if set(DEDUP_COLS) - set(cols_comunes):
        sys.exit(f"ERROR: asistencias no tiene las columnas {DEDUP_COLS}: {cols_asist}")
    print(f"Columnas de asistencias usadas en la importación: {cols_comunes}\n")

    with engine.begin() as conn:
        asegurar_padres(conn, df)

        crear_staging(conn)
        df.to_sql(STAGING_TABLE, conn, if_exists="append", index=False)
        print(f"staging_asistencias: {len(df)} filas cargadas")

        join_cond = " AND ".join(f"a.{c} = s.{c}" for c in DEDUP_COLS)
        col_list = ", ".join(cols_comunes)
        sel_list = ", ".join(f"s.{c}" for c in cols_comunes)
        result = conn.execute(
            text(
                f"""
                INSERT INTO asistencias ({col_list})
                SELECT {sel_list}
                FROM {STAGING_TABLE} s
                LEFT JOIN asistencias a ON {join_cond}
                WHERE a.{DEDUP_COLS[0]} IS NULL
                """
            )
        )
        print(f"Insertadas en asistencias: {result.rowcount} filas")
        print(f"Omitidas (ya existían): {len(df) - result.rowcount} filas")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo-validar", action="store_true",
                        help="Valida el CSV sin tocar la base de datos")
    args = parser.parse_args()

    print("== Validación del CSV ==")
    df = validar_csv(CSV_PATH)
    if args.solo_validar:
        print("Validación completada (--solo-validar, sin importar).")
        return 0

    print("== Importación a TiDB ==")
    importar(df)
    print("\nImportación completada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
