"""
utils/pipeline.py
Eksekusi pipeline 5 stasiun di latar belakang.

Stasiun 1  QC (fastp)
Stasiun 2  Read mapping (bwa-mem2 + samtools)
Stasiun 3  Variant calling (bcftools, ploidy 1 untuk virus)
Stasiun 4  Quality filtering (DP>=10, MQ>=30, QUAL>=30, AF>=0.20)
Stasiun 5  Anotasi SnpEff + epitope mapping IEDB + Grantham + risk level
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import traceback
from datetime import datetime, timezone

from sqlalchemy.orm import Session

import models
from config import UPLOAD_DIR, PIPELINE_THREADS, SNPEFF_CMD, SNPEFF_DB
from database import SessionLocal
from utils.genomics import calculate_tstv_ratio
from utils.snpeff import anotasi as anotasi_snpeff
from utils.vcf_parser import filter_vcf, parse_and_store_vcf

REQUIRED_TOOLS = ["fastp", "bwa-mem2", "samtools", "bcftools"]


class PipelineError(Exception):
    pass


def _now():
    return datetime.now(timezone.utc)


def _q(path) -> str:
    """Quote path agar aman untuk shell (spasi, karakter khusus)."""
    return shlex.quote(str(path))


def log_pipeline(db: Session, run_id: str, station_number: int, log_level: str, message: str):
    """Menyimpan log ke tabel pipeline_logs (dibaca FE lewat endpoint status) dan mencetak ke terminal."""
    print(f"[{run_id}][Stasiun {station_number}][{log_level}] {message}")
    try:
        db.add(models.PipelineLog(
            run_id=run_id,
            station_number=station_number,
            log_level=log_level,
            message=message,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Gagal menyimpan log pipeline: {e}")


def execute_cmd(command: str) -> str:
    """Menjalankan perintah CLI via bash. pipefail agar error di awal pipe (mis. bwa-mem2) tidak tertutup."""
    result = subprocess.run(["bash", "-c", f"set -o pipefail; {command}"], capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise PipelineError(f"Perintah gagal: {command}\n{err[-1500:]}")
    return result.stdout or result.stderr


def check_tools():
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing:
        raise PipelineError(
            f"Tool tidak ditemukan di PATH: {', '.join(missing)}. "
            "Pastikan uvicorn dijalankan dari WSL di environment (conda) yang berisi tool tersebut."
        )


def _get_file(db: Session, run_id: str, file_type: models.FileType):
    return db.query(models.UploadedFile).filter(
        models.UploadedFile.run_id == run_id,
        models.UploadedFile.file_type == file_type,
    ).first()


def run_analysis_pipeline(run_id: str):
    db: Session = SessionLocal()
    station = 0
    try:
        run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
        if not run:
            print(f"Run ID {run_id} tidak ditemukan.")
            return

        run.status = models.RunStatus.RUNNING
        if run.started_at is None:
            run.started_at = _now()
        db.commit()

        run_folder = UPLOAD_DIR / run_id
        run_folder.mkdir(parents=True, exist_ok=True)

        f_r1 = _get_file(db, run_id, models.FileType.FASTQ_R1)
        f_r2 = _get_file(db, run_id, models.FileType.FASTQ_R2)
        f_fa = _get_file(db, run_id, models.FileType.FASTA)
        f_iedb = _get_file(db, run_id, models.FileType.IEDB)

        if not f_r1 or not f_fa:
            raise PipelineError("Berkas FASTQ R1 atau FASTA genom acuan tidak ditemukan di database.")

        r1_path = f_r1.file_path
        r2_path = f_r2.file_path if f_r2 and os.path.exists(f_r2.file_path) else None
        fasta_path = f_fa.file_path
        iedb_path = f_iedb.file_path if f_iedb else ""

        for p in [r1_path, fasta_path]:
            if not os.path.exists(p):
                raise PipelineError(f"Berkas tidak ditemukan di disk: {p}")

        check_tools()

        clean_r1 = run_folder / "clean_R1.fq"
        clean_r2 = run_folder / "clean_R2.fq"
        aligned_bam = run_folder / "aligned.bam"
        raw_vcf = run_folder / "variants.vcf"
        filtered_vcf = run_folder / "variants.filtered.vcf"
        annotated_vcf = run_folder / "variants.ann.vcf"

        # --- STASIUN 1: Quality Control (fastp) ---
        station = 1
        log_pipeline(db, run_id, 1, "INFO", "Memulai Stasiun 1: Quality Control dengan fastp...")
        fastp_json = run_folder / "fastp.json"
        report = f"-h {_q(run_folder / 'fastp.html')} -j {_q(fastp_json)} -w {PIPELINE_THREADS}"
        if r2_path:
            execute_cmd(f"fastp -i {_q(r1_path)} -I {_q(r2_path)} -o {_q(clean_r1)} -O {_q(clean_r2)} {report}")
        else:
            execute_cmd(f"fastp -i {_q(r1_path)} -o {_q(clean_r1)} {report}")

        try:
            with open(fastp_json, "r") as f:
                after = json.load(f).get("summary", {}).get("after_filtering", {})
            run.q20_rate = round(after.get("q20_rate", 0.0) * 100, 2)
            run.q30_rate = round(after.get("q30_rate", 0.0) * 100, 2)
            db.commit()
        except Exception as e:
            log_pipeline(db, run_id, 1, "WARNING", f"Gagal membaca fastp.json: {e}")
        log_pipeline(db, run_id, 1, "SUCCESS", "Stasiun 1 selesai: pembersihan read FASTQ berhasil.")

        # --- STASIUN 2: Read Mapping (bwa-mem2 & samtools) ---
        station = 2
        log_pipeline(db, run_id, 2, "INFO", "Memulai Stasiun 2: pemetaan read dengan bwa-mem2...")
        if not os.path.exists(f"{fasta_path}.bwt.2bit.64"):
            execute_cmd(f"bwa-mem2 index {_q(fasta_path)}")
        if not os.path.exists(f"{fasta_path}.fai"):
            execute_cmd(f"samtools faidx {_q(fasta_path)}")

        reads = f"{_q(clean_r1)} {_q(clean_r2)}" if r2_path else _q(clean_r1)
        execute_cmd(
            f"bwa-mem2 mem -t {PIPELINE_THREADS} {_q(fasta_path)} {reads} "
            f"| samtools sort -@ 2 -o {_q(aligned_bam)} -"
        )
        execute_cmd(f"samtools index {_q(aligned_bam)}")

        try:
            flagstat = execute_cmd(f"samtools flagstat {_q(aligned_bam)}")
            m = re.search(r"mapped \((\d+(?:\.\d+)?)%", flagstat)
            if m:
                run.mapping_rate = float(m.group(1))

            cov_lines = [l for l in execute_cmd(f"samtools coverage {_q(aligned_bam)}").strip().splitlines() if l]
            if len(cov_lines) >= 2:
                header = cov_lines[0].lstrip("#").split("\t")
                idx = header.index("meandepth") if "meandepth" in header else 6
                depths = [float(l.split("\t")[idx]) for l in cov_lines[1:]]
                run.mean_depth = round(sum(depths) / len(depths), 2)
            db.commit()
        except Exception as e:
            db.rollback()
            log_pipeline(db, run_id, 2, "WARNING", f"Gagal menghitung statistik BAM: {e}")
        log_pipeline(db, run_id, 2, "SUCCESS", "Stasiun 2 selesai: alignment dan indexing BAM berhasil.")

        # --- STASIUN 3: Variant Calling (bcftools) ---
        station = 3
        log_pipeline(db, run_id, 3, "INFO", "Memulai Stasiun 3: variant calling dengan bcftools...")
        execute_cmd(
            f"bcftools mpileup -f {_q(fasta_path)} -d 10000 -a AD,DP -Ou {_q(aligned_bam)} "
            f"| bcftools call --ploidy 1 -mv -Ov -o {_q(raw_vcf)}"
        )
        log_pipeline(db, run_id, 3, "SUCCESS", "Stasiun 3 selesai: berkas VCF varian berhasil dibuat.")

        # --- STASIUN 4: Quality Filtering ---
        station = 4
        log_pipeline(db, run_id, 4, "INFO", "Memulai Stasiun 4: quality filtering varian...")
        total, passed = filter_vcf(str(raw_vcf), str(filtered_vcf))
        log_pipeline(
            db, run_id, 4, "SUCCESS",
            f"Stasiun 4 selesai: {passed} dari {total} varian lolos (DP≥10, MQ≥30, QUAL≥30, AF≥0.20).",
        )

        # --- STASIUN 5: Anotasi SnpEff, Epitope Mapping & Grantham ---
        station = 5
        log_pipeline(db, run_id, 5, "INFO", "Memulai Stasiun 5: anotasi SnpEff, epitope mapping & Grantham...")
        # Anotasi ditangani utils/snpeff.py: cek perintah, cek & unduh database,
        # lalu menyesuaikan nama kromosom bila FASTA berbeda dengan database.
        ok_ann, vcf_to_store, ringkas = anotasi_snpeff(
            str(filtered_vcf), str(annotated_vcf),
            catat=lambda level, pesan: log_pipeline(db, run_id, 5, level, pesan),
        )

        stored, annotated = parse_and_store_vcf(str(vcf_to_store), run_id, iedb_path, db)
        if stored and annotated == 0 and ok_ann:
            log_pipeline(db, run_id, 5, "WARNING",
                         f"VCF teranotasi tetapi tag ANN tidak terbaca saat penyimpanan "
                         f"(database {ringkas.get('db')}).")

        variants = db.query(models.VariantResult).filter(models.VariantResult.run_id == run_id).all()
        _, _, tstv = calculate_tstv_ratio([{"ref": v.ref_allele, "alt": v.alt_allele} for v in variants])

        run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
        run.tstv_ratio = tstv
        run.status = models.RunStatus.COMPLETED
        run.completed_at = _now()
        db.commit()
        log_pipeline(db, run_id, 5, "SUCCESS", f"Seluruh pipeline selesai: {stored} varian tersimpan.")

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        try:
            run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
            if run:
                run.status = models.RunStatus.FAILED
                run.completed_at = _now()
                db.commit()
        except Exception:
            db.rollback()
        log_pipeline(db, run_id, station or 1, "ERROR", f"Pipeline terhenti: {e}"[:4000])
    finally:
        db.close()
