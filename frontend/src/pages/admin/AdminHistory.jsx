import { useEffect, useMemo, useState } from 'react'
import { getAdminAnalyses } from '../../lib/api'
import { pick } from '../../lib/risk'
import Icon from '../../components/Icon'
import '../history.css'

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' }) : '-')
const STATUS = { COMPLETED: ['SELESAI', ''], FAILED: ['GAGAL', 'bad'], RUNNING: ['BERJALAN', 'run'], PROCESSING: ['BERJALAN', 'run'], QUEUED: ['ANTRI', 'wait'], PENDING: ['MENUNGGU', 'wait'], UPLOADED: ['SIAP', 'wait'] }

// Riwayat hasil analisis seluruh peneliti (Public & Private). Desain mengikuti /public/history.
// TODO(backend): butuh GET /admin/analyses (lihat lib/api.js)
export default function AdminHistory() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [vis, setVis] = useState('ALL')

  useEffect(() => {
    let stop = false
    getAdminAnalyses()
      .then((d) => { if (!stop) setRows([...(Array.isArray(d) ? d : d.items ?? [])].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))) })
      .catch((e) => { if (!stop) { setRows([]); setError(e.status === 404 ? 'Endpoint /admin/analyses belum tersedia di backend (TODO).' : e.message) } })
    return () => { stop = true }
  }, [])

  const shown = useMemo(() => (rows ?? []).filter((r) => {
    if (vis !== 'ALL' && r.visibility !== vis) return false
    return !q.trim() || `${r.run_id} ${r.sample_name} ${pick(r, 'owner_name', 'owner_email') ?? ''}`.toLowerCase().includes(q.trim().toLowerCase())
  }), [rows, q, vis])
  const total = rows?.length ?? 0
  const pub = (rows ?? []).filter((r) => r.visibility === 'PUBLIC').length

  return (
    <>
      <div className="hh">
        <div><h1>Riwayat Analisis Peneliti</h1><p>Menampilkan seluruh hasil analisis para peneliti, baik yang berstatus Public maupun Private.</p></div>
        <div className="mini"><div><small>TOTAL ANALISIS</small><b>{total} Berkas</b> <span>({pub} Public · {total - pub} Private)</span></div></div>
      </div>

      <div className="bar-f">
        <div className="grp">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari berdasarkan Run ID, sampel, atau peneliti..." aria-label="Cari" style={{ maxWidth: 420 }} />
          <select value={vis} onChange={(e) => setVis(e.target.value)} aria-label="Visibilitas"><option value="ALL">Semua Visibilitas</option><option value="PUBLIC">Public</option><option value="PRIVATE">Private</option></select>
        </div>
        <button className="a-btn" onClick={() => { setQ(''); setVis('ALL') }}><Icon name="refresh" size={11} /> Reset Filter</button>
      </div>

      {error && <p className="alert error" role="alert" style={{ marginBottom: 12 }}>{error}</p>}

      <div className="tbl-card">
        <div className="sec-h" style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}><h2 style={{ fontSize: 15 }}><Icon name="clock" size={14} /> Daftar Riwayat Analisis</h2><small className="muted">Menampilkan {shown.length} dari {total} berkas</small></div>
        <div className="h-row th" style={{ gridTemplateColumns: '1.2fr 1.8fr 1.8fr 1.1fr 1.6fr 1.1fr' }}><span>RUN ID</span><span>SAMPEL</span><span>PENELITI</span><span>VISIBILITAS</span><span>TANGGAL ANALISIS</span><span>STATUS</span></div>
        {!rows && !error && <div className="empty">Memuat…</div>}
        {rows && !shown.length && <div className="empty">Belum ada riwayat analisis.</div>}
        {shown.map((r) => {
          const [label, cls] = STATUS[r.status] ?? [r.status ?? '-', 'wait']
          return (
            <div className="h-row" style={{ gridTemplateColumns: '1.2fr 1.8fr 1.8fr 1.1fr 1.6fr 1.1fr' }} key={r.run_id}>
              <b style={{ color: 'var(--teal-d)' }}>{r.run_id}</b>
              <b>{r.sample_name}</b>
              <span className="d" style={{ fontSize: 12 }}>{pick(r, 'owner_name', 'owner_email') ?? '-'}</span>
              <span className={`vis ${r.visibility === 'PUBLIC' ? 'pub' : ''}`}><Icon name={r.visibility === 'PUBLIC' ? 'globe' : 'lock'} size={10} />{r.visibility ?? '-'}</span>
              <span className="d">{fmt(r.created_at)}</span>
              <span className={`sbadge ${cls}`}><i />{label}</span>
            </div>
          )
        })}
      </div>
    </>
  )
}
