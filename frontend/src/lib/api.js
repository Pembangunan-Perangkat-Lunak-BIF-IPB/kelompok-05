const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

// Pesan galat 422/400 dari backend (string atau array detail FastAPI)
export function errorMessage(data, fallback = 'Permintaan gagal. Coba lagi.') {
  const d = data?.detail ?? data?.message
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg).join('; ')
  return fallback
}

// Token login disimpan di localStorage (dipakai saat halaman Login sudah dibangun)
export const auth = {
  get token() {
    try { return localStorage.getItem('ve_token') } catch { return null }
  },
  set token(v) {
    try { v ? localStorage.setItem('ve_token', v) : localStorage.removeItem('ve_token') } catch { /* abaikan */ }
  },
}

// Pembungkus fetch tunggal: menambah header Authorization bila ada token,
// menerjemahkan galat jaringan dan galat HTTP menjadi Error berpesan Indonesia.
async function request(path, { method = 'GET', json, body, fallback } = {}) {
  const headers = {}
  if (json !== undefined) headers['Content-Type'] = 'application/json'
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`

  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: json !== undefined ? JSON.stringify(json) : body,
    })
  } catch {
    throw new Error('Server tidak dapat dihubungi. Pastikan backend berjalan di port 8000.')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(errorMessage(data, fallback))
  return data
}

export const health = () => request('/health')

export const register = (payload) => request('/auth/register', { method: 'POST', json: payload })

export async function login(email, password) {
  const data = await request('/auth/login', { method: 'POST', json: { email, password } })
  auth.token = data.access_token
  return data
}

export function uploadAnalysis({ sampleName, r1, r2, fasta, iedb }) {
  const fd = new FormData()
  if (sampleName) fd.append('sample_name', sampleName)
  fd.append('file_fastq_r1', r1)
  fd.append('file_fastq_r2', r2)
  fd.append('file_fasta', fasta)
  fd.append('file_iedb', iedb)
  return request('/analysis/upload', {
    method: 'POST',
    body: fd, // jangan set Content-Type: browser mengisi boundary multipart sendiri
    fallback: 'Unggah gagal. Periksa kembali berkas Anda.',
  })
}

export const getStatus = (runId) => request(`/analysis/${encodeURIComponent(runId)}/status`)

export const getResults = (runId) => request(`/analysis/${encodeURIComponent(runId)}/results`)

export const setVisibility = (runId, visibility) =>
  request(`/analysis/${encodeURIComponent(runId)}/visibility`, { method: 'PATCH', json: { visibility } })

export const runAnalysis = (runId) =>
  request(`/analysis/${encodeURIComponent(runId)}/run`, { method: 'POST' })