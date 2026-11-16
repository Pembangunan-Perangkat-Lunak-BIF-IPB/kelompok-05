-- Jalankan di database PostgreSQL VarEscape dengan AUTOCOMMIT (DBeaver).
-- Enum PostgreSQL tidak diperbarui otomatis oleh create_all().
ALTER TYPE runstatus ADD VALUE IF NOT EXISTS 'CANCELLED';
