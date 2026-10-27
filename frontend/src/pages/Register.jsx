import { useState } from 'react'
import { Link } from 'react-router-dom'
import { register } from '../lib/api'
import './pages.css'
import './auth.css'

const EMPTY = {
  full_name: '', email: '', institution: '', phone_number: '',
  registration_reason: '', password: '', confirm: '',
}

export default function Register() {
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [done, setDone] = useState(null)
  const [busy, setBusy] = useState(false)

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  function validate() {
    if (!form.full_name.trim()) return 'Nama lengkap wajib diisi.'
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) return 'Format email tidak valid.'
    if (form.password.length < 8) return 'Kata sandi minimal 8 karakter.'
    if (form.password !== form.confirm) return 'Konfirmasi kata sandi tidak sama.'
    return ''
  }

  async function onSubmit(e) {
    e.preventDefault()
    const problem = validate()
    if (problem) { setError(problem); return }
    setBusy(true)
    setError('')
    try {
      const data = await register({
        email: form.email.trim(),
        password: form.password,
        full_name: form.full_name.trim(),
        institution: form.institution.trim() || null,
        phone_number: form.phone_number.trim() || null,
        registration_reason: form.registration_reason.trim() || null,
        role: 'RESEARCHER',
      })
      setDone(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    const waiting = done.status_aktif === 'PENDING_APPROVAL'
    return (
      <div className="auth-wrap">
        <div className="auth-card">
          <div className="brand-mark">VarEscape</div>
          <h1>Registrasi berhasil</h1>
          <p className={`msg ${waiting ? 'warn' : 'ok'}`} role="status">
            {waiting
              ? 'Akun Anda menunggu persetujuan admin. Anda dapat login setelah akun disetujui.'
              : 'Akun Anda sudah dibuat. Silakan login.'}
          </p>
          <Link className="btn btn-primary" to="/login">Ke halaman login</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={onSubmit} noValidate>
        <div className="brand-mark">VarEscape</div>
        <h1>Daftar Akun Baru</h1>

        <label htmlFor="full_name">Nama lengkap</label>
        <input id="full_name" className="input" value={form.full_name} onChange={set('full_name')} />

        <label htmlFor="email">Email</label>
        <input id="email" type="email" className="input" autoComplete="username"
          value={form.email} onChange={set('email')} />

        <label htmlFor="institution">Institusi <span className="tag">Opsional</span></label>
        <input id="institution" className="input" value={form.institution} onChange={set('institution')} />

        <label htmlFor="phone_number">Nomor telepon <span className="tag">Opsional</span></label>
        <input id="phone_number" className="input" value={form.phone_number} onChange={set('phone_number')} />

        <label htmlFor="registration_reason">Alasan pendaftaran <span className="tag">Opsional</span></label>
        <input id="registration_reason" className="input" value={form.registration_reason}
          onChange={set('registration_reason')} />

        <label htmlFor="password">Kata sandi</label>
        <input id="password" type="password" className="input" autoComplete="new-password"
          value={form.password} onChange={set('password')} />

        <label htmlFor="confirm">Ulangi kata sandi</label>
        <input id="confirm" type="password" className="input" autoComplete="new-password"
          value={form.confirm} onChange={set('confirm')} />

        {error && <p className="msg bad" role="alert">{error}</p>}

        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? 'Mendaftarkan…' : 'Daftar'}
        </button>
        <p className="auth-foot">Sudah punya akun? <Link to="/login">Login</Link></p>
      </form>
    </div>
  )
}