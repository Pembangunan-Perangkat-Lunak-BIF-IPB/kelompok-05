import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query
from utils.pipeline import run_analysis_pipeline
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import case

import models
from database import SessionLocal, get_db
from schemas.analysis import VisibilityUpdateRequest
from security import get_current_user
from utils.validators import (
    validate_fasta_single_contig,
    validate_fastq_pairs,
    validate_iedb_coordinates,
)

router = APIRouter(prefix="/api/v1/analysis", tags=["Workbench Analysis"])
security = HTTPBearer()

@router.get("", dependencies=[Depends(security)])
def get_user_analyses(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
):
    """Lanjutan M7: Endpoint untuk mengambil seluruh daftar riwayat analisis milik pengguna."""
    runs = db.query(models.AnalysisRun).filter(models.AnalysisRun.user_id == current_user_id).all()
    return runs


@router.post("/upload", status_code=status.HTTP_201_CREATED, dependencies=[Depends(security)])
async def upload_analysis_files(
    sample_name: str = Form(...),
    file_fastq_r1: UploadFile = File(...),
    file_fastq_r2: UploadFile = File(...),
    file_fasta: UploadFile = File(...),
    file_iedb: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
):
    # Validasi Lapis 1 (Format Ekstensi)
    validations = [
        (file_fastq_r1.filename, ('.fastq', '.fq', '.fastq.gz', '.fq.gz'), "FASTQ R1"),
        (file_fastq_r2.filename, ('.fastq', '.fq', '.fastq.gz', '.fq.gz'), "FASTQ R2"),
        (file_fasta.filename, ('.fasta', '.fa', '.fna'), "FASTA Genom Acuan"),
        (file_iedb.filename, ('.csv', '.tsv', '.gff'), "Tabel Epitope IEDB")
    ]

    for fname, allowed_exts, label in validations:
        if not fname.lower().endswith(allowed_exts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format berkas {label} tidak valid ({fname}). Ekstensi yang diizinkan: {allowed_exts}"
            )

    short_code = uuid.uuid4().hex[:4].upper()
    run_id = f"VE-{short_code}"

    upload_dir = os.path.join("uploads", run_id)
    os.makedirs(upload_dir, exist_ok=True)

    # Kaitkan user_id milik pengguna yang sedang login
    analysis_run = models.AnalysisRun(
        run_id=run_id,
        sample_name=sample_name,
        user_id=current_user_id,
        status=models.RunStatus.PENDING,
        visibility=models.VisibilityType.PRIVATE
    )
    db.add(analysis_run)

    files_info = [
        (file_fastq_r1, models.FileType.FASTQ_R1),
        (file_fastq_r2, models.FileType.FASTQ_R2),
        (file_fasta, models.FileType.FASTA),
        (file_iedb, models.FileType.IEDB),
    ]

    saved_files_summary = []

    # 1. Simpan berkas fisik ke disk
    for upload_file, file_type in files_info:
        file_path = os.path.join(upload_dir, upload_file.filename)
        content = await upload_file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        db_file = models.UploadedFile(
            run_id=run_id,
            file_type=file_type,
            file_name=upload_file.filename,
            file_path=file_path,
            validation_status="PASS"
        )
        db.add(db_file)
        saved_files_summary.append({
            "file_type": file_type,
            "file_name": upload_file.filename,
            "validation_status": "PASS"
        })

    # 2. Jalankan Validasi Server Lapis 2 & Lapis 3
    path_r1 = os.path.join(upload_dir, file_fastq_r1.filename)
    path_r2 = os.path.join(upload_dir, file_fastq_r2.filename)
    path_fasta = os.path.join(upload_dir, file_fasta.filename)
    path_iedb = os.path.join(upload_dir, file_iedb.filename)

    # Validasi Lapis 2 (Header FASTA & FASTQ Pair)
    genome_len = validate_fasta_single_contig(path_fasta)
    validate_fastq_pairs(path_r1, path_r2)

    # Validasi Lapis 3 (Koordinat Epitope IEDB)
    validate_iedb_coordinates(path_iedb, genome_len)

    # Jika seluruh validasi lolos, simpan ke Database
    db.commit()

    return {
        "run_id": run_id,
        "sample_name": sample_name,
        "status": models.RunStatus.PENDING,
        "uploaded_files_summary": saved_files_summary
    }


@router.get("/{run_id}/status", dependencies=[Depends(security)])
def get_analysis_status(
    run_id: str, 
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
):
    run = db.query(models.AnalysisRun).filter(
        models.AnalysisRun.run_id == run_id,
        models.AnalysisRun.user_id == current_user_id
    ).first()

    if not run:
        raise HTTPException(status_code=404, detail="Sesi analisis tidak ditemukan")

    # 1. Ambil log pipeline dari database (jika model PipelineLog ada)
    pipeline_logs = []
    if hasattr(models, 'PipelineLog'):
        logs_db = db.query(models.PipelineLog).filter(
            models.PipelineLog.run_id == run_id
        ).order_by(models.PipelineLog.created_at.asc()).all()
        
        pipeline_logs = [
            {
                "station_number": log.station_number,
                "timestamp": log.created_at.strftime("%H:%M:%S") if hasattr(log, 'created_at') else "",
                "log_level": log.log_level,
                "message": log.message
            }
            for log in logs_db
        ]

    # 2. Tentukan status per stasiun (sekuensial atau berdasarkan log/status stasiun)
    stations_def = [
        (1, "Quality Control (fastp)"),
        (2, "Read Mapping (BWA-MEM2)"),
        (3, "Variant Calling (BCFtools)"),
        (4, "Quality Filtering"),
        (5, "Epitope Mapping & Grantham")
    ]

    # Tentukan status stasiun berdasarkan run.status
    stations_status_list = []
    for st_num, st_name in stations_def:
        if run.status == models.RunStatus.COMPLETED:
            st_status = "COMPLETED"
        elif run.status == models.RunStatus.FAILED:
            st_status = "FAILED"
        elif run.status == models.RunStatus.RUNNING:
            # Jika sedang berjalan, stasiun 1 COMPLETED/RUNNING, sisanya PENDING (atau sesuaikan dengan DB)
            st_status = "RUNNING" if st_num == 1 else "PENDING"
        else:
            st_status = "PENDING"

        stations_status_list.append({
            "station": st_num,
            "name": st_name,
            "status": st_status
        })

    return {
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "overall_status": run.status,
        "stations": stations_status_list,
        "pipeline_logs": pipeline_logs
    }


