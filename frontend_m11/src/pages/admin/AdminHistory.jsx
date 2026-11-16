
import { useEffect, useMemo, useState } from 'react'
import { getAdminAnalyses } from '../../lib/api'
import Icon from '../../components/Icon'
import '../history.css'

const STATUS = {
  COMPLETED: ['SELESAI', ''],
  FAILED: ['GAGAL', 'bad'],
  RUNNING: ['BERJALAN', 'run'],
  PROCESSING: ['BERJALAN', 'run'],
  QUEUED: ['ANTRI', 'wait'],
  PENDING: ['MENUNGGU', 'wait'],
  UPLOADED: ['SIAP', 'wait'],
  CANCELLED: ['DIBATALKAN', 'bad'],
}

function fmt(value) {
  if (!value) return '-'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  return date.toLocaleString('id-ID', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function ownerLabel(row) {
  return (
    row.owner_name ||
    row.owner_email ||
    '-'
  )
}

function normalizeRows(response) {
  if (Array.isArray(response)) {
    return response
  }

  if (Array.isArray(response?.items)) {
    return response.items
  }

  if (Array.isArray(response?.analyses)) {
    return response.analyses
  }

  throw new Error(
    'Format respons riwayat analisis tidak sesuai.'
  )
}

export default function AdminHistory() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [vis, setVis] = useState('ALL')

  useEffect(() => {
    let cancelled = false

    async function loadHistory() {
      try {
        setError('')
        setRows(null)

        const response = await getAdminAnalyses()

        const data = normalizeRows(response)

        const sorted = [...data].sort((a, b) => {
          return String(b.created_at ?? '').localeCompare(
            String(a.created_at ?? '')
          )
        })

        if (!cancelled) {
          setRows(sorted)
        }
      } catch (err) {
        if (cancelled) return

        const message =
          err?.status === 403
            ? 'Akses ditolak. Endpoint ini hanya untuk Administrator aktif.'
            : err?.status === 404
              ? 'Endpoint riwayat analisis belum ditemukan di backend.'
              : err?.message ||
                'Gagal mengambil riwayat analisis.'

        setError(message)
        setRows(null)
      }
    }

    loadHistory()

    return () => {
      cancelled = true
    }
  }, [])

  const shown = useMemo(() => {
    const keyword = q.trim().toLowerCase()

    return (rows ?? []).filter((row) => {
      const visibility = String(
        row.visibility ?? ''
      ).toUpperCase()

      if (vis !== 'ALL' && visibility !== vis) {
        return false
      }

      if (!keyword) {
        return true
      }

      const searchable = [
        row.run_id,
        row.sample_name,
        row.owner_name,
        row.owner_email,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return searchable.includes(keyword)
    })
  }, [rows, q, vis])

  const total = rows?.length ?? 0

  const pub = (rows ?? []).filter(
    (row) =>
      String(row.visibility).toUpperCase() === 'PUBLIC'
  ).length

  const priv = (rows ?? []).filter(
    (row) =>
      String(row.visibility).toUpperCase() === 'PRIVATE'
  ).length

  return (
    <>
      <div className="hh">
        <div>
          <h1>Riwayat Analisis Peneliti</h1>
          <p>
            Menampilkan seluruh riwayat analisis
            para peneliti, baik Public maupun Private.
          </p>
        </div>

        <div className="mini">
          <div>
            <small>TOTAL ANALISIS</small>
            <b>
              {rows === null && !error
                ? 'Memuat...'
                : `${total} Berkas`}
            </b>

            <span>
              {rows !== null
                ? ` (${pub} Public · ${priv} Private)`
                : ''}
            </span>
          </div>
        </div>
      </div>

      <div className="bar-f">
        <div className="grp">
          <input
            value={q}
            onChange={(event) =>
              setQ(event.target.value)
            }
            placeholder="Cari berdasarkan Run ID, sampel, atau peneliti..."
            aria-label="Cari riwayat analisis"
            style={{ maxWidth: 420 }}
          />

          <select
            value={vis}
            onChange={(event) =>
              setVis(event.target.value)
            }
            aria-label="Visibilitas"
          >
            <option value="ALL">
              Semua Visibilitas
            </option>
            <option value="PUBLIC">
              Public
            </option>
            <option value="PRIVATE">
              Private
            </option>
          </select>
        </div>

        <button
          className="a-btn"
          onClick={() => {
            setQ('')
            setVis('ALL')
          }}
        >
          <Icon name="refresh" size={11} />
          {' '}
          Reset Filter
        </button>
      </div>

      {error && (
        <p
          className="alert error"
          role="alert"
          style={{ marginBottom: 12 }}
        >
          {error}
        </p>
      )}

      <div className="tbl-card">
        <div
          className="sec-h"
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid #e2e8f0',
          }}
        >
          <h2 style={{ fontSize: 15 }}>
            <Icon name="clock" size={14} />
            {' '}
            Daftar Riwayat Analisis
          </h2>

          <small className="muted">
            {rows !== null
              ? `Menampilkan ${shown.length} dari ${total} berkas`
              : 'Data belum tersedia'}
          </small>
        </div>

        <div
          className="h-row th"
          style={{
            gridTemplateColumns:
              '1.2fr 1.8fr 1.8fr 1.1fr 1.6fr 1.1fr',
          }}
        >
          <span>RUN ID</span>
          <span>SAMPEL</span>
          <span>PENELITI</span>
          <span>VISIBILITAS</span>
          <span>TANGGAL ANALISIS</span>
          <span>STATUS</span>
        </div>

        {rows === null && !error && (
          <div className="empty">
            Memuat riwayat analisis...
          </div>
        )}

        {rows === null && error && (
          <div className="empty">
            Riwayat belum dapat ditampilkan.
          </div>
        )}

        {rows !== null &&
          shown.length === 0 && (
            <div className="empty">
              {total === 0
                ? 'Belum ada riwayat analisis.'
                : 'Tidak ditemukan analisis yang sesuai dengan filter.'}
            </div>
          )}

        {shown.map((row) => {
          const status = String(
            row.status ?? ''
          ).toUpperCase()

          const visibility = String(
            row.visibility ?? ''
          ).toUpperCase()

          const [label, cls] =
            STATUS[status] ?? [status || '-', 'wait']

          return (
            <div
              className="h-row"
              style={{
                gridTemplateColumns:
                  '1.2fr 1.8fr 1.8fr 1.1fr 1.6fr 1.1fr',
              }}
              key={row.run_id}
            >
              <b
                style={{
                  color: 'var(--teal-d)',
                }}
              >
                {row.run_id}
              </b>

              <b>{row.sample_name || '-'}</b>

              <span
                className="d"
                style={{ fontSize: 12 }}
                title={row.owner_email || ''}
              >
                {ownerLabel(row)}
              </span>

              <span
                className={`vis ${
                  visibility === 'PUBLIC'
                    ? 'pub'
                    : ''
                }`}
              >
                <Icon
                  name={
                    visibility === 'PUBLIC'
                      ? 'globe'
                      : 'lock'
                  }
                  size={10}
                />
                {' '}
                {visibility || '-'}
              </span>

              <span className="d">
                {fmt(row.created_at)}
              </span>

              <span className={`sbadge ${cls}`}>
                <i />
                {label}
              </span>
            </div>
          )
        })}
      </div>
    </>
  )
}