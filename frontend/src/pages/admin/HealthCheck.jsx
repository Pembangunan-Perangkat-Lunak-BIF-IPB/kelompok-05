import { useCallback, useEffect, useRef, useState } from 'react'
import { getAdminHealth } from '../../lib/api'
import { pick } from '../../lib/risk'
import Icon from '../../components/Icon'
import '../history.css'

const POLL = 5000
const pct = (v) => (v == null || Number.isNaN(Number(v)) ? null : Math.max(0, Math.min(100, Number(v))))
const dash = (v, s = '') => (v == null ? '-' : `${v}${s}`)

// TODO(backend): /admin/health belum ada; saat 404 dipakai /health. Nama field di bawah adalah asumsi.
export default function HealthCheck() {
  const [d, setD] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const timer = useRef()

  const load = useCallback(async () => {
    setBusy(true)
    try {
      const x = await getAdminHealth()
      setD(x); setError('')
    } catch (e) { setError(e.message || 'Data pemantauan ini tidak dapat diperoleh. Periksa koneksi soket daemon bioinformatika.') } finally { setBusy(false) }
  }, [])
  useEffect(() => { load(); timer.current = setInterval(load, POLL); return () => clearInterval(timer.current) }, [load])

  const cpu = pct(pick(d, 'cpu_percent', 'cpu_usage')), ram = pct(pick(d, 'ram_percent', 'memory_percent'))
  const disk = pct(pick(d, 'disk_percent', 'scratch_percent'))
  const queue = d?.queue ?? d?.job_queue ?? []
  const status = pick(d, 'status') ?? (d ? 'ok' : null)

  return (
    <>
      <div className="hh"><div><h1 style={{ fontSize: 22 }}>Pemantauan Server &amp; Diagnostik Komputasi</h1><p>Status kesehatan node HPC (High Performance Computing), alokasi sumber daya, dan antrean daemon bioinformatika secara real-time.</p></div>
        <button className="btn-ok" onClick={load} disabled={busy} style={{ background: 'var(--teal-d)', borderRadius: 2 }}>{busy ? <span className="spinner" /> : <Icon name="refresh" size={11} />} Perbarui Sekarang</button></div>
      {error && <p className="alert error" role="alert" style={{ marginTop: 16 }}>{error}</p>}
      {d && status && <p className={`alert ${String(status).toLowerCase() === 'ok' ? 'ok' : 'error'}`} style={{ marginTop: 16 }}>Status layanan API: <b>{String(status)}</b></p>}

      <div className="hc-grid">
        <div className="hc"><small>Utilisasi CPU <Icon name="server" size={13} /></small><div className="n">{dash(cpu, '%')} <span className="tg">{cpu == null ? 'Tidak ada data' : cpu < 85 ? 'Core Load Nominal' : 'High Load'}</span></div><div className="hbar"><i style={{ width: `${cpu ?? 0}%` }} /></div><div className="f"><span>{dash(pick(d, 'cpu_cores_active'))} / {dash(pick(d, 'cpu_cores'))} Core aktif</span></div></div>
        <div className={`hc`}><small>Utilisasi RAM <Icon name="alert" size={13} /></small><div className="n">{dash(ram, '%')} <span className={`tg ${ram > 85 ? 'w' : ''}`}>{ram > 85 ? 'MEMORY ALERT' : 'Nominal'}</span></div><div className={`hbar ${ram > 85 ? 'w' : ''}`}><i style={{ width: `${ram ?? 0}%` }} /></div><div className="f"><span>{dash(pick(d, 'ram_used_gb'))} GB / {dash(pick(d, 'ram_total_gb'))} GB terpakai</span></div></div>
        <div className="hc"><small>Penyimpanan Scratch</small><div className="n">{dash(pick(d, 'disk_used_gb'))} <span style={{ fontSize: 14, color: '#475569' }}>GB</span></div><div className="hbar g"><i style={{ width: `${disk ?? 0}%` }} /></div><div className="f"><span>dari {dash(pick(d, 'disk_total_gb'))} GB kapasitas total</span></div></div>
        <div className="hc"><small>Antrean Tugas (Job Queue)</small><div className="n">{queue.length} <span className="tg g">HEALTHY PIPE</span></div><div className="f"><b>{queue.filter((j) => /RUN/i.test(j.status)).length} berjalan, {queue.filter((j) => !/RUN/i.test(j.status)).length} menunggu</b></div></div>
      </div>

      <section className="sec" style={{ border: '1px solid #e2e8f0', borderRadius: 4 }}>
        <div className="sec-h"><div><h2 style={{ fontSize: 18 }}><Icon name="server" size={13} /> Antrean Tugas Bioinformatika</h2><p>Daftar eksekusi analisis genomic pipeline yang sedang berjalan dan antrean prioritas komputasi saat ini.</p></div><small className="muted">Slot Terpakai: {queue.filter((j) => /RUN/i.test(j.status)).length}</small></div>
        <div className="q-row th"><span>PEMILIK</span><span>PIPELINE STAGE</span><span>ALOKASI CPU / RAM</span><span>WAKTU BERJALAN</span><span>STATUS</span></div>
        {!queue.length && <div className="empty">Tidak ada tugas dalam antrean (atau backend belum mengirim data antrean).</div>}
        {queue.map((j, i) => (
          <div className="q-row" key={j.run_id ?? i}>
            <span>{j.owner ?? '-'}</span><span>{j.stage ?? '-'}</span><span>{j.alloc ?? '-'}</span><span>{j.elapsed ?? '-'}</span><span className="sbadge run">{j.status}</span>
          </div>
        ))}
        <div className="tbl-foot"><span>Menampilkan {queue.length} antrean aktif</span></div>
      </section>

      <div className="hc-2">
        <div className="hc">
          <div className="box-g">
            <div className="kv-r"><span>Genomic Tools:</span><b>fastp, FastQC, BWA-MEM2, SAMtools, BCFtools, dan SnpEff</b></div>
          </div></div>
      </div>
    </>
  )
}
