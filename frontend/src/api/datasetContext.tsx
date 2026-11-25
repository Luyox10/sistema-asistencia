import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import type { DatasetReporte } from './types'

export interface DatasetActivo {
  id: string
  reporte: DatasetReporte
}

interface DatasetCtx {
  activo: DatasetActivo | null
  setActivo: (d: DatasetActivo | null) => void
}

const Ctx = createContext<DatasetCtx>({ activo: null, setActivo: () => {} })

export function DatasetProvider({ children }: { children: ReactNode }) {
  const [activo, setActivoState] = useState<DatasetActivo | null>(() => {
    try {
      return JSON.parse(localStorage.getItem('dataset_activo') || 'null')
    } catch {
      return null
    }
  })

  const setActivo = (d: DatasetActivo | null) => {
    setActivoState(d)
    if (d) localStorage.setItem('dataset_activo', JSON.stringify(d))
    else localStorage.removeItem('dataset_activo')
  }

  return <Ctx.Provider value={{ activo, setActivo }}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useDataset = () => useContext(Ctx)
