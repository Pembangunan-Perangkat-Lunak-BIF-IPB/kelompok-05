const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export function errorMessage(data, fallback = 'Permintaan gagal. Coba lagi.') {
  const d = data?.detail ?? data?.message
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg).join('; ')
  return fallback
}

export const auth = {
  get token() {
    try { return localStorage.getItem('ve_token') } catch { return null }
  },
  set token(v) {
    try { v ? localStorage.setItem('ve_token', v) : localStorage.removeItem('ve_token') } catch { /* abaikan */ }
  },
}

export const lastRun = {
  get() {
    try { return localStorage.getItem('ve_last_run') } catch { return null }
  },
  set(id) {
    try { id ? localStorage.setItem('ve_last_run', id) : localStorage.removeItem('ve_last_run') } catch { /* abaikan */ }
  },
}

export function logout() {
  auth.token = null
  lastRun.set(null)
}

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
  if (!res.ok) {
    const notAuth = res.status === 401 ||
      (res.status === 403 && /not authenticated/i.test(String(data?.detail)))
    if (notAuth && !path.startsWith('/auth/')) {
      logout()
      window.location.assign('/login')
      const err = new Error('Sesi berakhir. Silakan login kembali.')
      err.status = res.status
      throw err
    }
    const err = new Error(errorMessage(data, fallback))
    err.status = res.status
    throw err
  }
  return data
}

export const health = () => request('/health')

export const register = (payload) => request('/auth/register', { method: 'POST', json: payload })

export async function login(email, password) {
  const data = await request('/auth/login', { method: 'POST', json: { email, password } })
  if (data.user?.status_aktif === 'PENDING_APPROVAL') {
    const err = new Error('Akun Anda masih menunggu persetujuan admin. Anda belum dapat masuk.')
    err.code = 'PENDING_APPROVAL'
    throw err
  }
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
    body: fd,
    fallback: 'Unggah gagal. Periksa kembali berkas Anda.',
  })
}

export const runAnalysis = (runId) =>
  request(`/analysis/${encodeURIComponent(runId)}/run`, { method: 'POST' })

export const getHistory = () => request('/analysis')

export const getStatus = (runId) => request(`/analysis/${encodeURIComponent(runId)}/status`)

export const getResults = (runId) => request(`/analysis/${encodeURIComponent(runId)}/results`)

export const setVisibility = (runId, visibility) =>
  request(`/analysis/${encodeURIComponent(runId)}/visibility`, { method: 'PATCH', json: { visibility } })