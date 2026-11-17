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

export const session = {
  get user() {
    try { return JSON.parse(localStorage.getItem('ve_user') ?? 'null') } catch { return null }
  },
  set user(v) {
    try { v ? localStorage.setItem('ve_user', JSON.stringify(v)) : localStorage.removeItem('ve_user') } catch { /* abaikan */ }
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
  session.user = null
  lastRun.set(null)
}

async function request(path, { method = 'GET', json, body, fallback, publicApi = false } = {}) {
  const headers = {}
  if (json !== undefined) headers['Content-Type'] = 'application/json'
  // Endpoint publik (Pembaca Publik) tidak memakai token
  if (auth.token && !publicApi) headers.Authorization = `Bearer ${auth.token}`

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
    if (notAuth && !publicApi && !path.startsWith('/auth/')) {
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
  session.user = data.user ?? null
  return data
}

// Validasi FASTQ sebelum pengguna mengatur parameter.
// Tidak membuat run ataupun memulai pipeline.
export function validateFastqHeaders(r1, r2) {
  if (!r1 || !r2) {
    throw new Error('FASTQ R1 dan R2 wajib dipilih.')
  }

  const form = new FormData()
  form.append('file_fastq_r1', r1)
  form.append('file_fastq_r2', r2)

  return request('/analysis/validate-headers', {
    method: 'POST',
    body: form,
    fallback: 'Validasi header FASTQ gagal.',
  })
}

// FASTA acuan (NC_045512.2) = preset sistem; tabel IEDB sudah tidak dipakai -> hanya FASTQ R1/R2 yang diunggah.
export function uploadAnalysis({
  sampleName, r1, r2 = null, executionMode = 'default', parameters = {},
}) {
  if (!r1) throw new Error('FASTQ R1 wajib dipilih.')
  const mode = String(executionMode).toLowerCase()
  if (!['default', 'custom'].includes(mode)) throw new Error('Mode parameter tidak valid.')
  const fd = new FormData()
  fd.append('sample_name', sampleName || 'Sampel Uji Coba')
  fd.append('file_fastq_r1', r1)
  if (r2) fd.append('file_fastq_r2', r2)
  fd.append('execution_mode', mode)
  if (mode === 'custom') {
    for (const key of ['min_dp','min_mq','min_base_quality','max_depth','min_qual','min_af']) {
      const v = parameters?.[key]
      if (v === null || v === undefined || v === '') throw new Error(`Parameter ${key} belum diisi.`)
      fd.append(key, String(v))
    }
  }
  return request('/analysis/upload', {
    method: 'POST', body: fd, fallback: 'Unggah gagal. Periksa berkas FASTQ.',
  })
}

// Konfigurasi sudah disimpan oleh backend di tahap upload.
// Endpoint /run hanya memicu eksekusi; parameter tidak dikirim ulang.
export const runAnalysis = (runId) =>
  request(`/analysis/${encodeURIComponent(runId)}/run`, { method: 'POST' })

// Endpoint pembatalan hanya akan berfungsi bila didukung backend.
// Jika 404/405, permintaan ditolak dan UI tidak mengklaim berhasil membatalkan.
export const cancelAnalysis = (runId) =>
  request(`/analysis/${encodeURIComponent(runId)}/cancel`, {
    method: 'POST',
    fallback: 'Backend belum mendukung pembatalan proses.',
  })

export const getArtifacts = (runId) =>
  request(`/analysis/${encodeURIComponent(runId)}/artifacts`)

// Unduh berkas hasil per stasiun. Memakai fetch + header Authorization (tautan <a href> biasa
// tidak membawa token), lalu menyimpan blob ke disk.
const API_ORIGIN = () => { try { return new URL(BASE, window.location.origin).origin } catch { return '' } }
export const resolveApiUrl = (url) => (/^https?:\/\//i.test(url) ? url : url.startsWith('/api/') ? `${API_ORIGIN()}${url}` : `${BASE}${url}`)

export async function downloadFile(url, fallbackName = 'berkas') {
  let res
  try {
    res = await fetch(resolveApiUrl(url), { headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {} })
  } catch {
    throw new Error('Server tidak dapat dihubungi. Pastikan backend berjalan di port 8000.')
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(errorMessage(data, res.status === 404 ? 'Berkas belum tersedia dari backend.' : 'Unduhan gagal. Coba lagi.'))
  }
  const cd = res.headers.get('Content-Disposition') ?? ''
  const name = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd)?.[1]
  const blob = await res.blob()
  const href = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = href; a.download = name ? decodeURIComponent(name) : fallbackName
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}

export const getHistory = () => request('/analysis')

export const getStatus = (runId) => request(`/analysis/${encodeURIComponent(runId)}/status`)

export const getResults = (runId) => request(`/analysis/${encodeURIComponent(runId)}/results`)

export const getFilterAudit = (runId) =>
  request(
    `/analysis/${encodeURIComponent(runId)}/filter-audit`
  )

export const setVisibility = (runId, visibility) =>
  request(`/analysis/${encodeURIComponent(runId)}/visibility`, { method: 'PATCH', json: { visibility } })

// Pembaca Publik: tanpa token, hanya hasil berstatus PUBLIC
export const getPublicAnalyses = () => request('/public/analyses', { publicApi: true })

export const getPublicResults = (runId) =>
  request(`/public/analyses/${encodeURIComponent(runId)}/results`, { publicApi: true })

// Riwayat berkas publik yang pernah dibuka Pembaca (disimpan di peramban, tanpa akun)
export const viewedFiles = {
  list() {
    try { return JSON.parse(localStorage.getItem('ve_viewed') ?? '[]') } catch { return [] }
  },
  add(item) {
    try {
      const rest = this.list().filter((x) => x.run_id !== item.run_id)
      localStorage.setItem('ve_viewed', JSON.stringify([{ ...item, viewed_at: new Date().toISOString() }, ...rest].slice(0, 50)))
    } catch { /* abaikan */ }
  },
  clear() {
    try { localStorage.removeItem('ve_viewed') } catch { /* abaikan */ }
  },
}

// ---- Administrator ----------------------------------------------------------
// TODO(backend): endpoint di bawah BELUM ada di kode referensi (frontend_m9).
// Path dan bentuk respons adalah asumsi; sesuaikan dengan backend saat tersedia.

// TODO: GET /admin/accounts -> daftar akun (status_aktif: PENDING_APPROVAL | ACTIVE | REJECTED | SUSPENDED)
export const getAccounts = () => request('/admin/accounts')

// TODO: PATCH /admin/accounts/{id}/status  body: { status_aktif }
export const setAccountStatus = (id, status_aktif) =>
  request(`/admin/accounts/${encodeURIComponent(id)}/status`, { method: 'PATCH', json: { status_aktif } })

// TODO: POST /admin/accounts/{id}/reset-password
export const resetAccountPassword = (id) =>
  request(`/admin/accounts/${encodeURIComponent(id)}/reset-password`, { method: 'POST' })

// TODO(backend): GET /admin/analyses -> semua analisis seluruh peneliti (PUBLIC & PRIVATE).
// Field yang dipakai: run_id, sample_name, owner_name | owner_email, visibility, status, created_at
export const getAdminAnalyses = () => request('/admin/analyses')

// TODO: GET /admin/health -> telemetri node, Nextflow daemon, storage. Sementara memakai /health yang sudah ada.
export const getAdminHealth = async () => {
  try { return await request('/admin/health') } catch (e) { if (e.status === 404) return health(); throw e }
}
