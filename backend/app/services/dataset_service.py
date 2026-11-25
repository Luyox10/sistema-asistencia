"""Validación y registro en memoria de datasets CSV de asistencia.

Esquema mínimo requerido (cabecera exacta):
    student_id,course_id,session_id,session_date,attendance_status

Columnas opcionales admitidas: institucion | institution_id, nombres,
apellidos, course_name. Cualquier otra columna extra se ignora.

Los datasets validados quedan en memoria (_DATASETS) identificados por un
dataset_id; el frontend los usa para alimentar todas las vistas sin tocar
la base de datos.
"""

import io
import uuid

import pandas as pd

REQUIRED_COLS = [
    "student_id",
    "course_id",
    "session_id",
    "session_date",
    "attendance_status",
]
COL_INSTITUCION = ["institucion", "institution_id"]
COLS_OPCIONALES = ["nombres", "apellidos", "course_name"]
ESTADOS_VALIDOS = {"0", "1"}
MAX_FILAS = 500_000

# dataset_id -> (DataFrame, reporte)
_DATASETS: dict[str, tuple[pd.DataFrame, dict]] = {}


class DatasetInvalidoError(Exception):
    """El CSV no cumple el esquema mínimo o contiene datos inválidos."""


class DatasetNoEncontradoError(Exception):
    """El dataset_id solicitado no está cargado en memoria."""


def cargar_y_validar(contenido: bytes, nombre_archivo: str) -> tuple[pd.DataFrame, dict]:
    """Valida el CSV y devuelve (DataFrame limpio, reporte).

    Lanza DatasetInvalidoError con la lista de problemas encontrados.
    """
    if not nombre_archivo.lower().endswith(".csv"):
        raise DatasetInvalidoError("El archivo debe tener extensión .csv")

    try:
        df = pd.read_csv(io.BytesIO(contenido), dtype=str).fillna("")
    except Exception as exc:
        raise DatasetInvalidoError(f"No se pudo leer el CSV: {exc}") from exc

    if len(df) == 0:
        raise DatasetInvalidoError("El CSV no contiene filas de datos")
    if len(df) > MAX_FILAS:
        raise DatasetInvalidoError(
            f"El CSV tiene {len(df)} filas; el máximo permitido es {MAX_FILAS}"
        )

    # Columnas requeridas exactas (extras se ignoran)
    faltan = [c for c in REQUIRED_COLS if c not in df.columns]
    if faltan:
        raise DatasetInvalidoError(
            f"Faltan columnas requeridas: {faltan}. "
            f"Esquema mínimo: {REQUIRED_COLS}"
        )
    col_inst = next((c for c in COL_INSTITUCION if c in df.columns), None)
    cols_opc = [c for c in COLS_OPCIONALES if c in df.columns]
    cols_extra = [
        c
        for c in df.columns
        if c not in REQUIRED_COLS and c != col_inst and c not in cols_opc
    ]
    df = df[REQUIRED_COLS + ([col_inst] if col_inst else []) + cols_opc].copy()

    errores: list[str] = []

    for col in ("student_id", "course_id", "session_id"):
        n = int((df[col].str.strip() == "").sum())
        if n:
            errores.append(f"{n} valores vacíos en {col}")

    n_bad = int((~df["attendance_status"].isin(ESTADOS_VALIDOS)).sum())
    if n_bad:
        errores.append(f"{n_bad} valores inválidos en attendance_status (solo 0/1)")

    fechas = pd.to_datetime(df["session_date"], format="%Y-%m-%d", errors="coerce")
    n_fechas = int(fechas.isna().sum())
    if n_fechas:
        errores.append(
            f"{n_fechas} fechas inválidas en session_date (formato YYYY-MM-DD)"
        )

    n_dup = int(df.duplicated(subset=["student_id", "session_id"]).sum())
    if n_dup:
        errores.append(f"{n_dup} filas duplicadas por (student_id, session_id)")

    if errores:
        raise DatasetInvalidoError("; ".join(errores))

    df["attendance_status"] = df["attendance_status"].astype(int)
    df["session_date"] = fechas.dt.date
    if col_inst and col_inst != "institucion":
        df = df.rename(columns={col_inst: "institucion"})

    reporte = {
        "archivo": nombre_archivo,
        "filas": len(df),
        "estudiantes": int(df.student_id.nunique()),
        "cursos": int(df.course_id.nunique()),
        "sesiones": int(df.session_id.nunique()),
        "fecha_min": str(df.session_date.min()),
        "fecha_max": str(df.session_date.max()),
        "asistencias": int(df.attendance_status.sum()),
        "inasistencias": int(len(df) - df.attendance_status.sum()),
        "instituciones": (
            sorted(df.institucion.unique().tolist()) if col_inst else []
        ),
        "columnas_ignoradas": cols_extra,
        "estado": "valido",
    }
    return df, reporte


def registrar_dataset(df: pd.DataFrame, reporte: dict) -> str:
    """Guarda el dataset en memoria y devuelve su dataset_id."""
    dataset_id = uuid.uuid4().hex[:12]
    _DATASETS[dataset_id] = (df, {**reporte, "dataset_id": dataset_id})
    return dataset_id


def obtener_dataset(dataset_id: str) -> pd.DataFrame:
    try:
        return _DATASETS[dataset_id][0]
    except KeyError:
        raise DatasetNoEncontradoError(
            f"Dataset '{dataset_id}' no está cargado (la memoria se vacía al reiniciar el backend)"
        )


def obtener_reporte(dataset_id: str) -> dict:
    try:
        return _DATASETS[dataset_id][1]
    except KeyError:
        raise DatasetNoEncontradoError(f"Dataset '{dataset_id}' no está cargado")


def listar_datasets() -> list[dict]:
    return [meta for _, meta in _DATASETS.values()]


def eliminar_dataset(dataset_id: str) -> None:
    if _DATASETS.pop(dataset_id, None) is None:
        raise DatasetNoEncontradoError(f"Dataset '{dataset_id}' no está cargado")
