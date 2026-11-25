from datetime import date

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from ..services.dataset_service import (
    DatasetInvalidoError,
    DatasetNoEncontradoError,
    cargar_y_validar,
    eliminar_dataset,
    listar_datasets,
    obtener_dataset,
    obtener_reporte,
    registrar_dataset,
)
from ..services.prediction_service import (
    ModeloNoDisponibleError,
    predecir_desde_df,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])

MAX_BYTES = 50 * 1024 * 1024  # 50 MB


def _ds(dataset_id: str):
    try:
        return obtener_dataset(dataset_id)
    except DatasetNoEncontradoError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


async def _leer_dataset(file: UploadFile):
    contenido = await file.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera los 50 MB")
    try:
        return cargar_y_validar(contenido, file.filename or "dataset.csv")
    except DatasetInvalidoError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ---------- Gestión de datasets ----------


@router.post("")
async def subir_dataset(file: UploadFile = File(...)):
    """Sube un CSV, lo valida y lo registra en memoria.

    Devuelve dataset_id + reporte. Todas las vistas del sistema pueden
    trabajar sobre ese dataset_id."""
    df, reporte = await _leer_dataset(file)
    dataset_id = registrar_dataset(df, reporte)
    return {**reporte, "dataset_id": dataset_id}


@router.post("/validar")
async def validar_dataset(file: UploadFile = File(...)):
    """Valida un CSV y devuelve el reporte sin registrarlo."""
    _, reporte = await _leer_dataset(file)
    return reporte


@router.get("")
def datasets_cargados():
    """Lista los datasets actualmente en memoria."""
    return listar_datasets()


@router.get("/{dataset_id}")
def reporte_dataset(dataset_id: str):
    try:
        return obtener_reporte(dataset_id)
    except DatasetNoEncontradoError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{dataset_id}")
def borrar_dataset(dataset_id: str):
    try:
        eliminar_dataset(dataset_id)
    except DatasetNoEncontradoError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"eliminado": dataset_id}


# ---------- Vistas tipo dashboard ----------


@router.get("/{dataset_id}/dashboard")
def dashboard_dataset(dataset_id: str):
    df = _ds(dataset_id)
    total = len(df)
    asist = int(df.attendance_status.sum())
    return {
        "total_estudiantes": int(df.student_id.nunique()),
        "total_cursos": int(df.course_id.nunique()),
        "total_sesiones": int(df.session_id.nunique()),
        "total_asistencias": total,
        "asistencias": asist,
        "inasistencias": total - asist,
        "porcentaje_asistencia": round(asist / total * 100, 2) if total else 0.0,
    }


@router.get("/{dataset_id}/evolucion")
def evolucion_dataset(dataset_id: str):
    df = _ds(dataset_id)
    g = (
        df.groupby("session_date")["attendance_status"]
        .agg(asistencias="sum", total="count")
        .reset_index()
        .sort_values("session_date")
    )
    return [
        {
            "fecha": str(r.session_date),
            "asistencias": int(r.asistencias),
            "inasistencias": int(r.total - r.asistencias),
        }
        for r in g.itertuples(index=False)
    ]


@router.get("/{dataset_id}/por-curso")
def por_curso_dataset(dataset_id: str):
    df = _ds(dataset_id)
    nombres = (
        df.groupby("course_id")["course_name"].first().to_dict()
        if "course_name" in df.columns
        else {}
    )
    resultado = []
    for cid, g in df.groupby("course_id"):
        total = len(g)
        asist = int(g.attendance_status.sum())
        resultado.append(
            {
                "course_id": cid,
                "course_name": nombres.get(cid) or cid,
                "total": total,
                "asistencias": asist,
                "inasistencias": total - asist,
                "porcentaje_asistencia": round(asist / total * 100, 2) if total else 0.0,
            }
        )
    return sorted(resultado, key=lambda r: r["course_id"])


# ---------- Estudiantes / cursos / sesiones ----------


@router.get("/{dataset_id}/estudiantes")
def estudiantes_dataset(dataset_id: str):
    df = _ds(dataset_id)
    cols = ["student_id"] + [c for c in ("nombres", "apellidos") if c in df.columns]
    return (
        df[cols]
        .drop_duplicates("student_id")
        .sort_values("student_id")
        .to_dict("records")
    )


