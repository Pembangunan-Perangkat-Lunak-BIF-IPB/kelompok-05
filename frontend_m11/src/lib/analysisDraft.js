
import { useSyncExternalStore } from 'react'
import { validateFormat, splitFastqPair } from './validators'
import { defaultValues, validateParams, buildRunPayload } from './params'
import {
  uploadAnalysis,
  runAnalysis,
  lastRun,
  validateFastqHeaders,
} from './api'

const initial = () => ({
  sampleName: '',
  files: {},
  checks: {},
  headerCheck: null,
  mode: 'default',
  vals: defaultValues(),
  phase: 'idle',
  error: '',
  pairError: '',
  result: null,
  ownerId: null,
})

let state = initial()
let validationId = 0
let activeRequest = null

const listeners = new Set()

function emit(patch) {
  state = { ...state, ...patch }
  listeners.forEach((listener) => listener())
}

function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function getSnapshot() {
  return state
}

export function useAnalysisDraft() {
  return useSyncExternalStore(subscribe, getSnapshot)
}

function busy() {
  return ['uploading', 'starting'].includes(state.phase)
}

export const analysisDraft = {
  setOwner(id) {
    if (state.ownerId !== id) {
      validationId += 1
      activeRequest = null
      state = { ...initial(), ownerId: id }
      listeners.forEach((listener) => listener())
    }
  },

  setSampleName(value) {
    if (!busy() && !state.result) {
      emit({ sampleName: value })
    }
  },

  setMode(value) {
    if (!busy() && !state.result && state.headerCheck?.ok) {
      emit({ mode: value, error: '' })
    }
  },

  setValues(values) {
    if (!busy() && !state.result && state.headerCheck?.ok) {
      emit({ vals: values, error: '' })
    }
  },

  restoreDefaults() {
    if (!busy() && !state.result && state.headerCheck?.ok) {
      emit({ vals: defaultValues(), error: '' })
    }
  },

  
  async selectFiles(fileList) {
    if (busy() || state.result) return

    const selectedFiles = Array.from(fileList ?? [])
    if (!selectedFiles.length) return

    const pair = splitFastqPair(selectedFiles)

    if (pair.error) {
      emit({ pairError: pair.error, error: '' })
      return
    }

    const currentId = ++validationId
    const selected = { r1: pair.r1, r2: pair.r2 }

    // Simpan File objects agar tidak hilang saat navigasi.
    emit({
      files: selected,
      checks: {},
      headerCheck: null,
      pairError: '',
      error: '',
      phase: 'validating',
    })

    try {
      // LAPIS 1 — Pemeriksaan lokal di browser.
      const [r1, r2] = await Promise.all([
        validateFormat('fastq', pair.r1),
        validateFormat('fastq', pair.r2),
      ])

      if (currentId !== validationId) return

      const checks = { r1, r2 }

      if (!r1.ok || !r2.ok) {
        emit({
          checks,
          phase: 'invalid',
          error: 'Ada FASTQ yang tidak lolos validasi format.',
        })
        return
      }

      // Format PASS, tetapi header masih belum diperiksa.
      emit({
        checks,
        phase: 'checking_headers',
        error: '',
      })

      // LAPIS 2 — Pemeriksaan di backend.
      const validation = await validateFastqHeaders(
        pair.r1,
        pair.r2
      )

      // Abaikan respons lama jika pengguna memilih file lain.
      if (currentId !== validationId) return

      const passed =
        validation.status === 'PASS' &&
        validation.header === 'PASS' &&
        validation.sequence_integrity === 'PASS' &&
        validation.paired_end === true

      emit({
        headerCheck: {
          ok: passed,
          readCount: validation.read_count,
          message: validation.message,
        },
        phase: passed ? 'ready' : 'invalid',
        error: passed
          ? ''
          : 'Validasi header FASTQ tidak berhasil.',
      })
    } catch (err) {
      if (currentId !== validationId) return

      emit({
        headerCheck:
          state.checks.r1?.ok && state.checks.r2?.ok
            ? {
                ok: false,
                message: err.message || 'Validasi header gagal.',
              }
            : null,
        phase: 'invalid',
        error: err.message || 'Pemeriksaan FASTQ gagal.',
      })
    }
  },


  async start() {
    if (activeRequest) return activeRequest

    if (state.phase === 'started' && state.result?.run_id) {
      return state.result.run_id
    }

    if (busy()) return null

    const { files, checks, mode, vals, sampleName } = state

    if (
      !files.r1 ||
      !files.r2 ||
      !checks.r1?.ok ||
      !checks.r2?.ok ||
      !state.headerCheck?.ok ||
      state.phase === 'validating' ||
      state.phase === 'checking_headers'
    ) {
      emit({
        error: 'Kedua FASTQ harus lolos validasi format dan header terlebih dahulu.',
      })
      return null
    }

    if (mode === 'custom' &&
        Object.keys(validateParams(vals)).length > 0) {
      emit({ error: 'Perbaiki parameter Custom terlebih dahulu.' })
      return null
    }

    const payload = buildRunPayload(mode, vals)

    activeRequest = (async () => {
      try {
        let runId = state.result?.run_id

        if (!runId) {
          emit({ phase: 'uploading', error: '' })

          // Parameter final dikirim bersamaan dengan FASTQ.
          const uploaded = await uploadAnalysis({
            sampleName: sampleName.trim() || 'Sampel Uji Coba',
            r1: files.r1,
            r2: files.r2,
            executionMode: payload.execution_mode,
            parameters: payload.parameters,
          })

          runId = uploaded.run_id
          lastRun.set(runId)
          emit({ result: uploaded })
        }

        emit({ phase: 'starting', error: '' })

        await runAnalysis(runId)

        emit({ phase: 'started', error: '' })
        return runId
      } catch (err) {
        emit({
          phase: state.result?.run_id ? 'retry' : 'ready',
          error: err.message || 'Gagal memulai analisis.',
        })
        return null
      } finally {
        activeRequest = null
      }
    })()

    return activeRequest
  },

  reset() {
    if (busy()) return false

    validationId += 1
    const ownerId = state.ownerId
    emit({ ...initial(), ownerId })
    return true
  },
}
