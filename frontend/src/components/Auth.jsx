import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from './Icon'
import logo from '../assets/logo.png'
import '../pages/auth.css'

export function AuthShell({ children, footer = 'admin@gmail.com' }) {
  return (
    <div className="auth">
      <Link to="/" className="auth-top"><img src={logo} alt="" /> VarEscape</Link>
      <div className="auth-body">{children}</div>
      <p className="auth-foot-text">{footer}</p>
    </div>
  )
}

export function Brand({ title = 'VarEscape', sub }) {
  return (
    <>
      <img className="auth-logo" src={logo} alt="VarEscape" />
      <h1 className="auth-title">{title}</h1>
      <p className="auth-sub">{sub}</p>
    </>
  )
}

export function Field({ label, icon, type = 'text', right, hint, value, onChange, placeholder, autoComplete, required }) {
  const [show, setShow] = useState(false)
  const pw = type === 'password'
  const id = `f-${label.replace(/\W+/g, '-').toLowerCase()}`
  return (
    <div className="field">
      <div className="field-head"><label htmlFor={id}>{label}</label>{right}</div>
      <div className="input-wrap">
        {icon && <Icon name={icon} size={15} />}
        <input id={id} type={pw && show ? 'text' : type} value={value} onChange={onChange} placeholder={placeholder} autoComplete={autoComplete} required={required} />
        {pw && (
          <button type="button" className="eye" onClick={() => setShow((s) => !s)} aria-label={show ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi'}>
            <Icon name={show ? 'eye-off' : 'eye'} size={15} />
          </button>
        )}
      </div>
      {hint && <span className="hint">{hint}</span>}
    </div>
  )
}

export function RolePills({ active }) {
  return (
    <div className="role-pills">
      <Link to="/login" className={`role-pill ${active === 'researcher' ? 'active' : ''}`}>Log in Peneliti</Link>
      <Link to="/public/login" className={`role-pill ${active === 'reader' ? 'active' : ''}`}>Log in Guest</Link>
    </div>
  )
}
