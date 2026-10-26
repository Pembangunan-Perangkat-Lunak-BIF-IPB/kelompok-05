import os
import subprocess
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from utils.vcf_parser import parse_and_store_vcf

REF_GENOME = "data/references/reference.fasta" 
BASE_UPLOAD_DIR = "uploads"

def execute_cmd(command: str):
    """Menjalankan perintah CLI bioinformatika Linux secara native di WSL"""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Command failed: {command}\nError output: {result.stderr}")
    return result.stdout

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

        # Cari file FASTQ R1 & R2 dari tabel uploaded_files
        file_r1 = db.query(models.UploadedFile).filter(
            models.UploadedFile.run_id == run_id,
            models.UploadedFile.file_type == models.FileType.FASTQ_R1
        ).first()

        file_r2 = db.query(models.UploadedFile).filter(
            models.UploadedFile.run_id == run_id,
            models.UploadedFile.file_type == models.FileType.FASTQ_R2
        ).first()

        if not file_r1:
            raise Exception(f"File FASTQ R1 tidak ditemukan untuk run_id: {run_id}")

        r1_path = file_r1.file_path
        r2_path = file_r2.file_path if file_r2 else None

        clean_r1 = os.path.join(run_folder, "clean_R1.fq")
        clean_r2 = os.path.join(run_folder, "clean_R2.fq") if r2_path else None
        aligned_bam = os.path.join(run_folder, "aligned.bam")
        output_vcf = os.path.join(run_folder, "variants.vcf")

        # --- STASIUN 1: QC & Preprocessing (fastp) ---
        if r2_path and os.path.exists(r2_path):
            # Paired-End Mode (-i dan -I)
            cmd_fastp = f"fastp -i {r1_path} -I {r2_path} -o {clean_r1} -O {clean_r2} -h {run_folder}/fastp.html -j {run_folder}/fastp.json"
        else:
            # Single-End Mode (-i saja)
            cmd_fastp = f"fastp -i {r1_path} -o {clean_r1} -h {run_folder}/fastp.html -j {run_folder}/fastp.json"
        
        execute_cmd(cmd_fastp)

        # --- STASIUN 2: Read Alignment (bwa-mem2 & samtools) ---
        if r2_path and os.path.exists(r2_path):
            cmd_align = f"bwa-mem2 mem -t 4 {REF_GENOME} {clean_r1} {clean_r2} | samtools sort -o {aligned_bam}"
        else:
            cmd_align = f"bwa-mem2 mem -t 4 {REF_GENOME} {clean_r1} | samtools sort -o {aligned_bam}"
        
        execute_cmd(cmd_align)
        execute_cmd(f"samtools index {aligned_bam}")

        # --- STASIUN 3: Variant Calling (bcftools) ---
        cmd_bcftools = f"bcftools mpileup -f {REF_GENOME} {aligned_bam} | bcftools call -mv -Ov -o {output_vcf}"
        execute_cmd(cmd_bcftools)

        # --- PARSE & SIMPAN HASIL VCF KE POSTGRESQL ---
        parse_and_store_vcf(output_vcf, run.run_id, db)

        # 2. Update status analisis menjadi COMPLETED
        run.status = models.RunStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        db.commit()
        print(f"Pipeline berhasil diselesaikan untuk {run_id}")

    except Exception as e:
        db.rollback()
        if run:
            run.status = models.RunStatus.FAILED
            db.commit()
        print(f"Pipeline error on {run_id}: {str(e)}")
    finally:
        db.close()