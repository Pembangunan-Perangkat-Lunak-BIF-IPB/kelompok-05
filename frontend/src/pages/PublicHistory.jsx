import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { viewedFiles } from '../lib/api'
import Icon from '../components/Icon'
import './history.css'

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' }) : '-')

// Riwayat Berkas: berkas publik yang pernah dibuka di peramban ini (tanpa akun)
export default function PublicHistory() {
  const [rows, setRows] = useState(() => viewedFiles.list())
  const [q, setQ] = useState('')
  const shown = useMemo(() => rows.filter((r) => !q.trim() || `${r.run_id} ${r.sample_name}`.toLowerCase().includes(q.trim().toLowerCase())), [rows, q])

  return (
    <>
      <div className="hh"><div><h1>Riwayat Berkas</h1><p>Menampilkan berkas publik yang pernah Anda buka.</p></div>
        <div className="mini"><div><small>LAPORAN DIBUKA</small><b>{rows.length} Berkas</b></div></div></div>
      <div className="bar-f">
        <div className="grp"><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari berdasarkan Run ID atau nama sampel..." aria-label="Cari" style={{ maxWidth: 420 }} /></div>
        <button className="a-btn" onClick={() => { setQ('') }}><Icon name="refresh" size={11} /> Reset Filter</button>
        <button className="a-btn" disabled={!rows.length} onClick={() => { viewedFiles.clear(); setRows([]) }}><Icon name="trash" size={11} /> Hapus riwayat</button>
      </div>
      <div className="tbl-card">
        <div className="sec-h" style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}><h2 style={{ fontSize: 15 }}><Icon name="clock" size={14} /> Daftar Riwayat Analisis</h2><small className="muted">Menampilkan {shown.length} dari {rows.length} berkas</small></div>
        <div className="h-row th" style={{ gridTemplateColumns: '1.4fr 2fr 1.6fr 1.6fr' }}><span>RUN ID</span><span>SAMPEL</span><span>DIBUKA</span><span>AKSI</span></div>
        {!shown.length && <div className="empty">Belum ada riwayat. Buka berkas dari <Link to="/public">Berkas Publik</Link>.</div>}
        {shown.map((r) => (
          <div className="h-row" style={{ gridTemplateColumns: '1.4fr 2fr 1.6fr 1.6fr' }} key={r.run_id}>
            <b style={{ color: 'var(--teal-d)' }}>{r.run_id}</b><b>{r.sample_name}</b><span className="d">{fmt(r.viewed_at)}</span>
            <div className="acts"><Link className="a-btn pri" style={{ background: 'var(--teal-d)' }} to={`/public/${r.run_id}/result`}><Icon name="file" size={10} /> Detail</Link>
              {/* TODO(backend): unduhan ZIP laporan belum tersedia */}
              <button className="a-btn" disabled title="Unduhan ZIP belum tersedia"><Icon name="download" size={10} /> ZIP</button></div>
          </div>
        ))}
      </div>
    </>
  )
}
