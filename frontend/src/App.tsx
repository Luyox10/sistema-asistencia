import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { DatasetProvider } from './api/datasetContext'
import Layout from './components/Layout'
import Asistencias from './pages/Asistencias'
import Cursos from './pages/Cursos'
import Dashboard from './pages/Dashboard'
import Datasets from './pages/Datasets'
import Estudiantes from './pages/Estudiantes'
import HistorialPredicciones from './pages/HistorialPredicciones'
import Predicciones from './pages/Predicciones'

export default function App() {
  return (
    <DatasetProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="datasets" element={<Datasets />} />
            <Route path="estudiantes" element={<Estudiantes />} />
            <Route path="cursos" element={<Cursos />} />
            <Route path="asistencias" element={<Asistencias />} />
            <Route path="predicciones" element={<Predicciones />} />
            <Route path="historial-predicciones" element={<HistorialPredicciones />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </DatasetProvider>
  )
}
