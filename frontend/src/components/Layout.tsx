import { NavLink, Outlet } from 'react-router-dom'
import { useDataset } from '../api/datasetContext'

const enlaces = [
  { to: '/', label: 'Dashboard', fin: true },
  { to: '/datasets', label: 'Datasets' },
  { to: '/estudiantes', label: 'Estudiantes' },
  { to: '/cursos', label: 'Cursos' },
  { to: '/asistencias', label: 'Historial de asistencia' },
  { to: '/predicciones', label: 'Predicciones LSTM' },
  { to: '/historial-predicciones', label: 'Historial de predicciones' },
]

export default function Layout() {
  const { activo } = useDataset()

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="logo-uni">🎓</span>
          <div>
            <h1>Sistema de Asistencia</h1>
            <p>Predicción LSTM</p>
          </div>
        </div>
        <nav>
          {enlaces.map((e) => (
            <NavLink
              key={e.to}
              to={e.to}
              end={e.fin}
              className={({ isActive }) => (isActive ? 'nav-link activo' : 'nav-link')}
            >
              {e.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-dataset">
          <span className="ds-etiqueta">Dataset activo</span>
          <span className="ds-nombre">
            {activo ? activo.reporte.archivo : 'ninguno — sube un CSV en Datasets'}
          </span>
          {activo && activo.reporte.instituciones.length > 0 && (
            <span className="ds-inst">{activo.reporte.instituciones.join(', ')}</span>
          )}
        </div>
      </aside>
      <main className="contenido">
        <Outlet />
      </main>
    </div>
  )
}
