// Mesin animasi "read pileup" ala genome browser untuk hero Landing.
// Modul murni (tanpa DOM): computeScene() menghasilkan daftar primitif gambar
// yang dipakai kanvas 2D di Landing.jsx. Skrip snapshot Figma memakai fungsi
// yang sama, jadi frame statis di Figma = satu frame animasi di kode.

export const RISK_COLOR = { HIGH: '#EF4444', MODERATE: '#F59E0B', LOW: '#14B8A6' }
export const READ_COLORS = ['#38BDF8', '#818CF8'] // biru / ungu (warna logo)
export const GRAY = '#CBD5E1'
export const BASE_COLOR = '#64748B'

// Data CONTOH untuk ilustrasi, BUKAN hasil analisis.
export const MUTATIONS = [
  { pos: 23063, ref: 'A', alt: 'T', aa: 'N501Y', risk: 'HIGH' },
  { pos: 23403, ref: 'A', alt: 'G', aa: 'D614G', risk: 'LOW' },
  { pos: 22917, ref: 'T', alt: 'G', aa: 'L452R', risk: 'MODERATE' },
  { pos: 23012, ref: 'G', alt: 'A', aa: 'E484K', risk: 'HIGH' },
  { pos: 23604, ref: 'C', alt: 'A', aa: 'P681H', risk: 'LOW' },
  { pos: 22813, ref: 'G', alt: 'T', aa: 'K417N', risk: 'MODERATE' },
]

export const CFG = {
  cell: 16, // lebar satu kolom basa (px)
  speed: 38, // px/detik, aliran ke kiri
  scan: 0.56, // posisi scanner (fraksi lebar)
  lanes: 10,
  laneTop: 78,
  laneStep: 12,
  readH: 6,
  baseY: 234, // baseline huruf referensi
  varGap: 19, // jarak rata-rata antar varian (kolom)
  offset0: 520, // geser awal dunia (px) agar frame pertama sudah berisi
  staticT: 0, // detik yang dipakai untuk gambar diam
}

const BASES = 'ACGT'
const MONO = 'ui-monospace, "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace'
export const FONT_MONO = MONO

// Hash deterministik -> [0,1)
function h(a, b = 0, c = 0) {
  let x = Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263) + Math.imul(c | 0, 2147483647)
  x = Math.imul(x ^ (x >>> 13), 1274126177)
  x ^= x >>> 16
  return ((x >>> 0) % 100000) / 100000
}

function variantCol(k) {
  return 6 + k * CFG.varGap + Math.round((h(k, 3) - 0.5) * 6)
}
const mutationOf = (k) => MUTATIONS[((k % MUTATIONS.length) + MUTATIONS.length) % MUTATIONS.length]

function variantAtCol(col) {
  const k = Math.round((col - 6) / CFG.varGap)
  for (const kk of [k - 1, k, k + 1]) if (variantCol(kk) === col) return kk
  return null
}

function refBase(col) {
  const k = variantAtCol(col)
  if (k !== null) return mutationOf(k).ref
  return BASES[Math.floor(h(col, 7) * 4)]
}
// Lajur read: dibangkitkan berurutan dan di-cache agar akses acak murah
export class Pileup {
  constructor() {
    this.lanes = Array.from({ length: CFG.lanes }, (_, i) => ({
      i,
      x: -h(i, 1) * 320,
      k: 0,
      reads: [],
    }))
  }

  ensure(minX, maxX) {
    for (const lane of this.lanes) {
      lane.reads = lane.reads.filter((r) => r.x1 > minX - 40)
      while (lane.x < maxX + 40) {
        const k = lane.k++
        const gap = 18 + h(lane.i, k, 2) * 130
        const len = 150 + h(lane.i, k, 3) * 230
        const x0 = lane.x + gap
        const x1 = x0 + len
        const color = READ_COLORS[h(lane.i, k, 4) < 0.5 ? 0 : 1]
        const errors = []
        const nErr = h(lane.i, k, 5) < 0.4 ? (h(lane.i, k, 6) < 0.3 ? 2 : 1) : 0
        for (let e = 0; e < nErr; e++) {
          const col = Math.floor((x0 + 12 + h(lane.i, k, 8 + e) * (len - 24)) / CFG.cell)
          if (variantAtCol(col) === null) errors.push(col)
        }
        lane.reads.push({ id: lane.i * 100003 + k, x0, x1, color, errors })
        lane.x = x1
      }
    }
  }
}

