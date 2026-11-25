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

export default function Estudiantes() {
  const { activo } = useDataset()
  const [estudiantes, setEstudiantes] = useState<Estudiante[]>([])
  const [cursos, setCursos] = useState<Curso[]>([])
  const [busqueda, setBusqueda] = useState('')
  const [seleccionado, setSeleccionado] = useState<Estudiante | null>(null)
  const [historial, setHistorial] = useState<Asistencia[]>([])
  const [cargando, setCargando] = useState(true)
  const [cargandoHist, setCargandoHist] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!activo) return
    setCargando(true)
    setSeleccionado(null)
    setError('')
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
      .finally(() => setCargando(false))
  }, [activo])

  const filtrados = estudiantes.filter(
    (e) =>
      e.student_id.toLowerCase().includes(busqueda.toLowerCase()) ||
      `${e.nombres ?? ''} ${e.apellidos ?? ''}`
        .toLowerCase()
        .includes(busqueda.toLowerCase())
  )

  function verDetalle(e: Estudiante) {
    if (!activo) return
    setSeleccionado(e)
    setCargandoHist(true)
    setHistorial([])
    api
      .get<Asistencia[]>(`/datasets/${activo.id}/estudiantes/${e.student_id}/asistencias`)
      .then((r) => setHistorial(r.data))
      .catch((err) => setError(detalleError(err)))
      .finally(() => setCargandoHist(false))
  }

  if (!activo) return <SinDataset />
  if (cargando) return <Loading />
  if (error) return <ErrorMessage mensaje={error} />

  // Historial agrupado por curso, en el orden de los cursos del dataset
  const nombresCurso = new Map(cursos.map((c) => [c.course_id, c.course_name]))
  const porCurso = new Map<string, Asistencia[]>()
  for (const a of historial) {
    const cid = a.course_id ?? '—'
    if (!porCurso.has(cid)) porCurso.set(cid, [])
    porCurso.get(cid)!.push(a)
  }
  const cursosOrdenados = [
    ...cursos.map((c) => c.course_id).filter((id) => porCurso.has(id)),
    ...[...porCurso.keys()].filter(
      (id) => !cursos.some((c) => c.course_id === id)
    ),
  ]

  return (
    <div>
      <div className="barra-pagina">
        <h2 className="titulo-pagina">Estudiantes</h2>
        <div className="busqueda-contenedor">
          <input
            className="input-buscar"
            placeholder="Buscar por identificador o nombre…"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </div>
      </div>

      <div className="panel">
        <div className="tabla-wrap">
        <table className="tabla">
          <thead>
            <tr>
              <th>ID</th>
              <th>Nombres</th>
              <th>Apellidos</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtrados.map((e) => (
              <tr key={e.student_id}>
                <td>{e.student_id}</td>
                <td>{e.nombres ?? '—'}</td>
                <td>{e.apellidos ?? '—'}</td>
                <td>
                  <button className="btn btn-secundario" onClick={() => verDetalle(e)}>
                    Ver historial
                  </button>
                </td>
              </tr>
            ))}
            {filtrados.length === 0 && (
              <tr>
                <td colSpan={4} className="sin-datos">
                  Sin resultados para «{busqueda}»
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </div>
      </div>

      {seleccionado && (
        <div className="panel">
          <h3>
            Historial de {seleccionado.student_id}
            {seleccionado.nombres ? ` — ${seleccionado.nombres} ${seleccionado.apellidos ?? ''}` : ''}
          </h3>
          {cargandoHist ? (
            <Loading texto="Cargando historial…" />
          ) : historial.length === 0 ? (
            <p className="sin-datos">Sin registros de asistencia.</p>
          ) : (
            cursosOrdenados.map((cid) => {
              const registros = porCurso.get(cid)!
              const asist = registros.filter((a) => a.attendance_status === 1).length
              return (
                <div key={cid} className="bloque-curso">
                  <div className="bloque-curso-header">
                    <h4>
                      {cid}
                      {nombresCurso.get(cid) ? ` — ${nombresCurso.get(cid)}` : ''}
                    </h4>
                    <span className="badge badge-ok">{asist} asist.</span>
                    <span className="badge badge-fail">
                      {registros.length - asist} faltas
                    </span>
                  </div>
                  <div className="tabla-wrap tabla-wrap-interna">
                  <table className="tabla">
                    <thead>
                      <tr>
                        <th>Sesión</th>
                        <th>Fecha</th>
                        <th>Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {registros.map((a) => (
                        <tr key={a.session_id}>
                          <td>{a.session_id}</td>
                          <td>{a.session_date}</td>
                          <td>
                            <EstadoBadge status={a.attendance_status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
