import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { lastRun, logout } from '../lib/api'

export default function Layout({ role, links }) {
  useLocation()
  const last = lastRun.get()
  const items = links
    .filter((l) => !l.to.includes(':last') || last)
    .map((l) => ({ ...l, to: l.to.replace(':last', last ?? '') }))

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">VarEscape</div>
        <nav>
          {items.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) => (isActive ? 'nav active' : 'nav')}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <NavLink to="/login" className="nav logout" onClick={logout}>Keluar</NavLink>
      </aside>
      <div className="main">
        <header className="header">{role}</header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}