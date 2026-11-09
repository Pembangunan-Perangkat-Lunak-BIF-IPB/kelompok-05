"""
utils/snpeff.py
Menyiapkan dan menjalankan anotasi SnpEff untuk Stasiun 5.

Tiga masalah yang sering bikin anotasi gagal diam-diam, dan ditangani di sini:

1. Perintah snpEff tidak ada / berupa .jar
   Diatur lewat SNPEFF_CMD, boleh "snpEff" atau "java -jar /path/snpEff.jar".

2. Database belum diunduh
   Dicek lewat `snpEff databases`; kalau SNPEFF_AUTO_DOWNLOAD=1 akan diunduh otomatis.

3. Nama kromosom di FASTA tidak sama dengan nama di database SnpEff
   Ini penyebab paling sering "semua Grantham = 0". SnpEff tidak gagal, ia hanya
   menulis ERROR_CHROMOSOME_NOT_FOUND. Di sini nama kromosom dideteksi dari pesan
   SnpEff lalu VCF ditulis ulang dengan nama yang benar, dan anotasi diulang.

Pakai dari terminal untuk memeriksa pemasangan:
    python -m utils.snpeff --cek
"""

import os
import re
import shlex
import shutil
import subprocess
from typing import List, Optional, Tuple

try:
    from config import SNPEFF_CMD, SNPEFF_DB, SNPEFF_DATADIR, SNPEFF_AUTO_DOWNLOAD
except ImportError:  # supaya modul tetap bisa diuji sendiri
    SNPEFF_CMD = os.getenv("SNPEFF_CMD", "snpEff")
    SNPEFF_DB = os.getenv("SNPEFF_DB", "NC_045512.2")
    SNPEFF_DATADIR = os.getenv("SNPEFF_DATADIR", "")
    SNPEFF_AUTO_DOWNLOAD = os.getenv("SNPEFF_AUTO_DOWNLOAD", "1") not in ("0", "", "false")


class SnpEffError(Exception):
    pass


def _q(x) -> str:
    return shlex.quote(str(x))


def _opsi_datadir() -> str:
    return f"-dataDir {_q(os.path.abspath(SNPEFF_DATADIR))}" if SNPEFF_DATADIR else ""


def _jalan(perintah: str, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f"set -o pipefail; {perintah}"],
                          capture_output=True, text=True, timeout=timeout)


def tersedia() -> bool:
    """Perintah SnpEff bisa dipanggil? Mendukung 'snpEff' maupun 'java -jar ....jar'."""
    bagian = shlex.split(SNPEFF_CMD or "")
    return bool(bagian) and shutil.which(bagian[0]) is not None


def versi() -> Optional[str]:
    if not tersedia():
        return None
    p = _jalan(f"{SNPEFF_CMD} -version")
    teks = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"SnpEff\s+([0-9][\w.\-]*)", teks)
    return m.group(1) if m else (teks.strip().splitlines() or [None])[0]


def database_terpasang(db: str = None) -> bool:
    """Cek nama database ada di daftar `snpEff databases` yang sudah terunduh/terdaftar."""
    db = db or SNPEFF_DB
    p = _jalan(f"{SNPEFF_CMD} databases {_opsi_datadir()}")
    if p.returncode != 0:
        return False
    for baris in (p.stdout or "").splitlines():
        if baris.split("\t")[0].strip() == db or baris.split()[:1] == [db]:
            return True
    return False


def unduh_database(db: str = None) -> Tuple[bool, str]:
    db = db or SNPEFF_DB
    p = _jalan(f"{SNPEFF_CMD} download {_opsi_datadir()} -v {_q(db)}")
    if p.returncode == 0:
        return True, f"Database SnpEff '{db}' berhasil diunduh."
    return False, f"Gagal mengunduh database '{db}': {((p.stderr or p.stdout) or '').strip()[-600:]}"


