import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { auth, login } from '../lib/api'
import './pages.css'
import './auth.css'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [busy, setBusy] = useState(false)

  if (auth.token) return <Navigate to="/guide" replace />

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setPending(false)
    if (!email.trim() || !password) {
      setError('Email dan kata sandi wajib diisi.')
      return
    }
    setBusy(true)
    try {
      await login(email.trim(), password)
      navigate(location.state?.from ?? '/guide', { replace: true })
    } catch (err) {
      setPending(err.code === 'PENDING_APPROVAL')
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={onSubmit} noValidate>
        <div className="brand-mark">VarEscape</div>
        <h1>Login Peneliti</h1>
        <p className="muted">Masuk untuk mengunggah berkas dan menjalankan analisis.</p>

        <label htmlFor="email">Email</label>
        <input id="email" type="email" className="input" autoComplete="username"
          value={email} onChange={(e) => setEmail(e.target.value)} placeholder="peneliti@ipb.ac.id" />

        <label htmlFor="password">Kata sandi</label>
        <input id="password" type="password" className="input" autoComplete="current-password"
          value={password} onChange={(e) => setPassword(e.target.value)} />

        {error && <p className={`msg ${pending ? 'warn' : 'bad'}`} role="alert">{error}</p>}

        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? 'Memeriksa…' : 'Masuk'}
        </button>
        <p className="auth-foot">Belum punya akun? <Link to="/register">Daftar</Link></p>
      </form>
    </div>
  )
}