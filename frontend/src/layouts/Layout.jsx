import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { lastRun, logout, session, viewedFiles } from '../lib/api'
import logo from '../assets/logo.png'
import { NAV, ROLE_LABEL } from './nav'

// variant: 'researcher' | 'reader' | 'admin'
export default function Layout({ variant = 'researcher' }) {
  useLocation()
  const navigate = useNavigate()
  const last = lastRun.get()
  const user = session.user
  const items = NAV[variant].map((l) => {
    if (l.to === '/progress') return { ...l, to: last ? `/analysis/${last}/progress` : '/history' }
    if (l.to === '/result') return { ...l, to: last ? `/analysis/${last}/result` : '/history' }
    if (l.to === '/public/result') { const v = viewedFiles.list()[0]; return { ...l, to: v ? `/public/${v.run_id}/result` : '/public' } }
    return l
  })
  const name = user?.full_name ?? user?.name ?? user?.email ?? ROLE_LABEL[variant]
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
            <NavLink key={l.label} to={l.to} end={l.end} className={({ isActive }) => `sb-link${isActive && !items.some((o) => o !== l && o.to === l.to && o.end) && !(l.to === '/history' && l.label !== 'Riwayat analisis') && !(l.to === '/public' && l.label === 'Hasil') ? ' active' : ''}`}>{l.label}</NavLink>
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
          {variant !== 'reader' && <div className="user"><b>{name}</b>{inst && <small>{inst}</small>}</div>}
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  )
}
