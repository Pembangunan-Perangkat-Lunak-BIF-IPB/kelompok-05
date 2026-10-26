import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getStatus } from '../lib/api'
import './pages.css'

const POLL_MS = 3000
const DONE = ['COMPLETED', 'FAILED']

export default function Progress() {
  const { runId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let stop = false
    let timer

    async function tick() {
      try {
        const d = await getStatus(runId)
        if (stop) return
        setData(d)
        setError('')
        if (!DONE.includes(d.status)) timer = setTimeout(tick, POLL_MS)
      } catch (err) {
        if (stop) return
        setError(err.message)
        timer = setTimeout(tick, POLL_MS * 2)
      }
    }

    tick()
    return () => { stop = true; clearTimeout(timer) }
  }, [runId])

  const stations = data?.stations_status_list ?? data?.stations ?? []

  return (
    <div className="page">
      <header>
        <h1>Progres analisis {runId}</h1>
        <p className="muted">
          {data ? <>Sampel <strong>{data.sample_name}</strong> · status <strong>{data.status}</strong></> : 'Memuat status…'}
        </p>
      </header>

      {error && <p className="msg bad" role="alert">{error}</p>}

      <section className="card">
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Stasiun</th><th>Tahap</th><th>Status</th></tr></thead>
            <tbody>
              {stations.map((s) => (
                <tr key={s.station}>
                  <td>{s.station}</td>
                  <td>{s.name}</td>
                  <td>{s.status}</td>
                </tr>
              ))}
              {!stations.length && <tr><td colSpan={3}>-</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card row-between">
        <Link className="btn" to="/analysis/new">Analisis baru</Link>
        <Link className="btn btn-primary" to={`/analysis/${runId}/result`}>Lihat hasil</Link>
      </section>
    </div>
  )
}
