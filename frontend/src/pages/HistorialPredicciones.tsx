import { useEffect, useState } from 'react'
import api, { detalleError } from '../api/client'
import { leerHistorial, limpiarHistorial, type PredHistorial } from '../api/historial'
import type { PrediccionGuardada } from '../api/types'
import {
  ClasificacionBadge,
  ErrorMessage,
  EtiquetaBadge,
  Loading,
  ProbabilidadBar,
  RiesgoBadge,
} from '../components/ui'

interface FilaHistorial {
  student_id: string
  course_id: string
  probabilidad: number
  prediccion: number
  origen: string
  fecha: string
  nivel_riesgo?: string
  etiqueta?: string
  alerta?: boolean
}

export default function HistorialPredicciones() {
  const [filas, setFilas] = useState<FilaHistorial[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  function cargar() {
    setCargando(true)
    const locales: FilaHistorial[] = leerHistorial().map((p: PredHistorial) => ({
      student_id: p.student_id,
      course_id: p.course_id,
      probabilidad: p.probabilidad,
      prediccion: p.prediccion,
      origen: p.dataset,
      fecha: p.fecha,
      nivel_riesgo: p.nivel_riesgo,
      etiqueta: p.etiqueta,
      alerta: p.alerta,
    }))
    api
      .get<PrediccionGuardada[]>('/predicciones')
      .then((r) => {
        const bd: FilaHistorial[] = r.data.map((p) => ({
          student_id: p.student_id,
          course_id: p.course_id ?? '—',
          probabilidad: Number(p.attendance_probability),
          prediccion: p.predicted_status,
          origen: 'Base de datos TiDB',
          fecha: p.created_at,
        }))
        setFilas([...locales, ...bd])
      })
      .catch((err) => setError(detalleError(err)))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [])

  if (cargando) return <Loading />
  if (error) return <ErrorMessage mensaje={error} />

  return (
    <div>
      <h2 className="titulo-pagina">Historial de predicciones</h2>
      <div className="panel">
        <div className="filtros" style={{ justifyContent: 'flex-end' }}>
          <button
            className="btn btn-secundario"
            onClick={() => {
              limpiarHistorial()
              cargar()
            }}
          >
            Borrar historial de datasets
          </button>
        </div>
        <div className="tabla-wrap">
        <table className="tabla">
          <thead>
            <tr>
              <th>Estudiante</th>
              <th>Curso</th>
              <th>Probabilidad</th>
              <th>Clasificación</th>
              <th>Riesgo</th>
              <th>Origen</th>
              <th>Fecha de generación</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((p, i) => (
              <tr key={i}>
                <td>{p.student_id}</td>
                <td>{p.course_id}</td>
                <td className="celda-prob">
                  <ProbabilidadBar valor={p.probabilidad} />
                </td>
                <td>
                  {p.etiqueta ? (
                    <EtiquetaBadge etiqueta={p.etiqueta} />
                  ) : (
                    <ClasificacionBadge prediccion={p.prediccion} />
                  )}
                </td>
                <td>
                  {p.nivel_riesgo ? (
                    <span>
                      <RiesgoBadge nivel={p.nivel_riesgo} />
                      {p.alerta && ' ⚠'}
                    </span>
                  ) : (
                    '—'
                  )}
                </td>
                <td>{p.origen}</td>
                <td>{new Date(p.fecha).toLocaleString('es-PE')}</td>
              </tr>
            ))}
            {filas.length === 0 && (
              <tr>
                <td colSpan={7} className="sin-datos">
                  Todavía no hay predicciones generadas
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  )
}
