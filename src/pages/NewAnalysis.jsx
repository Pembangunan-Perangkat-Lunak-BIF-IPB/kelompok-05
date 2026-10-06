import { useRef, useState } from 'react'
import { validateFormat, splitFastqPair, formatSize } from '../lib/validators'
import { uploadAnalysis } from '../lib/api'
import './pages.css'

const ROWS = [
  ['r1', 'FASTQ_R1'],
  ['r2', 'FASTQ_R2'],
  ['fasta', 'FASTA'],
  ['iedb', 'IEDB'],
]

const LAYERS = [
  ['Lapis 1: format biner', 'Verifikasi signature gzip dan ekstensi MIME valid.'],
  ['Lapis 2: header integritas', 'Kesesuaian identifier sequence Illumina dan FASTA defline.'],
  ['Lapis 3: batas koordinat', 'Toleransi posisi 1 s.d. L (L=29.903 bp pada Wuhan-Hu-1).'],
]

function UploadCard({ title, desc, hint, multiple, accept, onChange, inputKey, disabled, names, size }) {
  return (
    <div className="card upload-card">
      <h3>{title}</h3>
      <p className="muted">{desc}</p>
      <label className="btn">
        Pilih berkas
        <input key={inputKey} type="file" hidden disabled={disabled}
          multiple={multiple} accept={accept} onChange={onChange} />
      </label>
      <small className="muted">{hint}</small>
      <div className="upload-foot">
        <span>{names || 'belum ada berkas diunggah'}</span>
        <span>{size}</span>
      </div>
    </div>
  )
}

