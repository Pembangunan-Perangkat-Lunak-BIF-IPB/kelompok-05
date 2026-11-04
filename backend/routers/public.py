"""
routers/public.py
Endpoint publik tanpa autentikasi JWT untuk Pembaca Publik (Guest).
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import case

import models
from database import get_db

router = APIRouter(prefix="/api/v1/public", tags=["Public"])


@router.get("/analyses")
def get_public_analyses(db: Session = Depends(get_db)):
    """
    Menyajikan daftar katalog seluruh analisis yang berstatus PUBLIC.
    Dapat diakses secara umum tanpa login.
    """
    public_runs = (
        db.query(models.AnalysisRun)
        .filter(models.AnalysisRun.visibility == "PUBLIC")
        .order_by(models.AnalysisRun.created_at.desc())
        .all()
    )
    return public_runs


@router.get("/analyses/{run_id}/results")
def get_public_analysis_results(
    run_id: str,
    risk_level: Optional[str] = Query(None, description="Filter risk level (HIGH, MODERATE, LOW, OUTSIDE_EPITOPE)"),
    snpeff_effect: Optional[str] = Query(None, description="Filter efek SnpEff"),
    min_pos: Optional[int] = Query(None, description="Posisi minimal"),
    max_pos: Optional[int] = Query(None, description="Posisi maksimal"),
    db: Session = Depends(get_db)
):
    """
    Mengembalikan detail hasil varian dan metrik khusus untuk analisis berstatus PUBLIC.
    Jika analisis berstatus PRIVATE, kembalikan 403 Forbidden.
    """
    # 1. Cari analisis
    run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesi analisis tidak ditemukan."
        )

    # 2. Penegakan Keamanan Visibilitas
    if run.visibility != "PUBLIC":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analisis ini berstatus PRIVATE dan tidak dapat diakses publik."
        )

    # 3. Base Query Varian
    query = db.query(models.VariantResult).filter(models.VariantResult.run_id == run_id)

    # 4. Filter Query
    if risk_level:
        query = query.filter(models.VariantResult.risk_level == risk_level.upper())
    if snpeff_effect:
        query = query.filter(models.VariantResult.snpeff_effect.ilike(f"%{snpeff_effect}%"))
    if min_pos is not None:
        query = query.filter(models.VariantResult.pos >= min_pos)
    if max_pos is not None:
        query = query.filter(models.VariantResult.pos <= max_pos)

    # 5. Default Sorting (Risk Level -> POS)
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

    variants = query.order_by(risk_hierarchy, models.VariantResult.pos.asc()).all()

    # 6. Response
    return {
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "status": run.status,
        "visibility": run.visibility,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "summary_metrics": {
            "q20_rate": run.q20_rate,
            "q30_rate": run.q30_rate,
            "mapping_rate": run.mapping_rate,
            "mean_depth": run.mean_depth,
            "tstv_ratio": run.tstv_ratio,
            "total_variants": len(variants)
        },
        "variants": variants
    }