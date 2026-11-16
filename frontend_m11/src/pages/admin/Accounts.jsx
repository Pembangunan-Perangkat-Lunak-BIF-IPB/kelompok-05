import { useCallback, useEffect, useMemo, useState } from 'react'
import { getAccounts, setAccountStatus } from '../../lib/api'
import Icon from '../../components/Icon'
import '../history.css'

const ini = (n = '?') => n.split(/\s+/).filter(Boolean).slice(0, 2).map((s) => s[0]).join('').toUpperCase()
const fmt = (iso) => (iso ? new Date(iso).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' }) : '-')
const norm = (u) => ({ ...u, id: u.id ?? u.user_id ?? u.email, name: u.full_name ?? u.name ?? u.email, status: String(u.status_aktif ?? u.status ?? '').toUpperCase() })

// TODO(backend): GET /admin/accounts dan PATCH .../status belum ada di kode referensi (lihat lib/api.js)
export default function Accounts() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [q, setQ] = useState('')

  const load = useCallback(() => {
    getAccounts().then((d) => { setRows((Array.isArray(d) ? d : d.items ?? []).map(norm)); setError('') })
      .catch((e) => { setRows([]); setError(e.status === 404 ? 'Endpoint /admin/accounts belum tersedia di backend (TODO).' : e.message) })
  }, [])
  useEffect(load, [load])

  async function change(u, status) {
    setBusy(u.id); setError('')
    try { await setAccountStatus(u.id, status); load() } catch (e) { setError(e.message) } finally { setBusy('') }
  }

  const pending = (rows ?? []).filter((u) => u.status === 'PENDING_APPROVAL')
  const users = useMemo(() => (rows ?? []).filter((u) => u.status !== 'PENDING_APPROVAL' && u.status !== 'REJECTED')
    .filter((u) => !q.trim() || `${u.name} ${u.email}`.toLowerCase().includes(q.trim().toLowerCase())), [rows, q])

  return (
    <>
      <div className="hh">
        <div><h1 style={{ fontSize: 22 }}>Manajemen Akun &amp; Otorisasi Pengguna</h1><p>Kelola antrean persetujuan pendaftaran akun baru dan status akses pengguna terdaftar.</p></div>
        <div className="ad-kpis">
          <div className="ad-kpi"><span className="ic"><Icon name="user" size={16} /></span><div><small>ANTREAN BARU</small><b>{pending.length} Permohonan</b></div></div>
          <div className="ad-kpi"><span className="ic" style={{ background: 'rgba(204,226,250,.4)', color: '#4c6075' }}><Icon name="building" size={16} /></span><div><small>TOTAL TERDAFTAR</small><b>{rows?.length ?? 0} Akun</b></div></div>
        </div>
      </div>
      {error && <p className="alert error" role="alert" style={{ marginTop: 16 }}>{error}</p>}

      <section className="sec">
        <div className="sec-h q"><div><h2><Icon name="shield-check" size={14} /> Permohonan Pendaftaran Akun Baru <span className="cpill">{pending.length} PENDING</span></h2><p>Permohonan akun baru yang memerlukan verifikasi identitas institusi sebelum diaktifkan.</p></div></div>
        <div className="u-row q th"><span>NAMA PEMOHON</span><span>EMAIL INSTITUSI</span><span>TANGGAL PENGAJUAN</span><span>AKSI OTORISASI</span></div>
        {!rows && <div className="empty">Memuat…</div>}
        {rows && !pending.length && <div className="empty">Tidak ada permohonan menunggu.</div>}
        {pending.map((u) => (
          <div className="u-row q" key={u.id}>
            <div className="who"><span className="av">{ini(u.name)}</span><div><b>{u.name}</b><small>{u.institution ?? ''}</small></div></div>
            <span>{u.email}</span><span style={{ fontSize: 12 }}>{fmt(u.created_at)}</span>
            <div className="row" style={{ gap: 8 }}>
              <button className="btn-ok" disabled={busy === u.id} onClick={() => change(u, 'ACTIVE')}><Icon name="check" size={12} /> Setujui</button>
              <button className="btn-no" disabled={busy === u.id} onClick={() => change(u, 'REJECTED')}><Icon name="x" size={10} /> Tolak</button>
            </div>
          </div>
        ))}
      </section>

      <section className="sec">
        <div className="sec-h">
          <div><h2><Icon name="user" size={13} /> Daftar Akun Terdaftar</h2><p>Manajemen status operasional pengguna aktif dan nonaktif di lingkungan platform VarEscape.</p></div>
          <div className="row" style={{ gap: 8 }}><input className="search2" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari nama atau email pengguna" aria-label="Cari pengguna" /></div>
        </div>
        <div className="u-row th"><span>NAMA PENGGUNA</span><span>EMAIL INSTITUSI</span><span>TANGGAL TERDAFTAR</span><span>STATUS</span><span>AKSI</span></div>
        {rows && !users.length && <div className="empty">Tidak ada pengguna.</div>}
        {users.map((u) => {
          const active = u.status === 'ACTIVE'
          return (
            <div className="u-row" key={u.id}>
              <div className="who"><span className={`av`}>{ini(u.name)}</span><div><b>{u.name}</b><small>{u.institution ?? ''}</small></div></div>
              <span style={{ fontSize: 12 }}>{u.email}</span><span style={{ fontSize: 12 }}>{fmt(u.created_at)}</span>
              <span className={`stt ${active ? '' : 'off'}`}><i />{active ? 'AKTIF' : 'NONAKTIF'}</span>
              {active
                ? <button className="btn-off" disabled={busy === u.id} onClick={() => change(u, 'SUSPENDED')}><Icon name="x2" size={12} /> Nonaktifkan</button>
                : <button className="btn-on" disabled={busy === u.id} onClick={() => change(u, 'ACTIVE')}><Icon name="refresh" size={11} /> Aktifkan Kembali</button>}
            </div>
          )
        })}
        <div className="tbl-foot"><span>Menampilkan {users.length} dari {(rows ?? []).filter((u) => u.status !== 'PENDING_APPROVAL').length} pengguna terdaftar</span></div>
      </section>

      <div className="protocol"><span className="ic"><Icon name="lock" size={13} /></span><div><h3>Protokol Penegakan Akses &amp; Integritas Akun</h3>
        <p>Perubahan status akun langsung memengaruhi hak akses login. Akun nonaktif akan ditolak saat mencoba login dengan pesan peringatan keamanan dan penghentian sesi otomatis pada API gateway.</p></div></div>
    </>
  )
}