const fmtLabel = (m) => `${m.pos} ${m.ref}>${m.alt} · ${m.aa}`
const clamp01 = (v) => Math.max(0, Math.min(1, v))

// t = detik sejak mulai. Mengembalikan primitif untuk satu frame.
export function computeScene(pileup, W, H, t) {
  const { cell, speed, readH } = CFG
  const offset = CFG.offset0 + t * speed
  const scanX = Math.round(W * CFG.scan)
  const out = []
  pileup.ensure(offset - 60, offset + W + 60)

  const c0 = Math.floor((offset - 40) / cell)
  const c1 = Math.ceil((offset + W + 40) / cell)

  // Varian yang terlihat (dipakai kolom, tick, huruf, label)
  const vars = []
  for (let k = Math.floor((c0 - 6) / CFG.varGap) - 1; k <= Math.ceil((c1 - 6) / CFG.varGap) + 1; k++) {
    const col = variantCol(k)
    if (col < c0 || col > c1) continue
    const m = mutationOf(k)
    const sx = col * cell + cell / 2 - offset
    const age = (scanX - sx) / speed // >0 : sudah melewati scanner
    vars.push({ k, col, m, sx, age, passed: age >= 0 })
  }
  const byCol = new Map(vars.map((v) => [v.col, v]))

  // Sorotan kolom untuk varian yang sudah lewat
  for (const v of vars) {
    if (!v.passed) continue
    const a = 0.1 * clamp01(1 - v.age / 14) + 0.035
    out.push({ k: 'rect', x: v.sx - cell / 2, y: CFG.laneTop - 8, w: cell, h: CFG.baseY - CFG.laneTop + 14, r: 3, fill: RISK_COLOR[v.m.risk], a })
  }

  // Read
  for (const lane of pileup.lanes) {
    const y = CFG.laneTop + lane.i * CFG.laneStep
    for (const r of lane.reads) {
      const x0 = r.x0 - offset
      const x1 = r.x1 - offset
      if (x1 < -10 || x0 > W + 10) continue
      out.push({ k: 'rect', x: x0, y, w: x1 - x0, h: readH, r: 3, fill: r.color, a: 0.4 })
      // Mismatch varian (sebagian besar read membawa alel alt)
      for (const v of vars) {
        const wx = v.col * cell
        if (wx < r.x0 + 4 || wx + cell > r.x1 - 4) continue
        if (h(r.id, v.col, 9) > 0.82) continue
        const col = v.passed ? RISK_COLOR[v.m.risk] : GRAY
        out.push({ k: 'rect', x: v.sx - cell / 2 + 3, y: y - 1, w: cell - 6, h: readH + 2, r: 2, fill: col, a: v.passed ? 0.95 : 0.8 })
      }
      // Mismatch acak abu-abu = error sekuensing
      for (const col of r.errors) {
        const sx = col * cell + cell / 2 - offset
        out.push({ k: 'rect', x: sx - cell / 2 + 4, y: y - 1, w: cell - 8, h: readH + 2, r: 2, fill: GRAY, a: 0.55 })
      }
    }
  }

  // Baris huruf basa referensi
  for (let col = c0; col <= c1; col++) {
    const sx = col * cell + cell / 2 - offset
    const v = byCol.get(col)
    if (!v) {
      out.push({ k: 'text', x: sx, y: CFG.baseY, s: refBase(col), fill: BASE_COLOR, a: 0.7, size: 13, weight: 500 })
    } else if (!v.passed) {
      out.push({ k: 'text', x: sx, y: CFG.baseY, s: v.m.alt, fill: GRAY, a: 0.95, size: 13, weight: 700 })
    } else {
      const bump = v.age < 0.9 ? 1 + 0.35 * Math.sin((v.age / 0.9) * Math.PI) : 1
      out.push({ k: 'text', x: sx, y: CFG.baseY, s: v.m.alt, fill: RISK_COLOR[v.m.risk], a: 1, size: 13 * bump, weight: 800 })
    }
  }

  // Denyut + label
  for (const v of vars) {
    if (!v.passed) continue
    const color = RISK_COLOR[v.m.risk]
    if (v.age < 1.4) {
      const p = v.age / 1.4
      out.push({ k: 'ring', x: v.sx, y: CFG.baseY - 5, r: 7 + 26 * p, stroke: color, a: 0.9 * (1 - p), w: 2 })
    }
    const la = clamp01(v.age / 0.4) * clamp01((11 - v.age) / 2)
    if (la > 0.01) {
      const label = fmtLabel(v.m)
      const w = Math.round(label.length * 6.9 + 22)
      const ly = 38 // posisi tetap di atas lajur
      out.push({ k: 'pill', x: v.sx - w / 2, y: ly, w, h: 22, r: 11, fill: '#07121A', stroke: color, a: la })
      out.push({ k: 'text', x: v.sx, y: ly + 15, s: label, fill: '#F1F5F9', a: la, size: 11, weight: 600 })
      out.push({ k: 'rect', x: v.sx - 0.5, y: ly + 22, w: 1, h: CFG.baseY - 14 - (ly + 22), r: 0, fill: color, a: 0.35 * la })
    }
  }

  out.push({ k: 'scan', x: scanX, y0: 28, y1: H - 14 })
  out.push({ k: 'text', x: scanX, y: H - 3, s: 'VARIANT CALLER', fill: '#22D3EE', a: 0.85, size: 10, weight: 700, spacing: 2.4 })
  return out
}