@router.get("/{dataset_id}/estudiantes/{student_id}/asistencias")
def asistencias_estudiante_dataset(dataset_id: str, student_id: str):
    df = _ds(dataset_id)
    sub = df[df.student_id == student_id].sort_values("session_date")
    if sub.empty:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado en el dataset")
    return [
        {
            "student_id": r.student_id,
            "course_id": r.course_id,
            "session_id": r.session_id,
            "session_date": str(r.session_date),
            "attendance_status": int(r.attendance_status),
        }
        for r in sub.itertuples(index=False)
    ]


@router.get("/{dataset_id}/cursos")
def cursos_dataset(dataset_id: str):
    df = _ds(dataset_id)
    nombres = (
        df.groupby("course_id")["course_name"].first().to_dict()
        if "course_name" in df.columns
        else {}
    )
    return [
        {"course_id": cid, "course_name": nombres.get(cid) or cid}
        for cid in sorted(df.course_id.unique())
    ]


@router.get("/{dataset_id}/cursos/{course_id}/sesiones")
def sesiones_curso_dataset(dataset_id: str, course_id: str):
    df = _ds(dataset_id)
    sub = (
        df[df.course_id == course_id][["session_id", "session_date"]]
        .drop_duplicates("session_id")
        .sort_values("session_date")
    )
    if sub.empty:
        raise HTTPException(status_code=404, detail="Curso no encontrado en el dataset")
    return [
        {"session_id": r.session_id, "course_id": course_id, "session_date": str(r.session_date)}
        for r in sub.itertuples(index=False)
    ]


@router.get("/{dataset_id}/cursos/{course_id}/estadisticas")
def estadisticas_curso_dataset(dataset_id: str, course_id: str):
    df = _ds(dataset_id)
    sub = df[df.course_id == course_id]
    if sub.empty:
        raise HTTPException(status_code=404, detail="Curso no encontrado en el dataset")
    total = len(sub)
    asist = int(sub.attendance_status.sum())
    return {
        "course_id": course_id,
        "total_sesiones": int(sub.session_id.nunique()),
        "total_registros": total,
        "asistencias": asist,
        "inasistencias": total - asist,
        "porcentaje_asistencia": round(asist / total * 100, 2) if total else 0.0,
    }


# ---------- Asistencias ----------


@router.get("/{dataset_id}/asistencias")
def asistencias_dataset(
    dataset_id: str,
    student_id: str | None = None,
    course_id: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = Query(default=5000, ge=1, le=200000),
):
    df = _ds(dataset_id)
    sub = df
    if student_id:
        sub = sub[sub.student_id == student_id]
    if course_id:
        sub = sub[sub.course_id == course_id]
    if fecha_desde:
        sub = sub[sub.session_date >= fecha_desde]
    if fecha_hasta:
        sub = sub[sub.session_date <= fecha_hasta]
    sub = sub.sort_values(["session_date", "student_id"]).head(limit)
    return [
        {
            "student_id": r.student_id,
            "course_id": r.course_id,
            "session_id": r.session_id,
            "session_date": str(r.session_date),
            "attendance_status": int(r.attendance_status),
        }
        for r in sub.itertuples(index=False)
    ]


@router.get("/{dataset_id}/historial/{student_id}/{course_id}")
def historial_dataset(dataset_id: str, student_id: str, course_id: str):
    df = _ds(dataset_id)
    sub = (
        df[(df.student_id == student_id) & (df.course_id == course_id)]
        .sort_values("session_date")
    )
    return [
        {
            "student_id": r.student_id,
            "course_id": r.course_id,
            "session_id": r.session_id,
            "session_date": str(r.session_date),
            "attendance_status": int(r.attendance_status),
        }
        for r in sub.itertuples(index=False)
    ]


# ---------- Predicciones ----------


@router.get("/{dataset_id}/predicciones")
def predicciones_dataset(
    dataset_id: str, student_id: str | None = None, course_id: str | None = None
):
    """Predicciones por alumno/curso sobre el dataset cargado.

    Para cada par usa sus últimas 7 asistencias y predice la próxima sesión."""
    df = _ds(dataset_id)
    try:
        resultados = predecir_desde_df(df, student_id, course_id)
    except ModeloNoDisponibleError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not resultados:
        raise HTTPException(
            status_code=404, detail="Ningún par estudiante-curso coincide con los filtros"
        )
    return resultados
