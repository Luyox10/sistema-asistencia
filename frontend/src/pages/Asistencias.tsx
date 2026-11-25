import { useEffect, useState } from 'react'
import api, { detalleError } from '../api/client'
import { useDataset } from '../api/datasetContext'
import type { Asistencia, Curso, Estudiante } from '../api/types'
import {
  ErrorMessage,
  EstadoBadge,
  Loading,
  SinDataset,
} from '../components/ui'

export default function Asistencias() {
  const { activo } = useDataset()
  const [asistencias, setAsistencias] = useState<Asistencia[]>([])
  const [estudiantes, setEstudiantes] = useState<Estudiante[]>([])
  const [cursos, setCursos] = useState<Curso[]>([])
  const [fEstudiante, setFEstudiante] = useState('')
  const [fCurso, setFCurso] = useState('')
  const [fDesde, setFDesde] = useState('')
  const [fHasta, setFHasta] = useState('')
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!activo) return
    const base = `/datasets/${activo.id}`
    Promise.all([
      api.get<Estudiante[]>(`${base}/estudiantes`),
      api.get<Curso[]>(`${base}/cursos`),
    ])
      .then(([e, c]) => {
        setEstudiantes(e.data)
        setCursos(c.data)
      })
      .catch((err) => setError(detalleError(err)))
  }, [activo])

  function cargar() {
    if (!activo) return
    setCargando(true)
    setError('')
    api
      .get<Asistencia[]>(`/datasets/${activo.id}/asistencias`, {
        params: {
          student_id: fEstudiante || undefined,
          course_id: fCurso || undefined,
          fecha_desde: fDesde || undefined,
          fecha_hasta: fHasta || undefined,
        },
      })
      .then((r) => setAsistencias(r.data))
      .catch((err) => setError(detalleError(err)))
      .finally(() => setCargando(false))
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(cargar, [activo])

  if (!activo) return <SinDataset />
  if (error) return <ErrorMessage mensaje={error} />

  return (
    <div>
      <h2 className="titulo-pagina">Historial de asistencia</h2>

      <div className="filtros">
        <select value={fEstudiante} onChange={(e) => setFEstudiante(e.target.value)}>
          <option value="">Todos los estudiantes</option>
          {estudiantes.map((e) => (
            <option key={e.student_id} value={e.student_id}>
              {e.student_id}
              {e.nombres ? ` — ${e.nombres} ${e.apellidos ?? ''}` : ''}
            </option>
          ))}
        </select>
        <select value={fCurso} onChange={(e) => setFCurso(e.target.value)}>
          <option value="">Todos los cursos</option>
          {cursos.map((c) => (
            <option key={c.course_id} value={c.course_id}>
              {c.course_id} — {c.course_name}
            </option>
          ))}
        </select>
        <input type="date" value={fDesde} onChange={(e) => setFDesde(e.target.value)} />
        <input type="date" value={fHasta} onChange={(e) => setFHasta(e.target.value)} />
        <button className="btn" onClick={cargar}>
          Filtrar
        </button>
      </div>

      <div className="panel">
        {cargando ? (
          <Loading />
        ) : (
          <div className="tabla-wrap">
          <table className="tabla">
            <thead>
              <tr>
                <th>Estudiante</th>
                <th>Curso</th>
                <th>Sesión</th>
                <th>Fecha</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {asistencias.map((a) => (
                <tr key={`${a.student_id}-${a.session_id}`}>
                  <td>{a.student_id}</td>
                  <td>{a.course_id}</td>
                  <td>{a.session_id}</td>
                  <td>{a.session_date}</td>
                  <td>
                    <EstadoBadge status={a.attendance_status} />
                  </td>
                </tr>
              ))}
              {asistencias.length === 0 && (
                <tr>
                  <td colSpan={5} className="sin-datos">
                    No hay registros con esos filtros
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </div>
  )
}
