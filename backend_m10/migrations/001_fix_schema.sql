-- VarEscape (BIFIVE) - Migrasi perbaikan skema backend
-- Jalankan sekali di database varescape_db sebelum menyalakan uvicorn versi baru

-- Kolom metrik ringkasan pada analysis_runs
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS q20_rate DOUBLE PRECISION;
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS q30_rate DOUBLE PRECISION;
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS mapping_rate DOUBLE PRECISION;
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS mean_depth DOUBLE PRECISION;
ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS tstv_ratio DOUBLE PRECISION;

-- Samakan tipe waktu menjadi TIMESTAMPTZ (data lama dianggap UTC)
ALTER TABLE analysis_runs ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
ALTER TABLE analysis_runs ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE uploaded_files ALTER COLUMN uploaded_at TYPE TIMESTAMPTZ USING uploaded_at AT TIME ZONE 'UTC';
ALTER TABLE uploaded_files ALTER COLUMN uploaded_at SET DEFAULT now();

-- Tabel log pipeline (juga dibuat otomatis oleh create_all jika belum ada)
CREATE TABLE IF NOT EXISTS pipeline_logs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL REFERENCES analysis_runs(run_id),
    station_number INTEGER NOT NULL,
    log_level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pipeline_logs_run_id ON pipeline_logs (run_id);

-- Aktifkan akun untuk testing (ganti email sesuai akun kalian)
-- UPDATE users SET status_aktif = 'ACTIVE' WHERE email = 'peneliti@ipb.ac.id';
