from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AsistenciaOut, EstudianteOut

router = APIRouter(prefix="/estudiantes", tags=["estudiantes"])


@router.get("", response_model=list[EstudianteOut])
def listar_estudiantes(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT student_id, nombres, apellidos FROM estudiantes ORDER BY student_id")
    ).mappings().all()
    return rows


@router.get("/{student_id}", response_model=EstudianteOut)
def obtener_estudiante(student_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text(
            "SELECT student_id, nombres, apellidos FROM estudiantes "
            "WHERE student_id = :sid"
        ),
        {"sid": student_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return row


@router.get("/{student_id}/asistencias", response_model=list[AsistenciaOut])
def asistencias_estudiante(student_id: str, db: Session = Depends(get_db)):
    obtener_estudiante(student_id, db)
    rows = db.execute(
        text(
            """
            SELECT a.attendance_id, a.student_id, a.session_id,
                   a.attendance_status, s.session_date, s.course_id
            FROM asistencias a
            JOIN sesiones s ON a.session_id = s.session_id
            WHERE a.student_id = :sid
            ORDER BY s.session_date
            """
        ),
        {"sid": student_id},
    ).mappings().all()
    return rows
