import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getStatus, lastRun } from '../lib/api'
import Icon from '../components/Icon'
import './pages.css'

const POLL_MS = 3000
const DONE = ['COMPLETED', 'FAILED']
const STATION_LABELS = {
  1: ['QC & Preprocessing', 'fastp'], 2: ['Read Alignment', 'BWA-MEM & samtools'], 3: ['Variant Calling', 'LoFreq + FreeBayes'],
  4: ['Quality Filtering', 'bcftools filter'], 5: ['Downstream', 'VarEscape Engine'],
}
const stDone = (s) => ['COMPLETED', 'SUCCESS', 'DONE', 'FINISHED'].includes(String(s).toUpperCase())
const stRun = (s) => ['RUNNING', 'IN_PROGRESS', 'PROCESSING'].includes(String(s).toUpperCase())

function groupLogs(logs) {
  const map = new Map()
  logs.forEach((l) => { const k = l.station_number ?? '?'; map.set(k, [...(map.get(k) ?? []), l]) })
  return [...map.entries()].sort((a, b) => Number(a[0]) - Number(b[0]))
}

export default function Progress() {
  const { runId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let stop = false, timer
    lastRun.set(runId)
    async function poll() {
      try {
        const d = await getStatus(runId)
        if (stop) return
        setData(d); setError('')
        if (!DONE.includes(d.overall_status ?? d.status)) timer = setTimeout(poll, POLL_MS)
      } catch (err) {
        if (stop) return
        setError(err.message)
        if (err.status !== 404) timer = setTimeout(poll, POLL_MS * 2)
      }
    }
    poll()
    return () => { stop = true; clearTimeout(timer) }
  }, [runId, tick])

  const overall = data?.overall_status ?? data?.status
  const stations = data?.stations ?? data?.stations_status_list ?? data?.pipeline_stations ?? []
  const logs = data?.pipeline_logs ?? []
  const finished = stations.filter((s) => stDone(s.status)).length
  const total = stations.length || 5
  const pct = overall === 'COMPLETED' ? 100 : Math.round((finished / total) * 100)
  const cls = overall === 'COMPLETED' ? 'ok' : overall === 'FAILED' ? 'bad' : ''
  const label = overall === 'COMPLETED' ? 'SELESAI' : overall === 'FAILED' ? 'GAGAL' : overall === 'QUEUED' || overall === 'PENDING' ? 'ANTRI' : 'BERJALAN'
  const rows = stations.length ? stations : [1, 2, 3, 4, 5].map((n) => ({ station: n, name: STATION_LABELS[n][0], status: 'PENDING' }))

  return (
    <>
      <div className="tr-head">
        <div className="tr-top">
          <div>
            <h1>Progressive Diagnostic Tracker</h1>
            <div className="tr-meta">
              <span>Run:</span><code>{runId}</code>
              <span className={`status-pill ${cls}`}><i />{label}</span>
              <span className="chip">Paired-End NGS</span>
            </div>
            <div className="tr-meta">{data ? <>Sampel <b>{data.sample_name}</b></> : 'Memuat status…'}</div>
          </div>
          <div className="row" style={{ gap: 8 }}>
            {/* TODO(backend): endpoint pembatalan analisis belum ada di frontend_m9 */}
            <button className="btn-danger" disabled title="Pembatalan belum didukung backend"><Icon name="x" size={10} /> Batalkan analisis</button>
            <button className="btn-refresh" onClick={() => setTick((t) => t + 1)}><Icon name="refresh" size={11} /> Refresh Telemetri</button>
          </div>
        </div>
        <div className="total">
          <div className="total-row"><span><Icon name="clock" size={11} /> Total Progress Keseluruhan</span><b>{pct}%</b></div>
          <div className="track"><i style={{ width: `${pct}%` }} /></div>
          <div className="total-foot">
            <span>{overall === 'COMPLETED' ? 'Semua stasiun selesai.' : `Stasiun ${Math.min(finished + 1, total)} dari ${total} ${stations.some((s) => stRun(s.status)) ? 'berjalan' : 'menunggu'}.`}</span>
            <small>{data?.created_at ? `Dibuat: ${new Date(data.created_at).toLocaleString('id-ID')}` : ''}</small>
          </div>
        </div>
      </div>

      {error && <p className="alert error" role="alert" style={{ marginTop: 16 }}>{error}</p>}
      {overall === 'FAILED' && <p className="alert error" role="alert" style={{ marginTop: 16 }}>Pipeline berhenti karena kegagalan pada salah satu stasiun. Periksa log di bawah, lalu unggah ulang berkas.</p>}

      <div className="stations">
        {rows.map((s) => {
          const n = Number(s.station)
          const done = stDone(s.status), run = stRun(s.status)
          const failed = String(s.status).toUpperCase() === 'FAILED'
          const [defName, tool] = STATION_LABELS[n] ?? [s.name, '']
          return (
            <article key={s.station} className={`st ${run ? 'run' : done || failed ? '' : 'wait'}`}>
              <div>
                <div className="st-top"><span>Step {String(n).padStart(2, '0')}{run ? ' (aktif)' : ''}</span>
                  <span className={`pill ${done ? 'ok' : failed ? 'bad' : run ? 'info' : ''}`} style={{ borderRadius: 2, fontSize: 11, textTransform: 'uppercase', fontWeight: 400 }}>
                    {done ? 'Selesai' : failed ? 'Gagal' : run ? 'Berjalan' : 'Menunggu'}
                  </span></div>
                <h3>{s.name ?? defName}</h3>
                <div className="st-box">{done ? 'Stasiun selesai dijalankan.' : failed ? 'Stasiun gagal. Lihat log.' : run ? 'Sedang diproses…' : `Menunggu stasiun ${Math.max(1, n - 1)}`}</div>
              </div>
              <div className="st-foot">{tool}</div>
            </article>
          )
        })}
      </div>

      <section className="logs">
        <h3>Log pipeline per stasiun</h3>
        {!logs.length && <p className="muted" style={{ fontSize: 13 }}>Belum ada log. Log muncul setelah stasiun mulai berjalan.</p>}
        {groupLogs(logs).map(([num, items]) => (
          <details key={num} open={items.some((l) => l.log_level === 'ERROR')}>
            <summary>Stasiun {num} ({items.length} log)</summary>
            {items.map((l, i) => <p key={i} className={`log-line ${l.log_level ?? ''}`}>{`[${l.timestamp ?? ''}] ${l.log_level ?? ''} ${l.message ?? ''}`}</p>)}
          </details>
        ))}
      </section>

      <div className="row" style={{ marginTop: 16 }}>
        <Link className="btn btn-ghost" to="/analysis/new">Analisis baru</Link>
        <Link className="btn btn-primary" to={`/analysis/${runId}/result`}>Lihat hasil</Link>
      </div>
    </>
  )
}
