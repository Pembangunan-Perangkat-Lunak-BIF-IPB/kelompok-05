import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPublicAnalyses } from '../lib/api'
import './pages.css'
import '../components/result.css'

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('id-ID') : '-')

// Berkas Publik: katalog hasil berstatus PUBLIC (hanya baca)
export default function PublicFiles() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')

  useEffect(() => {
    let stop = false
    getPublicAnalyses()
      .then((d) => { if (!stop) setRows(Array.isArray(d) ? d : (d.items ?? [])) })
      .catch((err) => { if (!stop) setError(err.message) })
    return () => { stop = true }
  }, [])

  const shown = useMemo(() => {
    const k = q.trim().toLowerCase()
    const list = [...(rows ?? [])].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
    return k ? list.filter((r) => `${r.run_id} ${r.sample_name}`.toLowerCase().includes(k)) : list
  }, [rows, q])

  return (
    <div className="page">
      <header>
        <h1>Berkas Publik</h1>
        <p className="muted">Hasil analisis yang dibagikan Peneliti. Anda dapat melihat dan mengunduh, tetapi tidak dapat mengubah data.</p>
      </header>

      {error && <p className="msg bad" role="alert">{error}</p>}

      <section className="card">
        <label htmlFor="cari" className="muted">Cari berdasarkan ID atau nama sampel</label>
        <input id="cari" className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="mis. VE-C48A" />
      </section>

      {rows === null && !error && <p className="muted">Memuat berkas publik…</p>}

      <div className="grid-2">
        {shown.map((r) => (
          <article key={r.run_id} className="card file-card">
            <div>
              <h3>{r.sample_name}</h3>
              <p className="muted">{r.run_id} · {r.total_variants ?? '-'} varian</p>
              <p className="muted">Dibuat {fmt(r.created_at)}</p>
            </div>
            <Link className="btn btn-primary" to={`/public/${r.run_id}/result`}>Lihat hasil</Link>
          </article>
        ))}
      </div>
      {rows && !shown.length && (
        <p className="card muted">{q ? 'Tidak ada berkas yang cocok dengan pencarian.' : 'Belum ada hasil berstatus PUBLIC.'}</p>
      )}
    </div>
  )
}