@router.get("/{run_id}/results", dependencies=[Depends(security)])
def get_analysis_results(
    run_id: str,
    risk_level: Optional[str] = Query(None, description="Filter berdasarkan risk level (HIGH, MODERATE, LOW, OUTSIDE_EPITOPE)"),
    snpeff_effect: Optional[str] = Query(None, description="Filter berdasarkan anotasi efek SnpEff"),
    min_pos: Optional[int] = Query(None, description="Posisi genom minimal"),
    max_pos: Optional[int] = Query(None, description="Posisi genom maksimal"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 1. Cek keberadaan sesi analisis (AnalysisRun)
    run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesi analisis tidak ditemukan."
        )

    # 2. Penegakan Keamanan: Hasil PRIVATE hanya bisa diakses oleh pemiliknya
    if run.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki hak akses untuk melihat hasil analisis PRIVATE ini."
        )

    # 3. Buat Base Query ke tabel VariantResult
    query = db.query(models.VariantResult).filter(models.VariantResult.run_id == run_id)

    # 4. Terapkan Filter Query jika dikirimkan oleh Frontend
    if risk_level:
        query = query.filter(models.VariantResult.risk_level == risk_level.upper())
    if snpeff_effect:
        query = query.filter(models.VariantResult.snpeff_effect.ilike(f"%{snpeff_effect}%"))
    if min_pos is not None:
        query = query.filter(models.VariantResult.position >= min_pos)
    if max_pos is not None:
        query = query.filter(models.VariantResult.position <= max_pos)

    # 5. Menerapkan Urutan Default (Default Sorting) sesuai Spesifikasi SA
    # Hirarki: HIGH (1) -> MODERATE (2) -> LOW (3) -> OUTSIDE_EPITOPE (4), lalu POS (asc)
    risk_hierarchy = case(
        {
            "HIGH": 1,
            "MODERATE": 2,
            "LOW": 3,
            "OUTSIDE_EPITOPE": 4
        },
        value=models.VariantResult.risk_level,
        else_=5
    )
    
    variants = query.order_by(risk_hierarchy, models.VariantResult.position.asc()).all()

    # 6. Kembalikan Kartu Ringkasan Metrik Run + Daftar Varian VCF
    return {
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "status": run.status,
        "visibility": run.visibility,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        # Ganti bagian summary_metrics dengan versi aman ini:
        "summary_metrics": {
            "q20_rate": getattr(run, "q20_rate", None),
            "q30_rate": getattr(run, "q30_rate", None),
            "mapping_rate": getattr(run, "mapping_rate", None),
            "mean_depth": getattr(run, "mean_depth", None),
            "tstv_ratio": getattr(run, "tstv_ratio", None),
            "total_variants": len(variants)
        },
        "variants": variants
    }


@router.patch("/{run_id}/visibility", dependencies=[Depends(security)])
def update_analysis_visibility(run_id: str, req: VisibilityUpdateRequest, db: Session = Depends(get_db)):
    run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesi analisis dengan run_id '{run_id}' tidak ditemukan"
        )

    if req.visibility not in ["PUBLIC", "PRIVATE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nilai visibility harus 'PUBLIC' atau 'PRIVATE'"
        )

    run.visibility = req.visibility
    db.commit()

    return {
        "run_id": run.run_id,
        "visibility": run.visibility,
        "message": f"Visibilitas analisis berhasil diubah menjadi {run.visibility}"
    }


@router.post("/{run_id}/run", dependencies=[Depends(security)])
def trigger_analysis_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
):
    """Memicu eksekusi pipeline 5 stasiun di latar belakang."""
    run = db.query(models.AnalysisRun).filter(
        models.AnalysisRun.run_id == run_id,
        models.AnalysisRun.user_id == current_user_id
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesi analisis dengan run_id '{run_id}' tidak ditemukan"
        )

    if run.status != models.RunStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analisis tidak dapat dijalankan karena status saat ini adalah '{run.status}'"
        )

    # Jalankan pipeline di latar belakang
    background_tasks.add_task(run_analysis_pipeline, run_id)

    return {
        "run_id": run_id,
        "status": models.RunStatus.RUNNING,
        "message": "Pipeline analisis berhasil dipicu di latar belakang"
    }

@router.get("", dependencies=[Depends(security)])
def get_user_analysis_history(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
):
    """Mengambil seluruh riwayat analisis milik user terautentikasi."""
    runs = db.query(models.AnalysisRun).filter(
        models.AnalysisRun.user_id == current_user_id
    ).order_by(models.AnalysisRun.created_at.desc()).all()

    return [
        {
            "run_id": run.run_id,
            "sample_name": run.sample_name,
            "status": run.status,
            "visibility": run.visibility,
            "created_at": run.created_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at
        }
        for run in runs
    ]