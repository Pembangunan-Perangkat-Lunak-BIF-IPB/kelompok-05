// VarEscape M11 V3 — metrik asli backend, bukan skor atau penilaian klinis frontend.
export const STATION_COUNT = 4
export const STATIONS = {
  1: { name: 'Quality Control & Preprocessing', tool: 'fastp' },
  2: { name: 'Read Alignment', tool: 'BWA-MEM2 & SAMtools' },
  3: { name: 'Variant Calling', tool: 'BCFtools' },
  4: { name: 'Quality Filtering & Annotation', tool: 'BCFtools filter & SnpEff' },
}
const finite = v => v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v)
const fmt = (v, d = 2) => finite(v) == null ? '-' : Number(v).toLocaleString('id-ID', {maximumFractionDigits:d})
const pct = v => finite(v) == null ? null : `${fmt(v)}%`
const number = v => finite(v) == null ? null : fmt(v, 0)
const pairPct = (a,b) => finite(a) == null && finite(b) == null ? null : `${pct(a) ?? '-'} → ${pct(b) ?? '-'}`
const row = (title, value, hint) => [title, value, hint]
export function stationDiagnostic(data, runId, n, done) {
  const summary = data?.summary_metrics ?? {}
  const status = data?.stations_diagnostic?.[`station_${n}`] ?? data?.stations_diagnostic?.[n] ?? {}
  const m = {...summary,...(status.metrics || {})}
  const interpretation = data?.station_interpretations?.[`station_${n}`] ?? {}
  const metricRows = {
    1: [
      
      row(
        'Passed reads',
        number(m.reads_after),
        'Jumlah reads yang lolos preprocessing'
      ),
      row(
        'Filtered reads',
        finite(m.reads_before) != null &&
        finite(m.reads_after) != null
          ? number(Number(m.reads_before) - Number(m.reads_after))
          : null,
        'Jumlah reads yang dibuang saat preprocessing'
      ),
      row('Q20 sebelum → sesudah', pairPct(m.q20_before, m.q20_rate ?? m.q20_after), 'fastp'),
      row('Q30 sebelum → sesudah', pairPct(m.q30_before, m.q30_rate ?? m.q30_after), 'fastp'),
      row('Jumlah reads awal', number(m.reads_before), 'Sebelum fastp'),
      row('Jumlah reads akhir', number(m.reads_after), 'Setelah fastp'),
      row('Adapter terpotong', pct(m.adapter_trimmed_pct), 'fastp'),
    ],
    2: [
      row('Mapping rate', pct(m.mapping_rate), 'SAMtools flagstat'),
      row('Mean depth', finite(m.mean_depth)==null ? null : `${fmt(m.mean_depth)}×`, 'SAMtools coverage'),
      row('Unmapped reads', number(m.unmapped_reads), 'Read tidak terpetakan'),
      row('Genome coverage ≥1×', pct(m.genome_coverage_pct), 'Wilayah genom'),
      row('Genome coverage ≥30×', pct(m.genome_coverage_30x_pct), 'Wilayah genom'),
    ],
    3: [
      row('Varian mentah', number(m.raw_variant_count), 'BCFtools'),
      row('SNP', number(m.raw_snp_count), 'Substitusi satu basa'),
      row('INDEL', number(m.raw_indel_count), 'Insersi/delesi'),
      row('Rasio Ts/Tv', finite(m.tstv_ratio)==null ? null : fmt(m.tstv_ratio), 'Raw VCF'),
    ],
    4: [
      row('Varian PASS', number(m.passed_variant_count), 'Lolos filtering'),
      row('Terfilter', number(m.filtered_variant_count), 'Tidak lolos filtering'),
      row('Teranotasi', number(m.annotated_variant_count), 'SnpEff'),
      row('Status anotasi', m.annotation_status == null ? null : String(m.annotation_status), 'SnpEff'),
    ],
  }[n] ?? []
  const artifacts = Array.isArray(data?.artifacts) ? data.artifacts : (data?.artifacts?.artifacts ?? [])
  const files = done ? artifacts.filter(x => Number(x.station ?? x.station_number)===n && x.url)
    .map(x => ({label:x.label??x.filename??'Unduh', filename:x.filename??'hasil', url:x.url})) : []
  
  const descriptionRaw =
    typeof interpretation === 'string'
      ? interpretation
      : (interpretation.interpretation ?? status.interpretation ?? null)

  const description =
    typeof descriptionRaw === 'string'
      ? descriptionRaw.replace(
          /(\d+)\.(\d+)(?=%|x\b)/g,
          '$1,$2'
        )
      : null

  const localSummary = n === 1 && finite(m.reads_before) != null && finite(m.reads_after) != null
      ? `Dari ${fmt(m.reads_before,0)} reads awal, ${fmt(m.reads_after,0)} reads diteruskan setelah preprocessing.`
      : null
  return {
    n, done, fromBackend: Boolean(description) || metricRows.some(x=>x[1]!=null),
    hasMetrics: metricRows.some(x=>x[1]!=null),
    status_code: status.status_code ?? null, badge_color: status.badge_color ?? null,
    interpretation: description, notes: interpretation.notes ?? [],
    recommendations: interpretation.recommendations ?? [],
    metrics: metricRows, summary: localSummary, files,
  }
}
