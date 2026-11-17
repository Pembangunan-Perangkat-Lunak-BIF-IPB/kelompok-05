import tempfile
import os
import shutil
import uuid
import csv
import io
import json
import re
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import update

import models
from config import UPLOAD_DIR, PIPELINE_THREADS, SNPEFF_DB
from database import get_db
from schemas.analysis import VisibilityUpdateRequest, RunConfiguration, ExecutionParameters
from security import require_researcher
from utils.pipeline import run_analysis_pipeline, cancellation_path
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
)
from utils.result_interpretation import build_station_interpretations
from utils.report_generator import generate_variant_report


router = APIRouter(prefix="/api/v1/analysis", tags=["Workbench Analysis"])

# Ekstensi berlapis (.fastq.gz) dicek lebih dulu
FASTQ_EXTS = (".fastq.gz", ".fq.gz", ".fastq", ".fq")
FASTA_EXTS = (".fasta", ".fa", ".fna")
SYSTEM_REFERENCE = (
    Path(__file__).resolve().parents[1]
    / "reference"
    / "NC_045512.2.fasta"
)
MAX_UPLOAD_BYTES = {models.FileType.FASTQ_R1: 1024**3, models.FileType.FASTQ_R2: 1024**3, models.FileType.FASTA: 50 * 1024**2}


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


@router.post("/validate-headers")
def validate_fastq_headers(
    file_fastq_r1: UploadFile = File(...),
    file_fastq_r2: UploadFile = File(...),
    current_user_id: int = Depends(require_researcher),
):
    """
    Pemeriksaan FASTQ sebelum pengaturan parameter.

    - Wajib dua berkas paired-end.
    - Tidak membuat AnalysisRun atau UploadedFile.
    - Berkas sementara dihapus setelah pemeriksaan.
    - Upload final tetap wajib memvalidasi ulang.
    """
    uploads = [
        (
            file_fastq_r1,
            models.FileType.FASTQ_R1,
            "FASTQ R1",
            "reads_R1",
        ),
        (
            file_fastq_r2,
            models.FileType.FASTQ_R2,
            "FASTQ R2",
            "reads_R2",
        ),
    ]

    extensions = [
        _match_ext(upload.filename, FASTQ_EXTS, label)
        for upload, _, label, _ in uploads
    ]

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Direktori ini terpisah dari direktori run yang permanen.
    with tempfile.TemporaryDirectory(
        prefix=".fastq-validation-",
        dir=str(UPLOAD_DIR),
    ) as temp_dir:
        stored_paths = []

        for (upload, file_type, label, stem), ext in zip(
            uploads, extensions
        ):
            path = Path(temp_dir) / f"{stem}{ext}"
            received = 0

            with path.open("wb") as output:
                while True:
                    chunk = upload.file.read(1024 * 1024)
                    if not chunk:
                        break

                    received += len(chunk)

                    if received > MAX_UPLOAD_BYTES[file_type]:
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                f"Berkas {label} melebihi "
                                "batas 1 GB."
                            ),
                        )

                    output.write(chunk)

            if received == 0:
                raise HTTPException(
                    status_code=422,
                    detail=f"Berkas {label} kosong.",
                )

            stored_paths.append(str(path))

        # Validator yang sudah ada:
        # header, identifier pasangan, struktur record, dan quality.
        result = validate_fastq_pairs(
            stored_paths[0],
            stored_paths[1],
        )

    # TemporaryDirectory sudah dibersihkan sebelum respons.
    return {
        "status": "PASS",
        "format": result["format"],
        "header": result["header"],
        "sequence_integrity": result["sequence_integrity"],
        "read_count": result["read_count"],
        "paired_end": result["paired_end"],
        "message": (
            "Header dan pasangan FASTQ valid. "
            "Berkas siap digunakan untuk analisis."
        ),
    }

