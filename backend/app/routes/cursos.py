from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import CursoOut, SesionOut

router = APIRouter(prefix="/cursos", tags=["cursos"])


@router.get("", response_model=list[CursoOut])
def listar_cursos(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT course_id, course_name FROM cursos ORDER BY course_id")
    ).mappings().all()
    return rows


@router.get("/{course_id}", response_model=CursoOut)
def obtener_curso(course_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT course_id, course_name FROM cursos WHERE course_id = :cid"),
        {"cid": course_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return row


@router.get("/{course_id}/sesiones", response_model=list[SesionOut])
def sesiones_curso(course_id: str, db: Session = Depends(get_db)):
    obtener_curso(course_id, db)
    rows = db.execute(
        text(
            "SELECT session_id, course_id, session_date FROM sesiones "
            "WHERE course_id = :cid ORDER BY session_date"
        ),
        {"cid": course_id},
    ).mappings().all()
    return rows


@router.get("/{course_id}/estadisticas")
def estadisticas_curso(course_id: str, db: Session = Depends(get_db)):
    """Estadísticas de asistencia del curso."""
    obtener_curso(course_id, db)
    row = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT s.session_id) AS total_sesiones,
                   COUNT(a.attendance_id) AS total_registros,
                   COALESCE(SUM(a.attendance_status), 0) AS asistencias
            FROM sesiones s
            LEFT JOIN asistencias a ON a.session_id = s.session_id
            WHERE s.course_id = :cid
            """
        ),
        {"cid": course_id},
    ).mappings().one()
    total = row["total_registros"]
    asist = int(row["asistencias"])
    return {
        "course_id": course_id,
        "total_sesiones": row["total_sesiones"],
        "total_registros": total,
        "asistencias": asist,
        "inasistencias": total - asist,
        "porcentaje_asistencia": round(asist / total * 100, 2) if total else 0.0,
    }


@router.get("/{course_id}/sesiones-pendientes/{student_id}")
def sesiones_pendientes(course_id: str, student_id: str, db: Session = Depends(get_db)):
    """Sesiones del curso para las que el estudiante aún NO tiene asistencia
    registrada (candidatas a predicción)."""
    obtener_curso(course_id, db)
    rows = db.execute(
        text(
            """
            SELECT s.session_id, s.session_date
            FROM sesiones s
            LEFT JOIN asistencias a
                ON a.session_id = s.session_id AND a.student_id = :sid
            WHERE s.course_id = :cid AND a.attendance_id IS NULL
            ORDER BY s.session_date
            """
        ),
        {"cid": course_id, "sid": student_id},
    ).mappings().all()
    return [dict(r) for r in rows]
