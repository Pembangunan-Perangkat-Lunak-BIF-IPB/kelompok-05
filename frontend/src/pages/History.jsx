import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getHistory } from '../lib/api'
import './pages.css'

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('id-ID') : '-')

export default function History() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let stop = false
    getHistory()
      .then((d) => {
        if (stop) return
        setRows([...d].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at))))
      })
      .catch((err) => { if (!stop) setError(err.message) })
    return () => { stop = true }
  }, [])

  return (
    <div className="page">
      <header>
        <h1>Riwayat analisis</h1>
        <p className="muted">Daftar analisis yang pernah Anda unggah dan jalankan.</p>
      </header>

      {error && <p className="msg bad" role="alert">{error}</p>}

      <section className="card">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>ID</th><th>Sampel</th><th>Status</th><th>Visibilitas</th><th>Dibuat</th><th>Selesai</th><th></th></tr>
            </thead>
            <tbody>
              {rows?.map((r) => {
                const finished = r.status === 'COMPLETED'
                return (
                  <tr key={r.run_id}>
                    <td>{r.run_id}</td>
                    <td>{r.sample_name}</td>
                    <td>{r.status}</td>
                    <td>{r.visibility}</td>
                    <td>{fmt(r.created_at)}</td>
                    <td>{fmt(r.completed_at)}</td>
                    <td>
                      <Link to={`/analysis/${r.run_id}/${finished ? 'result' : 'progress'}`}>
                        {finished ? 'Lihat hasil' : 'Lihat progres'}
                      </Link>
                    </td>
                  </tr>
                )
              })}
              {rows && !rows.length && (
                <tr><td colSpan={7}>Belum ada analisis. <Link to="/analysis/new">Mulai analisis baru</Link></td></tr>
              )}
              {!rows && !error && <tr><td colSpan={7}>Memuat…</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}