def kromosom_vcf(path: str) -> List[str]:
    """Daftar nama kromosom (kolom CHROM) yang muncul di VCF."""
    nama: List[str] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for baris in f:
            if baris.startswith("#"):
                continue
            c = baris.split("\t", 1)[0]
            if c and c not in nama:
                nama.append(c)
    return nama


def _kromosom_dari_pesan(teks: str) -> List[str]:
    """SnpEff menuliskan daftar kromosom yang dikenalnya saat nama tidak cocok."""
    nama: List[str] = []
    for m in re.finditer(r"[Aa]vailable chromosomes?:?\s*([^\n]+)", teks or ""):
        for bagian in re.findall(r"'([^']+)'", m.group(1)) or m.group(1).split(","):
            b = bagian.strip().strip("'\"[] ")
            if b and b not in nama:
                nama.append(b)
    return nama


def _hitung_ann(path: str) -> Tuple[int, int, int]:
    """(jumlah varian, jumlah ber-ANN, jumlah ERROR_CHROMOSOME_NOT_FOUND)."""
    total = ber_ann = chr_salah = 0
    if not os.path.exists(path):
        return 0, 0, 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for baris in f:
            if baris.startswith("#"):
                continue
            total += 1
            if "ANN=" in baris:
                ber_ann += 1
            if "ERROR_CHROMOSOME_NOT_FOUND" in baris:
                chr_salah += 1
    return total, ber_ann, chr_salah


def tulis_ulang_kromosom(vcf_in: str, vcf_out: str, nama_baru: str) -> int:
    """Menyalin VCF dengan kolom CHROM (dan header ##contig) diganti nama_baru."""
    diganti = 0
    with open(vcf_in, "r", encoding="utf-8", errors="ignore") as fin, \
         open(vcf_out, "w", encoding="utf-8") as fout:
        for baris in fin:
            if baris.startswith("##contig="):
                fout.write(re.sub(r"ID=[^,>]+", f"ID={nama_baru}", baris, count=1))
                continue
            if baris.startswith("#"):
                fout.write(baris)
                continue
            kolom = baris.split("\t")
            if kolom and kolom[0] != nama_baru:
                kolom[0] = nama_baru
                diganti += 1
            fout.write("\t".join(kolom))
    return diganti


