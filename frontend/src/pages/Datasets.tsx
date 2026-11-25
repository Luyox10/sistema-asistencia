import { useEffect, useState } from 'react'
import api, { detalleError } from '../api/client'
import { useDataset } from '../api/datasetContext'
import type { DatasetReporte } from '../api/types'
import { Loading } from '../components/ui'

interface DatasetItem extends DatasetReporte {
  dataset_id: string
}

export default function Datasets() {
  const { activo, setActivo } = useDataset()
  const [lista, setLista] = useState<DatasetItem[]>([])
  const [archivo, setArchivo] = useState<File | null>(null)
  const [subiendo, setSubiendo] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  function cargar() {
    api
      .get<DatasetItem[]>('/datasets')
      .then((r) => {
        setLista(r.data)
        setError('')
      })
      .catch((err) => setError(detalleError(err)))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [])

  function subir() {
    if (!archivo) return
    setSubiendo(true)
    setAviso('')
    const form = new FormData()
    form.append('file', archivo)
    api
      .post<DatasetItem>('/datasets', form)
      .then((r) => {
        setActivo({ id: r.data.dataset_id, reporte: r.data })
        setArchivo(null)
        cargar()
      })
      .catch((err) => setAviso(detalleError(err)))
      .finally(() => setSubiendo(false))
  }

  function eliminar(id: string) {
    api
      .delete(`/datasets/${id}`)
      .then(() => {
        if (activo?.id === id) setActivo(null)
        cargar()
      })
      .catch((err) => setAviso(detalleError(err)))
  }

  if (cargando) return <Loading />

  return (
    <div>
      <h2 className="titulo-pagina">Datasets</h2>

      <div className="panel">
        <h3>Cargar nuevo dataset (CSV)</h3>
        <p className="texto-ayuda">
          El archivo debe contener, para cada registro histórico de asistencia:
          el <strong>ID del estudiante</strong>, el <strong>ID del curso</strong>, el{' '}
          <strong>ID de la sesión</strong>, la <strong>fecha de la sesión</strong> (AAAA-MM-DD)
          y el <strong>estado</strong> (1 = asistió, 0 = no asistió).
        </p>
        <p className="texto-ayuda">
          También puedes incluir opcionalmente la <strong>institución</strong>, los{' '}
          <strong>nombres</strong> y <strong>apellidos</strong> del estudiante y el{' '}
          <strong>nombre del curso</strong>. Los datos se procesan en memoria; no se
          guardan en la base de datos.
        </p>
        <div className="filtros">
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
          />
          <button className="btn" disabled={!archivo || subiendo} onClick={subir}>
            {subiendo ? 'Subiendo…' : 'Subir y usar'}
          </button>
        </div>
        {aviso && <div className="aviso">⚠ {aviso}</div>}
      </div>

      <div className="panel">
        <h3>Datasets cargados</h3>
        {error && <div className="aviso">⚠ No se pudo consultar el backend: {error}</div>}
        <table className="tabla">
          <thead>
            <tr>
              <th>Archivo</th>
              <th>Institución</th>
              <th>Filas</th>
              <th>Estudiantes</th>
              <th>Cursos</th>
              <th>Periodo</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {lista.map((d) => (
              <tr key={d.dataset_id} className={activo?.id === d.dataset_id ? 'fila-activa' : ''}>
                <td>
                  {d.archivo}
                  {activo?.id === d.dataset_id && (
                    <span className="badge badge-ok" style={{ marginLeft: 8 }}>
                      activo
                    </span>
                  )}
                </td>
                <td>{d.instituciones.join(', ') || '—'}</td>
                <td>{d.filas}</td>
                <td>{d.estudiantes}</td>
                <td>{d.cursos}</td>
                <td>
                  {d.fecha_min} → {d.fecha_max}
                </td>
                <td>
                  {activo?.id !== d.dataset_id && (
                    <button
                      className="btn btn-secundario"
                      onClick={() =>
                        setActivo({ id: d.dataset_id, reporte: d })
                      }
                    >
                      Usar
                    </button>
                  )}{' '}
                  <button className="btn btn-secundario" onClick={() => eliminar(d.dataset_id)}>
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
            {lista.length === 0 && (
              <tr>
                <td colSpan={7} className="sin-datos">
                  No hay datasets cargados. Sube un CSV arriba.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
