from datetime import date, datetime

from pydantic import BaseModel, Field


class EstudianteOut(BaseModel):
    student_id: str
    nombres: str | None = None
    apellidos: str | None = None


class CursoOut(BaseModel):
    course_id: str
    course_name: str


class SesionOut(BaseModel):
    session_id: str
    course_id: str
    session_date: date


class AsistenciaOut(BaseModel):
    attendance_id: int
    student_id: str
    session_id: str
    attendance_status: int
    session_date: date | None = None
    course_id: str | None = None


class DashboardOut(BaseModel):
    total_estudiantes: int
    total_cursos: int
    total_sesiones: int
    total_asistencias: int
    asistencias: int
    inasistencias: int
    porcentaje_asistencia: float


class PrediccionRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=20)
    course_id: str = Field(min_length=1, max_length=20)
    session_id: str = Field(min_length=1, max_length=50)


class PrediccionOut(BaseModel):
    prediction_id: int | None = None
    student_id: str
    course_id: str
    session_id: str
    probabilidad: float
    prediccion: int
    umbral: float | None = None
    historial_usado: list[int] | None = None
    guardada: bool = False
    created_at: datetime | None = None
