from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import PrediccionOut, PrediccionRequest
from ..services.prediction_service import (
    EntradaInvalidaError,
    HistorialInsuficienteError,
    ModeloNoDisponibleError,
    guardar_prediccion,
    predecir_asistencia,
    prediccion_existente,
)

router = APIRouter(prefix="/predicciones", tags=["predicciones"])


def _mapear_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ModeloNoDisponibleError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, HistorialInsuficienteError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


@router.get("", response_model=list[dict])
def listar_predicciones(db: Session = Depends(get_db)):
    """Predicciones almacenadas en la tabla predicciones."""
    rows = db.execute(
        text(
            """
            SELECT p.prediction_id, p.student_id, p.session_id, s.course_id,
                   p.attendance_probability, p.predicted_status, p.created_at
            FROM predicciones p
            LEFT JOIN sesiones s ON p.session_id = s.session_id
            ORDER BY p.prediction_id
            """
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/estudiante/{student_id}", response_model=list[dict])
def predicciones_estudiante(student_id: str, db: Session = Depends(get_db)):
    """Predicciones almacenadas de un estudiante concreto."""
    existe = db.execute(
        text("SELECT 1 FROM estudiantes WHERE student_id = :sid"), {"sid": student_id}
    ).first()
    if existe is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    rows = db.execute(
        text(
            """
            SELECT p.prediction_id, p.student_id, p.session_id, s.course_id,
                   p.attendance_probability, p.predicted_status, p.created_at
            FROM predicciones p
            LEFT JOIN sesiones s ON p.session_id = s.session_id
            WHERE p.student_id = :sid ORDER BY p.prediction_id
            """
        ),
        {"sid": student_id},
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/{student_id}/{course_id}/{session_id}", response_model=PrediccionOut)
def predecir(
    student_id: str, course_id: str, session_id: str, db: Session = Depends(get_db)
):
    """Calcula la probabilidad de asistencia en vivo (no guarda nada)."""
    try:
        return predecir_asistencia(db, student_id, course_id, session_id)
    except (ModeloNoDisponibleError, HistorialInsuficienteError, EntradaInvalidaError) as exc:
        raise _mapear_error(exc)


@router.post("", response_model=PrediccionOut)
def generar_y_guardar(req: PrediccionRequest, db: Session = Depends(get_db)):
    """Genera la predicción y la guarda en la tabla predicciones.

    Si ya existe una predicción para (student_id, session_id) devuelve la
    existente sin duplicarla."""
    fila = prediccion_existente(db, req.student_id, req.session_id)
    if fila is not None:
        return PrediccionOut(
            prediction_id=fila["prediction_id"],
            student_id=req.student_id,
            course_id=req.course_id,
            session_id=req.session_id,
            probabilidad=float(fila["attendance_probability"]),
            prediccion=int(fila["predicted_status"]),
            guardada=True,
            created_at=fila["created_at"],
        )
    try:
        resultado = predecir_asistencia(
            db, req.student_id, req.course_id, req.session_id
        )
        fila = guardar_prediccion(
            db,
            req.student_id,
            req.session_id,
            resultado["probabilidad"],
            resultado["prediccion"],
        )
    except (ModeloNoDisponibleError, HistorialInsuficienteError, EntradaInvalidaError) as exc:
        raise _mapear_error(exc)
    return PrediccionOut(
        prediction_id=fila["prediction_id"],
        student_id=req.student_id,
        course_id=req.course_id,
        session_id=req.session_id,
        probabilidad=float(fila["attendance_probability"]),
        prediccion=int(fila["predicted_status"]),
        umbral=resultado["umbral"],
        historial_usado=resultado["historial_usado"],
        guardada=True,
        created_at=fila["created_at"],
    )
