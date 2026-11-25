import { useEffect, useState } from 'react'
import api, { detalleError } from '../api/client'
import { useDataset } from '../api/datasetContext'
import type { Curso, CursoEstadisticas, Sesion } from '../api/types'
import {
  ErrorMessage,
  Loading,
  SinDataset,
  StatCard,
} from '../components/ui'

export default function Cursos() {
  const { activo } = useDataset()
  const [cursos, setCursos] = useState<Curso[]>([])
  const [seleccionado, setSeleccionado] = useState<Curso | null>(null)
  const [sesiones, setSesiones] = useState<Sesion[]>([])
  const [stats, setStats] = useState<CursoEstadisticas | null>(null)
  const [cargando, setCargando] = useState(true)
  const [cargandoDet, setCargandoDet] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!activo) return
    setCargando(true)
    setSeleccionado(null)
    setError('')
    api
      .get<Curso[]>(`/datasets/${activo.id}/cursos`)
      .then((r) => setCursos(r.data))
      .catch((err) => setError(detalleError(err)))
      .finally(() => setCargando(false))
  }, [activo])

  function verDetalle(c: Curso) {
    if (!activo) return
    setSeleccionado(c)
    setCargandoDet(true)
    setSesiones([])
    setStats(null)
    const base = `/datasets/${activo.id}`
    Promise.all([
      api.get<Sesion[]>(`${base}/cursos/${c.course_id}/sesiones`),
      api.get<CursoEstadisticas>(`${base}/cursos/${c.course_id}/estadisticas`),
    ])
      .then(([s, st]) => {
        setSesiones(s.data)
        setStats(st.data)
      })
      .catch((err) => setError(detalleError(err)))
      .finally(() => setCargandoDet(false))
  }

  if (!activo) return <SinDataset />
  if (cargando) return <Loading />
  if (error) return <ErrorMessage mensaje={error} />

  return (
    <div>
      <h2 className="titulo-pagina">Cursos</h2>
      <div className="grid-cursos">
        {cursos.map((c) => (
          <div key={c.course_id} className="curso-card" onClick={() => verDetalle(c)}>
            <h3>{c.course_id}</h3>
            <p>{c.course_name}</p>
          </div>
        ))}
      </div>

      {seleccionado && (
        <div className="panel">
          <h3>
            {seleccionado.course_id} — {seleccionado.course_name}
          </h3>
          {cargandoDet ? (
            <Loading texto="Cargando detalle…" />
          ) : (
            <>
              {stats && (
                <div className="grid-stats">
                  <StatCard titulo="Sesiones" valor={stats.total_sesiones} variante="info" />
                  <StatCard titulo="Asistencias" valor={stats.asistencias} variante="exito" />
                  <StatCard titulo="Inasistencias" valor={stats.inasistencias} variante="alerta" />
                  <StatCard
                    titulo="% Asistencia"
                    valor={`${stats.porcentaje_asistencia}%`}
                  />
                </div>
              )}
              <h4>Sesiones</h4>
              <div className="tabla-wrap tabla-wrap-interna">
              <table className="tabla">
                <thead>
                  <tr>
                    <th>Sesión</th>
                    <th>Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {sesiones.map((s) => (
                    <tr key={s.session_id}>
                      <td>{s.session_id}</td>
                      <td>{s.session_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
