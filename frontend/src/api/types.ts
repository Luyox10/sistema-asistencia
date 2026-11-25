export interface Dashboard {
  total_estudiantes: number
  total_cursos: number
  total_sesiones: number
  total_asistencias: number
  asistencias: number
  inasistencias: number
  porcentaje_asistencia: number
}

export interface EvolucionPoint {
  fecha: string
  asistencias: number
  inasistencias: number
}

export interface CursoResumen {
  course_id: string
  course_name: string
  total: number
  asistencias: number
  inasistencias: number
  porcentaje_asistencia: number
}

export interface Estudiante {
  student_id: string
  nombres: string | null
  apellidos: string | null
}

export interface Curso {
  course_id: string
  course_name: string
}

export interface Sesion {
  session_id: string
  course_id: string
  session_date: string
}

export interface SesionPendiente {
  session_id: string
  session_date: string
}

export interface CursoEstadisticas {
  course_id: string
  total_sesiones: number
  total_registros: number
  asistencias: number
  inasistencias: number
  porcentaje_asistencia: number
}

export interface Asistencia {
  attendance_id?: number
  student_id: string
  session_id: string
  attendance_status: number
  session_date: string | null
  course_id: string | null
}

export interface Prediccion {
  prediction_id: number | null
  student_id: string
  course_id: string
  session_id: string
  probabilidad: number
  prediccion: number
  umbral: number | null
  historial_usado: number[] | null
  guardada: boolean
  created_at: string | null
}

export interface PrediccionGuardada {
  prediction_id: number
  student_id: string
  session_id: string
  course_id: string | null
  attendance_probability: string
  predicted_status: number
  created_at: string
}

export interface DatasetReporte {
  archivo: string
  filas: number
  estudiantes: number
  cursos: number
  sesiones: number
  fecha_min: string
  fecha_max: string
  asistencias: number
  inasistencias: number
  instituciones: string[]
  columnas_ignoradas: string[]
  estado: string
}

export interface HechosExperto {
  probabilidad: number
  ausencias_ultimas: number
  racha_ausencias: number
  tendencia: string
  porcentaje_asistencia: number
}

export interface ExpertoResultado {
  nivel_riesgo: 'bajo' | 'medio' | 'alto'
  alerta: boolean
  etiqueta: string
  recomendacion: string
  reglas_activadas: string[]
  hechos: HechosExperto
}

export interface PrediccionDataset {
  student_id: string
  course_id: string
  estado: 'ok' | 'historial_insuficiente'
  probabilidad?: number
  prediccion?: number
  umbral?: number
  historial_usado?: number[]
  registros?: number
  experto?: ExpertoResultado
}

export interface RespuestaDataset {
  reporte: DatasetReporte
  predicciones: PrediccionDataset[]
}
