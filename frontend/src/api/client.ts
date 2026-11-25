import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
})

export function detalleError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detalle = err.response?.data?.detail
    if (typeof detalle === 'string') return detalle
    return err.message
  }
  return 'Error inesperado'
}

export default api