export default function NewAnalysis() {
  const [sampleName, setSampleName] = useState('')
  const [files, setFiles] = useState({})
  const [checks, setChecks] = useState({})
  const [pairError, setPairError] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | success | error
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [inputKey, setInputKey] = useState(0)
  const filesRef = useRef({})
  const checksRef = useRef({})

  async function setChecked(key, file, kind) {
    const chk = file ? await validateFormat(kind, file) : null
    filesRef.current = { ...filesRef.current, [key]: file }
    checksRef.current = { ...checksRef.current, [key]: chk }
    setFiles(filesRef.current)
    setChecks(checksRef.current)
    setResult(null)
    setStatus('idle')
    setNotice('')
  }

  // Unggah otomatis begitu keempat berkas lolos Lapis 1 (tanpa tombol tambahan)
  async function uploadIfReady() {
    const f = filesRef.current
    const c = checksRef.current
    if (!ROWS.every(([k]) => f[k] && c[k]?.ok)) return
    setStatus('loading')
    setError('')
    try {
      const data = await uploadAnalysis({
        sampleName: sampleName.trim(),
        r1: f.r1, r2: f.r2, fasta: f.fasta, iedb: f.iedb,
      })
      setResult(data)
      setStatus('success')
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  async function onFastq(e) {
    const picked = e.target.files
    if (!picked.length) return
    const pair = splitFastqPair(picked)
    if (pair.error) {
      setPairError(pair.error)
      await setChecked('r1', null)
      await setChecked('r2', null)
      return
    }
    setPairError('')
    await setChecked('r1', pair.r1, 'fastq')
    await setChecked('r2', pair.r2, 'fastq')
    await uploadIfReady()
  }

  async function onSingle(key, kind, e) {
    const file = e.target.files[0]
    if (!file) return
    await setChecked(key, file, kind)
    await uploadIfReady()
  }

  // "Ganti kondisi validasi": kosongkan semua berkas dan hasil
  function onReset() {
    filesRef.current = {}
    checksRef.current = {}
    setFiles({})
    setChecks({})
    setPairError('')
    setResult(null)
    setError('')
    setNotice('')
    setStatus('idle')
    setInputKey((k) => k + 1)
  }

  const summaryList = result?.uploaded_files_summary ?? []
  const summary = (type) => summaryList.find((s) => s.file_type === type)
  const allPass = status === 'success' && summaryList.length > 0 &&
    summaryList.every((s) => s.validation_status === 'PASS')
  const badge = status === 'error' ? ['GAGAL', 'bad'] : allPass ? ['AMAN', 'ok'] : ['MENUNGGU', 'wait']
  const busy = status === 'loading'

  return (
    <div className="page">
      <header>
        <h1>Unggah berkas & validasi analisis baru</h1>
        <p className="muted">Pemeriksaan integritas 3 lapis (format, header, koordinat) sebelum eksekusi pipeline varian dan profiling immune escape.</p>
      </header>

      <section className="card">
        <h3>Identitas sampel & metadata <span className="tag">Opsional</span></h3>
        <label htmlFor="sample">Nama sampel / label isolat (opsional)</label>
        <input id="sample" className="input" maxLength={80} value={sampleName}
          onChange={(e) => setSampleName(e.target.value)} placeholder="Isolat bogor 01" />
        <small className="muted">Maks. 80 karakter. Isi sebelum memilih berkas. Dipakai sebagai pengenal di riwayat dan laporan hasil.</small>
      </section>

      <section className="grid-3">
        <UploadCard
          title="FASTQ Read 1 dan 2"
          desc="Pilih 2 berkas sekaligus (_R1 dan _R2)"
          hint="maks. 1 GB per berkas (.fastq.gz)"
          multiple
          accept=".fastq,.fq,.gz"
          onChange={onFastq}
          inputKey={inputKey}
          disabled={busy}
          names={files.r1 && files.r2 ? `${files.r1.name}, ${files.r2.name}` : ''}
          size={formatSize((files.r1?.size || 0) + (files.r2?.size || 0))}
        />
        <UploadCard
          title="FASTA genom acuan"
          desc="Pilih berkas genom acuan"
          hint="maks. 50 MB (.fasta)"
          accept=".fasta,.fa,.fna"
          onChange={(e) => onSingle('fasta', 'fasta', e)}
          inputKey={inputKey}
          disabled={busy}
          names={files.fasta?.name}
          size={formatSize(files.fasta?.size)}
        />
        <UploadCard
          title="Tabel epitope IEDB"
          desc="Pilih tabel koordinat epitope"
          hint="CSV/TSV/GFF, maks. 20 MB"
          accept=".csv,.tsv,.gff"
          onChange={(e) => onSingle('iedb', 'iedb', e)}
          inputKey={inputKey}
          disabled={busy}
          names={files.iedb?.name}
          size={formatSize(files.iedb?.size)}
        />
      </section>
      {pairError && <p className="msg bad" role="alert">{pairError}</p>}

      <section className="card">
        <div className="row-between">
          <h3>Hasil validasi otomatis 3 lapis</h3>
          <span className={`badge ${badge[1]}`}>Status batch: {badge[0]}</span>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Berkas</th><th>Ukuran</th><th>1. Format</th><th>2. Header</th><th>3. Koordinat</th><th>Status</th></tr></thead>
            <tbody>
              {ROWS.map(([key, type]) => {
                const f = files[key], c = checks[key], s = summary(type)
                const final = s ? s.validation_status : busy && c?.ok ? 'Memeriksa…' : c ? (c.ok ? 'Siap' : 'Gagal') : '-'
                return (
                  <tr key={key}>
                    <td>{f?.name ?? type}</td>
                    <td>{f ? formatSize(f.size) : '-'}</td>
                    <td className={c && !c.ok ? 'bad' : ''}>{c ? (c.ok ? 'Lolos' : c.message) : '-'}</td>
                    <td>{s ? s.validation_status : '-'}</td>
                    <td>{key === 'iedb' && s ? s.validation_status : '-'}</td>
                    <td>{final}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {busy && <p className="msg" role="status">Mengunggah dan memeriksa berkas…</p>}
        {status === 'success' && (
          <p className="msg ok" role="status">Berkas terunggah. ID analisis: <strong>{result.run_id}</strong> (status {result.status}).</p>
        )}
        {status === 'error' && <p className="msg bad" role="alert">{error}</p>}
      </section>

      <section className="card row-between">
        <button className="btn" onClick={onReset} disabled={busy}>Ganti kondisi validasi</button>
        <div className="exec">
          <small className="muted">Status tombol eksekusi</small>
          {!allPass && <small className="msg bad">Aktif setelah semua berkas valid.</small>}
          {notice && <small className="msg ok">{notice}</small>}
          <button className="btn btn-primary" disabled={!allPass}
            onClick={() => setNotice('Eksekusi pipeline disambungkan pada Minggu 8.')}>
            Jalankan analisis (One-Click)
          </button>
        </div>
      </section>

      <section className="grid-3">
        {LAYERS.map(([t, d]) => (
          <div className="card layer" key={t}><strong>{t}</strong><p className="muted">{d}</p></div>
        ))}
      </section>
    </div>
  )
}
