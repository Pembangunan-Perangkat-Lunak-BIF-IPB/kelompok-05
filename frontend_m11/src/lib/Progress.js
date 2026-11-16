// Diagnostik per stasiun (4 stasiun final): metrik, interpretasi otomatis berbasis aturan, dan berkas unduhan.
// Sumber: HASIL STASIUN - BAHAN RANCANGAN PERUBAHAN.pdf
//
// Kontrak data (dibaca dari respons GET /analysis/{id}/status):
//   stations_diagnostic: { station_1: { status_code, badge_color, interpretation, metrics: {...}, download_files: [{label,url}] }, ... station_4 }
// Bila backend belum mengirim `interpretation`, FE menghitungnya dari `metrics` dengan aturan yang sama
// seperti pseudo-code rancangan. Metrik yang hilang ditampilkan "-" (missing), bukan 0.

export const STATION_COUNT = 4

export const STATIONS = {
  1: { name: 'Quality Control & Preprocessing', tool: 'fastp' },
  2: { name: 'Read Alignment', tool: 'BWA-MEM2 & SAMtools' },
  3: { name: 'Variant Calling', tool: 'BCFtools' },
  4: { name: 'Quality Filtering & Annotation', tool: 'BCFtools filter & SnpEff' },
}

// Berkas diperoleh dari GET /analysis/{run_id}/artifacts, bukan URL tebakan.
// API daftar artefak memverifikasi keberadaan berkas dan log SUCCESS stasiun.
export const defaultFiles = () => []

