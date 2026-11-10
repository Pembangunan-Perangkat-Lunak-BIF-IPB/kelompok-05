import { useMemo, useState } from 'react'
import { RISK_ORDER, RISK_LABEL, SORTS, readMetrics, sortVariants, filterVariants, toCsv, downloadText } from '../lib/risk'
import Icon from './Icon'
import './result.css'

const AA3 = { Ala: ['A', 'Alanine'], Arg: ['R', 'Arginine'], Asn: ['N', 'Asparagine'], Asp: ['D', 'Aspartate'], Cys: ['C', 'Cysteine'], Gln: ['Q', 'Glutamine'], Glu: ['E', 'Glutamate'], Gly: ['G', 'Glycine'], His: ['H', 'Histidine'], Ile: ['I', 'Isoleucine'], Leu: ['L', 'Leucine'], Lys: ['K', 'Lysine'], Met: ['M', 'Methionine'], Phe: ['F', 'Phenylalanine'], Pro: ['P', 'Proline'], Ser: ['S', 'Serine'], Thr: ['T', 'Threonine'], Trp: ['W', 'Tryptophan'], Tyr: ['Y', 'Tyrosine'], Val: ['V', 'Valine'] }
const DOT = { HIGH: '#b4233c', MODERATE: '#a86400', LOW: '#14b8a6', OUTSIDE_EPITOPE: '#bec9c8' }

export function RiskBadge({ level }) {
  if (!level) return <span className="muted">-</span>
  return <span className={`rk rk-${level.toLowerCase()}`}>{RISK_LABEL[level] ?? level}</span>
}

const parseAA = (effect) => {
  const m = /p\.([A-Z][a-z]{2})\d+([A-Z][a-z]{2})/.exec(effect ?? '')
  return m && AA3[m[1]] && AA3[m[2]] ? [AA3[m[1]], AA3[m[2]]] : null
}

function Flank({ v }) {
  const seq = v.flanking_sequence ?? v.flank_seq ?? null
  const aa = parseAA(v.snpeff_effect)
  const mid = seq ? Math.floor(seq.length / 2) : 0
  return (
    <div className="panel">
      <div className="row-h"><h3><Icon name="search" size={13} /> Flanking area varian {v.position} (20-50 bp tiap sisi)</h3><span className="chip teal">SPIKE RECEPTOR-BINDING DOMAIN</span></div>
      <div className="lokus"><span>Lokus: <b>{v.gene ?? 'Spike (S-Gene)'}</b></span><span>•</span><span>Posisi Genom Acuan: <b>{v.position}</b></span></div>
      {seq ? (
        <div className="flank">
          <div className="l"><span>5' FLANKING</span><span className="mid">MUTATION LOCUS</span><span>3' FLANKING</span></div>
          <div className="seq"><span>{seq.slice(0, mid)}</span><span className="mut">{v.ref_allele} &gt; {v.alt_allele}</span><span>{seq.slice(mid + 1)}</span></div>
          {aa && <div className="aa"><b>TRANSLASI ASAM AMINO:</b><span>{aa[0][0]} ({aa[0][1]})</span>→<span className="m">{aa[1][0]} ({aa[1][1]})</span></div>}
        </div>
      ) : (
        <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>Urutan flanking belum dikirim backend untuk varian ini.</p>
      )}
      {seq && (
        <div className="flank-foot"><span>Panjang window flanking: {seq.length} bp total</span>
          <button onClick={() => navigator.clipboard?.writeText(seq)}><Icon name="copy" size={11} /> Salin FASTA Flank</button></div>
      )}
    </div>
  )
}

function Impact({ v }) {
  const g = Number(v.grantham_score)
  const has = v.grantham_score != null && !Number.isNaN(g)
  const radical = has && g > 100
  return (
    <div className="panel">
      <div className="row-h"><h3>Evaluasi Dampak Klinis</h3></div>
      <div className="gr">
        <div><small>SKOR GRANTHAM</small><div className="n" style={{ color: radical ? '#b4233c' : 'var(--ink)' }}>{has ? g : '-'}</div><div className="t" style={{ color: radical ? '#b4233c' : 'var(--ink2)' }}>{has ? (radical ? 'Substitusi Radikal (>100)' : g > 50 ? 'Substitusi Moderat' : 'Substitusi Konservatif') : 'Tidak tersedia'}</div></div>
        <RiskBadge level={v.risk_level} />
      </div>
      <p className="gr-note">{has ? `Grantham score ${g} pada posisi ${v.position} (${v.snpeff_effect ?? 'varian'}). ${radical ? 'Mengindikasikan substitusi asam amino radikal yang berpotensi menurunkan netralisasi antibodi.' : ''}` : 'Belum ada skor Grantham untuk varian ini.'}</p>
      <div className="db">DATABASE REKOMENDASI:<div>{(v.iedb_id ?? v.epitope_id) && <span>IEDB: {v.iedb_id ?? v.epitope_id}</span>}<span>GISAID Marker</span></div></div>
    </div>
  )
}

