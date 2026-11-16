import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { cancelAnalysis, downloadFile, getArtifacts, getResults, getStatus, lastRun } from '../lib/api'
import { STATIONS, STATION_COUNT, stationDiagnostic } from '../lib/diagnostics'
import { PARAM_GROUPS } from '../lib/params'
import Icon from '../components/Icon'
import './pages.css'

const POLL_MS = 3000
const DONE = ['COMPLETED', 'FAILED', 'CANCELLED']
const STATION_LABELS = Object.fromEntries(Object.entries(STATIONS).map(([n, v]) => [n, [v.name, v.tool]]))
const BADGE = { green: 'ok', yellow: 'warn', red: 'bad', purple: 'purple', orange: 'orange' }
const stDone = (s) => ['COMPLETED', 'SUCCESS', 'DONE', 'FINISHED'].includes(String(s).toUpperCase())
const stRun = (s) => ['RUNNING', 'IN_PROGRESS', 'PROCESSING'].includes(String(s).toUpperCase())


function DownloadBtn({ file }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  async function go() {
    setBusy(true); setErr('')
    try { await downloadFile(file.url, file.filename) } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <span className="dl-wrap">
      <button className={`dl-btn ${/PAKET/.test(file.label) ? 'main' : ''}`} onClick={go} disabled={busy}>
        {busy ? <span className="spinner" /> : <Icon name="download" size={12} />} {file.label}
      </button>
      {err && <small className="dl-err" role="alert">{err}</small>}
    </span>
  )
}

function StationResult({ d, params }) {
  if (!d.done && !d.fromBackend) return <p className="muted diag-wait">Hasil stasiun ini tersedia setelah stasiun selesai dijalankan.</p>
  return (
    <div className="diag">
      <div className="diag-head">
        <b>Hasil Stasiun {d.n}: {STATIONS[d.n].name}</b>
        {d.status_code && <span className={`dbadge ${BADGE[d.badge_color] ?? ''}`}>{d.status_code.replace(/_/g, ' ')}</span>}
      </div>
      <div className="mgrid">
        {d.metrics.filter(([, v], i) => v != null || i < 4).map(([label, v, note]) => (
          <div className="mcard" key={label}><small>{label}</small><b>{v ?? '-'}</b><span>{note}</span></div>
        ))}
      </div>
      {params && <div className="eff-params"><b>Parameter efektif:</b> {params}</div>}
      <div className="interp">
        <b>Interpretasi otomatis</b>
        {d.interpretation ? <p>{String(d.interpretation).replace(/(?<![A-Za-z0-9_])(\d+)\.(\d{1,2})(?!\d)/g, '$1,$2')}</p> : <p className="muted">{d.hasMetrics ? '' : 'Metrik diagnostik belum dikirim backend untuk stasiun ini, sehingga interpretasi belum dapat dihitung.'}</p>}
        {d.summary && <p>{d.summary}</p>}
      </div>
      <div className="dl-row">
        <b>Berkas hasil stasiun</b>
        <div>{d.files.map((f) => <DownloadBtn key={f.url} file={f} />)}</div>
        {!d.done && <small className="muted">Berkas tersedia setelah stasiun selesai.</small>}
      </div>
    </div>
  )
}

