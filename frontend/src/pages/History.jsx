import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getHistory } from '../lib/api'
import Icon from '../components/Icon'
import './history.css'

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('id-ID', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-')
const STATUS = {
  COMPLETED: ['SELESAI', ''], FAILED: ['GAGAL', 'bad'], RUNNING: ['BERJALAN', 'run'], PROCESSING: ['BERJALAN', 'run'], QUEUED: ['ANTRI', 'wait'], PENDING: ['MENUNGGU', 'wait'], UPLOADED: ['SIAP', 'wait'],
}

export default function History() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [st, setSt] = useState('ALL')
  const [vis, setVis] = useState('ALL')

  useEffect(() => {
    let stop = false
    getHistory()
      .then((d) => { if (!stop) setRows([...d].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))) })
      .catch((err) => { if (!stop) setError(err.message) })
    return () => { stop = true }
  }, [])

  const shown = useMemo(() => (rows ?? []).filter((r) => {
    if (st !== 'ALL' && r.status !== st) return false
    if (vis !== 'ALL' && r.visibility !== vis) return false
    return !q.trim() || `${r.run_id} ${r.sample_name}`.toLowerCase().includes(q.trim().toLowerCase())
  }), [rows, q, st, vis])

  const done = (rows ?? []).filter((r) => r.status === 'COMPLETED').length
  const pct = rows?.length ? Math.round((done / rows.length) * 100) : 0

  return (
    <>
      <div className="hh">
        <div>
          <h1><span className="ic-sq"><Icon name="clock" size={15} /></span>Riwayat Analisis</h1>
          <p>Daftar riwayat eksekusi pipeline bioinformatika. Filter sampel berdasarkan kriteria akses dan status mutasi.</p>
        </div>
        <div className="mini"><div><small>TOTAL RUN BERHASIL</small><b>{pct}%</b> <span>({done}/{rows?.length ?? 0} Selesai)</span></div><span className="ok"><Icon name="check" size={15} /></span></div>
      </div>

      <div className="bar-f">
        <div className="grp">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari Run ID, mis. VE-0142" aria-label="Cari" />
          <select value={st} onChange={(e) => setSt(e.target.value)} aria-label="Status"><option value="ALL">Semua Status</option><option value="COMPLETED">Selesai</option><option value="RUNNING">Berjalan</option><option value="FAILED">Gagal</option></select>
          <select value={vis} onChange={(e) => setVis(e.target.value)} aria-label="Visibilitas"><option value="ALL">Semua Visibilitas</option><option value="PRIVATE">Private</option><option value="PUBLIC">Public</option></select>
        </div>
        <Link to="/public" className="btn-pub"><Icon name="globe" size={13} /> Berkas publik</Link>
      </div>

      {error && <p className="alert error" role="alert" style={{ marginBottom: 12 }}>{error}</p>}

      <div className="tbl-card">
        <div className="h-row th"><span>RUN ID</span><span>SAMPEL</span><span>TANGGAL EKSEKUSI</span><span>VISIBILITAS</span><span>VARIAN TERDETEKSI</span><span>STATUS</span><span>AKSI</span></div>
        {!rows && !error && <div className="empty">Memuat…</div>}
        {rows && !shown.length && <div className="empty">{rows.length ? 'Tidak ada analisis yang cocok.' : <>Belum ada analisis. <Link to="/analysis/new">Mulai analisis baru</Link></>}</div>}
        {shown.map((r) => {
          const [label, cls] = STATUS[r.status] ?? [r.status, 'wait']
          const finished = r.status === 'COMPLETED'
          const failed = r.status === 'FAILED'
          return (
            <div className={`h-row ${failed ? 'fail' : ''}`} key={r.run_id}>
              <b style={{ color: failed ? 'var(--bad)' : 'var(--teal)' }}>{r.run_id}</b>
              <div><b>{r.sample_name}</b></div>
              <span className="d">{fmt(r.created_at)}</span>
              <span className={`vis ${r.visibility === 'PUBLIC' ? 'pub' : ''}`}><Icon name={r.visibility === 'PUBLIC' ? 'globe' : 'lock'} size={10} />{r.visibility ?? '-'}</span>
              <div className="cnt">{r.total_variants != null ? <span>{r.total_variants}<br />PASS</span> : <span className="muted" style={{ background: 'none' }}>-</span>}</div>
              <span className={`sbadge ${cls}`}><i />{label}</span>
              <div className="acts">
                <Link className="a-btn pri" to={`/analysis/${r.run_id}/${finished ? 'result' : 'progress'}`}>{finished ? 'Buka' : 'Lihat progres'}</Link>
                {/* TODO(backend): unduh VCF & ulangi run belum tersedia di API */}
                {finished && <button className="a-btn" disabled title="Unduhan VCF belum tersedia"><Icon name="download" size={9} /> VCF</button>}
                {failed && <Link className="a-btn" to="/analysis/new">Ulangi</Link>}
              </div>
            </div>
          )
        })}
        <div className="tbl-foot"><span>Menampilkan {shown.length} dari {rows?.length ?? 0} proses analisis</span></div>
      </div>

      <div className="note-card"><span className="ic"><Icon name="check" size={13} /></span><div><b>Kosong: "Belum ada hasil yang dapat ditampilkan."</b><p>Berkas berstatus <b style={{ color: 'var(--teal)' }}>Public</b> dapat diakses langsung oleh peran Pembaca tanpa token otorisasi tambahan. Berkas <b>Private</b> hanya dapat ditelaah oleh Peneliti pemilik berkas dan Administrator Lab.</p></div></div>
    </>
  )
}
