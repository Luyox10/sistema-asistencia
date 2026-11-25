from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import DashboardOut

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    """Resumen general: totales y porcentaje de asistencia."""
    row = db.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM estudiantes)                          AS total_estudiantes,
                (SELECT COUNT(*) FROM cursos)                               AS total_cursos,
                (SELECT COUNT(*) FROM sesiones)                             AS total_sesiones,
                (SELECT COUNT(*) FROM asistencias)                          AS total_asistencias,
                (SELECT COALESCE(SUM(attendance_status), 0)
                   FROM asistencias)                                        AS asistencias
            """
        )
    ).mappings().one()

    total = row["total_asistencias"]
    asistencias = int(row["asistencias"])
    return DashboardOut(
        total_estudiantes=row["total_estudiantes"],
        total_cursos=row["total_cursos"],
        total_sesiones=row["total_sesiones"],
        total_asistencias=total,
        asistencias=asistencias,
        inasistencias=total - asistencias,
        porcentaje_asistencia=round(asistencias / total * 100, 2) if total else 0.0,
    )


@router.get("/dashboard/evolucion")
def evolucion(db: Session = Depends(get_db)):
    """Asistencias e inasistencias agrupadas por fecha de sesión."""
    rows = db.execute(
        text(
            """
            SELECT s.session_date AS fecha,
                   SUM(a.attendance_status) AS asistencias,
                   COUNT(*) - SUM(a.attendance_status) AS inasistencias
            FROM asistencias a
            JOIN sesiones s ON a.session_id = s.session_id
            GROUP BY s.session_date
            ORDER BY s.session_date
            """
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/dashboard/por-curso")
def por_curso(db: Session = Depends(get_db)):
    """Resumen de asistencia agrupado por curso."""
    rows = db.execute(
        text(
            """
            SELECT c.course_id, c.course_name,
                   COUNT(a.attendance_id) AS total,
                   COALESCE(SUM(a.attendance_status), 0) AS asistencias,
                   COUNT(a.attendance_id) - COALESCE(SUM(a.attendance_status), 0)
                       AS inasistencias
            FROM cursos c
            LEFT JOIN sesiones s ON s.course_id = c.course_id
            LEFT JOIN asistencias a ON a.session_id = s.session_id
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_id
            """
        )
    ).mappings().all()
    result = []
    for r in rows:
        total = r["total"] or 0
        asist = int(r["asistencias"] or 0)
        result.append(
            {
                "course_id": r["course_id"],
                "course_name": r["course_name"],
                "total": total,
                "asistencias": asist,
                "inasistencias": total - asist,
                "porcentaje_asistencia": round(asist / total * 100, 2) if total else 0.0,
            }
        )
    return result
