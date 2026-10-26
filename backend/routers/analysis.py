import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from utils.pipeline import run_analysis_pipeline
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

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

    # Tentukan status stasiun berdasarkan run.status
    station_status = "COMPLETED" if run.status == models.RunStatus.COMPLETED else (
        "RUNNING" if run.status == models.RunStatus.RUNNING else "PENDING"
    )

    return {
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "overall_status": run.status,
        "stations": [
            {"station": 1, "name": "Quality Control (fastp)", "status": station_status},
            {"station": 2, "name": "Read Mapping (BWA-MEM2)", "status": station_status},
            {"station": 3, "name": "Variant Calling (BCFtools)", "status": station_status},
            {"station": 4, "name": "Quality Filtering", "status": station_status},
            {"station": 5, "name": "Epitope Mapping & Grantham", "status": station_status}
        ]
    }


@router.get("/{run_id}/results", dependencies=[Depends(security)])
def get_analysis_results(run_id: str, db: Session = Depends(get_db)):
    run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesi analisis dengan run_id '{run_id}' tidak ditemukan"
        )

    results = db.query(models.VariantResult).filter(models.VariantResult.run_id == run_id).all()

    return {
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "visibility": run.visibility,
        "total_variants": len(results),
        "variant_results": results
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