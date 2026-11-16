import FilterAudit from './FilterAudit'
import { useEffect, useMemo, useState } from 'react'
import {
  readMetrics, normalizeVariants, SORTS, sortVariants,
  filterVariants, toCsv, downloadText,
} from '../lib/risk'
import { downloadFile } from '../lib/api'
import Icon from './Icon'
import './result.css'

const display = v => v === null || v === undefined || v === '' ? '-' : String(v)
const percentage = v => v == null ? '-' : `${Number(v).toFixed(2)}%`

function Flank({ v }) {
  const left = v.flank_left ?? ''
  const right = v.flank_right ?? ''
  const legacy = v.flanking_sequence ?? v.flank_seq ?? ''
  const hasFlank = Boolean(left || right || legacy)
  const sequence = left || right ? `${left}${v.ref_allele ?? ''}${right}` : legacy
  const mid = left || right ? left.length : Math.floor(legacy.length / 2)

  return (
    <div className="panel">
      <div className="row-h">
        <h3><Icon name="search" size={13} /> Detail sekuens varian {display(v.position)}</h3>
        <span className="chip teal">NC_045512.2</span>
      </div>
      <div className="lokus">
        <span>Gen: <b>{display(v.gene)}</b></span>
        <span>•</span>
        <span>Posisi genom: <b>{display(v.position)}</b></span>
      </div>
      {hasFlank ? (
        <div className="flank">
          <div className="l">
            <span>5' FLANKING</span><span className="mid">LOKUS VARIAN</span><span>3' FLANKING</span>
          </div>
          <div className="seq">
            <span>{sequence.slice(0, mid)}</span>
            <span className="mut">{display(v.ref_allele)} &gt; {display(v.alt_allele)}</span>
            <span>{left || right ? right : sequence.slice(mid + 1)}</span>
          </div>
          <div className="flank-foot">
            <span>Sekuens konteks referensi ({sequence.length} bp)</span>
            <button type="button" onClick={() => navigator.clipboard?.writeText(sequence)}>
              <Icon name="copy" size={11} /> Salin sekuens
            </button>
          </div>
        </div>
      ) : (
        <p className="muted" style={{ marginTop: 12 }}>
          Konteks sekuens belum tersedia dari backend.
        </p>
      )}
    </div>
  )
}

function Annotation({ v }) {
  return (
    <div className="panel">
      <div className="row-h"><h3>Anotasi fungsional SnpEff</h3></div>
      <div className="lokus" style={{ marginTop: 12, flexDirection: 'column', alignItems: 'flex-start' }}>
        <span>Gen: <b>{display(v.gene)}</b></span>
        <span>Efek: <b>{display(v.snpeff_effect)}</b></span>
        <span>Impact SnpEff: <b>{display(v.impact)}</b></span>
        <span>HGVS.c: <b>{display(v.hgvs_c)}</b></span>
        <span>HGVS.p: <b>{display(v.hgvs_p)}</b></span>
        <span>QUAL: <b>{display(v.qual)}</b> · DP: <b>{display(v.dp)}</b> · AF: <b>{display(v.af)}</b> · MQ: <b>{display(v.mq)}</b></span>
      </div>
      <p className="muted" style={{ marginTop: 12 }}>
        Impact merupakan kategori anotasi SnpEff, bukan prediksi risiko klinis atau immune escape.
      </p>
    </div>
  )
}

function Kpi({ label, number, note }) {
  return (
    <div className="kcard">
      <div><small>{label}</small><div className="big">{display(number)}</div></div>
      <p>{note}</p>
    </div>
  )
}

function VariantDetailModal({ variant, onClose }) {
  useEffect(() => {
    if (!variant) return
    const onKey = (event) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [variant, onClose])

  if (!variant) return null
  return (
    <div role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}
      style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 18, background: 'rgba(8,30,42,.65)' }}>
      <div role="dialog" aria-modal="true" aria-label={`Detail varian posisi ${variant.position}`}
        style={{ width: '100%', maxWidth: 940, maxHeight: '90vh', overflowY: 'auto', padding: 22, background: '#f8fafc', borderRadius: 14 }}>
        <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', gap: 16, marginBottom: 16 }}>
          <div>
            <h2 style={{ margin: 0 }}>Detail Varian Genomik</h2>
            <p className="muted">Posisi {display(variant.position)} · {display(variant.ref_allele)} &gt; {display(variant.alt_allele)}</p>
          </div>
          <button className="btn-r" type="button" autoFocus onClick={onClose}>Tutup ✕</button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(275px, 1fr))', gap: 16 }}>
          <Annotation v={variant} />
          <Flank v={variant} />
        </div>
      </div>
    </div>
  )
}

