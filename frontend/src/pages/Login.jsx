import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { auth, errorMessage, login } from '../lib/api'
import Icon from '../components/Icon'
import { AuthShell, Brand, Field, RolePills } from '../components/Auth'

const SUB = 'Platform Analisis Genomik & Immune Escape Mapping'

// Satu komponen untuk tiga layar masuk: Peneliti, Pembaca (guest), Administrator
export default function Login({ role = 'researcher' }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (role === 'researcher' && auth.token) return <Navigate to="/guide" replace />

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const data = await login(email.trim(), password)
      // TODO(backend): pastikan respons login membawa peran pengguna (user.role).
      const r = String(data?.user?.role ?? '').toUpperCase()
      if (role === 'admin' && r && r !== 'ADMIN' && r !== 'ADMINISTRATOR') {
        throw new Error('Akun ini bukan Administrator.')
      }
      navigate(role === 'admin' ? '/admin/accounts' : (location.state?.from ?? '/guide'), { replace: true })
    } catch (err) {
      setError(err.message || errorMessage(null))
      if (role === 'admin') auth.token = null
    } finally {
      setBusy(false)
    }
  }

  if (role === 'reader') {
    return (
      <AuthShell>
        <div className="auth-card">
          <Brand sub={SUB} />
          <RolePills active="reader" />
          <div className="tab-line"><span className="tab">Akses Publik</span></div>
          <div className="access-box">
            <h3>Modus Akses Publik (Read-Only)</h3>
            <ul>
              {['Lihat berkas hasil analisis yang dipublikasikan peneliti', 'Tanpa akun dan tanpa kata sandi', 'Tidak dapat mengunggah atau mengubah data'].map((t) => (
                <li key={t}><Icon name="check-circle" size={14} />{t}</li>
              ))}
            </ul>
          </div>
          <Link to="/public" className="auth-btn"><Icon name="globe" size={14} /> Masuk sebagai Pembaca Publik</Link>
          <p className="auth-alt">Peneliti? <Link to="/login">Masuk dengan akun</Link></p>
          <p className="auth-meta">VarEscape v1.0.0 • Bioinformatika</p>
        </div>
      </AuthShell>
    )
  }

  const admin = role === 'admin'
  return (
    <AuthShell>
      <form className={`auth-card ${admin ? 'wide' : ''}`} onSubmit={onSubmit}>
        <Brand title="VarEscape" sub={admin ? 'Konsol Administrator • Manajemen Akun & Pemantauan Server' : SUB} />
        {!admin && <RolePills active="researcher" />}
        {!admin && <div className="tab-line"><span className="tab">Masuk Akun</span></div>}
        {admin && (
          <div className="access-box">
            <h3>Hak Akses Superuser (Root Admin)</h3>
            <ul>
              {['Verifikasi dan kelola akun peneliti', 'Pantau kesehatan server dan pipeline', 'Semua aktivitas dicatat dalam audit log'].map((t) => (
                <li key={t}><Icon name="shield-check" size={14} />{t}</li>
              ))}
            </ul>
          </div>
        )}
        {error && <p className="auth-err" role="alert">{error}</p>}
        <Field label={admin ? 'Email Administrator / Root ID' : 'Email Akademik / Lembaga'} icon="mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={admin ? 'admin@varescape.id' : 'peneliti@apps.ipb.ac.id'} autoComplete="username" required />
        <Field
          label={admin ? 'Kunci Enkripsi / Token Akses Lab' : 'Kata Sandi'} icon="lock" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••••" autoComplete="current-password" required
        />
        <button className="auth-btn" disabled={busy}>
          {busy ? <span className="spinner" /> : <Icon name="log-in" size={14} />}
          {admin ? 'Masuk ke Dashboard Administrator' : 'Masuk ke Dashboard Peneliti'}
        </button>
        {!admin && <p className="auth-alt">Belum memiliki akun? <Link to="/register">Daftar di sini</Link></p>}
        <p className="auth-meta">VarEscape v1.0.0 • Bioinformatika</p>
      </form>
    </AuthShell>
  )
}
