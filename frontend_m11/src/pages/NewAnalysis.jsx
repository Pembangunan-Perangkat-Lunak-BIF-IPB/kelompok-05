
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatSize } from '../lib/validators'
import {
  PARAM_GROUPS,
  validateParams,
  rangeText,
} from '../lib/params'
import { session } from '../lib/api'
import {
  useAnalysisDraft,
  analysisDraft,
} from '../lib/analysisDraft'
import Icon from '../components/Icon'
import './pages.css'

const ROWS = [
  ['r1', 'FASTQ_R1'],
  ['r2', 'FASTQ_R2'],
]

function Drop({ onFiles, files, disabled }) {
  const [over, setOver] = useState(false)

  const totalSize =
    (files.r1?.size ?? 0) + (files.r2?.size ?? 0)

  return (
    <div
      className={`drop ${over ? 'over' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        if (!disabled) onFiles(e.dataTransfer.files)
      }}
    >
      <div className="drop-top">
        <span>INPUT 01</span>
        <i />
      </div>

      <div className="drop-mid">
        <div
          className="drop-ic"
          style={{
            background: 'rgba(14,110,110,.1)',
            color: '#0e6e6e',
          }}
        >
          <Icon name="file" size={20} />
        </div>

        <h3>FASTQ Read 1 dan 2</h3>
        <p>Tarik berkas ke sini atau</p>

        <label className="pick">
          <Icon name="upload" size={12} />
          {' '}Pilih berkas

          <input
            type="file"
            hidden
            multiple
            disabled={disabled}
            accept=".fastq,.fq,.fastq.gz,.fq.gz"
            onChange={(e) => {
              onFiles(e.target.files)
              e.target.value = ''
            }}
          />
        </label>

        <small>Maks. 1 GB per berkas FASTQ</small>

        <div className="drop-note">
          <Icon name="info" size={13} />
          <span>
            Pilih dua berkas dari sampel yang sama,
            dengan nama mengandung _R1 dan _R2.
            Mengubah parameter tidak akan menghapus berkas.
          </span>
        </div>
      </div>

      <div className="drop-foot">
        <span>
          {files.r1 && files.r2
            ? `${files.r1.name}, ${files.r2.name}`
            : 'Belum ada pasangan FASTQ dipilih'}
        </span>
        <span>{totalSize ? formatSize(totalSize) : '-'}</span>
      </div>
    </div>
  )
}

export default function NewAnalysis() {
  const navigate = useNavigate()
  const draft = useAnalysisDraft()

  const {
    sampleName,
    files,
    checks,
    mode,
    vals,
    phase,
    error,
    pairError,
    result,
  } = draft

  const custom = mode === 'custom'
  const errors = custom ? validateParams(vals) : {}
  const paramsInvalid = Object.keys(errors).length > 0

  const busy = ['uploading', 'starting'].includes(phase)
  const validating = phase === 'validating'
  const locked = busy || Boolean(result)

  const ready =
    Boolean(files.r1 && files.r2) &&
    checks.r1?.ok === true &&
    checks.r2?.ok === true &&
    !validating &&
    !paramsInvalid

  useEffect(() => {
    analysisDraft.setOwner(session.user?.id ?? null)
  }, [])

  async function handleRun() {
    const runId = await analysisDraft.start()

    if (runId) {
      navigate(`/analysis/${runId}/progress`)
    }
  }

  function handleReset() {
    if (
      window.confirm(
        'Hapus seluruh draft analisis, termasuk pilihan FASTQ dan parameter?'
      )
    ) {
      analysisDraft.reset()
    }
  }

  const summaryList = result?.uploaded_files_summary ?? []
  const summary = (type) =>
    summaryList.find((item) => item.file_type === type)

  const stateLabel =
    phase === 'validating'
      ? 'MEMERIKSA'
      : phase === 'uploading'
        ? 'MENGUNGGAH'
        : phase === 'starting'
          ? 'MENJALANKAN'
          : phase === 'started'
            ? 'BERJALAN'
            : ready
              ? 'SIAP'
              : phase === 'invalid'
                ? 'GAGAL'
                : 'MENUNGGU'

  return (
    <>
      <div className="up-head">
        <h1>Unggah Berkas &amp; Validasi Analisis Baru</h1>
        <p>
          Pilih FASTQ, periksa hasil validasi awal,
          tentukan parameter, kemudian jalankan analisis.
        </p>
      </div>

      <div className="meta-card">
        <div className="meta-head">
          <span className="ic">
            <Icon name="file" size={14} />
          </span>

          <div>
            <h2>Identitas Sampel &amp; Metadata Analisis</h2>
            <p>
              Tentukan nama sampel sebagai pengenal
              pada riwayat dan laporan hasil.
            </p>
          </div>
        </div>

        <div>
          <div className="lbl">
            <span>Nama Sampel / Label Isolat</span>
            <small>Maks. 80 karakter</small>
          </div>

          <input
            className="txt"
            maxLength={80}
            placeholder="Isolat bogor 01"
            value={sampleName}
            disabled={locked}
            onChange={(e) =>
              analysisDraft.setSampleName(e.target.value)
            }
          />

          <div className="hint-line">
            <Icon name="info" size={12} />
            {' '}
            Nama sampel dapat diubah sebelum analisis dijalankan.
          </div>
        </div>
      </div>

      <div className="drops">
        <Drop
          files={files}
          disabled={locked}
          onFiles={(list) => analysisDraft.selectFiles(list)}
        />

        <div
          className="drop locked"
          aria-label="Genom acuan baku"
        >
          <div className="drop-top">
            <span>INPUT 02</span>
            <span className="lock-tag">
              <Icon name="lock" size={10} />
              {' '}PRESET OTOMATIS
            </span>
          </div>

          <div className="drop-mid">
            <div
              className="drop-ic"
              style={{
                background: 'var(--ok-bg)',
                color: 'var(--ok)',
              }}
            >
              <Icon name="check-circle" size={20} />
            </div>

            <h3>Genom Acuan Baku (Reference FASTA)</h3>
            <p className="lock-id">
              NC_045512.2 (SARS-CoV-2 Wuhan-Hu-1)
            </p>
            <small>
              Referensi terpasang otomatis di backend.
              Pengguna tidak perlu mengunggah FASTA.
            </small>
          </div>

          <div className="drop-foot">
            <span>Terkunci (tidak dapat diubah)</span>
            <Icon name="lock" size={11} />
          </div>
        </div>
      </div>

      <section className="valid">
        <div className="valid-head">
          <div>
            <h2>
              <Icon name="shield-check" size={13} />
              {' '}Pemeriksaan Awal FASTQ
            </h2>

            <p>
              Pemeriksaan ekstensi, ukuran, dan signature gzip.
              Integritas isi serta pasangan reads akan
              divalidasi backend saat analisis dikirim.
            </p>
          </div>

          <div className="row" style={{ gap: 8 }}>
            <span className="muted" style={{ fontSize: 11 }}>
              Status Batch:
            </span>

            <span
              className={`badge-s ${
                ready ? 'ok' : phase === 'invalid' ? 'bad' : ''
              }`}
            >
              {stateLabel}
            </span>
          </div>
        </div>

        <div className="v-row th">
          <span>BERKAS</span>
          <span>UKURAN</span>
          <span>1. FORMAT</span>
          <span>2. INTEGRITAS</span>
          <span>STATUS</span>
        </div>

        {ROWS.map(([key, type]) => {
          const file = files[key]
          const check = checks[key]
          const server = summary(type)

          return (
            <div className="v-row" key={key}>
              <span className="row" style={{ gap: 8 }}>
                <Icon name="file" size={13} />
                {file?.name || type}
              </span>

              <span>
                {file ? formatSize(file.size) : '-'}
              </span>

              <span
                className={
                  check ? (check.ok ? 'ok' : 'bad') : 'mu'
                }
              >
                {check
                  ? check.ok ? '✓ Lolos' : '✕ Gagal'
                  : validating && file ? 'Memeriksa...' : '-'}
              </span>

              <span
                className={
                  server?.validation_status === 'PASS'
                    ? 'ok'
                    : 'mu'
                }
              >
                {server
                  ? server.validation_status === 'PASS'
                    ? '✓ Lolos'
                    : '✕ Gagal'
                  : 'Saat dikirim'}
              </span>

              <span className={check?.ok ? 'ok' : 'mu'}>
                {server?.validation_status === 'PASS'
                  ? '● Valid server'
                  : check?.ok
                    ? '● Lolos pemeriksaan'
                    : '-'}
              </span>
            </div>
          )
        })}

        <div className="v-row">
          <span className="row">
            <Icon name="lock" size={13} />
            {' '}FASTA NC_045512.2
          </span>
          <span className="mu">-</span>
          <span className="ok">✓ Preset</span>
          <span className="ok">✓ Sistem</span>
          <span className="ok">● Terpasang</span>
        </div>
      </section>

      {pairError && (
        <p className="alert error" role="alert">
          {pairError}
        </p>
      )}

      {(checks.r1?.ok === false ||
        checks.r2?.ok === false) && (
        <p className="alert error" role="alert">
          {checks.r1?.ok === false &&
            `R1: ${checks.r1.message} `}
          {checks.r2?.ok === false &&
            `R2: ${checks.r2.message}`}
        </p>
      )}

      <div className="layers">
        <div className="layer">
          <Icon name="check-circle" size={12} />
          <div>
            <b>Lapis 1: Pemeriksaan Format</b>
            <span>
              Ekstensi, ukuran, dan signature gzip.
            </span>
          </div>
        </div>

        <div className="layer">
          <Icon name="shield-check" size={12} />
          <div>
            <b>Lapis 2: Validasi Integritas</b>
            <span>
              Pemeriksaan struktur FASTQ dan pasangan reads
              dilakukan backend sebelum run dibuat.
            </span>
          </div>
        </div>
      </div>

      <section className="params">
        <div className="params-head">
          <div>
            <h2>
              <Icon name="info" size={13} />
              {' '}Parameter Analisis
            </h2>

            <p>
              Pilih Default atau Custom setelah memilih FASTQ.
              Mengubah parameter tidak menghapus file.
            </p>
          </div>

          <div
            className="seg2"
            role="group"
            aria-label="Mode parameter"
          >
            <button
              type="button"
              className={!custom ? 'on' : ''}
              disabled={locked}
              onClick={() => analysisDraft.setMode('default')}
            >
              Default (Direkomendasikan)
            </button>

            <button
              type="button"
              className={custom ? 'on' : ''}
              disabled={locked}
              onClick={() => analysisDraft.setMode('custom')}
            >
              Custom
            </button>
          </div>
        </div>

        <div className="params-grid">
          {PARAM_GROUPS.map((group) => (
            <div className="pgroup" key={group.station}>
              <div className="pgroup-t">
                <b>{group.title}</b>
                <span>{group.tool}</span>
              </div>

              {group.params.map((param) => (
                <div className="pfield" key={param.key}>
                  <label htmlFor={`p-${param.key}`}>
                    <span>{param.label}</span>
                    <small>
                      {param.op} {rangeText(param)}
                    </small>
                  </label>

                  <div className="pinput">
                    <input
                      id={`p-${param.key}`}
                      className={`txt ${
                        errors[param.key] ? 'err' : ''
                      }`}
                      type="number"
                      inputMode="decimal"
                      step={param.step ?? (param.int ? 1 : 'any')}
                      min={param.min}
                      max={param.max}
                      value={
                        custom
                          ? vals[param.key]
                          : String(param.def)
                      }
                      disabled={!custom || locked}
                      onChange={(e) =>
                        analysisDraft.setValues({
                          ...vals,
                          [param.key]: e.target.value,
                        })
                      }
                    />

                    <em>{param.unit}</em>
                  </div>

                  {errors[param.key] ? (
                    <span className="perr" role="alert">
                      {errors[param.key]}
                    </span>
                  ) : (
                    <span className="phint">
                      {param.hint}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="params-foot">
          <span>
            {custom
              ? 'Mode Custom: atur keenam parameter sebelum menjalankan analisis.'
              : 'Mode Default: menggunakan preset backend.'}
          </span>

          <span>
            Parameter disimpan di database saat upload final.
            Nilai default bukan ambang yang tervalidasi klinis.
          </span>

          {custom && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={locked}
              onClick={() => analysisDraft.restoreDefaults()}
            >
              Kembalikan ke default
            </button>
          )}
        </div>
      </section>

      {error && (
        <p
          className="alert error"
          role="alert"
          style={{ marginTop: 16 }}
        >
          {error}
        </p>
      )}

      <div className="run-bar">
        <button
          type="button"
          className="btn btn-ghost"
          disabled={busy}
          onClick={handleReset}
        >
          <Icon name="refresh" size={13} />
          {' '}Atur ulang draft
        </button>

        <div className="row" style={{ gap: 16 }}>
          <div>
            <div className="st-label">
              STATUS TOMBOL EKSEKUSI
            </div>

            <div className={`st-msg ${ready ? 'ok' : ''}`}>
              {phase === 'uploading'
                ? 'Mengunggah dan memvalidasi FASTQ di backend...'
                : phase === 'starting'
                  ? 'Memulai pipeline analisis...'
                  : result?.run_id && phase === 'retry'
                    ? 'Run sudah dibuat. Silakan coba jalankan lagi.'
                    : ready
                      ? 'FASTQ siap dikirim. Parameter bisa diubah.'
                      : 'Pilih dua FASTQ dan selesaikan pemeriksaan awal.'}
            </div>
          </div>

          <button
            type="button"
            className="btn-run"
            disabled={
              (!ready && !result?.run_id) ||
              busy ||
              validating ||
              paramsInvalid
            }
            onClick={handleRun}
          >
            {busy ? (
              <span className="spinner" />
            ) : (
              <Icon name="play" size={14} />
            )}

            {' '}
            {phase === 'uploading'
              ? 'Mengunggah...'
              : phase === 'starting'
                ? 'Memulai...'
                : result?.run_id && phase === 'retry'
                  ? 'Coba jalankan lagi'
                  : 'Jalankan analisis (One-Click)'}
          </button>
        </div>
      </div>
    </>
  )
}