@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_analysis_files(
    sample_name: str = Form(...),
    file_fastq_r1: UploadFile = File(...),
    file_fastq_r2: UploadFile = File(...),
    execution_mode: str = Form("default", description="default atau custom"),
    min_dp: Optional[int] = Form(None),
    min_mq: Optional[int] = Form(None),
    min_base_quality: Optional[int] = Form(None),
    max_depth: Optional[int] = Form(None),
    min_qual: Optional[float] = Form(None),
    min_af: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    try:
        mode = execution_mode.strip().lower()
        custom_fields = {
            "min_dp": min_dp,
            "min_mq": min_mq,
            "min_base_quality": min_base_quality,
            "max_depth": max_depth,
            "min_qual": min_qual,
            "min_af": min_af
        }
        if mode == "custom" and any(v is None for v in custom_fields.values()):
            raise ValueError(
                "Mode custom membutuhkan keenam parameter: "
                "min_dp, min_mq, min_base_quality, max_depth, min_qual, dan min_af."
            )
        settings = RunConfiguration(
            execution_mode=mode,
            parameters=ExecutionParameters(**custom_fields) if mode == "custom" else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Parameter analisis tidak valid: {exc}") from exc
    effective = settings.parameters or ExecutionParameters()
    sample_name = sample_name.strip()
    if not sample_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nama sampel tidak boleh kosong")

    # (berkas, tipe, ekstensi_diizinkan, label, nama_simpan)
    specs = [
        (file_fastq_r1, models.FileType.FASTQ_R1, FASTQ_EXTS, "FASTQ R1", "reads_R1"),
        ( file_fastq_r2,
        models.FileType.FASTQ_R2,
        FASTQ_EXTS,
        "FASTQ R2",
        "reads_R2",
        ),
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
            total_bytes = 0
            with open(path, "wb") as out:
                while chunk := uf.file.read(1024 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > MAX_UPLOAD_BYTES[ftype]:
                        raise HTTPException(status_code=413, detail=f"Berkas {label} melebihi batas ukuran")
                    out.write(chunk)
            if path.stat().st_size == 0:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Berkas {label} kosong.")
            saved.append((os.path.basename(uf.filename or f"{stem}{ext}"), ftype, str(path)))

        # Validasi isi FASTA dan pasangan FASTQ
        # Validasi genom referensi sistem
        if not SYSTEM_REFERENCE.is_file():
            raise HTTPException(
                status_code=500,
                detail="Reference genome sistem NC_045512.2 tidak ditemukan."
            )

        genome_len = validate_fasta_single_contig(str(SYSTEM_REFERENCE))

        if genome_len != 29903:
            raise HTTPException(
                status_code=500,
                detail="Panjang reference genome sistem tidak sesuai."
            )

        # Validasi FASTQ paired-end jika R2 tersedia
        fastq_validation = validate_fastq_pairs(
            saved[0][2],
            saved[1][2] if file_fastq_r2 is not None else None
        )
        # Catat referensi sistem pada run agar pipeline tetap kompatibel
        saved.append((
            "NC_045512.2.fasta",
            models.FileType.FASTA,
            str(SYSTEM_REFERENCE)
        ))
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
            execution_mode=models.ExecutionMode(mode),
            min_dp=effective.min_dp, min_mq=effective.min_mq,min_base_quality=effective.min_base_quality,
            max_depth=effective.max_depth,min_qual=effective.min_qual, min_af=effective.min_af,
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
        "execution_mode": mode,
        "parameters": effective.model_dump(),
        "uploaded_files_summary": [
            {"file_type": ftype.value, "file_name": name, "validation_status": "PASS"}
            for name, ftype, _ in saved
        ],
        "validation_results": {
            ftype.value: {
                "format": fastq_validation["format"],
                "header": fastq_validation["header"],
                "sequence_integrity": fastq_validation["sequence_integrity"],
                "read_count": fastq_validation["read_count"],
            }
            for _, ftype, _ in saved
            if ftype in (
                models.FileType.FASTQ_R1,
                models.FileType.FASTQ_R2,
            )
        },
    }


@router.post("/{run_id}/run")
def trigger_analysis_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    """Memicu eksekusi pipeline 4 stasiun di latar belakang."""
    run = _get_owned_run(db, run_id, current_user_id)

    if run.status != models.RunStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analisis tidak dapat dijalankan karena status saat ini adalah '{enum_value(run.status)}'",
        )

    # Atomic transition PENDING -> RUNNING protects against double-click and concurrent requests.
    changed = db.execute(
        update(models.AnalysisRun)
        .where(models.AnalysisRun.run_id == run_id,
               models.AnalysisRun.user_id == current_user_id,
               models.AnalysisRun.status == models.RunStatus.PENDING)
        .values(status=models.RunStatus.RUNNING, started_at=datetime.now(timezone.utc))
    )
    db.commit()
    if changed.rowcount != 1:
        raise HTTPException(status_code=409, detail="Run sudah dipicu atau tidak lagi PENDING.")

    background_tasks.add_task(run_analysis_pipeline, run_id)

    return {
        "run_id": run_id,
        "status": models.RunStatus.RUNNING.value,
        "message": "Pipeline analisis berhasil dipicu di latar belakang",
    }


@router.post("/{run_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
def request_analysis_cancel(
    run_id: str,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    """Minta pembatalan kooperatif; acknowledge tidak sama dengan CANCELLED."""
    run = _get_owned_run(db, run_id, current_user_id)
    if run.status != models.RunStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail=f"Tidak dapat membatalkan run berstatus {enum_value(run.status)}."
        )
    # Path dan status sudah diverifikasi; penanda persisten aman lintas worker.
    marker = cancellation_path(run_id)
    marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        with marker.open("x", encoding="utf-8") as stream:
            stream.write("requested\\n")
    except FileExistsError:
        pass
    return {
        "run_id": run_id,
        "status": "CANCELLATION_REQUESTED",
        "message": "Permintaan diterima. Tunggu /status sampai status CANCELLED; proses masih mungkin berjalan."
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
    
    station_rows = build_station_status(run, logs)

    coverage_metrics = {}

    coverage_path = UPLOAD_DIR / run_id / "coverage_metrics.json"

    if coverage_path.is_file():
        try:
            with coverage_path.open("r", encoding="utf-8") as f:
                coverage_metrics = json.load(f)
        except (OSError, ValueError):
            coverage_metrics = {}

    # Metrik tersedia bahkan jika status keseluruhan FAILED/CANCELLED.
    summary_metrics = {
        "q20_before": run.q20_before,
        "q30_before": run.q30_before,
        "q20_rate": run.q20_rate,
        "q30_rate": run.q30_rate,
        "reads_before": run.reads_before,
        "reads_after": run.reads_after,
        "passed_reads_pct": run.passed_reads_pct,
        "adapter_trimmed_pct": run.adapter_trimmed_pct,
        "mapping_rate": run.mapping_rate,
        "mean_depth": run.mean_depth,
        "unmapped_reads": run.unmapped_reads,

        "genome_coverage_pct": coverage_metrics.get(
            "genome_coverage_pct"
        ),
        "genome_coverage_30x_pct": coverage_metrics.get(
            "genome_coverage_30x_pct"
        ),
        "raw_variant_count": run.raw_variant_count,
        "raw_snp_count": run.raw_snp_count,
        "raw_indel_count": run.raw_indel_count,
        "tstv_ratio": run.tstv_ratio,
        "passed_variant_count": run.passed_variant_count,
        "filtered_variant_count": run.filtered_variant_count,
        "annotated_variant_count": run.annotated_variant_count,
        "annotation_status": enum_value(run.annotation_status),
    }
    return {
        "summary_metrics": summary_metrics,
        "cancellation_requested": cancellation_path(run_id).exists(),
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "overall_status": enum_value(run.status),
        "created_at": run.created_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "stations": station_rows,
        "station_interpretations": build_station_interpretations(
            run, station_rows
        ),
        "pipeline_logs": serialize_logs(logs),
    }


@router.get("/{run_id}/filter-audit")
def get_filter_audit(
    run_id: str,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    """
    Mengambil hasil audit Quality Filtering Stasiun 4.

    - Menampilkan jumlah kandidat PASS dan FILTERED.
    - Mengembalikan alasan penolakan varian terfilter.
    - Tidak mengubah data hasil analisis.
    """

    # Pastikan pengguna merupakan pemilik run
    run = _get_owned_run(db, run_id, current_user_id)

    query = db.query(models.VariantFilterResult).filter(
        models.VariantFilterResult.run_id == run_id
    )

    total_candidates = query.count()

    # Bedakan data audit yang belum tersedia dari hasil 0 varian
    if total_candidates == 0:
        if (run.raw_variant_count or 0) > 0:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Data audit filtering belum tersedia "
                    "untuk run ini."
                ),
            )

        return {
            "run_id": run_id,
            "audit_available": False,
            "total_candidates": 0,
            "passed": 0,
            "filtered": 0,
            "filtered_variants": [],
        }

    passed = query.filter(
        models.VariantFilterResult.filter_status == "PASS"
    ).count()

    filtered_rows = (
        query.filter(
            models.VariantFilterResult.filter_status == "FILTERED"
        )
        .order_by(models.VariantFilterResult.position.asc())
        .all()
    )

    filtered_variants = [
        {
            "position": item.position,
            "ref": item.ref_allele,
            "alt": item.alt_allele,
            "chrom": item.chrom,
            "dp": item.dp,
            "qual": item.qual,
            "af": item.af,
            "filter_status": item.filter_status,
            "filter_reason": item.filter_reason,
        }
        for item in filtered_rows
    ]

    return {
        "run_id": run_id,
        "audit_available": True,
        "total_candidates": total_candidates,
        "passed": passed,
        "filtered": len(filtered_variants),
        "filtered_variants": filtered_variants,
    }

@router.get("/{run_id}/results")
def get_analysis_results(
    run_id: str,
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
        db, run_id, None, snpeff_effect, min_pos, max_pos
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
    "gene_name", "impact", "hgvs_c", "hgvs_p", "filter_status",
    "flank_left", "flank_right", "annotation_status",
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


def _require_terminal_with_artifact(run: models.AnalysisRun, run_id: str):
    # Pada RUNNING jangan zip file yang sedang ditulis oleh tool.
    if run.status not in (models.RunStatus.COMPLETED, models.RunStatus.FAILED, models.RunStatus.CANCELLED):
        raise HTTPException(status_code=409, detail="Tunggu sampai run selesai atau berhenti.")
    directory = (UPLOAD_DIR / run_id).resolve()
    if not directory.is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Run tidak valid")
    if not any((directory / x).is_file() for x in ("fastp.html", "fastp.json", "variants.vcf", "aligned.bam")):
        raise HTTPException(status_code=404, detail="Belum ada hasil stasiun tersedia untuk laporan.")


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

    if kind == "pdf":
        _require_terminal_with_artifact(run, run_id)
        variants = (db.query(models.VariantResult)
                    .filter(models.VariantResult.run_id == run_id)
                    .order_by(models.VariantResult.position.asc()).all())
        
        filter_audit = (
            db.query(models.VariantFilterResult)
            .filter(
                models.VariantFilterResult.run_id == run_id
            )
            .order_by(
                models.VariantFilterResult.position.asc(),
                models.VariantFilterResult.id.asc()
            )
            .all()
        )
        logs = (db.query(models.PipelineLog)
                .filter(models.PipelineLog.run_id == run_id)
                .order_by(models.PipelineLog.id.asc()).all())
        station_rows = build_station_status(run, logs)
        report = generate_variant_report(
            run, variants, UPLOAD_DIR / run_id,
            build_station_interpretations(run, station_rows),
            filter_audit=filter_audit,
        )
        return Response(
            report,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{_export_name(run_id, "pdf")}"',
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

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
            "execution_mode": enum_value(run.execution_mode),
            "parameters": {"min_dp": run.min_dp, "min_mq": run.min_mq, "min_base_quality": run.min_base_quality, "max_depth": run.max_depth, "min_qual": run.min_qual, "min_af": run.min_af},
        }
        return _text_download(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", run_id, "config.json", "application/json")

    if kind == "zip":
        _require_terminal_with_artifact(run, run_id)
        run_dir = (UPLOAD_DIR / run_id).resolve()
        if not run_dir.is_relative_to(UPLOAD_DIR.resolve()):
            raise HTTPException(status_code=400, detail="Run directory tidak valid")
        finished = _completed_stations(db, run_id)
        available = []
        for artifact_id, (station, name, _, _) in ARTIFACTS.items():
            if station not in finished:
                continue
            if artifact_id == "annotated_vcf" and enum_value(run.annotation_status) != "COMPLETED":
                continue
            candidate = run_dir / name
            if candidate.is_file() and not candidate.is_symlink():
                available.append(candidate)
        if not available:
            raise HTTPException(status_code=404, detail="Belum ada artefak pipeline untuk diunduh")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in available:
                archive.write(path, arcname=path.name)
            variants = (db.query(models.VariantResult)
                        .filter(models.VariantResult.run_id == run_id)
                        .order_by(models.VariantResult.position.asc()).all())
            filter_audit = (
                db.query(models.VariantFilterResult)
                .filter(
                    models.VariantFilterResult.run_id == run_id
                )
                .order_by(
                    models.VariantFilterResult.position.asc(),
                    models.VariantFilterResult.id.asc()
                )
                .all()
            )
            logs = (db.query(models.PipelineLog)
                    .filter(models.PipelineLog.run_id == run_id)
                    .order_by(models.PipelineLog.id.asc()).all())
            station_rows = build_station_status(run, logs)
            report = generate_variant_report(
                run, variants, run_dir,
                build_station_interpretations(run, station_rows),
                filter_audit=filter_audit,
            )   
            archive.writestr(f"{run_id}_Variant_Report.pdf", report)
            for extra in ["alignment.flagstat.txt", "alignment.coverage.tsv",
                          "coverage_metrics.json", "variants.stats.txt"]:
                extra_path = run_dir / extra
                if extra_path.is_file() and not extra_path.is_symlink():
                    archive.write(extra_path, arcname=extra)
            logs_text = "\n".join(
                f"[{log.created_at.isoformat() if log.created_at else ''}] "
                f"Stasiun {log.station_number} [{log.log_level}] {str(log.message).replace(chr(10), ' ')}"
                for log in logs
            )
            archive.writestr("pipeline_logs.txt", logs_text + "\n")
            for ext, delimiter in (("csv", ","), ("tsv", "\t")):
                text_output = io.StringIO(newline="")
                writer = csv.writer(text_output, delimiter=delimiter, lineterminator="\r\n")
                writer.writerow(EXPORT_COLUMNS)
                for var in variants:
                    assessment = safe_assessment_values(var)
                    writer.writerow([
                        _spreadsheet_safe(assessment[field] if field in assessment else getattr(var, field, None))
                        for field in EXPORT_COLUMNS
                    ])
                archive.writestr(f"variants.{ext}", text_output.getvalue().encode("utf-8-sig"))
            # Ekspor metadata tanpa rahasia
            archive.writestr("run_metadata.json", json.dumps({
                "run_id": run.run_id,
                "sample_name": run.sample_name,
                "execution_mode": enum_value(run.execution_mode),
                "parameters": {"min_dp": run.min_dp, "min_mq": run.min_mq, "min_qual": run.min_qual, "min_af": run.min_af},
            }, indent=2))
        return Response(buf.getvalue(), media_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="{_export_name(run_id, "zip")}"',
            "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

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

    raise HTTPException(status_code=400, detail="Format ekspor harus pdf, csv, tsv, vcf, zip, logs, atau config.")



# Artefak yang dihasilkan pipeline. ID berasal dari daftar tetap, bukan dari path pengguna.

ARTIFACTS = {
    # STASIUN 1 — Quality Control
    "fastp_html": (1, "fastp.html", "Laporan QC fastp (HTML)", "text/html"),
    "fastp_json": (1, "fastp.json", "Metrik QC fastp (JSON)", "application/json"),
    "clean_r1": (1, "clean_R1.fq", "FASTQ R1 hasil preprocessing", "text/plain"),
    "clean_r2": (1, "clean_R2.fq", "FASTQ R2 hasil preprocessing", "text/plain"),

    # STASIUN 2 — Read Alignment
    "aligned_bam": (2, "aligned.bam", "Sorted BAM", "application/octet-stream"),
    "aligned_bai": (2, "aligned.bam.bai", "BAM index (BAI)", "application/octet-stream"),

    "alignment_flagstat": (
        2,
        "alignment.flagstat.txt",
        "Statistik Alignment (SAMtools flagstat)",
        "text/plain",
    ),

    "alignment_coverage": (
        2,
        "alignment.coverage.tsv",
        "Statistik Coverage (SAMtools)",
        "text/tab-separated-values",
    ),

    # STASIUN 3 — Variant Calling
    "raw_vcf": (3, "variants.vcf", "Raw VCF", "text/plain"),

    "variants_stats": (
        3,
        "variants.stats.txt",
        "Statistik Variant Calling (BCFtools)",
        "text/plain",
    ),

    # STASIUN 4 — Filtering & Annotation
    "filtered_vcf": (4, "variants.filtered.vcf", "Filtered VCF", "text/plain"),
    "annotated_vcf": (4, "variants.ann.vcf", "Annotated VCF (SnpEff)", "text/plain"),
}


def _completed_stations(db: Session, run_id: str) -> set[int]:
    """Stasiun baru dianggap siap diunduh setelah log SUCCESS tersimpan."""
    logs = (
        db.query(models.PipelineLog)
        .filter(models.PipelineLog.run_id == run_id, models.PipelineLog.log_level == "SUCCESS")
        .all()
    )
    return {int(log.station_number) for log in logs if log.station_number in (1, 2, 3, 4)}


def _artifact_path(run_id: str, artifact_id: str) -> Path:
    """Cegah path traversal/symlink dengan daftar nama yang statis."""
    spec = ARTIFACTS.get(artifact_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Jenis artefak tidak dikenal")

    root = UPLOAD_DIR.resolve()
    run_dir = root / run_id
    if not re.fullmatch(r"VE-[A-Za-z0-9-]+", run_id):
        raise HTTPException(status_code=400, detail="Run ID tidak valid")
    if run_dir.is_symlink() or not run_dir.resolve().is_relative_to(root):
        raise HTTPException(status_code=400, detail="Direktori run tidak valid")

    path = run_dir / spec[1]
    if path.is_symlink() or not path.resolve().is_relative_to(run_dir.resolve()):
        raise HTTPException(status_code=404, detail="Artefak tidak tersedia")
    return path


@router.get("/{run_id}/artifacts")
def list_run_artifacts(
    run_id: str,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    """Daftar artefak nyata yang boleh diunduh pemilik run."""
    run = _get_owned_run(db, run_id, current_user_id)
    finished = _completed_stations(db, run_id)
    artifacts = []
    for artifact_id, (station, filename, label, _media_type) in ARTIFACTS.items():
        if station not in finished:
            continue
        if artifact_id == "annotated_vcf" and enum_value(run.annotation_status) != "COMPLETED":
            continue
        path = _artifact_path(run_id, artifact_id)
        if not path.is_file():
            continue
        artifacts.append({
            "station": station,
            "artifact_id": artifact_id,
            "label": label,
            "filename": filename,
            "size_bytes": path.stat().st_size,
            "url": f"/analysis/{run_id}/artifacts/{artifact_id}",
        })
    return {"run_id": run_id, "artifacts": artifacts}


@router.get("/{run_id}/artifacts/{artifact_id}")
def download_run_artifact(
    run_id: str,
    artifact_id: str,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(require_researcher),
):
    """Unduh berkas output asli melalui autentikasi, tanpa membuka direktori arbitrer."""
    _get_owned_run(db, run_id, current_user_id)
    spec = ARTIFACTS.get(artifact_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Jenis artefak tidak dikenal")
    station, filename, _label, media_type = spec
    if station not in _completed_stations(db, run_id):
        raise HTTPException(status_code=409, detail="Stasiun belum selesai")
    path = _artifact_path(run_id, artifact_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Berkas artefak belum tersedia")
    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        content_disposition_type="attachment",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


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
