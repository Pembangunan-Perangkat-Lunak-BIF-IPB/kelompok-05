import { useState } from 'react'
import { Link } from 'react-router-dom'
import { viewedFiles } from '../lib/api'
import './pages.css'

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('id-ID') : '-')

// Riwayat Berkas: berkas publik yang pernah dibuka di peramban ini
export default function PublicHistory() {
  const [rows, setRows] = useState(() => viewedFiles.list())

  return (
    <div className="page">
      <header>
        <h1>Riwayat Berkas</h1>
        <p className="muted">Berkas publik yang pernah Anda buka di peramban ini. Riwayat tidak disimpan di server.</p>
      </header>

      <section className="card">
        <div className="row-between">
          <span className="muted">{rows.length} berkas</span>
          <button className="btn" disabled={!rows.length} onClick={() => { viewedFiles.clear(); setRows([]) }}>Hapus riwayat</button>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>ID</th><th>Sampel</th><th>Dibuka</th><th></th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.run_id}>
                  <td>{r.run_id}</td>
                  <td>{r.sample_name ?? '-'}</td>
                  <td>{fmt(r.viewed_at)}</td>
                  <td><Link to={`/public/${r.run_id}/result`}>Buka lagi</Link></td>
                </tr>
              ))}
              {!rows.length && <tr><td colSpan={4}>Belum ada riwayat. Buka berkas dari <Link to="/public">Berkas Publik</Link>.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
