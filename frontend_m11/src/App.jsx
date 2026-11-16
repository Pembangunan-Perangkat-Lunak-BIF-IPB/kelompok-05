import { Routes, Route, Navigate } from 'react-router-dom'
import Landing from './pages/Landing'
import Layout from './layouts/Layout'
import Placeholder from './pages/Placeholder'
import Guide from './pages/Guide'
import NewAnalysis from './pages/NewAnalysis'
import Progress from './pages/Progress'
import Result from './pages/Result'
import History from './pages/History'
import Login from './pages/Login'
import Register from './pages/Register'
import PublicFiles from './pages/PublicFiles'
import PublicHistory from './pages/PublicHistory'
import PublicResult from './pages/PublicResult'
import RequireAuth from './layouts/RequireAuth'
import Accounts from './pages/admin/Accounts'
import HealthCheck from './pages/admin/HealthCheck'
import AdminHistory from './pages/admin/AdminHistory'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />

      {/* Halaman tanpa sidebar */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/public/login" element={<Login role="reader" />} />
      <Route path="/admin/login" element={<Login role="admin" />} />

      {/* Peneliti */}
      <Route element={<RequireAuth />}>
        <Route element={<Layout variant="researcher" />}>
          <Route path="/guide" element={<Guide />} />
          <Route path="/analysis/new" element={<NewAnalysis />} />
          <Route path="/analysis/:runId/progress" element={<Progress />} />
          <Route path="/analysis/:runId/result" element={<Result />} />
          <Route path="/history" element={<History />} />
        </Route>
      </Route>

      {/* Pembaca */}
      <Route element={<Layout variant="reader" />}>
        <Route path="/public" element={<PublicFiles />} />
        <Route path="/public/history" element={<PublicHistory />} />
        <Route path="/public/:runId/result" element={<PublicResult />} />
      </Route>

      {/* Administrator */}
      <Route element={<RequireAuth to="/admin/login" />}>
        <Route element={<Layout variant="admin" />}>
          <Route path="/admin/accounts" element={<Accounts />} />
          <Route path="/admin/health" element={<HealthCheck />} />
          <Route path="/admin/history" element={<AdminHistory />} />
        </Route>
      </Route>

      <Route path="*" element={<Placeholder title="Halaman tidak ditemukan" />} />
    </Routes>
  )
}