import { useEffect, useState } from 'react'
import api, { detalleError } from '../api/client'
import { useDataset } from '../api/datasetContext'
import { guardarPredicciones } from '../api/historial'
import type { Curso, Estudiante, PrediccionDataset } from '../api/types'
import {
  ErrorMessage,
  EstadoBadge,
  EtiquetaBadge,
  Loading,
  ProbabilidadBar,
  RiesgoBadge,
  SinDataset,
} from '../components/ui'

export default function Predicciones() {
  const { activo } = useDataset()
  const [estudiantes, setEstudiantes] = useState<Estudiante[]>([])
  const [cursos, setCursos] = useState<Curso[]>([])
  const [fEstudiante, setFEstudiante] = useState('')
  const [fCurso, setFCurso] = useState('')
  const [resultados, setResultados] = useState<PrediccionDataset[]>([])
  const [aviso, setAviso] = useState('')
  const [cargando, setCargando] = useState(true)
  const [prediciendo, setPrediciendo] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!activo) return
    setCargando(true)
    setError('')
    setResultados([])
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

  function generar() {
    if (!activo) return
    setPrediciendo(true)
    setAviso('')
    setResultados([])
    api
      .get<PrediccionDataset[]>(`/datasets/${activo.id}/predicciones`, {
        params: {
          student_id: fEstudiante || undefined,
          course_id: fCurso || undefined,
        },
      })
      .then((r) => {
        setResultados(r.data)
        const ok = r.data.filter((p) => p.estado === 'ok')
        if (ok.length) {
          guardarPredicciones(
            ok.map((p) => ({
              student_id: p.student_id,
              course_id: p.course_id,
              probabilidad: p.probabilidad ?? 0,
              prediccion: p.prediccion ?? 0,
              nivel_riesgo: p.experto?.nivel_riesgo,
              etiqueta: p.experto?.etiqueta,
              alerta: p.experto?.alerta,
              dataset: activo.reporte.archivo,
              dataset_id: activo.id,
              fecha: new Date().toISOString(),
            }))
          )
        }
        if (r.data.every((p) => p.estado !== 'ok')) {
          setAviso(
            'Ningún alumno tiene al menos 7 asistencias válidas en el dataset con esos filtros.'
          )
        }
      })
      .catch((err) => setAviso(detalleError(err)))
      .finally(() => setPrediciendo(false))
  }

  if (!activo) return <SinDataset />
  if (cargando) return <Loading />
  if (error) return <ErrorMessage mensaje={error} />

  return (
    <div>
      <h2 className="titulo-pagina">Predicción de asistencia (LSTM)</h2>

      <div className="panel">
        <p className="texto-ayuda">
          Sistema híbrido: el modelo LSTM estima la probabilidad con las últimas
          7 asistencias y el motor de reglas IF-THEN asigna el nivel de riesgo,
          la etiqueta (asiste / probable asistencia / no asiste) y las alertas
          tempranas. Umbral del modelo: 0.5.
        </p>
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
          <button className="btn" disabled={prediciendo} onClick={generar}>
            {prediciendo ? 'Generando…' : 'Generar predicciones'}
          </button>
        </div>
        {aviso && <div className="aviso">⚠ {aviso}</div>}
      </div>

      {resultados.length > 0 && (
        <div className="panel">
          <h3>Predicciones generadas ({resultados.length})</h3>
          {resultados.some((p) => p.experto?.alerta) && (
            <div className="aviso">
              ⚠ {resultados.filter((p) => p.experto?.alerta).length} caso(s) con
              alerta temprana — pasa el cursor sobre la recomendación para verla
              completa.
            </div>
          )}
          <div className="tabla-wrap">
          <table className="tabla">
            <thead>
              <tr>
                <th>Estudiante</th>
                <th>Curso</th>
                <th>Últimas 7 asistencias</th>
                <th>Probabilidad</th>
                <th>Estado próxima clase</th>
                <th>Riesgo</th>
                <th>Recomendación</th>
              </tr>
            </thead>
            <tbody>
              {resultados.map((p) => (
                <tr key={`${p.student_id}-${p.course_id}`}>
                  <td>{p.student_id}</td>
                  <td>{p.course_id}</td>
                  <td>
                    {p.estado === 'ok' ? (
                      <div className="historial-chips">
                        {(p.historial_usado ?? []).map((v, i) => (
                          <span key={i} className="chip">
                            <EstadoBadge status={v} />
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="badge badge-fail">
                        Solo {p.registros} registros (mín. 7)
                      </span>
                    )}
                  </td>
                  <td className="celda-prob">
                    {p.estado === 'ok' && p.probabilidad !== undefined ? (
                      <ProbabilidadBar valor={p.probabilidad} />
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>
                    {p.experto ? <EtiquetaBadge etiqueta={p.experto.etiqueta} /> : '—'}
                  </td>
                  <td>
                    {p.experto ? (
                      <span title={`Reglas: ${p.experto.reglas_activadas.join(', ')}`}>
                        <RiesgoBadge nivel={p.experto.nivel_riesgo} />
                        {p.experto.alerta && ' ⚠'}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="celda-reco">
                    {p.experto ? (
                      <span title={p.experto.recomendacion}>
                        {p.experto.recomendacion}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </div>
  )
}