// Gambar primitif ke konteks Canvas 2D
export function drawScene(ctx, prims) {
  for (const p of prims) {
    ctx.save()
    ctx.globalAlpha = p.a ?? 1
    if (p.k === 'rect' || p.k === 'pill') {
      ctx.beginPath()
      if (ctx.roundRect) ctx.roundRect(p.x, p.y, p.w, p.h, p.r || 0)
      else ctx.rect(p.x, p.y, p.w, p.h)
      ctx.fillStyle = p.fill
      ctx.fill()
      if (p.k === 'pill') {
        ctx.strokeStyle = p.stroke
        ctx.lineWidth = 1
        ctx.stroke()
      }
    } else if (p.k === 'text') {
      ctx.font = `${p.weight} ${p.size}px ${MONO}`
      ctx.textAlign = 'center'
      ctx.fillStyle = p.fill
      if (p.spacing && 'letterSpacing' in ctx) ctx.letterSpacing = `${p.spacing}px`
      ctx.fillText(p.s, p.x, p.y)
    } else if (p.k === 'ring') {
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.strokeStyle = p.stroke
      ctx.lineWidth = p.w
      ctx.stroke()
    } else if (p.k === 'scan') {
      const g = ctx.createLinearGradient(0, p.y0, 0, p.y1)
      g.addColorStop(0, 'rgba(34,211,238,0)')
      g.addColorStop(0.15, 'rgba(34,211,238,0.95)')
      g.addColorStop(0.85, 'rgba(34,211,238,0.95)')
      g.addColorStop(1, 'rgba(34,211,238,0)')
      ctx.shadowColor = 'rgba(34,211,238,0.8)'
      ctx.shadowBlur = 10
      ctx.fillStyle = g
      ctx.fillRect(p.x - 0.75, p.y0, 1.5, p.y1 - p.y0)
    }
    ctx.restore()
  }
}
