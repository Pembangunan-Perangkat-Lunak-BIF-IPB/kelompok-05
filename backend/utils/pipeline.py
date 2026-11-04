import os
import subprocess
import json
import re
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from utils.vcf_parser import parse_and_store_vcf
from utils.genomics import calculate_tstv_ratio

BASE_UPLOAD_DIR = "uploads"

def log_pipeline(db: Session, run_id: str, station_number: int, log_level: str, message: str):
    """Menyimpan catatan log pipeline ke database agar dapat dibaca oleh Frontend."""
    if hasattr(models, 'PipelineLog'):
        log_entry = models.PipelineLog(
            run_id=run_id,
            station_number=station_number,
            log_level=log_level,
            message=message
        )
        db.add(log_entry)
        db.commit()

def execute_cmd(command: str):
    """Menjalankan perintah CLI bioinformatika Linux secara native di WSL."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Command failed: {command}\nError output: {result.stderr}")
    return result.stdout or result.stderr

def run_analysis_pipeline(run_id: str):
    db: Session = SessionLocal()
    run = None
    try:
        run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
        if not run:
            print(f"Run ID {run_id} tidak ditemukan.")
            return

        # 1. Update status analisis menjadi RUNNING
        run.status = models.RunStatus.RUNNING
        run.started_at = datetime.utcnow()
        db.commit()

        run_folder = os.path.join(BASE_UPLOAD_DIR, run_id)
        os.makedirs(run_folder, exist_ok=True)

        file_r1 = db.query(models.UploadedFile).filter(
            models.UploadedFile.run_id == run_id,
            models.UploadedFile.file_type == models.FileType.FASTQ_R1
        ).first()

        file_r2 = db.query(models.UploadedFile).filter(
            models.UploadedFile.run_id == run_id,
            models.UploadedFile.file_type == models.FileType.FASTQ_R2
        ).first()

        file_fasta = db.query(models.UploadedFile).filter(
            models.UploadedFile.run_id == run_id,
            models.UploadedFile.file_type == models.FileType.FASTA
        ).first()

        file_iedb = db.query(models.UploadedFile).filter(
            models.UploadedFile.run_id == run_id,
            models.UploadedFile.file_type == models.FileType.IEDB
        ).first()

        if not file_r1 or not file_fasta:
            raise Exception("Berkas FASTQ R1 atau FASTA genom acuan tidak ditemukan di database.")

        r1_path = file_r1.file_path
        r2_path = file_r2.file_path if file_r2 else None
        fasta_path = file_fasta.file_path
        iedb_path = file_iedb.file_path if file_iedb else ""

        clean_r1 = os.path.join(run_folder, "clean_R1.fq")
        clean_r2 = os.path.join(run_folder, "clean_R2.fq") if r2_path else None
        aligned_bam = os.path.join(run_folder, "aligned.bam")
        output_vcf = os.path.join(run_folder, "variants.vcf")

        # --- STASIUN 1: Quality Control (fastp) ---
        log_pipeline(db, run_id, 1, "INFO", "Memulai Stasiun 1: Quality Control dengan fastp...")
        if r2_path and os.path.exists(r2_path):
            cmd_fastp = f"fastp -i {r1_path} -I {r2_path} -o {clean_r1} -O {clean_r2} -h {run_folder}/fastp.html -j {run_folder}/fastp.json"
        else:
            cmd_fastp = f"fastp -i {r1_path} -o {clean_r1} -h {run_folder}/fastp.html -j {run_folder}/fastp.json"
        
        execute_cmd(cmd_fastp)
        
        # Ekstrak Q20 & Q30
        fastp_json_path = os.path.join(run_folder, "fastp.json")
        if os.path.exists(fastp_json_path):
            try:
                with open(fastp_json_path, "r") as f:
                    qdata = json.load(f)
                    after_filt = qdata.get("summary", {}).get("after_filtering", {})
                    run.q20_rate = round(after_filt.get("q20_rate", 0.0) * 100, 2)
                    run.q30_rate = round(after_filt.get("q30_rate", 0.0) * 100, 2)
                    db.commit()
            except Exception as e:
                print(f"Gagal membaca fastp.json: {e}")

        log_pipeline(db, run_id, 1, "INFO", "Stasiun 1 Selesai: Pembersihan read FASTQ berhasil.")

        # --- STASIUN 2: Read Alignment (bwa-mem2 & samtools) ---
        log_pipeline(db, run_id, 2, "INFO", "Memulai Stasiun 2: Pemetaan Read menggunakan bwa-mem2...")
        
        execute_cmd(f"bwa-mem2 index {fasta_path}")
        
        if r2_path and os.path.exists(r2_path):
            cmd_align = f"bwa-mem2 mem -t 4 {fasta_path} {clean_r1} {clean_r2} | samtools sort -o {aligned_bam}"
        else:
            cmd_align = f"bwa-mem2 mem -t 4 {fasta_path} {clean_r1} | samtools sort -o {aligned_bam}"
        
        execute_cmd(cmd_align)
        execute_cmd(f"samtools index {aligned_bam}")

        # Hitung Mapping Rate & Read Depth
        try:
            flagstat = execute_cmd(f"samtools flagstat {aligned_bam}")
            mapped_matches = re.findall(r'(\d+(?:\.\d+)?)%', flagstat)
            if mapped_matches:
                run.mapping_rate = float(mapped_matches[0])

            coverage_out = execute_cmd(f"samtools coverage {aligned_bam}")
            cov_lines = coverage_out.strip().split("\n")
            if len(cov_lines) >= 2:
                cols = cov_lines[1].split("\t")
                if len(cols) >= 7:
                    run.read_depth = round(float(cols[6]), 2)
            db.commit()
        except Exception as e:
            print(f"Gagal menghitung statistik BAM: {e}")

        log_pipeline(db, run_id, 2, "INFO", "Stasiun 2 Selesai: Alignment ke genom acuan dan indexing BAM sukses.")

        # --- STASIUN 3: Variant Calling (bcftools) ---
        log_pipeline(db, run_id, 3, "INFO", "Memulai Stasiun 3: Variant Calling dengan bcftools...")
        cmd_bcftools = f"bcftools mpileup -f {fasta_path} {aligned_bam} | bcftools call -mv -Ov -o {output_vcf}"
        execute_cmd(cmd_bcftools)
        log_pipeline(db, run_id, 3, "INFO", "Stasiun 3 Selesai: Berkas VCF varian berhasil dibuat.")

        # --- STASIUN 4 & 5: Filtering & Epitope Risk Scoring ---
        log_pipeline(db, run_id, 4, "INFO", "Memulai Stasiun 4 & 5: Quality Filtering & Immune Escape Profiling...")
        
        # PERBAIKAN: Pemanggilan fungsi parse_and_store_vcf dengan 4 argumen
        parse_and_store_vcf(output_vcf, run.run_id, iedb_path, db)

        # Hitung Ts/Tv Ratio
        variants = db.query(models.VariantResult).filter(models.VariantResult.run_id == run_id).all()
        snp_list = [{"ref": v.ref_allele, "alt": v.alt_allele} for v in variants]
        _, _, tstv = calculate_tstv_ratio(snp_list)
        run.tstv_ratio = tstv

        # 2. Update status analisis menjadi COMPLETED
        run.status = models.RunStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        db.commit()
        log_pipeline(db, run_id, 5, "INFO", f"Seluruh eksekusi pipeline selesai untuk {run_id}")

    except Exception as e:
        db.rollback()
        if run:
            run.status = models.RunStatus.FAILED
            db.commit()
        log_pipeline(db, run_id, 1, "ERROR", f"Pipeline terhenti akibat error: {str(e)}")
        print(f"Pipeline error on {run_id}: {str(e)}")
    finally:
        db.close()