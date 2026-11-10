import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { auth } from '../lib/api'

// Pembungkus rute Peneliti: tanpa token, arahkan ke /login lalu kembali setelah masuk
export default function RequireAuth({ to = '/login' }) {
  const location = useLocation()
  if (!auth.token) return <Navigate to={to} replace state={{ from: location.pathname }} />
  return <Outlet />
}