export default function Progress() {
  const { runId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [tick, setTick] = useState(0)
  const [cancelling, setCancelling] = useState(false)
  const [cancelError, setCancelError] = useState('')
  const [cancelMessage, setCancelMessage] = useState('')

  async function handleCancel() {
    if (String(data?.overall_status ?? data?.status).toUpperCase() !== 'RUNNING' || cancelling) return
    if (!window.confirm('Batalkan pipeline yang sedang berjalan? Hasil stasiun yang sudah selesai akan tetap disimpan.')) return
    setCancelling(true)
    setCancelError('')
    setCancelMessage('')
    try {
      const response = await cancelAnalysis(runId)
      setCancelMessage(response?.message || 'Permintaan pembatalan diterima backend. Memeriksa status terbaru…')
      setTick(t => t + 1)
    } catch (err) {
      setCancelError([404, 405, 501].includes(err.status)
        ? 'Backend saat ini belum menyediakan endpoint cancel. Pipeline tetap berjalan; permintaan tidak membatalkan proses.'
        : err.message || 'Pembatalan gagal.')
    } finally {
      setCancelling(false)
    }
  }

  useEffect(() => {
    let stop = false, timer
    lastRun.set(runId)
    async function poll() {
      try {
        const d = await getStatus(runId)
        // Kedua endpoint tidak boleh menghalangi status/progres jika gagal.
        const [resultsRes, filesRes] = await Promise.allSettled([
          getResults(runId),
          getArtifacts(runId),
        ])
        if (stop) return
        const results = resultsRes.status === 'fulfilled' ? resultsRes.value : null
        const artifacts = filesRes.status === 'fulfilled' ? filesRes.value : null
        setData({
          ...d,
          summary_metrics: d.summary_metrics ?? results?.summary_metrics ?? {},
          artifacts: artifacts?.artifacts ?? [],
        })
        setError('')
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
  // Pipeline final = 4 stasiun; stasiun 5 (epitope IEDB) sudah dihapus dari rancangan
  const stations = (data?.stations ?? data?.stations_status_list ?? data?.pipeline_stations ?? []).filter((s) => Number(s.station) <= STATION_COUNT)
  const logs = (data?.pipeline_logs ?? []).filter((l) => Number(l.station_number ?? 0) <= STATION_COUNT)
  const finished = stations.filter((s) => stDone(s.status)).length
  const total = stations.length || STATION_COUNT
  const pct = overall === 'COMPLETED' ? 100 : Math.round((finished / total) * 100)
  const cls = overall === 'COMPLETED' ? 'ok' : overall === 'FAILED' ? 'bad' : ''
  const label = overall === 'CANCELLED' ? 'DIBATALKAN' : overall === 'COMPLETED' ? 'SELESAI' : overall === 'FAILED' ? 'GAGAL' : overall === 'QUEUED' || overall === 'PENDING' ? 'ANTRI' : 'BERJALAN'
  const rows = stations.length ? stations : [1, 2, 3, 4].map((n) => ({ station: n, name: STATION_LABELS[n][0], status: 'PENDING' }))

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
            <button type="button" className="btn-danger"
              disabled={overall !== 'RUNNING' || cancelling}
              title={overall === 'RUNNING' ? 'Minta backend menghentikan proses' : 'Hanya aktif selama RUNNING'}
              onClick={handleCancel}>
              <Icon name="x" size={10} /> {cancelling ? 'Membatalkan…' : 'Batalkan analisis'}
            </button>
            <button className="btn-refresh" onClick={() => setTick((t) => t + 1)}><Icon name="refresh" size={11} /> Refresh Telemetri</button>
          </div>
        </div>
        <div className="total">
          <div className="total-row"><span><Icon name="clock" size={11} /> Total Progress Keseluruhan</span><b>{pct}%</b></div>
          <div className="track"><i style={{ width: `${pct}%` }} /></div>
          <div className="total-foot">
            <span>{overall === 'COMPLETED' ? 'Semua stasiun selesai.' : overall === 'FAILED'
               ? `Pipeline terhenti. ${finished} dari ${total} stasiun selesai. Hasil stasiun berhasil tetap tersedia.`
               : overall === 'CANCELLED'
                 ? `Analisis dibatalkan. ${finished} stasiun selesai.`
                 : `Stasiun ${Math.min(finished + 1, total)} dari ${total} ${stations.some((s) => stRun(s.status)) ? 'berjalan' : 'menunggu'}.`}</span>
            <small>{data?.created_at ? `Dibuat: ${new Date(data.created_at).toLocaleString('id-ID')}` : ''}</small>
          </div>
        </div>
      </div>

      {cancelError && <p className="alert error" role="alert" style={{ marginTop: 12 }}>{cancelError}</p>}
      {cancelMessage && <p className="alert ok" role="status" style={{ marginTop: 12 }}>{cancelMessage}</p>}
      {error && <p className="alert error"  role="alert" style={{ marginTop: 16 }}>{error}</p>}
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
                <h3>{defName ?? s.name}</h3>
                <div className="st-box">{done ? 'Stasiun selesai dijalankan.' : failed ? 'Stasiun gagal. Lihat log.' : run ? 'Sedang diproses…' : `Menunggu stasiun ${Math.max(1, n - 1)}`}</div>
              </div>
              <div className="st-foot">{tool}</div>
            </article>
          )
        })}
      </div>

      <section className="logs">
        <h3>Log pipeline per stasiun</h3>
        <p className="muted" style={{ fontSize: 12, marginBottom: 6 }}>Buka tiap stasiun untuk melihat hasil, interpretasi otomatis, berkas unduhan, dan log eksekusinya.</p>
        {!logs.length && <p className="muted" style={{ fontSize: 13 }}>Belum ada log. Log muncul setelah stasiun mulai berjalan.</p>}
        {[1, 2, 3, 4].map((n) => {
          const row = rows.find((r) => Number(r.station) === n)
          const items = logs.filter((l) => Number(l.station_number) === n)
          const done = row ? stDone(row.status) : false
          const failed = row ? String(row.status).toUpperCase() === 'FAILED' : false
          const d = stationDiagnostic(data, runId, n, done)
          const eff = data?.effective_parameters ?? data?.parameters ?? data?.run_parameters
          const group = PARAM_GROUPS.find((g) => g.station === n)
          const params = eff && group ? group.params.filter((p) => eff[p.key] != null).map((p) => `${p.key} ${p.op} ${eff[p.key]}`).join(' • ') : ''
          return (
            <details key={n} open={items.some((l) => l.log_level === 'ERROR') || failed}>
              <summary>
                Stasiun {n} — {STATION_LABELS[n][0]} ({items.length} log)
                {d.status_code && (done || d.fromBackend) && <span className={`dbadge sm ${BADGE[d.badge_color] ?? ''}`}>{d.status_code.replace(/_/g, ' ')}</span>}
              </summary>
              <StationResult d={d} params={params} />
              {items.length > 0 && <div className="log-box"><b>Log eksekusi</b>
                {items.map((l, i) => <p key={i} className={`log-line ${l.log_level ?? ''}`}>{`[${l.timestamp ?? ''}] ${l.log_level ?? ''} ${l.message ?? ''}`}</p>)}</div>}
            </details>
          )
        })}
      </section>

      <div className="row" style={{ marginTop: 16 }}>
        <Link className="btn btn-ghost" to="/analysis/new">Analisis baru</Link>
        <Link className="btn btn-primary" to={`/analysis/${runId}/result`}>Lihat hasil</Link>
      </div>
    </>
  )
}