// mode: owner = peneliti; reader = pembaca publik, read-only
export default function ResultViewer({ data, runId, mode = 'owner', onToggle, saving, notice }) {
  const variants = useMemo(() => normalizeVariants(data), [data])
  const metrics = readMetrics(data)
  const [impact, setImpact] = useState('ALL')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('pos_asc')
  const [selectedVariant, setSelectedVariant] = useState(null)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')
  const reader = mode === 'reader'
  const isPublic = String(data?.visibility ?? '').toUpperCase() === 'PUBLIC'

  const shown = useMemo(
    () => sortVariants(filterVariants(variants, { impact, effect: query }), sort),
    [variants, impact, query, sort],
  )

  const [pdfError, setPdfError] = useState('')
  const [downloadingPdf, setDownloadingPdf] = useState(false)

  async function downloadPdf() {
    setPdfError('')
    setDownloadingPdf(true)
    try {
      await downloadFile(
        `/analysis/${encodeURIComponent(runId)}/export/pdf`,
        `${runId}_Variant_Report.pdf`,
      )
    } catch (err) {
      setPdfError(err.message || 'Gagal mengunduh PDF.')
    } finally {
      setDownloadingPdf(false)
    }
  }

  const impactCounts = useMemo(() => {
    const counts = { HIGH: 0, MODERATE: 0, LOW: 0, MODIFIER: 0 }
    for (const v of variants) {
      const k = String(v.impact ?? '').toUpperCase()
      if (Object.prototype.hasOwnProperty.call(counts, k)) counts[k] += 1
    }
    return Object.entries(counts).filter(([, count]) => count > 0)
  }, [variants])

  const effectCounts = useMemo(() => {
    const counts = {}
    for (const v of variants) {
      const raw = v.annotation_raw?.split(',')[0]?.split('|')[1]
      const fallback = v.snpeff_effect?.match(/\(([^()]*)\)\s*$/)?.[1]
      const effect = (raw || fallback || v.snpeff_effect || 'Tidak tersedia').split('&')[0]
      counts[effect] = (counts[effect] ?? 0) + 1
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8)
  }, [variants])

  async function downloadZip() {
    setDownloading(true)
    setDownloadError('')
    try {
      await downloadFile(
        `/analysis/${encodeURIComponent(runId)}/export/zip`,
        `${runId}_results.zip`,
      )
    } catch (err) {
      setDownloadError(err.message || 'Gagal mengunduh ZIP.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className={reader ? 'rv-reader' : ''}>
      <div className={`rv-head ${reader ? 'reader' : ''}`}>
        <div>
          <div className="rv-title">
            {reader ? <h1>{data.sample_name ?? runId}</h1> : <h1>Run <span>{runId}</span></h1>}
            <span className="tag-s"><i />{display(data?.status)}</span>
            {reader
              ? <span className="tag-s"><Icon name="globe" size={10} /> PUBLIC</span>
              : (
                <div className="seg" role="group" aria-label="Visibilitas">
                  <button type="button" className={!isPublic ? 'on' : ''} disabled={saving} onClick={() => isPublic && onToggle?.()}>
                    <Icon name="lock" size={10} /> Private
                  </button>
                  <button type="button" className={isPublic ? 'on' : ''} disabled={saving} onClick={() => !isPublic && onToggle?.()}>
                    <Icon name="globe" size={10} /> Public
                  </button>
                </div>
              )}
          </div>
          <div className="rv-meta">
            <span>Sampel: {display(data?.sample_name)}</span>
            <span className="dot">•</span>
            <span>Referensi: <code>NC_045512.2</code></span>
            <span className="dot">•</span>
            <span>Run: <code>{runId}</code></span>
          </div>
        </div>
        {!reader && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="btn-zip" type="button"
              disabled={downloadingPdf || data?.status !== 'COMPLETED'} onClick={downloadPdf}>
              <Icon name="download" size={13} />
              {downloadingPdf ? 'Menyiapkan PDF…' : 'Unduh Laporan PDF'}
            </button>
            <button className="btn-zip" type="button"
              disabled={downloading || data?.status !== 'COMPLETED'} onClick={downloadZip}>
              <Icon name="download" size={13} />
              {downloading ? 'Mengunduh…' : 'Unduh paket laporan (ZIP)'}
            </button>
          </div>
        )}
      </div>
      {notice && <p className="alert ok" role="status" style={{ marginTop: 12 }}>{notice}</p>}
      {downloadError && <p className="alert error" role="alert" style={{ marginTop: 12 }}>{downloadError}</p>}
      {pdfError && <p className="alert error" role="alert" style={{ marginTop: 12 }}>{pdfError}</p>}

      {String(data?.status).toUpperCase() === 'FAILED' && !reader && (
        <p className="alert error" style={{ marginTop: 14 }}>
          Analisis berhenti sebelum selesai. Hasil stasiun yang telah berhasil tetap tersedia
          pada halaman Progress dan dapat diunduh per berkas. Ekspor PDF/ZIP lengkap
          memerlukan backend yang mendukung laporan parsial.
        </p>
      )}
      <div className="rv-kpis">
        <Kpi label="Varian mentah" number={metrics.raw} note="Kandidat dari BCFtools" />
        <Kpi label="Varian PASS" number={metrics.passed ?? metrics.total ?? variants.length} note="Lolos quality filtering" />
        <Kpi label="Varian terfilter" number={metrics.filtered} note="Tidak memenuhi filter" />
        <Kpi label="Varian teranotasi" number={metrics.annotated} note={`SnpEff: ${display(metrics.annotation_status)}`} />
      </div>

      <section className="vt">
        <div className="vt-head">
          <div>
            <h2>Daftar Varian Teridentifikasi</h2>
            <p>Hasil variant calling, quality filtering, dan anotasi SnpEff</p>
          </div>
          <div className="vt-tools">
            <button type="button" className="btn-r" onClick={() => { setImpact('ALL'); setQuery(''); setSort('pos_asc'); setSelectedVariant(null) }}>
              Reset
            </button>
            <input value={query} onChange={e => setQuery(e.target.value)}
              placeholder="Cari posisi, gen, efek, atau HGVS..." aria-label="Cari varian" />
            <select value={impact} onChange={e => setImpact(e.target.value)} aria-label="Filter impact SnpEff">
              <option value="ALL">Semua impact</option>
              {['HIGH', 'MODERATE', 'LOW', 'MODIFIER'].map(v => <option value={v} key={v}>{v}</option>)}
            </select>
            <select value={sort} onChange={e => setSort(e.target.value)} aria-label="Urutkan varian">
              {Object.entries(SORTS).map(([key, label]) => <option value={key} key={key}>{label}</option>)}
            </select>
            <button className="btn-r" type="button" disabled={!shown.length}
              onClick={() => downloadText(`${runId}-varian.csv`, toCsv(shown))}>
              Unduh CSV
            </button>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Posisi</th><th>REF &gt; ALT</th><th>Gen</th>
                <th className="r">QUAL</th><th className="r">DP</th>
                <th className="r">AF</th><th>Efek SnpEff</th><th>Impact</th>
                <th className="c">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {shown.map(v => {
                const key = `${v.position}:${v.ref_allele}:${v.alt_allele}`
                return (
                  <tr key={v.id ?? key} className={selectedVariant === v ? 'sel' : ''}
                    onClick={() => setSelectedVariant(v)} style={{ cursor: 'pointer' }}>
                    <td className="pos">{display(v.position)}</td>
                    <td>{display(v.ref_allele)} &gt; {display(v.alt_allele)}</td>
                    <td>{display(v.gene)}</td>
                    <td className="r">{display(v.qual)}</td>
                    <td className="r">{display(v.dp)}</td>
                    <td className="r">
                      {v.af == null
                        ? '-'
                        : Number(v.af).toLocaleString('id-ID', {
                            maximumFractionDigits: 4
                          })}
                    </td>

                    <td>{display(v.snpeff_effect)}</td>
                    <td>{display(v.impact)}</td>
                    <td className="c">
                      <button type="button" className="btn-ins" onClick={e => { e.stopPropagation(); setSelectedVariant(v) }}>Lihat Detail</button>
                    </td>
                  </tr>
                )
              })}
              {!shown.length && (
                <tr><td colSpan={9} className="empty">
                  {variants.length
                    ? 'Tidak ada varian yang cocok dengan filter.'
                    : 'Belum ada varian yang tersedia pada respons hasil analisis.'}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="vt-foot">
          <span>Menampilkan {shown.length} dari {variants.length} varian</span>
          <span>Referensi NC_045512.2 · SnpEff</span>
        </div>
      </section>
      
      {!reader && runId && (
        <FilterAudit runId={runId} />
      )}

      
      <section className="panel" style={{ marginTop: 16 }}>
        <h3>Ringkasan kualitas data</h3>

        <div className="quality-summary-grid">
          <div className="quality-metric">
            <span className="quality-label">Q20 setelah preprocessing</span>
            <span className="quality-value">{percentage(metrics.q20).replace('.', ',')}</span>
          </div>

          <div className="quality-metric">
            <span className="quality-label">Q30 setelah preprocessing</span>
            <span className="quality-value">{percentage(metrics.q30).replace('.', ',')}</span>
          </div>

          <div className="quality-metric">
            <span className="quality-label">Mapping rate</span>
            <span className="quality-value">{percentage(metrics.mapping).replace('.', ',')}</span>
          </div>

          <div className="quality-metric">
            <span className="quality-label">Mean depth</span>
            <span className="quality-value">
              {metrics.depth == null
                ? '-'
                : `${Number(metrics.depth).toLocaleString('id-ID', { maximumFractionDigits: 2 })}×`}
            </span>
          </div>

          <div className="quality-metric">
            <span className="quality-label">Ts/Tv PASS</span>
            <span className="quality-value">
              {metrics.tstv == null
                ? '-'
                : Number(metrics.tstv).toLocaleString('id-ID', { maximumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        <p className="quality-note">
          Q20 dan Q30 berasal dari hasil preprocessing fastp.
          Mapping rate dan mean depth berasal dari tahap alignment.
          Ts/Tv PASS menggambarkan rasio transisi terhadap transversi
          pada varian yang lolos quality filtering.
        </p>
      </section>


      <section className="panel" style={{ marginTop: 16 }}>
        <h3>Visualisasi statistik varian PASS</h3>
        <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
          Grafik di bawah berasal dari varian tersimpan yang lolos filter dan dianotasi.
          Komposisi raw SNP/INDEL dan Ts/Tv raw ditampilkan dalam PDF bila raw VCF tersedia.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 24, marginTop: 16 }}>
          <div>
            <h4 style={{ marginBottom: 10 }}>Kategori IMPACT SnpEff</h4>
            {impactCounts.length ? impactCounts.map(([name, count]) => (
              <div key={name} style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span>{name}</span><b>{count}</b>
                </div>
                <div style={{ height: 9, background: '#e3eced', borderRadius: 5, marginTop: 5 }}>
                  <div style={{ height: '100%', width: `${100 * count / variants.length}%`, background: '#138d90', borderRadius: 5 }} />
                </div>
              </div>
            )) : <p className="muted">Kategori IMPACT belum tersedia.</p>}
          </div>
          <div>
            <h4 style={{ marginBottom: 10 }}>Efek anotasi terbanyak</h4>
            {effectCounts.length ? effectCounts.map(([name, count]) => (
              <div key={name} style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, gap: 8 }}>
                  <span>{name}</span><b>{count}</b>
                </div>
                <div style={{ height: 9, background: '#e3eced', borderRadius: 5, marginTop: 5 }}>
                  <div style={{ height: '100%', width: `${100 * count / variants.length}%`, background: '#3b7396', borderRadius: 5 }} />
                </div>
              </div>
            )) : <p className="muted">Efek anotasi belum tersedia.</p>}
          </div>
        </div>
        {variants.some(v => Number.isFinite(Number(v.position))) && (
          <div style={{ marginTop: 20 }}>
            <h4>Posisi varian PASS di sepanjang genom (NC_045512.2)</h4>
            <svg role="img" aria-label="Plot posisi varian sepanjang genom acuan"
              viewBox="0 0 900 75" style={{ width: '100%', marginTop: 10 }}>
              <line x1="25" y1="30" x2="875" y2="30" stroke="#345464" strokeWidth="3" />
              {variants.filter(v => Number(v.position) >= 1 && Number(v.position) <= 29903).map((v, i) => (
                <line key={`${v.id ?? i}`} x1={25 + (Number(v.position) - 1) * 850 / 29902}
                  x2={25 + (Number(v.position) - 1) * 850 / 29902}
                  y1="15" y2="31" stroke="#138d90" strokeWidth="2" />
              ))}
              <text x="25" y="58" fill="#526879" fontSize="14">1 bp</text>
              <text x="875" y="58" fill="#526879" textAnchor="end" fontSize="14">29.903 bp</text>
            </svg>
          </div>
        )}
        <p className="muted" style={{ fontSize: 11, marginTop: 10 }}>
          IMPACT SnpEff bukan skor risiko klinis atau prediksi immune escape.
        </p>
      </section>


      {reader && (
        <div className="ro-note">
          <Icon name="info" size={14} />
          <div>
            <b>Mode Pembaca Publik (Read-Only)</b>
            <p>Anda dapat melihat hasil yang dipublikasikan, tetapi tidak dapat mengubah visibilitas analisis.</p>
          </div>
        </div>
      )}
      <VariantDetailModal variant={selectedVariant} onClose={() => setSelectedVariant(null)} />
    </div>
  )
}
