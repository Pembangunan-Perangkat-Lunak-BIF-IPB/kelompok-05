import { useState } from 'react'
import { Link } from 'react-router-dom'
import { register } from '../lib/api'
import Icon from '../components/Icon'
import { AuthShell, Brand, Field } from '../components/Auth'

const EMPTY = { full_name: '', email: '', institution: '', password: '', confirm: '' }

function strength(p) {
  let s = 0
  if (p.length >= 8) s++
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) s++
  if (/\d/.test(p)) s++
  if (/[^A-Za-z0-9]/.test(p)) s++
  return s
}
const LABEL = ['Belum diisi', 'Lemah', 'Cukup', 'Baik', 'Kuat']

export default function Register() {
  const [form, setForm] = useState(EMPTY)
  const [agree, setAgree] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const score = strength(form.password)

  function validate() {
    if (!form.full_name.trim()) return 'Nama lengkap wajib diisi.'
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) return 'Format email tidak valid.'
    if (form.password.length < 8) return 'Kata sandi minimal 8 karakter.'
    if (form.password !== form.confirm) return 'Konfirmasi kata sandi tidak sama.'
    if (!agree) return 'Anda harus menyetujui kebijakan tata kelola data.'
    return ''
  }

  async function onSubmit(e) {
    e.preventDefault()
    const problem = validate()
    if (problem) return setError(problem)
    setBusy(true); setError('')
    try {
      setDone(await register({
        email: form.email.trim(), password: form.password, full_name: form.full_name.trim(),
        institution: form.institution.trim() || null, phone_number: null, registration_reason: null, role: 'RESEARCHER',
      }))
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  if (done) {
    const waiting = done.status_aktif === 'PENDING_APPROVAL'
    return (
      <AuthShell>
        <div className="auth-card xl">
          <Brand title="Registrasi berhasil" sub="" />
          <p className="auth-ok" role="status">
            {waiting ? 'Akun Anda menunggu persetujuan administrator. Anda baru dapat masuk setelah diverifikasi.' : 'Akun Anda aktif. Silakan masuk.'}
          </p>
          <Link className="auth-btn" to="/login">Ke halaman masuk</Link>
        </div>
      </AuthShell>
    )
  }

  return (
    <AuthShell>
      <form className="auth-card xl" onSubmit={onSubmit}>
        <Brand sub="Platform Analisis Genomik & Immune Escape Mapping" />
        <div className="role-pills" style={{ justifyContent: 'center' }}><span className="role-pill active">Pendaftaran Peneliti</span></div>
        <div className="tab-line"><span className="tab">Daftar di sini</span></div>
        <div className="access-box">
          <h3>Verifikasi Berjenjang</h3>
          <ul><li><Icon name="info" size={14} />Akun baru berstatus menunggu persetujuan administrator sebelum dapat dipakai masuk.</li></ul>
        </div>
        {error && <p className="auth-err" role="alert">{error}</p>}
        <Field label="Nama Lengkap" icon="user" value={form.full_name} onChange={set('full_name')} placeholder="Nama sesuai identitas akademik" autoComplete="name" required />
        <Field label="Email Akademik / Lembaga" icon="mail" type="email" value={form.email} onChange={set('email')} placeholder="nama@apps.ipb.ac.id" hint="Gunakan email institusi agar verifikasi lebih cepat." autoComplete="email" required />
        <Field label="Institusi" icon="building" value={form.institution} onChange={set('institution')} placeholder="Institut Pertanian Bogor" autoComplete="organization" />
        <div className="cols2">
          <Field label="Kata Sandi" icon="lock" type="password" value={form.password} onChange={set('password')} placeholder="Minimal 8 karakter" autoComplete="new-password" required />
          <Field label="Konfirmasi Kata Sandi" icon="lock" type="password" value={form.confirm} onChange={set('confirm')} placeholder="Ulangi kata sandi" autoComplete="new-password" required />
        </div>
        <div style={{ margin: '-4px 0 14px' }}>
          <div className="meter">{[1, 2, 3, 4].map((i) => <i key={i} className={score >= i ? 'on' : ''} />)}</div>
          <div className="meter-row"><span>Kekuatan Kata Sandi: {LABEL[score]}</span><span>Minimal 8 karakter &amp; simbol</span></div>
        </div>
        <label className="check">
          <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
          Saya menyetujui Kebijakan Tata Kelola Data Genomik Klinis dan Kode Etik Bioinformatika VarEscape.
        </label>
        <button className="auth-btn" disabled={busy}>{busy && <span className="spinner" />} Ajukan Pendaftaran Akun</button>
        <p className="auth-alt">Sudah memiliki akun terverifikasi? <Link to="/login">Masuk di sini</Link></p>
      </form>
    </AuthShell>
  )
}
