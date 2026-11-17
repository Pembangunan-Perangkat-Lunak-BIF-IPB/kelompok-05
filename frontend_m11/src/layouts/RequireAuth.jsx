
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { auth, session } from '../lib/api'

export default function RequireAuth({
  role = 'RESEARCHER',
  to = '/login',
}) {
  const location = useLocation()

  if (!auth.token) {
    return (
      <Navigate
        to={to}
        replace
        state={{ from: location.pathname }}
      />
    )
  }

  const userRole = String(session.user?.role ?? '').toUpperCase()
  const expectedRole = String(role).toUpperCase()

  if (!userRole || userRole !== expectedRole) {
    // Role berbeda: jangan izinkan melihat halaman.
    // Tidak menghapus sesi agar pengguna tidak logout
    // hanya karena mengakses URL yang salah.
    const destination =
      userRole === 'ADMIN'
        ? '/admin/accounts'
        : userRole === 'RESEARCHER'
          ? '/guide'
          : '/public'

    return <Navigate to={destination} replace />
  }

  return <Outlet />
}
