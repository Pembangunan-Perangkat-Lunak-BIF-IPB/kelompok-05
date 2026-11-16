// Parameter pengguna VarEscape (6 parameter): 3 untuk Stasiun 3 (BCFtools mpileup)
// dan 3 untuk Stasiun 4 (quality filtering VCF). Nilai default = preset prototipe,
// BUKAN ambang yang terbukti optimal/tervalidasi klinis.
// Sumber: PARAMETER BARU - BAHAN RANCANGAN PERUBAHAN.pdf

export const PARAM_GROUPS = [
  {
    station: 3,
    title: 'Stasiun 3 — Variant Calling',
    tool: 'BCFtools mpileup',
    params: [
      { key: 'min_mq', label: 'Mapping quality minimum (min_mq)', flag: '-q', op: '≥', def: 30, int: true, min: 0, max: 60, unit: 'Phred',
        hint: 'Read dengan MAPQ di bawah nilai ini tidak dipakai saat mpileup. Ini filter pada read, bukan nilai INFO/MQ di VCF.' },
      { key: 'min_base_quality', label: 'Base quality minimum (min_base_quality)', flag: '-Q', op: '≥', def: 20, int: true, min: 0, max: 60, unit: 'Phred',
        hint: 'Basa dengan kualitas di bawah nilai ini diabaikan. Q20 ≈ peluang salah 1% (skor Phred), bukan jaminan galat aktual.' },
      { key: 'max_depth', label: 'Kedalaman maksimum (max_depth)', flag: '-d', op: '≤', def: 10000, int: true, min: 1, max: 1000000, unit: 'reads',
        hint: 'Batas jumlah read yang diproses per posisi (pengaturan komputasi). Bukan batas kualitas: varian tidak otomatis FAIL bila depth tinggi.' },
    ],
  },
  {
    station: 4,
    title: 'Stasiun 4 — Quality Filtering',
    tool: 'filter VCF',
    params: [
      { key: 'min_dp', label: 'Read depth minimum (min_dp)', op: '≥', def: 10, int: true, min: 1, max: 1000000, unit: '×',
        hint: 'Kandidat varian harus punya DP (kedalaman baca di VCF) minimal sebesar nilai ini.' },
      { key: 'min_qual', label: 'Variant quality minimum (min_qual)', op: '≥', def: 30, int: false, min: 0, max: 1000000, unit: 'QUAL',
        hint: 'Skor QUAL dari caller. Tidak identik dengan kualitas basa (Q20/Q30).' },
      { key: 'min_af', label: 'Allele frequency minimum (min_af)', op: '≥', def: 0.2, int: false, min: 0.01, max: 1, unit: 'proporsi 0–1', step: 0.01,
        hint: 'Proporsi dukungan alel ALT minimal. Contoh: 15 ALT dari 50 read → AF 0,30, memenuhi min_af 0,20.' },
    ],
  },
]

export const ALL_PARAMS = PARAM_GROUPS.flatMap((g) => g.params)

export const defaultValues = () => Object.fromEntries(ALL_PARAMS.map((p) => [p.key, String(p.def)]))

const fmt = (n) => String(n).replace('.', ',')
export const rangeText = (p) => (p.max >= 1000000 ? `min. ${fmt(p.min)}` : `${fmt(p.min)} – ${fmt(p.max)}`)

// Validasi isian mode Custom -> { key: pesanError } (kosong = valid)
export function validateParams(values) {
  const errors = {}
  for (const p of ALL_PARAMS) {
    const raw = String(values[p.key] ?? '').trim().replace(',', '.')
    if (raw === '') { errors[p.key] = 'Wajib diisi.'; continue }
    const n = Number(raw)
    if (!Number.isFinite(n)) { errors[p.key] = 'Harus berupa angka.'; continue }
    if (p.int && !Number.isInteger(n)) { errors[p.key] = 'Harus bilangan bulat.'; continue }
    if (n < p.min || n > p.max) errors[p.key] = `Di luar rentang (${rangeText(p)}).`
  }
  return errors
}

// Payload untuk backend. Mode default -> parameters kosong, backend memakai preset-nya sendiri.
export function buildRunPayload(mode, values) {
  if (mode !== 'custom') return { execution_mode: 'default', parameters: {} }
  const parameters = {}
  for (const p of ALL_PARAMS) parameters[p.key] = Number(String(values[p.key]).trim().replace(',', '.'))
  return { execution_mode: 'custom', parameters }
}
