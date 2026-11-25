interface StatCardProps {
  titulo: string
  valor: string | number
  variante?: 'default' | 'exito' | 'alerta' | 'info'
}

export function StatCard({ titulo, valor, variante = 'default' }: StatCardProps) {
  return (
    <div className={`stat-card stat-${variante}`}>
      <span className="stat-titulo">{titulo}</span>
      <span className="stat-valor">{valor}</span>
    </div>
  )
}

export function Loading({ texto = 'Cargando datos…' }: { texto?: string }) {
  return (
    <div className="estado-box">
      <div className="spinner" />
      <p>{texto}</p>
    </div>
  )
}

export function ErrorMessage({ mensaje }: { mensaje: string }) {
  return <div className="estado-box error-box">⚠ {mensaje}</div>
}

export function EstadoBadge({ status }: { status: number }) {
  return status === 1 ? (
    <span className="badge badge-ok">Asistió</span>
  ) : (
    <span className="badge badge-fail">Faltó</span>
  )
}

export function ClasificacionBadge({ prediccion }: { prediccion: number }) {
  return prediccion === 1 ? (
    <span className="badge badge-ok">Probable asistencia</span>
  ) : (
    <span className="badge badge-fail">Probable inasistencia</span>
  )
}

export function EtiquetaBadge({ etiqueta }: { etiqueta: string }) {
  const clase =
    etiqueta === 'asiste'
      ? 'badge-ok'
      : etiqueta === 'no asiste'
        ? 'badge-fail'
        : 'badge-warn'
  return <span className={`badge ${clase}`}>{etiqueta}</span>
}

export function RiesgoBadge({ nivel }: { nivel: string }) {
  const clase =
    nivel === 'alto' ? 'badge-fail' : nivel === 'medio' ? 'badge-warn' : 'badge-ok'
  return <span className={`badge ${clase}`}>Riesgo {nivel}</span>
}

export function SinDataset() {
  return (
    <div className="estado-box">
      <p>
        No hay ningún dataset cargado. Sube uno en la sección{' '}
        <a href="/datasets">Datasets</a> para ver esta vista.
      </p>
    </div>
  )
}

export function ProbabilidadBar({ valor }: { valor: number }) {
  const pct = Math.round(valor * 100)
  const clase = valor >= 0.5 ? 'prob-ok' : 'prob-fail'
  return (
    <div className="prob-bar-wrap">
      <div className={`prob-bar ${clase}`} style={{ width: `${pct}%` }} />
      <span className="prob-label">{pct}%</span>
    </div>
  )
}
