import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { validateFormat, splitFastqPair, formatSize } from '../lib/validators'
import { uploadAnalysis, runAnalysis, lastRun } from '../lib/api'
import Icon from '../components/Icon'
import './pages.css'

const ROWS = [['r1', 'FASTQ_R1'], ['r2', 'FASTQ_R2'], ['fasta', 'FASTA'], ['iedb', 'IEDB']]
const LAYERS = [
  ['Lapis 1: Format Biner', 'Verifikasi signature gzip dan ekstensi MIME valid.'],
  ['Lapis 2: Header Integritas', 'Kesesuaian identifier sequence Illumina & FASTA defline.'],
  ['Lapis 3: Batas Koordinat', 'Toleransi posisi 1 s.d. L (L=29.903 bp pada Wuhan-Hu-1).'],
]

function Drop({ n, icon, iconBg, iconColor, title, hint, multiple, accept, onFiles, inputKey, disabled, names, size, error }) {
  const [over, setOver] = useState(false)
  return (
    <div className={`drop ${over ? 'over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); if (!disabled) onFiles(e.dataTransfer.files) }}>
      <div className="drop-top"><span>INPUT {n}</span><i /></div>
      <div className="drop-mid">
        <div className="drop-ic" style={{ background: iconBg, color: iconColor }}><Icon name={icon} size={20} /></div>
        <h3>{title}</h3>
        <p>Tarik berkas ke sini atau</p>
        <label className="pick"><Icon name="upload" size={12} /> Pilih berkas
          <input key={inputKey} type="file" hidden disabled={disabled} multiple={multiple} accept={accept} onChange={(e) => onFiles(e.target.files)} />
        </label>
        <small>{hint}</small>
        {error && <span className="drop-err" role="alert">{error}</span>}
      </div>
      <div className="drop-foot"><span>{names || 'belum ada berkas diunggah'}</span><span>{size}</span></div>
    </div>
  )
}

export default function NewAnalysis() {
  const navigate = useNavigate()
  const [sampleName, setSampleName] = useState('')
  const [files, setFiles] = useState({})
  const [checks, setChecks] = useState({})
  const [pairError, setPairError] = useState('')
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [inputKey, setInputKey] = useState(0)
  const [isStarting, setIsStarting] = useState(false)
  const filesRef = useRef({})
  const checksRef = useRef({})

  async function setChecked(key, file, kind) {
    const chk = file ? await validateFormat(kind, file) : null
    filesRef.current = { ...filesRef.current, [key]: file }
    checksRef.current = { ...checksRef.current, [key]: chk }
    setFiles(filesRef.current); setChecks(checksRef.current); setResult(null); setStatus('idle')
  }

  async function uploadIfReady() {
    const f = filesRef.current, c = checksRef.current
    if (!ROWS.every(([k]) => f[k] && c[k]?.ok)) return
    setStatus('loading'); setError('')
    try {
      const data = await uploadAnalysis({ sampleName: sampleName.trim() || 'Sampel Uji Coba', r1: f.r1, r2: f.r2, fasta: f.fasta, iedb: f.iedb })
      lastRun.set(data.run_id); setResult(data); setStatus('success')
    } catch (err) { setError(err.message); setStatus('error') }
  }

  async function handleRun() {
    if (!result?.run_id) return
    setIsStarting(true); setError('')
    try { await runAnalysis(result.run_id); navigate(`/analysis/${result.run_id}/progress`) }
    catch (err) { setError(err.message || 'Gagal memulai eksekusi analisis.'); setIsStarting(false) }
  }

  async function onFastq(list) {
    if (!list.length) return
    const pair = splitFastqPair(list)
    if (pair.error) { setPairError(pair.error); await setChecked('r1', null); await setChecked('r2', null); return }
    setPairError('')
    await setChecked('r1', pair.r1, 'fastq'); await setChecked('r2', pair.r2, 'fastq')
    await uploadIfReady()
  }
  async function onSingle(key, kind, list) {
    const file = list[0]
    if (!file) return
    await setChecked(key, file, kind); await uploadIfReady()
  }
  function onReset() {
    filesRef.current = {}; checksRef.current = {}
    setFiles({}); setChecks({}); setPairError(''); setResult(null); setError(''); setStatus('idle'); setIsStarting(false); setInputKey((k) => k + 1)
  }

  const summaryList = result?.uploaded_files_summary ?? []
  const summary = (type) => summaryList.find((s) => s.file_type === type)
  const allPass = status === 'success' && summaryList.length > 0 && summaryList.every((s) => s.validation_status === 'PASS')
  const badge = status === 'error' ? ['GAGAL', 'bad'] : allPass ? ['AMAN', 'ok'] : ['MENUNGGU', '']
  const busy = status === 'loading'
  const sizeOf = (k) => formatSize(files[k]?.size)

  return (
    <>
      <div className="up-head">
        <h1>Unggah Berkas &amp; Validasi Analisis Baru</h1>
        <p>Pemeriksaan integritas 3 lapis (Format, Header, Koordinat) sebelum eksekusi pipeline varian dan profiling immune escape.</p>
      </div>

      <div className="meta-card">
        <div className="meta-head">
          <span className="ic"><Icon name="file" size={14} /></span>
          <div>
            <h2>Identitas Sampel &amp; Metadata Analisis <span className="chip">OPSIONAL</span></h2>
            <p>Tetapkan label penanda spesifik isolat dan batch tracking sebelum memulai pipeline komputasi.</p>
          </div>
        </div>
        <div>
          <div className="lbl"><span>Nama Sampel / Label Isolat (Opsional)</span><small>Maks. 80 karakter</small></div>
          <input className="txt" maxLength={80} value={sampleName} onChange={(e) => setSampleName(e.target.value)} placeholder="Isolat bogor 01" disabled={busy || !!result} aria-label="Nama sampel" />
          <div className="hint-line"><Icon name="info" size={12} /> Isi sebelum memilih berkas. Dipakai sebagai pengenal pada katalog riwayat dan laporan hasil (opsional).</div>
        </div>
      </div>

      <div className="drops">
        <Drop n="01" icon="file" iconBg="rgba(14,110,110,.1)" iconColor="#0e6e6e" title="FASTQ Read 1 dan 2" hint="maks. 1 GB per berkas (.fastq.gz)" multiple accept=".fastq,.fq,.gz" inputKey={inputKey} disabled={busy || !!result}
          onFiles={onFastq} error={pairError || (checks.r1 && !checks.r1.ok ? `R1: ${checks.r1.message}` : checks.r2 && !checks.r2.ok ? `R2: ${checks.r2.message}` : '')}
          names={files.r1 && files.r2 ? `${files.r1.name}, ${files.r2.name}` : ''} size={formatSize((files.r1?.size || 0) + (files.r2?.size || 0))} />
        <Drop n="02" icon="file" iconBg="#cce2fa" iconColor="#506579" title="FASTA genom acuan" hint="maks. 50 MB (.fasta)" accept=".fasta,.fa,.fna" inputKey={inputKey} disabled={busy || !!result}
          onFiles={(l) => onSingle('fasta', 'fasta', l)} error={checks.fasta && !checks.fasta.ok ? checks.fasta.message : ''} names={files.fasta?.name} size={sizeOf('fasta')} />
        <Drop n="03" icon="file" iconBg="rgba(33,101,168,.1)" iconColor="#2165a8" title="Tabel epitope IEDB" hint="CSV/TSV/GFF, maks. 20 MB" accept=".csv,.tsv,.gff" inputKey={inputKey} disabled={busy || !!result}
          onFiles={(l) => onSingle('iedb', 'iedb', l)} error={checks.iedb && !checks.iedb.ok ? checks.iedb.message : ''} names={files.iedb?.name} size={sizeOf('iedb')} />
      </div>

      <section className="valid">
        <div className="valid-head">
          <div><h2><Icon name="shield-check" size={13} /> Hasil Validasi Otomatis 3 Lapis</h2><p>Integritas format biner, validitas header FASTQ/FASTA, serta batas koordinat relatif acuan.</p></div>
          <div className="row" style={{ gap: 8 }}><span className="muted" style={{ fontSize: 11, fontWeight: 600 }}>Status Batch:</span><span className={`badge-s ${badge[1]}`}>{busy ? 'MEMERIKSA' : badge[0]}</span></div>
        </div>
        <div className="v-row th"><span>BERKAS</span><span>UKURAN</span><span>1. FORMAT</span><span>2. HEADER</span><span>3. KOORDINAT</span><span>STATUS</span></div>
        {ROWS.map(([key, type]) => {
          const f = files[key], c = checks[key], s = summary(type)
          const fin = s ? s.validation_status : busy && c?.ok ? 'Memeriksa…' : c ? (c.ok ? 'Siap' : 'Gagal') : '-'
          const good = fin === 'PASS' || fin === 'Siap'
          return (
            <div className="v-row" key={key}>
              <span className="row" style={{ gap: 8 }}><Icon name="file" size={13} />{f?.name ?? <span className="mu">{type}</span>}</span>
              <span>{f ? formatSize(f.size) : '-'}</span>
              <span className={c ? (c.ok ? 'ok' : 'bad') : 'mu'}>{c ? (c.ok ? '✓ Lolos' : '✕ Gagal') : '-'}</span>
              <span className={s ? (s.validation_status === 'PASS' ? 'ok' : 'bad') : 'mu'}>{s ? (s.validation_status === 'PASS' ? '✓ Lolos' : '✕ Gagal') : '-'}</span>
              <span className={key === 'iedb' && s ? (s.validation_status === 'PASS' ? 'ok' : 'bad') : 'mu'}>{key === 'iedb' && s ? (s.validation_status === 'PASS' ? '✓ Lolos' : '✕ Gagal') : '-'}</span>
              <span className={good ? 'ok' : fin === 'Gagal' || fin === 'FAIL' ? 'bad' : 'mu'}>{fin === '-' ? '-' : `● ${fin}`}</span>
            </div>
          )
        })}
      </section>

      {error && <p className="alert error" role="alert" style={{ marginTop: 16 }}>{error}</p>}

      <div className="run-bar">
        <button className="btn btn-ghost" onClick={onReset} disabled={busy || isStarting}><Icon name="refresh" size={13} /> Atur ulang</button>
        <div className="row" style={{ gap: 16 }}>
          <div><div className="st-label">STATUS TOMBOL EKSEKUSI</div><div className={`st-msg ${allPass ? 'ok' : ''}`}>{allPass ? 'Semua berkas valid. Siap dijalankan.' : 'Aktif setelah semua berkas valid.'}</div></div>
          <button className="btn-run" disabled={!allPass || isStarting} onClick={handleRun}>{isStarting ? <span className="spinner" /> : <Icon name="play" size={14} />} Jalankan analisis (One-Click)</button>
        </div>
      </div>

      <div className="layers">
        {LAYERS.map(([t, d]) => <div className="layer" key={t}><Icon name="check-circle" size={12} /><div><b>{t}</b><span>{d}</span></div></div>)}
      </div>
    </>
  )
}
