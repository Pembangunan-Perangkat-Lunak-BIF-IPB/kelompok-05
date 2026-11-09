"""
routers/public.py
Endpoint publik tanpa autentikasi JWT untuk Pembaca Publik (Guest).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

import models
from database import get_db
from utils.serializers import build_results_response, query_variants, serialize_run

router = APIRouter(prefix="/api/v1/public", tags=["Public"])


@router.get("/analyses")
def get_public_analyses(db: Session = Depends(get_db)):
    """Katalog seluruh analisis berstatus PUBLIC, dapat diakses tanpa login."""
    runs = (
        db.query(models.AnalysisRun)
        .filter(models.AnalysisRun.visibility == models.VisibilityType.PUBLIC)
        .order_by(models.AnalysisRun.created_at.desc())
        .all()
    )
    return [serialize_run(run) for run in runs]


@router.get("/analyses/{run_id}/results")
def get_public_analysis_results(
    run_id: str,
    risk_level: Optional[str] = Query(None, description="Filter risk level (HIGH, MODERATE, LOW, OUTSIDE_EPITOPE)"),
    snpeff_effect: Optional[str] = Query(None, description="Filter efek SnpEff"),
    min_pos: Optional[int] = Query(None, description="Posisi minimal"),
    max_pos: Optional[int] = Query(None, description="Posisi maksimal"),
    db: Session = Depends(get_db),
):
    """Detail hasil varian dan metrik untuk analisis PUBLIC. Analisis PRIVATE mengembalikan 403."""
    run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi analisis tidak ditemukan.")

    if run.visibility != models.VisibilityType.PUBLIC:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analisis ini berstatus PRIVATE dan tidak dapat diakses publik.",
        )

    
    # Varian yang ditampilkan mengikuti filter pengguna
    variants = query_variants(
        db, run_id, risk_level, snpeff_effect, min_pos, max_pos
    )

    # Ringkasan Ts/Tv harus berdasarkan seluruh varian run
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
