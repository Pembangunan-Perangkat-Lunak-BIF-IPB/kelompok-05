"""
config.py
Konfigurasi terpusat. Dimuat paling awal agar .env terbaca sebelum modul lain.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

# Folder penyimpanan berkas unggahan (absolut, tidak bergantung pada folder tempat uvicorn dijalankan)
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))).resolve()

# Pengaturan pipeline
PIPELINE_THREADS = int(os.getenv("PIPELINE_THREADS", "4"))
# SnpEff. SNPEFF_CMD boleh berupa perintah ("snpEff") atau pemanggilan jar
# ("java -jar /opt/snpEff/snpEff.jar"). SNPEFF_DATADIR diisi kalau database
# disimpan di folder sendiri. SNPEFF_AUTO_DOWNLOAD=1 akan mengunduh database
# yang belum ada saat analisis pertama dijalankan.
SNPEFF_CMD = os.getenv("SNPEFF_CMD", "snpEff")
SNPEFF_DB = os.getenv("SNPEFF_DB", "NC_045512.2")
SNPEFF_DATADIR = os.getenv("SNPEFF_DATADIR", "")
SNPEFF_AUTO_DOWNLOAD = os.getenv("SNPEFF_AUTO_DOWNLOAD", "1").strip().lower() not in ("0", "false", "no", "")
