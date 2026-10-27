import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './layouts/Layout'
import Placeholder from './pages/Placeholder'
import Guide from './pages/Guide'
import NewAnalysis from './pages/NewAnalysis'
import Progress from './pages/Progress'
import Result from './pages/Result'
import History from './pages/History'
import Login from './pages/Login'
import Register from './pages/Register'
import RequireAuth from './layouts/RequireAuth'
import { researcherLinks, readerLinks, adminLinks } from './layouts/nav'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* Halaman tanpa sidebar */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/guest/login" element={<Placeholder title="Login Pembaca" />} />
      <Route path="/admin/login" element={<Placeholder title="Login Administrator" />} />

      {/* Peneliti */}
      <Route element={<RequireAuth />}>
        <Route element={<Layout role="Peneliti" links={researcherLinks} />}>
          <Route path="/guide" element={<Guide />} />
          <Route path="/analysis/new" element={<NewAnalysis />} />
          <Route path="/analysis/:runId/progress" element={<Progress />} />
          <Route path="/analysis/:runId/result" element={<Result />} />
          <Route path="/history" element={<History />} />
        </Route>
      </Route>

      {/* Pembaca */}
      <Route element={<Layout role="Pembaca Publik" links={readerLinks} />}>
        <Route path="/public" element={<Placeholder title="Berkas Publik" />} />
        <Route path="/public/history" element={<Placeholder title="Riwayat Berkas" />} />
        <Route path="/public/:runId/result" element={<Placeholder title="Hasil Berkas Publik" />} />
      </Route>

      {/* Administrator */}
      <Route element={<Layout role="Administrator" links={adminLinks} />}>
        <Route path="/admin/accounts" element={<Placeholder title="Kelola Akun" />} />
        <Route path="/admin/health" element={<Placeholder title="Health Check" />} />
      </Route>

      <Route path="*" element={<Placeholder title="Halaman tidak ditemukan" />} />
    </Routes>
  )
}