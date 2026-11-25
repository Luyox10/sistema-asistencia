from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AsistenciaOut

router = APIRouter(prefix="/asistencias", tags=["asistencias"])

_BASE = """
    SELECT a.attendance_id, a.student_id, a.session_id,
           a.attendance_status, s.session_date, s.course_id
    FROM asistencias a
    JOIN sesiones s ON a.session_id = s.session_id
"""


@router.get("", response_model=list[AsistenciaOut])
def listar_asistencias(
    student_id: str | None = None,
    course_id: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    condiciones = []
    params: dict = {"lim": limit, "off": offset}
    if student_id:
        condiciones.append("a.student_id = :sid")
        params["sid"] = student_id
    if course_id:
        condiciones.append("s.course_id = :cid")
        params["cid"] = course_id
    if fecha_desde:
        condiciones.append("s.session_date >= :desde")
        params["desde"] = fecha_desde
    if fecha_hasta:
        condiciones.append("s.session_date <= :hasta")
        params["hasta"] = fecha_hasta
    where = " WHERE " + " AND ".join(condiciones) if condiciones else ""
    rows = db.execute(
        text(
            f"{_BASE}{where} ORDER BY s.session_date, a.student_id "
            "LIMIT :lim OFFSET :off"
        ),
        params,
    ).mappings().all()
    return rows


@router.get("/estudiante/{student_id}", response_model=list[AsistenciaOut])
def asistencias_por_estudiante(student_id: str, db: Session = Depends(get_db)):
    rows = db.execute(
        text(f"{_BASE} WHERE a.student_id = :sid ORDER BY s.session_date"),
        {"sid": student_id},
    ).mappings().all()
    if not rows:
        existe = db.execute(
            text("SELECT 1 FROM estudiantes WHERE student_id = :sid"), {"sid": student_id}
        ).first()
        if existe is None:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return rows


@router.get("/curso/{course_id}", response_model=list[AsistenciaOut])
def asistencias_por_curso(course_id: str, db: Session = Depends(get_db)):
    rows = db.execute(
        text(f"{_BASE} WHERE s.course_id = :cid ORDER BY s.session_date, a.student_id"),
        {"cid": course_id},
    ).mappings().all()
    if not rows:
        existe = db.execute(
            text("SELECT 1 FROM cursos WHERE course_id = :cid"), {"cid": course_id}
        ).first()
        if existe is None:
            raise HTTPException(status_code=404, detail="Curso no encontrado")
    return rows


@router.get(
    "/historial/{student_id}/{course_id}", response_model=list[AsistenciaOut]
)
def historial(student_id: str, course_id: str, db: Session = Depends(get_db)):
    """Historial de asistencias de un estudiante en un curso, ordenado por fecha."""
    rows = db.execute(
        text(
            f"{_BASE} WHERE a.student_id = :sid AND s.course_id = :cid "
            "ORDER BY s.session_date"
        ),
        {"sid": student_id, "cid": course_id},
    ).mappings().all()
    return rows