def anotasi(vcf_in: str, vcf_out: str, db: str = None, catat=None) -> Tuple[bool, str, dict]:
    """
    Menjalankan anotasi SnpEff.

    catat: fungsi opsional catat(level, pesan) untuk menulis ke pipeline_logs.
    Mengembalikan (berhasil, path_vcf_terpakai, ringkasan).
    Jika gagal, path yang dikembalikan adalah vcf_in agar pipeline tetap jalan tanpa anotasi.
    """
    db = db or SNPEFF_DB
    ringkas = {"db": db, "versi": None, "total": 0, "ber_ann": 0,
               "kromosom_vcf": [], "kromosom_db": [], "diganti": False}

    def log(level, pesan):
        if catat:
            catat(level, pesan)
        else:
            print(f"[{level}] {pesan}")

    if not tersedia():
        log("WARNING", f"SnpEff tidak ditemukan (SNPEFF_CMD='{SNPEFF_CMD}'). "
                       "Anotasi dilewati, skor Grantham akan 0. "
                       "Pasang SnpEff lalu isi SNPEFF_CMD di .env.")
        return False, vcf_in, ringkas

    ringkas["versi"] = versi()
    ringkas["kromosom_vcf"] = kromosom_vcf(vcf_in)

    if not database_terpasang(db):
        if SNPEFF_AUTO_DOWNLOAD:
            log("INFO", f"Database SnpEff '{db}' belum ada, mencoba mengunduh...")
            ok, pesan = unduh_database(db)
            log("INFO" if ok else "WARNING", pesan)
            if not ok:
                return False, vcf_in, ringkas
        else:
            log("WARNING", f"Database SnpEff '{db}' belum terpasang dan unduh otomatis dimatikan. "
                           f"Jalankan: {SNPEFF_CMD} download {db}")
            return False, vcf_in, ringkas

    def sekali(masukan: str, keluaran: str):
        p = _jalan(f"{SNPEFF_CMD} ann -noStats {_opsi_datadir()} {_q(db)} {_q(masukan)} > {_q(keluaran)}")
        return p

    p = sekali(vcf_in, vcf_out)
    if p.returncode != 0:
        log("WARNING", f"SnpEff gagal dijalankan: {((p.stderr or p.stdout) or '').strip()[-800:]}")
        return False, vcf_in, ringkas

    total, ber_ann, chr_salah = _hitung_ann(vcf_out)
    ringkas.update(total=total, ber_ann=ber_ann)

    # Nama kromosom tidak cocok -> ganti nama lalu ulangi sekali
    if total and (chr_salah or ber_ann == 0):
        kandidat = _kromosom_dari_pesan((p.stderr or "") + (p.stdout or ""))
        ringkas["kromosom_db"] = kandidat
        if kandidat:
            nama_baru = kandidat[0]
            log("WARNING", f"Nama kromosom VCF {ringkas['kromosom_vcf']} tidak dikenal database "
                           f"'{db}'. Mengganti menjadi '{nama_baru}' lalu mengulang anotasi.")
            vcf_rename = vcf_in + ".renamed.vcf"
            tulis_ulang_kromosom(vcf_in, vcf_rename, nama_baru)
            p2 = sekali(vcf_rename, vcf_out)
            if p2.returncode == 0:
                total, ber_ann, chr_salah = _hitung_ann(vcf_out)
                ringkas.update(total=total, ber_ann=ber_ann, diganti=True)
        else:
            log("WARNING", f"Tidak ada varian yang teranotasi. Nama kromosom di FASTA "
                           f"({', '.join(ringkas['kromosom_vcf']) or '-'}) kemungkinan berbeda "
                           f"dengan database SnpEff '{db}'.")

    if ber_ann == 0:
        log("WARNING", "SnpEff selesai tetapi tidak ada varian yang teranotasi; "
                       "skor Grantham akan 0. Periksa kecocokan genom acuan dan database.")
        return False, vcf_in, ringkas

    log("SUCCESS", f"SnpEff {ringkas['versi'] or ''} selesai: {ber_ann} dari {total} varian teranotasi "
                   f"(database {db}{', nama kromosom disesuaikan' if ringkas['diganti'] else ''}).")
    return True, vcf_out, ringkas


def diagnosa() -> str:
    """Ringkasan kesiapan SnpEff, untuk dijalankan manual sebelum analisis."""
    baris = [f"SNPEFF_CMD        : {SNPEFF_CMD}",
             f"SNPEFF_DB         : {SNPEFF_DB}",
             f"SNPEFF_DATADIR    : {SNPEFF_DATADIR or '(bawaan SnpEff)'}",
             f"Unduh otomatis    : {'ya' if SNPEFF_AUTO_DOWNLOAD else 'tidak'}"]
    if not tersedia():
        baris.append("Status            : TIDAK SIAP - perintah SnpEff tidak ditemukan di PATH")
        baris.append("Saran             : conda install -c bioconda snpeff, "
                     "atau isi SNPEFF_CMD='java -jar /path/snpEff.jar'")
        return "\n".join(baris)
    baris.append(f"Versi SnpEff      : {versi()}")
    ada = database_terpasang()
    baris.append(f"Database '{SNPEFF_DB}' : {'sudah ada' if ada else 'BELUM ada'}")
    if not ada:
        baris.append(f"Saran             : {SNPEFF_CMD} download {SNPEFF_DB}")
    baris.append(f"Status            : {'SIAP' if ada else 'BELUM SIAP'}")
    return "\n".join(baris)


if __name__ == "__main__":
    import sys
    if "--cek" in sys.argv:
        print(diagnosa())
    elif len(sys.argv) >= 3:
        ok, path, ringkas = anotasi(sys.argv[1], sys.argv[2])
        print("berhasil:", ok, "| dipakai:", path, "|", ringkas)
    else:
        print(__doc__)
