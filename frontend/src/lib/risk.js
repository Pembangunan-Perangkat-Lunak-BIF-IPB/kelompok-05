// Aturan tampilan Result Viewer (sesuai SKPL/SA Minggu 9)
export const RISK_ORDER = ['HIGH', 'MODERATE', 'LOW', 'OUTSIDE_EPITOPE']

export const RISK_LABEL = {
  HIGH: 'HIGH',
  MODERATE: 'MODERATE',
  LOW: 'LOW',
  OUTSIDE_EPITOPE: 'OUTSIDE EPITOPE',
}

const rank = (r) => {
  const i = RISK_ORDER.indexOf(r)
  return i === -1 ? RISK_ORDER.length : i
}

const num = (v) => (v === null || v === undefined || v === '' ? null : Number(v))

// Ambil nilai pertama yang ada dari beberapa kemungkinan nama field
export const pick = (obj, ...keys) => {
  for (const k of keys) if (obj?.[k] !== undefined && obj?.[k] !== null) return obj[k]
  return null
}

export function readMetrics(data) {
  const m = data?.metrics ?? data?.run_metrics ?? data?.summary ?? {}
  return {
    q20: pick(m, 'q20', 'q20_percent', 'q20_rate'),
    q30: pick(m, 'q30', 'q30_percent', 'q30_rate'),
    mapping: pick(m, 'mapping_rate', 'mapping_rate_percent'),
    depth: pick(m, 'read_depth', 'mean_depth', 'avg_read_depth'),
    total: pick(m, 'total_variants', 'variant_count') ?? data?.total_variants ?? null,
    tstv: pick(m, 'ts_tv_ratio', 'ts_tv', 'tstv_ratio'),
  }
}

export const fmtPct = (v) => (v === null ? '-' : `${Number(v).toFixed(Number(v) % 1 ? 1 : 0)}%`)
export const fmtNum = (v, d = 2) => (v === null || Number.isNaN(Number(v)) ? '-' : Number(v).toFixed(d).replace(/\.?0+$/, ''))

export const SORTS = {
  default: 'Risiko tertinggi, lalu posisi',
  pos_asc: 'Posisi (naik)',
  pos_desc: 'Posisi (turun)',
  grantham_desc: 'Grantham (tertinggi)',
  qual_desc: 'QUAL (tertinggi)',
  dp_desc: 'DP (tertinggi)',
}

export function sortVariants(list, key = 'default') {
  const out = [...list]
  const byPos = (a, b) => num(a.position) - num(b.position)
  const desc = (f) => (a, b) => (num(b[f]) ?? -Infinity) - (num(a[f]) ?? -Infinity) || byPos(a, b)
  const cmp = {
    default: (a, b) => rank(a.risk_level) - rank(b.risk_level) || byPos(a, b),
    pos_asc: byPos,
    pos_desc: (a, b) => byPos(b, a),
    grantham_desc: desc('grantham_score'),
    qual_desc: desc('qual'),
    dp_desc: desc('dp'),
  }[key] ?? byPos
  return out.sort(cmp)
}

export function filterVariants(list, { risk = 'ALL', effect = '', min = '', max = '' }) {
  const q = effect.trim().toLowerCase()
  const lo = min === '' ? null : Number(min)
  const hi = max === '' ? null : Number(max)
  return list.filter((v) => {
    if (risk !== 'ALL' && v.risk_level !== risk) return false
    if (q && !String(v.snpeff_effect ?? '').toLowerCase().includes(q)) return false
    if (lo !== null && Number(v.position) < lo) return false
    if (hi !== null && Number(v.position) > hi) return false
    return true
  })
}

const csvCell = (x) => {
  const s = x === null || x === undefined ? '' : String(x)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function toCsv(list) {
  const head = ['position', 'ref', 'alt', 'qual', 'dp', 'snpeff_effect', 'grantham_score', 'risk_level']
  const rows = list.map((v) => [v.position, v.ref_allele, v.alt_allele, v.qual, v.dp, v.snpeff_effect, v.grantham_score, v.risk_level])
  return [head, ...rows].map((r) => r.map(csvCell).join(',')).join('\n')
}

export function downloadText(filename, text, type = 'text/csv') {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
