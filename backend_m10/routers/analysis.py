import os
import shutil
import uuid
import csv
import io
import json
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
from config import UPLOAD_DIR, PIPELINE_THREADS, SNPEFF_DB
from database import get_db
from schemas.analysis import VisibilityUpdateRequest
from security import require_researcher
from utils.pipeline import run_analysis_pipeline
from utils.serializers import (
    build_results_response,
    build_station_status,
    enum_value,
    query_variants,
    safe_assessment_values,
    serialize_logs,
    serialize_run,
)
from utils.validators import (
    validate_fasta_single_contig,
    validate_fastq_pairs,
    validate_iedb_coordinates,
)

router = APIRouter(prefix="/api/v1/analysis", tags=["Workbench Analysis"])

# Ekstensi berlapis (.fastq.gz) dicek lebih dulu
FASTQ_EXTS = (".fastq.gz", ".fq.gz", ".fastq", ".fq")
FASTA_EXTS = (".fasta", ".fa", ".fna")
IEDB_EXTS = (".csv", ".tsv", ".gff", ".gff3")


def _match_ext(filename: Optional[str], allowed: tuple, label: str) -> str:
    """Validasi Lapis 1: mengembalikan ekstensi yang cocok atau melempar 400."""
    name = (filename or "").lower()
    for ext in allowed:
        if name.endswith(ext):
            return ext
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Format berkas {label} tidak valid ({filename}). Ekstensi yang diizinkan: {', '.join(allowed)}",
    )


def _new_run_id(db: Session) -> str:
    for _ in range(20):
        run_id = f"VE-{uuid.uuid4().hex[:12].upper()}"
        if not db.query(models.AnalysisRun.run_id).filter(models.AnalysisRun.run_id == run_id).first():
            return run_id
    raise HTTPException(status_code=500, detail="Gagal membuat run_id unik, silakan coba lagi.")


def _get_owned_run(db: Session, run_id: str, user_id: int) -> models.AnalysisRun:
    run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sesi analisis '{run_id}' tidak ditemukan")
    if run.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Anda bukan pemilik sesi analisis ini")
    return run


