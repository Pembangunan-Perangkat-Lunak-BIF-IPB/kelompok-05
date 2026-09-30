import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './layouts/Layout'
import Placeholder from './pages/Placeholder'
import { researcherLinks, readerLinks, adminLinks } from './layouts/nav'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* Halaman tanpa sidebar */}
      <Route path="/login" element={<Placeholder title="Login Peneliti" />} />
      <Route path="/register" element={<Placeholder title="Daftar Akun Baru" />} />
      <Route path="/guest/login" element={<Placeholder title="Login Pembaca" />} />
      <Route path="/admin/login" element={<Placeholder title="Login Administrator" />} />

      {/* Peneliti */}
      <Route element={<Layout role="Peneliti" links={researcherLinks} />}>
        <Route path="/guide" element={<Placeholder title="Panduan Penggunaan" />} />
        <Route path="/analysis/new" element={<Placeholder title="Analisis Baru" />} />
        <Route path="/analysis/:runId/progress" element={<Placeholder title="Progres Analisis" />} />
        <Route path="/analysis/:runId/result" element={<Placeholder title="Hasil Analisis" />} />
        <Route path="/history" element={<Placeholder title="Riwayat Analisis" />} />
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