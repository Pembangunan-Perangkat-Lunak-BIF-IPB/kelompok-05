
import { useCallback, useEffect, useRef, useState } from 'react'
import { getAdminHealth } from '../../lib/api'
import Icon from '../../components/Icon'
import '../history.css'

const POLL_MS = 15000

const number = (value) => {
  if (value === null || value === undefined || value === '') return null
  const result = Number(value)
  return Number.isFinite(result) ? result : null
}

const percent = (value) => {
  const n = number(value)
  return n === null ? null : Math.min(100, Math.max(0, n))
}

const display = (value, unit = '') =>
  value === null || value === undefined ? '—' : `${value}${unit}`

export default function HealthCheck() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [checkedAt, setCheckedAt] = useState(null)
  const requestRunning = useRef(false)

  const load = useCallback(async () => {
    if (requestRunning.current) return
    requestRunning.current = true
    setBusy(true)

    try {
      const response = await getAdminHealth()
      setData(response)
      setCheckedAt(new Date())
      setError('')
    } catch (err) {
      setError(err.message || 'Gagal mengambil status layanan.')
    } finally {
      requestRunning.current = false
      setBusy(false)
    }
  }, [])

  useEffect(() => {
    load()
    const timer = setInterval(load, POLL_MS)
    return () => clearInterval(timer)
  }, [load])

  const cpu = percent(data?.cpu_percent ?? data?.cpu_usage)
  const ram = percent(data?.ram_percent ?? data?.memory_percent)
  const disk = percent(data?.disk_percent ?? data?.scratch_percent)

  const hasQueue = Array.isArray(data?.queue) ||
    Array.isArray(data?.job_queue)

  const queue = Array.isArray(data?.queue)
    ? data.queue
    : Array.isArray(data?.job_queue)
      ? data.job_queue
      : []

  const running = queue.filter((job) =>
    ['RUNNING', 'PROCESSING'].includes(
      String(job.status || '').toUpperCase()
    )
  ).length

  const pending = queue.filter((job) =>
    ['PENDING', 'QUEUED', 'WAITING'].includes(
      String(job.status || '').toUpperCase()
    )
  ).length

  const status = data?.status ?? null

  return (
    <>
      <div className="hh">
        <div>
          <h1 style={{ fontSize: 22 }}>
            Status Server &amp; Layanan VarEscape
          </h1>
          <p>
            Pemeriksaan ketersediaan API dan informasi sumber daya
            yang disediakan backend. Data yang tidak tersedia
            ditampilkan sebagai belum terpantau.
          </p>
        </div>
        <button
          type="button"
          className="btn-ok"
          onClick={load}
          disabled={busy}
          style={{
            background: 'var(--teal-d)',
            borderRadius: 2
          }}
        >
          {busy
            ? <span className="spinner" />
            : <Icon name="refresh" size={11} />}
          {' '}Perbarui Sekarang
        </button>
      </div>

      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}

      {data && (
        <p
          className={`alert ${
            ['ok', 'healthy'].includes(String(status).toLowerCase())
              ? 'ok'
              : 'error'
          }`}
          style={{ marginTop: 16 }}
        >
          Status API: <b>{display(status)}</b>
          {checkedAt && (
            <span style={{ marginLeft: 10 }}>
              • Diperiksa pukul {checkedAt.toLocaleTimeString('id-ID')}
            </span>
          )}
        </p>
      )}

      <div className="hc-grid">
        <div className="hc">
          <small>
            Utilisasi CPU <Icon name="server" size={13} />
          </small>
          <div className="n">
            {display(cpu, '%')}
            <span className="tg">
              {cpu === null ? 'Belum terpantau' : 'Data backend'}
            </span>
          </div>
          <div className="hbar">
            <i style={{ width: `${cpu ?? 0}%` }} />
          </div>
          <div className="f">
            <span>
              {cpu === null
                ? 'API belum memberikan angka utilisasi CPU.'
                : `${display(data?.cpu_cores_active)} / ${display(data?.cpu_cores)} core aktif`}
            </span>
          </div>
        </div>

        <div className="hc">
          <small>Penggunaan RAM</small>
          <div className="n">
            {display(ram, '%')}
            <span className="tg">
              {ram === null ? 'Belum terpantau' : 'Data backend'}
            </span>
          </div>
          <div className="hbar">
            <i style={{ width: `${ram ?? 0}%` }} />
          </div>
          <div className="f">
            <span>
              {ram === null
                ? 'API belum memberikan angka penggunaan RAM.'
                : `${display(data?.ram_used_gb, ' GB')} dari ${display(data?.ram_total_gb, ' GB')}`}
            </span>
          </div>
        </div>

        <div className="hc">
          <small>Penyimpanan Server</small>
          <div className="n">
            {display(data?.disk_used_gb)}
            <span style={{ fontSize: 14 }}> GB</span>
          </div>
          <div className="hbar g">
            <i style={{ width: `${disk ?? 0}%` }} />
          </div>
          <div className="f">
            <span>
              {data?.disk_used_gb == null
                ? 'Informasi penyimpanan belum tersedia.'
                : `Dari ${display(data?.disk_total_gb, ' GB')} kapasitas total`}
            </span>
          </div>
        </div>

        <div className="hc">
          <small>Analisis Aktif &amp; Menunggu</small>
          <div className="n">
            {hasQueue ? queue.length : '—'}
            <span className="tg">
              {hasQueue ? 'Tugas tercatat' : 'Belum terpantau'}
            </span>
          </div>
          <div className="f">
            <span>
              {hasQueue
                ? `${running} berjalan, ${pending} menunggu`
                : 'Data antrean tidak tersedia dari API.'}
            </span>
          </div>
        </div>
      </div>

      <section
        className="sec"
        style={{
          border: '1px solid #e2e8f0',
          borderRadius: 4
        }}
      >
        <div className="sec-h">
          <div>
            <h2 style={{ fontSize: 18 }}>
              <Icon name="server" size={13} />
              {' '}Daftar Analisis Aktif
            </h2>
            <p>
              Menampilkan tugas yang dikirim oleh API backend.
              Bukan pemantauan scheduler HPC terpisah.
            </p>
          </div>
          <small className="muted">
            {hasQueue ? `${running} berjalan` : 'Data tidak tersedia'}
          </small>
        </div>

        <div className="q-row th">
          <span>PEMILIK</span>
          <span>STASIUN</span>
          <span>ALOKASI</span>
          <span>DURASI</span>
          <span>STATUS</span>
        </div>

        {!hasQueue && (
          <div className="empty">
            Backend belum menyediakan daftar tugas.
          </div>
        )}

        {hasQueue && queue.length === 0 && (
          <div className="empty">
            Tidak ada tugas dalam daftar yang dikirim backend.
          </div>
        )}

        {queue.map((job, index) => (
          <div className="q-row" key={job.run_id ?? index}>
            <span>{display(job.owner)}</span>
            <span>{display(job.stage)}</span>
            <span>{display(job.alloc)}</span>
            <span>{display(job.elapsed)}</span>
            <span className="sbadge run">
              {display(job.status)}
            </span>
          </div>
        ))}

        <div className="tbl-foot">
          <span>
            {hasQueue
              ? `Menampilkan ${queue.length} tugas`
              : 'Antrean tidak terpantau'}
          </span>
        </div>
      </section>

      <div className="hc-2">
        <div className="hc">
          <div className="box-g">
            <div className="kv-r">
              <span>Perangkat pipeline:</span>
              <b>fastp, BWA-MEM2, SAMtools, BCFtools, SnpEff</b>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