@router.get("")
def get_user_analysis_history(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    """Mengambil seluruh riwayat analisis milik user terautentikasi (terbaru di atas)."""
    runs = (
        db.query(models.AnalysisRun)
        .filter(models.AnalysisRun.user_id == current_user_id)
        .order_by(models.AnalysisRun.created_at.desc())
        .all()
    )
    return [serialize_run(run) for run in runs]


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_analysis_files(
    sample_name: str = Form(...),
    file_fastq_r1: UploadFile = File(...),
    file_fastq_r2: UploadFile = File(...),
    file_fasta: UploadFile = File(...),
    file_iedb: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    sample_name = sample_name.strip()
    if not sample_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nama sampel tidak boleh kosong")

    # (berkas, tipe, ekstensi_diizinkan, label, nama_simpan)
    specs = [
        (file_fastq_r1, models.FileType.FASTQ_R1, FASTQ_EXTS, "FASTQ R1", "reads_R1"),
        (file_fastq_r2, models.FileType.FASTQ_R2, FASTQ_EXTS, "FASTQ R2", "reads_R2"),
        (file_fasta, models.FileType.FASTA, FASTA_EXTS, "FASTA Genom Acuan", "reference"),
        (file_iedb, models.FileType.IEDB, IEDB_EXTS, "Tabel Epitope IEDB", "epitopes"),
    ]

    # Validasi Lapis 1 (ekstensi) sebelum menulis apa pun ke disk
    exts = [_match_ext(uf.filename, allowed, label) for uf, _, allowed, label, _ in specs]

    run_id = _new_run_id(db)
    upload_dir = UPLOAD_DIR / run_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved = []  # (nama_asli, tipe, path_di_disk)
    try:
        # Simpan berkas dengan nama tetap (aman dari path traversal & spasi), streaming per 1 MB
        for (uf, ftype, _, label, stem), ext in zip(specs, exts):
            path = upload_dir / f"{stem}{ext}"
            with open(path, "wb") as out:
                shutil.copyfileobj(uf.file, out, 1024 * 1024)
            if path.stat().st_size == 0:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Berkas {label} kosong.")
            saved.append((os.path.basename(uf.filename or f"{stem}{ext}"), ftype, str(path)))

        # Validasi Lapis 2 (FASTA & pasangan FASTQ) dan Lapis 3 (koordinat IEDB)
        genome_len = validate_fasta_single_contig(saved[2][2])
        validate_fastq_pairs(saved[0][2], saved[1][2])
        validate_iedb_coordinates(saved[3][2], genome_len)
    except Exception:
        # Validasi gagal: hapus berkas supaya tidak menumpuk di disk
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise

    # Konsistensi data: hapus upload jika penyimpanan ke DB gagal.
    try:
        db.add(models.AnalysisRun(
            run_id=run_id,
            sample_name=sample_name,
            user_id=current_user_id,
            status=models.RunStatus.PENDING,
            visibility=models.VisibilityType.PRIVATE,
        ))
        for original_name, ftype, path in saved:
            db.add(models.UploadedFile(
                run_id=run_id,
                file_type=ftype,
                file_name=original_name[:255],
                file_path=path,
                validation_status="PASS",
            ))
        db.commit()
    except Exception:
        db.rollback()
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise

    return {
        "run_id": run_id,
        "sample_name": sample_name,
        "status": models.RunStatus.PENDING.value,
        "uploaded_files_summary": [
            {"file_type": ftype.value, "file_name": name, "validation_status": "PASS"}
            for name, ftype, _ in saved
        ],
    }


@router.post("/{run_id}/run")
def trigger_analysis_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    """Memicu eksekusi pipeline 5 stasiun di latar belakang."""
    run = _get_owned_run(db, run_id, current_user_id)

    if run.status != models.RunStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analisis tidak dapat dijalankan karena status saat ini adalah '{enum_value(run.status)}'",
        )

    # Set RUNNING sekarang agar FE langsung melihat status benar dan run tidak bisa dipicu dua kali
    run.status = models.RunStatus.RUNNING
    run.started_at = datetime.now(timezone.utc)
    db.commit()

    background_tasks.add_task(run_analysis_pipeline, run_id)

    return {
        "run_id": run_id,
        "status": models.RunStatus.RUNNING.value,
        "message": "Pipeline analisis berhasil dipicu di latar belakang",
    }


@router.get("/{run_id}/status")
def get_analysis_status(
    run_id: str,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    run = _get_owned_run(db, run_id, current_user_id)
    logs = (
        db.query(models.PipelineLog)
        .filter(models.PipelineLog.run_id == run_id)
        .order_by(models.PipelineLog.id.asc())
        .all()
    )
    return {
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "overall_status": enum_value(run.status),
        "created_at": run.created_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "stations": build_station_status(run, logs),
        "pipeline_logs": serialize_logs(logs),
    }


@router.get("/{run_id}/results")
def get_analysis_results(
    run_id: str,
    risk_level: Optional[str] = Query(None, description="Filter risk level (HIGH, MODERATE, LOW, OUTSIDE_EPITOPE)"),
    snpeff_effect: Optional[str] = Query(None, description="Filter kata kunci anotasi efek SnpEff"),
    min_pos: Optional[int] = Query(None, description="Posisi genom minimal"),
    max_pos: Optional[int] = Query(None, description="Posisi genom maksimal"),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi analisis tidak ditemukan.")

    # Hasil PRIVATE hanya untuk pemiliknya; hasil PUBLIC boleh dilihat user login mana pun
    if run.visibility == models.VisibilityType.PRIVATE and run.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki hak akses untuk melihat hasil analisis PRIVATE ini.",
        )

    
    # Varian yang ditampilkan sesuai filter pengguna
    variants = query_variants(
        db, run_id, risk_level, snpeff_effect, min_pos, max_pos
    )

    # Gunakan seluruh varian untuk penjelasan metrik Ts/Tv
    metric_variants = None

    if run.tstv_ratio is None:
        metric_variants = (
            db.query(models.VariantResult)
            .filter(models.VariantResult.run_id == run_id)
            .all()
        )

    return build_results_response(
        run,
        variants,
        tstv_variants=metric_variants
    )


# Ekspor laporan administratif dan hasil yang SUDAH disimpan: tidak menjalankan
# ulang/meningkatkan pipeline atau mengubah perhitungan biologis.

EXPORT_COLUMNS = (
    "id",
    "position",
    "ref_allele",
    "alt_allele",
    "qual",
    "dp",
    "snpeff_effect",
    "grantham_score",
    "risk_level",
    "annotation_status",
    "assessment_status",
)


def _spreadsheet_safe(value):
    """Mencegah formula injection pada file CSV/TSV yang dibuka di spreadsheet."""
    if value is None:
        return ""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def _export_name(run_id: str, extension: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", run_id)
    return f"{safe_id}.{extension}"


def _text_download(body: str, run_id: str, extension: str, media_type: str) -> Response:
    return Response(
        content=body.encode("utf-8-sig") if extension in {"csv", "tsv"} else body.encode("utf-8"),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{_export_name(run_id, extension)}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


def _require_complete(run: models.AnalysisRun):
    if run.status != models.RunStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data hasil belum final; ekspor hasil hanya tersedia untuk run COMPLETED.",
        )


def _has_annotation_header(path) -> bool:
    """Syarat minimum: header ANN, dan ada nilai ANN jika ada baris varian."""
    try:
        has_header = False
        seen_variants = False
        seen_ann = False
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if line.startswith("##INFO=<ID=ANN,"):
                    has_header = True
                elif not line.startswith("#") and line.strip():
                    seen_variants = True
                    columns = line.rstrip("\n").split("\t")
                    if len(columns) > 7 and any(item.startswith("ANN=") for item in columns[7].split(";")):
                        seen_ann = True
        return has_header and (not seen_variants or seen_ann)
    except OSError:
        return False


@router.get("/{run_id}/export/{format}")
def export_run_data(
    run_id: str,
    format: str,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    """Ekspor hanya untuk pemilik analisis; menjaga hasil PRIVATE/akun lain."""
    run = _get_owned_run(db, run_id, current_user_id)
    kind = format.lower()

    if kind in {"csv", "tsv"}:
        _require_complete(run)
        delimiter = "," if kind == "csv" else "\t"
        output = io.StringIO(newline="")
        writer = csv.writer(output, delimiter=delimiter, lineterminator="\r\n")
        writer.writerow(EXPORT_COLUMNS)
        # Data yang sudah ada saja; NULL tetap kosong (bukan diubah menjadi 0).
        variants = (db.query(models.VariantResult)
                    .filter(models.VariantResult.run_id == run_id)
                    .order_by(models.VariantResult.position.asc()).all())
        
        for var in variants:
            safe_values = safe_assessment_values(var)

            row = []

            for field in EXPORT_COLUMNS:
                if field in safe_values:
                    value = safe_values[field]
                else:
                    value = getattr(var, field, None)

                row.append(_spreadsheet_safe(value))

            writer.writerow(row)

        content_type = "text/csv" if kind == "csv" else "text/tab-separated-values"
        return _text_download(output.getvalue(), run_id, kind, content_type)

    if kind == "logs":
        logs = (db.query(models.PipelineLog)
                .filter(models.PipelineLog.run_id == run_id)
                .order_by(models.PipelineLog.id.asc()).all())
        lines = [f"Run ID: {run.run_id}", f"Status: {enum_value(run.status)}", ""]
        for log in logs:
            timestamp = log.created_at.isoformat() if log.created_at else "(tanpa waktu)"
            message = str(log.message).replace("\r", " ").replace("\n", " ")
            lines.append(f"[{timestamp}] Stasiun {log.station_number} [{log.log_level}] {message}")
        return _text_download("\n".join(lines) + "\n", run_id, "log.txt", "text/plain")

    if kind == "config":
        # Tidak mengembalikan .env atau kredensial. Konfigurasi server SAAT INI,
        # bukan snapshot konfigurasi historis saat sebuah run dijalankan.
        payload = {
            "run_id": run.run_id,
            "sample_name": run.sample_name,
            "status": enum_value(run.status),
            "visibility": enum_value(run.visibility),
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "configuration_scope": "current_backend_settings_not_historical_run_snapshot",
            "pipeline_threads_current": PIPELINE_THREADS,
            "annotation_database_name_current": SNPEFF_DB,
        }
        return _text_download(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", run_id, "config.json", "application/json")

    if kind == "vcf":
        _require_complete(run)
        run_dir = (UPLOAD_DIR / run_id).resolve()
        path = run_dir / "variants.ann.vcf"
        # Hanya nama file tetap yang dihasilkan backend, bukan path dari input API/DB.
        if not run_dir.is_relative_to(UPLOAD_DIR.resolve()) or path.is_symlink() or not path.is_file():
            raise HTTPException(status_code=404, detail="Annotated VCF belum tersedia untuk run ini.")
        if not _has_annotation_header(path):
            raise HTTPException(status_code=409, detail="VCF tidak memiliki header ANN; anotasi belum terkonfirmasi.")
        return FileResponse(
            str(path), media_type="text/plain", filename=_export_name(run_id, "ann.vcf"),
            headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
        )

    raise HTTPException(status_code=400, detail="Format ekspor harus csv, tsv, vcf, logs, atau config.")


@router.patch("/{run_id}/visibility")
def update_analysis_visibility(
    run_id: str,
    req: VisibilityUpdateRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    run = _get_owned_run(db, run_id, current_user_id)

    new_visibility = str(enum_value(req.visibility)).upper()
    if new_visibility not in (models.VisibilityType.PUBLIC.value, models.VisibilityType.PRIVATE.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nilai visibility harus 'PUBLIC' atau 'PRIVATE'")

    run.visibility = models.VisibilityType(new_visibility)
    db.commit()

    return {
        "run_id": run.run_id,
        "visibility": new_visibility,
        "message": f"Visibilitas analisis berhasil diubah menjadi {new_visibility}",
    }
