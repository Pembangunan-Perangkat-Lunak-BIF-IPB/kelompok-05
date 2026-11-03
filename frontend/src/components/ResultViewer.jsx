import { useMemo, useState } from 'react'
import { RISK_ORDER, RISK_LABEL, SORTS, readMetrics, fmtPct, fmtNum, sortVariants, filterVariants, toCsv, downloadText } from '../lib/risk'
import '../pages/pages.css'
import './result.css'

export function RiskBadge({ level }) {
  if (!level) return <span className="muted">-</span>
  return <span className={`risk risk-${level.toLowerCase()}`}>{RISK_LABEL[level] ?? level}</span>
}

function Metric({ label, value, hint }) {
  return (
    <div className="card metric">
      <small>{label}</small>
      <strong>{value}</strong>
      {hint && <span className="muted">{hint}</span>}
    </div>
  )
}

function Inspector({ v, onClose }) {
  const flank = v.flanking_sequence ?? v.flank_seq ?? null
  return (
    <section className="card inspect" aria-label={`Detail varian posisi ${v.position}`}>
      <div className="row-between">
        <h3>Inspeksi varian posisi {v.position}</h3>
        <button className="btn" onClick={onClose}>Tutup</button>
      </div>
      <dl className="kv">
        <div><dt>Substitusi</dt><dd>{v.ref_allele} &gt; {v.alt_allele}</dd></div>
        <div><dt>QUAL</dt><dd>{v.qual ?? '-'}</dd></div>
        <div><dt>DP</dt><dd>{v.dp != null ? `${v.dp}x` : '-'}</dd></div>
        <div><dt>AF</dt><dd>{v.af ?? v.allele_frequency ?? '-'}</dd></div>
        <div><dt>Efek SnpEff</dt><dd>{v.snpeff_effect ?? '-'}</dd></div>
        <div><dt>Grantham</dt><dd>{v.grantham_score ?? '-'}</dd></div>
        <div><dt>Epitope IEDB</dt><dd>{v.iedb_id ?? v.epitope_id ?? '-'}</dd></div>
        <div><dt>Tingkat risiko</dt><dd><RiskBadge level={v.risk_level} /></dd></div>
      </dl>
      <h4>Area flanking (20–50 bp)</h4>
      {flank
        ? <pre className="flank">{flank}</pre>
        : <p className="muted">Urutan flanking belum dikirim backend untuk varian ini.</p>}
    </section>
  )
}

// Tampilan hasil: dipakai Peneliti (pemilik) dan Pembaca Publik (readOnly)
export default function ResultViewer({ data, fileName = 'hasil' }) {
  const variants = useMemo(() => data?.variant_results ?? [], [data])
  const metrics = readMetrics(data)
  const [risk, setRisk] = useState('ALL')
  const [effect, setEffect] = useState('')
  const [min, setMin] = useState('')
  const [max, setMax] = useState('')
  const [sort, setSort] = useState('default')
  const [picked, setPicked] = useState(null)

  const shown = useMemo(
    () => sortVariants(filterVariants(variants, { risk, effect, min, max }), sort),
    [variants, risk, effect, min, max, sort],
  )
  const counts = useMemo(() => {
    const c = Object.fromEntries(RISK_ORDER.map((r) => [r, 0]))
    variants.forEach((v) => { if (c[v.risk_level] !== undefined) c[v.risk_level] += 1 })
    return c
  }, [variants])
  const filtered = risk !== 'ALL' || effect || min !== '' || max !== ''

  function reset() { setRisk('ALL'); setEffect(''); setMin(''); setMax(''); setSort('default') }

  return (
    <>
      <section className="grid-6" aria-label="Ringkasan metrik run">
        <Metric label="Q20" value={fmtPct(metrics.q20)} />
        <Metric label="Q30" value={fmtPct(metrics.q30)} />
        <Metric label="Mapping rate" value={fmtPct(metrics.mapping)} />
        <Metric label="Read depth" value={metrics.depth === null ? '-' : `${fmtNum(metrics.depth, 1)}x`} />
        <Metric label="Total varian" value={metrics.total ?? variants.length} />
        <Metric label="Rasio Ts/Tv" value={fmtNum(metrics.tstv)} />
      </section>

      <section className="card">
        <div className="legend" aria-label="Ringkasan tingkat risiko">
          {RISK_ORDER.map((r) => (
            <button key={r} className={`risk risk-${r.toLowerCase()} chip ${risk === r ? 'on' : ''}`}
              onClick={() => setRisk(risk === r ? 'ALL' : r)} aria-pressed={risk === r}>
              {RISK_LABEL[r]} · {counts[r]}
            </button>
          ))}
        </div>

        <div className="filters">
          <label>Tingkat risiko
            <select className="input" value={risk} onChange={(e) => setRisk(e.target.value)}>
              <option value="ALL">Semua</option>
              {RISK_ORDER.map((r) => <option key={r} value={r}>{RISK_LABEL[r]}</option>)}
            </select>
          </label>
          <label>Efek SnpEff
            <input className="input" value={effect} placeholder="mis. missense" onChange={(e) => setEffect(e.target.value)} />
          </label>
          <label>Posisi dari
            <input className="input" type="number" min="1" value={min} onChange={(e) => setMin(e.target.value)} />
          </label>
          <label>sampai
            <input className="input" type="number" min="1" value={max} onChange={(e) => setMax(e.target.value)} />
          </label>
          <label>Urutkan
            <select className="input" value={sort} onChange={(e) => setSort(e.target.value)}>
              {Object.entries(SORTS).map(([k, t]) => <option key={k} value={k}>{t}</option>)}
            </select>
          </label>
        </div>
        {min !== '' && max !== '' && Number(min) > Number(max) && (
          <p className="msg bad" role="alert">Batas awal posisi tidak boleh lebih besar dari batas akhir.</p>
        )}

        <div className="row-between" style={{ marginTop: 8 }}>
          <span className="muted">Menampilkan {shown.length} dari {variants.length} varian</span>
          <span className="actions">
            {filtered && <button className="btn" onClick={reset}>Reset filter</button>}
            <button className="btn" disabled={!shown.length}
              onClick={() => downloadText(`${fileName}-varian.csv`, toCsv(shown))}>Unduh CSV</button>
          </span>
        </div>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Posisi</th><th>Ref &gt; Alt</th><th>QUAL</th><th>DP</th><th>Efek SnpEff</th><th>Grantham</th><th>Risiko</th><th>Aksi</th></tr>
            </thead>
            <tbody>
              {shown.map((v) => (
                <tr key={v.id ?? `${v.position}-${v.alt_allele}`} className={picked?.id === v.id && v.id != null ? 'sel' : ''}>
                  <td>{v.position}</td>
                  <td>{v.ref_allele} &gt; {v.alt_allele}</td>
                  <td>{v.qual ?? '-'}</td>
                  <td>{v.dp != null ? `${v.dp}x` : '-'}</td>
                  <td>{v.snpeff_effect ?? '-'}</td>
                  <td>{v.grantham_score ?? '-'}</td>
                  <td><RiskBadge level={v.risk_level} /></td>
                  <td><button className="btn btn-sm" onClick={() => setPicked(v)}>Inspeksi</button></td>
                </tr>
              ))}
              {!shown.length && (
                <tr><td colSpan={8}>
                  {variants.length
                    ? 'Tidak ada varian yang cocok dengan filter.'
                    : 'Belum ada varian. Pipeline analisis belum menghasilkan data.'}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {picked && <Inspector v={picked} onClose={() => setPicked(null)} />}
    </>
  )
}
