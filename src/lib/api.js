const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export async function uploadAnalysis({ sampleName, r1, r2, fasta, iedb }) {
  const fd = new FormData()
  if (sampleName) fd.append('sample_name', sampleName)
  fd.append('file_fastq_r1', r1)
  fd.append('file_fastq_r2', r2)
  fd.append('file_fasta', fasta)
  fd.append('file_iedb', iedb)

  let res
  try {
    res = await fetch(`${BASE}/analysis/upload`, { method: 'POST', body: fd })
  } catch {
    throw new Error('Server tidak dapat dihubungi. Pastikan backend berjalan di port 8000.')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(errorMessage(data))
  return data
}

// Pesan galat 422/400 dari backend (string atau array detail FastAPI)
export function errorMessage(data) {
  const d = data?.detail ?? data?.message
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg).join('; ')
  return 'Unggah gagal. Periksa kembali berkas Anda.'
}