-- Jalankan sekali lewat DBeaver pada database varescape_db sebelum memakai
-- tombol Nonaktifkan dari frontend. Aman dijalankan ulang pada PostgreSQL modern.
-- Jalankan sebagai satu statement tersendiri (jangan dalam transaksi migrasi lain).
ALTER TYPE public.userstatus ADD VALUE IF NOT EXISTS 'SUSPENDED';
