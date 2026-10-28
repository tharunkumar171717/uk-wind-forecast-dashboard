import { Route, Routes } from 'react-router-dom'
import { api } from './api/client'
import Layout from './components/Layout'
import { useApi } from './hooks/useApi'
import Accuracy from './pages/Accuracy'
import DeliveryAnalysis from './pages/DeliveryAnalysis'
import Methodology from './pages/Methodology'
import Overview from './pages/Overview'

export default function App() {
  const meta = useApi(() => api.metadata(), [])
  return (
    <Routes>
      <Route element={<Layout metadata={meta.data} />}>
        <Route index element={<Overview metadata={meta.data} />} />
        <Route path="accuracy" element={<Accuracy />} />
        <Route path="delivery" element={<DeliveryAnalysis />} />
        <Route path="methodology" element={<Methodology meta={meta} />} />
        <Route path="*" element={<p className="text-sm text-muted">Page not found.</p>} />
      </Route>
    </Routes>
  )
}
