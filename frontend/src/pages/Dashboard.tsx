import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import api, { detalleError } from '../api/client'
import { useDataset } from '../api/datasetContext'
import type { CursoResumen, Dashboard as DashboardData, EvolucionPoint } from '../api/types'
import { ErrorMessage, Loading, SinDataset, StatCard } from '../components/ui'

const COLORES_PIE = ['#1f7ae0', '#e05252']

export default function Dashboard() {
  const { activo } = useDataset()
  const [data, setData] = useState<DashboardData | null>(null)
  const [evolucion, setEvolucion] = useState<EvolucionPoint[]>([])
  const [porCurso, setPorCurso] = useState<CursoResumen[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!activo) return
    setData(null)
    setError('')
    const base = `/datasets/${activo.id}`
    Promise.all([
      api.get<DashboardData>(`${base}/dashboard`),
      api.get<EvolucionPoint[]>(`${base}/evolucion`),
      api.get<CursoResumen[]>(`${base}/por-curso`),
    ])
      .then(([d, e, c]) => {
        setData(d.data)
        setEvolucion(e.data)
        setPorCurso(c.data)
      })
      .catch((err) => setError(detalleError(err)))
  }, [activo])

  if (!activo) return <SinDataset />
  if (error) return <ErrorMessage mensaje={error} />
  if (!data) return <Loading />

  const pie = [
    { name: 'Asistencias', value: data.asistencias },
    { name: 'Inasistencias', value: data.inasistencias },
  ]

  return (
    <div>
      <h2 className="titulo-pagina">Dashboard principal</h2>
      <div className="grid-stats">
        <StatCard titulo="Estudiantes" valor={data.total_estudiantes} variante="info" />
        <StatCard titulo="Cursos" valor={data.total_cursos} variante="info" />
        <StatCard titulo="Sesiones" valor={data.total_sesiones} variante="info" />
        <StatCard titulo="Asistencias" valor={data.asistencias} variante="exito" />
        <StatCard titulo="Inasistencias" valor={data.inasistencias} variante="alerta" />
        <StatCard
          titulo="% Asistencia general"
          valor={`${data.porcentaje_asistencia}%`}
          variante="default"
        />
      </div>

      <div className="grid-graficos">
        <div className="panel">
          <h3>Asistencia vs inasistencia</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={pie} dataKey="value" nameKey="name" outerRadius={100} label>
                {pie.map((_, i) => (
                  <Cell key={i} fill={COLORES_PIE[i]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <h3>Resumen por curso</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={porCurso}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="course_id" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="asistencias" name="Asistencias" fill="#1f7ae0" />
              <Bar dataKey="inasistencias" name="Inasistencias" fill="#e05252" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="panel panel-ancho">
          <h3>Evolución de la asistencia por fecha</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={evolucion}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="fecha" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Area
                type="monotone"
                dataKey="asistencias"
                name="Asistencias"
                stroke="#1f7ae0"
                fill="#9ec9f5"
              />
              <Area
                type="monotone"
                dataKey="inasistencias"
                name="Inasistencias"
                stroke="#e05252"
                fill="#f5b3b3"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
