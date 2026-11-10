import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPublicAnalyses } from '../lib/api'
import Icon from '../components/Icon'
import './pages.css'

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' }) : '-')

// Katalog Berkas Publik: hasil run berstatus PUBLIC (read-only).
// Backend mengembalikan daftar run, bukan daftar berkas, jadi satu baris = satu run.
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

  const totalVariants = (rows ?? []).reduce((n, r) => n + (Number(r.total_variants) || 0), 0)

  return (
    <>
      <h1 className="page-title" style={{ fontSize: 22, fontWeight: 700, color: 'var(--navy)' }}>Katalog Berkas Publik</h1>
      <p className="page-sub" style={{ fontSize: 13 }}>Repositori hasil analisis varian yang telah dipublikasikan untuk akses publik.</p>

      <div className="cat-stats">
        <div className="stat"><small>Total publikasi berkas</small><div>{rows ? rows.length : '–'} <span className="chip" style={{ color: 'var(--teal-d)' }}>READ ONLY</span></div></div>
        <div className="stat"><small>VCF variant sets</small><div>{rows ? totalVariants : '–'} <span style={{ fontSize: 24 }}>Calls</span> <span className="chip blue" style={{ color: '#004881', background: '#d3e4ff' }}>PASS ONLY</span></div></div>
        <div className="stat"><small>Laporan paket ZIP</small><div>{rows ? rows.length : '–'} <span style={{ fontSize: 24 }}>FILE</span> <span className="chip">CHECKSUM OK</span></div></div>
      </div>

      <div className="banner-info">
        <Icon name="info" size={14} />
        <span>Hanya berkas hasil dari run berstatus Public yang tampil di katalog ini. Pengguna dengan peran Pembaca memiliki akses read-only dan dapat mengunduh artefak untuk verifikasi independen.</span>
      </div>

      {error && <p className="alert error" role="alert" style={{ marginTop: 16 }}>{error}</p>}

      <div className="filter">
        <label className="search"><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari nama file atau Run ID..." aria-label="Cari berkas" /><Icon name="search" size={12} /></label>
        <span className="muted" style={{ fontSize: 11 }}>Menampilkan {shown.length} berkas rilis</span>
      </div>

      <div className="files">
        <div className="files-row th"><div>Nama berkas</div><div style={{ textAlign: 'right' }}>Varian</div><div>Run ID terkait</div><div>Sampel</div><div>Tanggal rilis</div><div style={{ textAlign: 'right' }}>Aksi</div></div>
        {rows === null && !error && <div className="empty">Memuat berkas publik…</div>}
        {rows && !shown.length && <div className="empty">Belum ada berkas publik.</div>}
        {shown.map((r) => (
          <div className="files-row" key={r.run_id}>
            <div className="fn"><span className="ic"><Icon name="file" size={13} /></span><div><b>{r.run_id}_results</b><small>Hasil analisis varian &amp; immune escape</small></div></div>
            <div style={{ textAlign: 'right', fontSize: 11 }}>{r.total_variants ?? '-'}</div>
            <div className="runid"><span>{r.run_id}</span><i /></div>
            <div><b style={{ fontSize: 13, fontWeight: 500 }}>{r.sample_name}</b></div>
            <div style={{ fontSize: 12, color: 'var(--ink2)' }}>{fmtDate(r.created_at)}</div>
            <div style={{ textAlign: 'right' }}><Link className="btn-open" to={`/public/${r.run_id}/result`}><Icon name="file" size={11} /> Buka hasil</Link></div>
          </div>
        ))}
      </div>

    </>
  )
}
