export interface PredHistorial {
  student_id: string
  course_id: string
  probabilidad: number
  prediccion: number
  dataset: string
  dataset_id: string
  fecha: string
  nivel_riesgo?: string
  etiqueta?: string
  alerta?: boolean
}

const KEY = 'historial_preds'

export function leerHistorial(): PredHistorial[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}

export function guardarPredicciones(items: PredHistorial[]): void {
  const actual = leerHistorial().filter(
    (h) =>
      !items.some(
        (n) =>
          n.dataset_id === h.dataset_id &&
          n.student_id === h.student_id &&
          n.course_id === h.course_id
      )
  )
  localStorage.setItem(KEY, JSON.stringify([...items, ...actual]))
}

export function limpiarHistorial(): void {
  localStorage.removeItem(KEY)
}