const num = (v) => { if (v == null || v === '') return null; const n = Number(v); return Number.isFinite(n) ? n : null }
const f1 = (v) => (v == null ? '-' : v.toLocaleString('id-ID', { minimumFractionDigits: 1, maximumFractionDigits: 1 }))
const f2 = (v) => (v == null ? '-' : v.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
const int = (v) => (v == null ? '-' : v.toLocaleString('id-ID', { maximumFractionDigits: 0 }))

// ---- Aturan interpretasi (cermin pseudo-code rancangan) ---------------------

function rule1(m) {
  const q30 = num(m.q30_rate ?? m.q30_after), pass = num(m.passed_reads_pct), ad = num(m.adapter_trimmed_pct)
  if (q30 == null || pass == null) return null
  if (q30 >= 85 && pass >= 80) return ['EXCELLENT', 'green', `Data sekuensing memiliki tingkat kebersihan Q30 sebesar ${f1(q30)}% dengan pemotongan adapter sebesar ${ad == null ? '-' : `${f1(ad)}%`}. Kualitas data dinyatakan SANGAT LAYAK untuk dilanjutkan ke proses alignment Stasiun 2.`]
  if (q30 >= 70 && q30 < 85 && pass >= 60) return ['ACCEPTABLE', 'yellow', `Data sekuensing berkategori CUKUP (Q30: ${f1(q30)}%, Passed Reads: ${f1(pass)}%). Terdapat sedikit penurunan mutu basa, namun data MASIH LAYAK dilanjutkan ke Stasiun 2.`]
  return ['WARNING_LOW_QUALITY', 'red', `PERINGATAN: Mutu sekuensing tergolong rendah (Q30: ${f1(q30)}%, Passed Reads: ${f1(pass)}%). Banyak basa bermutu rendah atau adapter terpotong berlebih. Hasil alignment berpotensi kurang presisi.`]
}

function rule2(m) {
  const mr = num(m.mapping_rate), md = num(m.mean_depth)
  if (mr == null || md == null) return null
  if (mr >= 90 && md >= 15) return ['OPTIMAL_ALIGNMENT', 'green', `Sebanyak ${f1(mr)}% sekuens reads berhasil tersejajarkan secara unik pada genom acuan NC_045512.2 dengan rata-rata kedalaman pembacaan ${f1(md)}x. Proses alignment dinyatakan PRESISI untuk pemanggilan varian di Stasiun 3.`]
  if (mr >= 75 && mr < 90 && md >= 10) return ['MODERATE_ALIGNMENT', 'yellow', `Sebanyak ${f1(mr)}% sekuens reads tersejajarkan pada genom acuan dengan kedalaman rata-rata ${f1(md)}x. Alignment tergolong CUKUP BAIK untuk pemanggilan varian dasar.`]
  return ['POOR_ALIGNMENT', 'red', `PERINGATAN: Mapping rate rendah (${f1(mr)}%) atau kedalaman pembacaan kurang (${f1(md)}x). Risiko ketidaklengkapan pemanggilan varian (high false negative rate) pada Stasiun 3.`]
}

function rule3(m) {
  const total = num(m.total_raw_variants), snp = num(m.snp_count), indel = num(m.indel_count), tstv = num(m.tstv_ratio)
  if (total == null) return null
  if (total === 0) return ['NO_VARIANTS_FOUND', 'red', 'TIDAK DITEMUKAN VARIAN: Tidak ada kandidat mutasi yang terdeteksi dari pemetaan sekuens terhadap genom rujukan NC_045512.2.']
  if (tstv != null && tstv >= 1.5 && tstv <= 2.5) return ['VARIANTS_CALL_SUCCESS', 'green', `Terdeteksi total ${int(total)} varian mentah (${int(snp)} SNP, ${int(indel)} INDEL) di seluruh genom dengan rasio Ts/Tv biologis yang normal (${f2(tstv)}). Data varian mentah BERHASIL DITERBITKAN dan siap masuk ke tahap quality filtering & anotasi di Stasiun 4.`]
  return ['VARIANTS_CALL_SUSPECT', 'yellow', `Terdeteksi total ${int(total)} varian mentah (${int(snp)} SNP, ${int(indel)} INDEL), namun rasio Ts/Tv (${f2(tstv)}) menyimpang dari tren umum atau tidak tersedia. Disarankan melakukan penyaringan ketat di Stasiun 4.`]
}

function rule4(m) {
  const pass = num(m.pass_variants_count), out = num(m.filtered_out_count)
  if (pass == null || out == null) return null
  const total = pass + out, rate = total > 0 ? (pass / total) * 100 : null
  if (pass > 0) return ['ANALYSIS_COMPLETE_SUCCESS', 'purple', `EXECUTIVE SUMMARY: Dari total ${int(total)} varian mentah, sebanyak ${int(pass)} varian (${f1(rate)}%) dinyatakan PASS berdasarkan parameter yang diterapkan.${m.top_impact_gene ? ` Mutasi dominan teridentifikasi pada ${m.top_impact_gene} berupa ${int(num(m.missense_count))} mutasi missense dan ${int(num(m.synonymous_count))} mutasi sinonim.` : ''} Seluruh data hasil analisis dan laporan terintegrasi siap diunduh.`]
  return ['ANALYSIS_COMPLETE_ZERO_PASS', 'orange', `EXECUTIVE SUMMARY: Seluruh varian mentah tereliminasi (${int(out)} varian terbuang) oleh ambang filter yang diterapkan. Tidak ada varian berstatus PASS yang dapat diteruskan ke laporan anotasi.`]
}

const RULES = { 1: rule1, 2: rule2, 3: rule3, 4: rule4 }

// ---- Metrik yang ditampilkan ----------------------------------------------

function metricList(n, m) {
  const pct = (k) => { const v = num(m[k]); return v == null ? null : `${f1(v)}%` }
  const cnt = (k) => { const v = num(m[k]); return v == null ? null : int(v) }
  if (n === 1) {
    const pass = num(m.passed_reads_pct)
    const filtered = num(m.filtered_reads_pct) ?? (pass == null ? null : Math.max(0, 100 - pass))
    return [
      ['Passed reads', pass == null ? null : `${f1(pass)}%`, 'Reads yang lolos pembersihan'],
      ['Filtered reads', filtered == null ? null : `${f1(filtered)}%`, 'Reads yang dibuang'],
      ['Q20 sebelum → sesudah', m.q20_before != null || m.q20_after != null ? `${f1(num(m.q20_before))}% → ${f1(num(m.q20_after))}%` : null, 'Trimming'],
      ['Q30 sebelum → sesudah', m.q30_before != null || m.q30_after != null || m.q30_rate != null ? `${f1(num(m.q30_before))}% → ${f1(num(m.q30_after ?? m.q30_rate))}%` : null, 'Trimming'],
      ['Adapter terpotong', pct('adapter_trimmed_pct'), 'Pemotongan adapter'],
      ['Basa mutu rendah terpotong', pct('low_quality_trimmed_pct'), 'Pemotongan basa bermutu rendah'],
      ['Total reads (sebelum → sesudah)', m.total_reads_before != null || m.total_reads_after != null ? `${int(num(m.total_reads_before))} → ${int(num(m.total_reads_after))}` : null, 'Jumlah reads'],
    ]
  }
  if (n === 2) {
    const mr = num(m.mapping_rate)
    const unm = num(m.unmapped_reads_pct) ?? (mr == null ? null : Math.max(0, 100 - mr))
    return [
      ['Mapping rate', mr == null ? null : `${f1(mr)}%`, 'Reads menempel pada NC_045512.2'],
      ['Mean depth', num(m.mean_depth) == null ? null : `${f1(num(m.mean_depth))}×`, 'Rata-rata kedalaman genom'],
      ['Unmapped reads', m.unmapped_reads != null ? `${cnt('unmapped_reads')}${unm == null ? '' : ` (${f1(unm)}%)`}` : unm == null ? null : `${f1(unm)}%`, 'Gagal menempel'],
      ['Total reads dipetakan', cnt('mapped_reads'), 'Mapped reads'],
    ]
  }
  if (n === 3) {
    return [
      ['Total varian mentah', cnt('total_raw_variants'), 'Seluruh genom ± 29,9 kb'],
      ['SNP', cnt('snp_count'), 'Single nucleotide polymorphism'],
      ['INDEL', cnt('indel_count'), 'Insersi / delesi'],
      ['Rasio Ts/Tv', num(m.tstv_ratio) == null ? null : f2(num(m.tstv_ratio)), 'Rasio transisi/transversi hasil analisis'],
    ]
  }
  const pass = num(m.pass_variants_count), out = num(m.filtered_out_count)
  const total = pass != null && out != null ? pass + out : null
  return [
    ['Varian PASS', cnt('pass_variants_count'), total ? `${f1((pass / total) * 100)}% dari ${int(total)} varian mentah` : 'Lolos quality filtering'],
    ['Filtered out', cnt('filtered_out_count'), 'Tereliminasi oleh ambang filter'],
    ['Gen dampak teratas', m.top_impact_gene ?? null, 'Hasil anotasi SnpEff'],
    ['Missense', cnt('missense_count'), 'Perubahan asam amino'],
    ['Sinonim', cnt('synonymous_count'), 'Tidak mengubah asam amino'],
    ['Frameshift', cnt('frameshift_count'), 'Pergeseran kerangka baca'],
    ['Stop-gained', cnt('stop_gained_count'), 'Kodon stop prematur'],
  ]
}

// Ringkasan "apa yang dibersihkan" untuk Stasiun 1 (hanya bila hitungan reads dikirim backend)
function cleanSummary(m) {
  const b = num(m.total_reads_before), a = num(m.total_reads_after)
  if (b == null || a == null || b <= 0) return null
  return `Dari ${int(b)} reads mentah, ${int(a)} reads (${f1((a / b) * 100)}%) berhasil dibersihkan dan diteruskan ke Stasiun 2; ${int(Math.max(0, b - a))} reads dibuang (kualitas rendah, terlalu pendek, atau berisi adapter).`
}

const REQUIRED = { 1: ['passed_reads_pct'], 2: ['mapping_rate', 'mean_depth'], 3: ['total_raw_variants'], 4: ['pass_variants_count', 'filtered_out_count'] }

// Metrik dari GET /results (jika run COMPLETED), status dari GET /status.
// Jangan menghasilkan interpretasi atau status evaluatif tanpa data pendukung.
export function stationDiagnostic(data, runId, n, done, artifacts = [], results = null) {
  const raw = data?.stations_diagnostic?.[`station_${n}`] ?? data?.stations_diagnostic?.[n] ?? null
  const sm = results?.summary_metrics ?? {}
  const metricsByStation = {
    1: {
      passed_reads_pct: sm.passed_reads_pct,
      q20_before: sm.q20_before,
      q20_after: sm.q20_rate,
      q30_before: sm.q30_before,
      q30_after: sm.q30_rate,
      total_reads_before: sm.reads_before,
      total_reads_after: sm.reads_after,
      adapter_trimmed_pct: sm.adapter_trimmed_pct,
    },
    2: { mapping_rate: sm.mapping_rate, mean_depth: sm.mean_depth, unmapped_reads: sm.unmapped_reads },
    3: {
      total_raw_variants: sm.raw_variant_count,
      snp_count: sm.raw_snp_count,
      indel_count: sm.raw_indel_count,
      tstv_ratio: sm.tstv_ratio,
    },
    4: {
      pass_variants_count: sm.passed_variant_count,
      filtered_out_count: sm.filtered_variant_count,
    },
  }
  const fromResults = Object.fromEntries(
    Object.entries(metricsByStation[n] ?? {}).filter(([, value]) => value != null)
  )
  const m = { ...fromResults, ...(raw?.metrics ?? {}) }
  const files = done
    ? artifacts.filter((a) => Number(a.station) === n && a.url).map((a) => ({
        label: a.label ?? a.filename ?? 'Unduh',
        filename: a.filename ?? `stasiun_${n}`,
        url: a.url,
        artifact_id: a.artifact_id,
        size_bytes: a.size_bytes,
      }))
    : []
  const hasMetrics = REQUIRED[n].every((k) => num(m[k]) != null)
  return {
    n, done, hasMetrics, fromBackend: !!raw || Object.keys(fromResults).length > 0,
    status_code: raw?.status_code ?? null,
    badge_color: raw?.badge_color ?? null,
    interpretation: raw?.interpretation ?? null,
    metrics: metricList(n, m),
    summary: n === 1 ? cleanSummary(m) : null,
    files,
  }
}
