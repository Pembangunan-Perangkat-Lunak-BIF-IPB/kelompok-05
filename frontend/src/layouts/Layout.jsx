import { NavLink, Outlet } from 'react-router-dom'

export default function Layout({ role, links }) {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">VarEscape</div>
        <nav>
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) => (isActive ? 'nav active' : 'nav')}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <NavLink to="/register" className="nav logout">Keluar</NavLink>
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