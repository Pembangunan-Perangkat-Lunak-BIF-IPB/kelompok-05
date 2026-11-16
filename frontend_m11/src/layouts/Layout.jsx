import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { lastRun, logout, session, viewedFiles } from '../lib/api'
import logo from '../assets/logo.png'
import { NAV, ROLE_LABEL } from './nav'

// variant: 'researcher' | 'reader' | 'admin'
export default function Layout({ variant = 'researcher' }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  // Run yang sedang dibuka (dari URL) diutamakan dibanding run terakhir di localStorage,
  // sehingga membuka hasil dari Riwayat langsung menandai tab "Hasil" (bukan "Riwayat analisis").
  const openRun = /^\/analysis\/([^/]+)\/(progress|result)/.exec(pathname)
  const last = openRun?.[1] ?? lastRun.get()
  const user = session.user
  const items = NAV[variant].map((l) => {
    if (l.to === '/progress') return { ...l, to: last ? `/analysis/${last}/progress` : '/history', active: openRun?.[2] === 'progress' }
    if (l.to === '/result') return { ...l, to: last ? `/analysis/${last}/result` : '/history', active: openRun?.[2] === 'result' }
    if (l.to === '/public/result') { const v = viewedFiles.list()[0]; return { ...l, to: v ? `/public/${v.run_id}/result` : '/public', active: /^\/public\/[^/]+\/result/.test(pathname) } }
    return l
  })
  const name = user?.full_name ?? user?.name ?? user?.email ?? null
  const inst = user?.institution ?? ''

  function out() {
    logout()
    navigate(variant === 'admin' ? '/admin/login' : variant === 'reader' ? '/public/login' : '/login')
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sb-brand"><img src={logo} alt="" />VarEscape</div>
        <nav className="sb-nav">
          {items.map((l) => (
            <NavLink key={l.label} to={l.to} end={l.end} className={({ isActive }) => `sb-link${(l.active ?? isActive) ? ' active' : ''}`}>{l.label}</NavLink>
          ))}
        </nav>
        <div className="sb-foot">
          <small>v1.0.0</small>
          <button className="sb-out" onClick={out}>Keluar</button>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <span className="role-badge">{ROLE_LABEL[variant]}</span>
          {variant !== 'reader' && name && <div className="user"><b>{name}</b>{inst && <small>{inst}</small>}</div>}
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  )
}
