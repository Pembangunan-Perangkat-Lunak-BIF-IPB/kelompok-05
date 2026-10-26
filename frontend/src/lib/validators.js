const MB = 1024 * 1024
const GB = 1024 * MB

export const RULES = {
  fastq: { ext: ['.fastq', '.fq', '.fastq.gz', '.fq.gz'], max: 1 * GB },
  fasta: { ext: ['.fasta', '.fa', '.fna'], max: 50 * MB },
  iedb: { ext: ['.csv', '.tsv', '.gff'], max: 20 * MB },
}

export function formatSize(bytes) {
  if (!bytes) return '0 KB'
  if (bytes >= GB) return (bytes / GB).toFixed(1) + ' GB'
  if (bytes >= MB) return Math.round(bytes / MB) + ' MB'
  return Math.max(1, Math.round(bytes / 1024)) + ' KB'
}

// Lapis 1: ekstensi, ukuran, signature gzip (1f 8b)
export async function validateFormat(kind, file) {
  const rule = RULES[kind]
  const name = file.name.toLowerCase()
  if (!rule.ext.some((e) => name.endsWith(e)))
    return { ok: false, message: `Format harus ${rule.ext.join(', ')}` }
  if (file.size > rule.max)
    return { ok: false, message: `Ukuran maksimal ${Math.round(rule.max / MB)} MB` }
  if (name.endsWith('.gz')) {
    const head = new Uint8Array(await file.slice(0, 2).arrayBuffer())
    if (head[0] !== 0x1f || head[1] !== 0x8b)
      return { ok: false, message: 'Signature gzip tidak valid' }
  }
  return { ok: true, message: '' }
}

// Pisahkan 2 berkas FASTQ menjadi R1 dan R2 dari nama berkas
export function splitFastqPair(files) {
  const list = Array.from(files)
  const r1 = list.find((f) => /_R1/i.test(f.name))
  const r2 = list.find((f) => /_R2/i.test(f.name))
  if (list.length !== 2 || !r1 || !r2)
    return { error: 'Pilih tepat 2 berkas dengan penamaan _R1 dan _R2' }
  return { r1, r2 }
}
