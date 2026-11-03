import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getStatus, lastRun } from '../lib/api'
import './pages.css'
import '../components/result.css'

const POLL_MS = 3000
const DONE = ['COMPLETED', 'FAILED']

function groupLogs(logs) {
  const map = new Map()
  logs.forEach((l) => {
    const k = l.station_number ?? '?'
    map.set(k, [...(map.get(k) ?? []), l])
  })
  return [...map.entries()].sort((a, b) => Number(a[0]) - Number(b[0]))
}

const stationName = (stations, num) => stations.find((s) => String(s.station) === String(num))?.name

export default function Progress() {
  const { runId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let stop = false
    let timer
    lastRun.set(runId)

    async function tick() {
      try {
        const d = await getStatus(runId)
        if (stop) return
        setData(d)
        setError('')
        if (!DONE.includes(d.overall_status ?? d.status)) timer = setTimeout(tick, POLL_MS)
      } catch (err) {
        if (stop) return
        setError(err.message)
        if (err.status !== 404) timer = setTimeout(tick, POLL_MS * 2)
      }
    }

    tick()
    return () => { stop = true; clearTimeout(timer) }
  }, [runId])

  const overall = data?.overall_status ?? data?.status
  const stations = data?.stations ?? data?.stations_status_list ?? data?.pipeline_stations ?? []
  const logs = data?.pipeline_logs ?? []
  const badge = overall === 'COMPLETED' ? 'ok' : overall === 'FAILED' ? 'bad' : 'wait'

  return (
    <div className="page">
      <header>
        <h1>Progres analisis {runId}</h1>
        <p className="muted">
          {data ? <>Sampel <strong>{data.sample_name}</strong></> : 'Memuat status…'}
          {overall && <> · <span className={`badge ${badge}`}>{overall}</span></>}
        </p>
      </header>

      {error && <p className="msg bad" role="alert">{error}</p>}
      {overall === 'FAILED' && (
        <p className="msg bad" role="alert">
          Pipeline berhenti karena kegagalan pada salah satu stasiun. Periksa log backend, lalu unggah ulang berkas.
        </p>
      )}

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

      <section className="card">
        <h3>Log pipeline per stasiun</h3>
        {!logs.length && <p className="muted">Belum ada log. Log muncul setelah stasiun mulai berjalan.</p>}
        {groupLogs(logs).map(([num, items]) => (
          <details key={num} className="log-group" open={items.some((l) => l.log_level === 'ERROR')}>
            <summary>Stasiun {num}{stationName(stations, num) ? ` · ${stationName(stations, num)}` : ''} ({items.length} log)</summary>
            {items.map((l, i) => (
              <p key={i} className={`log-line ${l.log_level ?? ''}`}>
                {`[${l.timestamp ?? ''}] ${l.log_level ?? ''} ${l.message ?? ''}`}
              </p>
            ))}
          </details>
        ))}
      </section>

      <section className="card row-between">
        <Link className="btn" to="/analysis/new">Analisis baru</Link>
        <Link className="btn btn-primary" to={`/analysis/${runId}/result`}>Lihat hasil</Link>
      </section>
    </div>
  )
}