// mode: 'owner' (Peneliti, Private/Public) | 'reader' (Pembaca, read-only)
export default function ResultViewer({ data, runId, mode = 'owner', onToggle, saving, notice }) {
  const variants = useMemo(() => data?.variant_results ?? [], [data])
  const metrics = readMetrics(data)
  const [risk, setRisk] = useState('ALL')
  const [q, setQ] = useState('')
  const [sort, setSort] = useState('default')
  const [picked, setPicked] = useState(null)
  const reader = mode === 'reader'

  const shown = useMemo(() => sortVariants(filterVariants(variants, { risk, effect: q }), sort), [variants, risk, q, sort])
  const sel = picked ?? shown.find((v) => v.risk_level === 'HIGH') ?? shown[0] ?? null
  const high = variants.filter((v) => v.risk_level === 'HIGH')
  const epitope = variants.filter((v) => v.risk_level && v.risk_level !== 'OUTSIDE_EPITOPE')
  const isPublic = data?.visibility === 'PUBLIC'
  const total = metrics.total ?? variants.length
  const date = data?.created_at ? new Date(data.created_at).toLocaleString('id-ID') : null

  return (
    <div className={reader ? 'rv-reader' : ''}>
      <div className={`rv-head ${reader ? 'reader' : ''}`}>
        <div>
          <div className="rv-title">
            {reader ? <h1>{data.sample_name ?? runId}</h1> : <h1>Run <span>{runId}</span></h1>}
            <span className="tag-s"><i />SELESAI</span>
            {reader
              ? <span className="tag-s"><Icon name="globe" size={10} />PUBLIC</span>
              : (
                <div className="seg" role="group" aria-label="Visibilitas">
                  <button className={!isPublic ? 'on' : ''} disabled={saving} onClick={() => isPublic && onToggle()}><Icon name="lock" size={10} /> Private</button>
                  <button className={isPublic ? 'on' : ''} disabled={saving} onClick={() => !isPublic && onToggle()}><Icon name="globe" size={10} /> Public</button>
                </div>
              )}
          </div>
          <div className="rv-meta">
            {reader ? <span>Dibagikan oleh Peneliti. Tampilan hanya baca (Read-only viewer) · Run <code>{runId}</code></span> : (
              <>
                <span>Sampel: {data.sample_name}</span><span className="dot">•</span>
                <span>Genom Acuan: <code>NC_045512.2</code></span>
                {date && <><span className="dot">•</span><span>Tanggal Analisis: {date}</span></>}
              </>
            )}
          </div>
        </div>
        {/* TODO(backend): endpoint unduh paket laporan (ZIP) belum ada di frontend_m9 */}
        <button className="btn-zip" disabled title="Unduhan ZIP belum tersedia dari backend"><Icon name="download" size={13} /> Unduh paket laporan (ZIP)</button>
      </div>
      {notice && <p className="alert ok" role="status" style={{ marginTop: 12 }}>{notice}</p>}

      <div className="rv-kpis">
        <div className="kcard"><div><small>Varian terpanggil (QC)</small><div className="big">{total} <span className="kpill">PASS FILTER</span></div></div><p>{metrics.tstv != null ? `Rasio Ts/Tv ${metrics.tstv}` : 'Hasil filter kualitas varian'}</p></div>
        <div className="kcard" style={{ '--k': 'rgba(204,226,250,.2)' }}><div><small>Wilayah epitope <span className="kpill blue">IEDB CROSS-MATCHED</span></small><div className="big" style={{ color: '#004d89' }}>{epitope.length}</div></div><p>{total ? `${Math.round((epitope.length / total) * 100)}% dari total varian` : '-'}</p></div>
        <div className="kcard" style={{ '--k': 'rgba(255,218,214,.3)' }}><div><small>Immune escape alerts <span className="kpill red">HIGH ESCAPE RISK</span></small><div className="big" style={{ color: '#b4233c' }}>{high.length}</div></div><p>{high.length ? `${high.slice(0, 3).map((v) => (/p\.[A-Za-z]{3}(\d+)/.exec(v.snpeff_effect ?? '')?.[0] ?? v.position)).join(' & ')}` : 'Tidak ada varian risiko tinggi'}</p></div>
        <div className="kcard"><div><small>QC threshold status <span className="kpill">MET</span></small></div><div className="qc-chips"><span>DP≥10×</span>•<span>MQ≥30</span>•<span>QUAL≥30</span>•<span>AF≥0.20</span></div><p>Standar Konsensus Klinis SARS-CoV-2</p></div>
      </div>

      <section className="vt">
        <div className="vt-head">
          <div><h2>Daftar Varian Teridentifikasi &amp; Prediksi Immune Escape</h2><p>Anotasi fungsional SnpEff dan kalkulasi disparitas fisikokimia Grantham</p></div>
          <div className="vt-tools">
            <button className="btn-r" onClick={() => { setRisk('ALL'); setQ(''); setSort('default') }}>Reset</button>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari efek SnpEff (mis. missense)..." aria-label="Cari varian" />
            <select value={risk} onChange={(e) => setRisk(e.target.value)} aria-label="Filter risiko">
              <option value="ALL">Semua Varian ({variants.length})</option>
              {RISK_ORDER.map((r) => <option key={r} value={r}>{RISK_LABEL[r]}</option>)}
            </select>
            <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Urutkan">{Object.entries(SORTS).map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select>
            <button className="btn-r" disabled={!shown.length} onClick={() => downloadText(`${runId}-varian.csv`, toCsv(shown))}>Unduh CSV</button>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Posisi</th><th>Ref &gt; Alt</th><th className="r">QUAL</th><th className="r">DP (read depth)</th><th>Efek SnpEff</th><th className="r">Grantham</th><th className="c">{reader ? 'Risiko escape' : 'Risiko'}</th>{!reader && <th className="c">Aksi</th>}</tr></thead>
            <tbody>
              {shown.map((v) => (
                <tr key={v.id ?? `${v.position}-${v.alt_allele}`} className={sel === v ? 'sel' : ''} onClick={() => setPicked(v)} style={{ cursor: 'pointer' }}>
                  <td className="pos">{v.position}</td><td>{v.ref_allele} &gt; {v.alt_allele}</td>
                  <td className="r">{v.qual ?? '-'}</td><td className="r">{v.dp != null ? `${v.dp}×` : '-'}</td>
                  <td><span className="effect"><i style={{ background: DOT[v.risk_level] ?? '#bec9c8' }} />{v.snpeff_effect ?? '-'}</span></td>
                  <td className="r" style={{ color: v.risk_level === 'HIGH' ? '#b4233c' : v.risk_level === 'MODERATE' ? '#a86400' : undefined }}>{v.grantham_score ?? '-'}</td>
                  <td className="c"><RiskBadge level={v.risk_level} /></td>
                  {!reader && <td className="c"><button className="btn-ins" onClick={(e) => { e.stopPropagation(); setPicked(v) }}>Inspeksi</button></td>}
                </tr>
              ))}
              {!shown.length && <tr><td colSpan={8} className="empty">{variants.length ? 'Tidak ada varian yang cocok dengan filter.' : 'Tidak ada varian yang lolos quality filtering (DP≥10, MQ≥30, QUAL≥30, AF≥0,20).'}</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="vt-foot"><span>Menampilkan {shown.length} dari {variants.length} varian terpilih di query viewport</span><span>● SNPEFF DATABASE: CLINVAR</span></div>
      </section>

      {sel && <div className="insp"><Flank v={sel} /><Impact v={sel} /></div>}
      {reader && (
        <div className="ro-note"><Icon name="info" size={14} /><div><b>Mode Pembaca Publik (Read-Only)</b><p>Tampilan ini bersifat read-only bagi peran Pembaca. Anda tidak dapat mengubah visibilitas run atau mengunggah data baru.</p></div></div>
      )}
    </div>
  )
}
