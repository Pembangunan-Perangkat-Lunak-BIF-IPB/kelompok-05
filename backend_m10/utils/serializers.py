"""
utils/serializers.py
Bentuk respons JSON yang dipakai bersama router analysis & public, mengikuti kontrak api.md
(pos/ref/alt, bukan nama kolom database position/ref_allele/alt_allele).
"""

from typing import List, Optional

from sqlalchemy import case

import models
from utils.genomics import calculate_tstv_ratio

STATIONS = [
    (1, "Quality Control (fastp)"),
    (2, "Read Mapping (BWA-MEM2)"),
    (3, "Variant Calling (BCFtools)"),
    (4, "Quality Filtering"),
    (5, "Epitope Mapping & Grantham"),
]


def enum_value(value):
    return getattr(value, "value", value)


def to_float(value) -> Optional[float]:
    if value in (None, "", "."):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def serialize_run(run: models.AnalysisRun) -> dict:
    return {
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "status": enum_value(run.status),
        "visibility": enum_value(run.visibility),
        "created_at": run.created_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }


def safe_assessment_values(v: models.VariantResult) -> dict:
    """
    Membedakan hasil yang tersedia dengan data yang belum
    dapat dievaluasi, termasuk data lama di PostgreSQL.
    Tidak mengubah isi database.
    """
    has_annotation = bool(
        v.snpeff_effect and str(v.snpeff_effect).strip()
    )

    score = v.grantham_score if has_annotation else None
    risk = v.risk_level if score is not None else None

    return {
        "grantham_score": score,
        "risk_level": risk,
        "annotation_status": (
            "PRESENT" if has_annotation else "UNAVAILABLE"
        ),
        "assessment_status": (
            "NOT_EVALUABLE"
            if score is None or risk is None
            else "UNVERIFIED"
        ),
    }


def serialize_variant(v: models.VariantResult) -> dict:
    return {
        "id": v.id,
        "run_id": v.run_id,
        "pos": v.position,
        "ref": v.ref_allele,
        "alt": v.alt_allele,
        "qual": to_float(v.qual),
        "dp": v.dp,
        "snpeff_effect": v.snpeff_effect,
        **safe_assessment_values(v),
    }




def build_results_response(
    run: models.AnalysisRun,
    variants: List[models.VariantResult],
    *,
    tstv_variants=None
) -> dict:

    tstv_note = None
    ts_count = None
    tv_count = None

    # Gunakan seluruh varian run untuk menghitung keterangan.
    # Jika hasil tabel difilter, gunakan tstv_variants
    # yang berisi seluruh varian dari run tersebut.
    source_variants = (
        tstv_variants
        if tstv_variants is not None
        else variants
    )

    if run.tstv_ratio is None:

        if enum_value(run.status) == "COMPLETED":

            ts_count, tv_count, _ = calculate_tstv_ratio([
                {
                    "ref": v.ref_allele,
                    "alt": v.alt_allele
                }
                for v in source_variants
            ])

            if tv_count == 0 and ts_count > 0:
                tstv_note = (
                    "Ts/Tv tidak terdefinisi karena "
                    "tidak ditemukan transversi."
                )

            elif ts_count == 0 and tv_count == 0:
                tstv_note = (
                    "Ts/Tv tidak tersedia karena "
                    "tidak ada substitusi SNP yang "
                    "dapat dihitung."
                )

            else:
                tstv_note = (
                    "Ts/Tv belum tersedia; "
                    "periksa kembali sumber metrik."
                )

        else:
            tstv_note = (
                "Ts/Tv belum tersedia karena "
                "analisis belum selesai."
            )

    return {
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "status": enum_value(run.status),
        "visibility": enum_value(run.visibility),
        "started_at": run.started_at,
        "completed_at": run.completed_at,

        "summary_metrics": {
            "q20_rate": run.q20_rate,
            "q30_rate": run.q30_rate,
            "mapping_rate": run.mapping_rate,
            "mean_depth": run.mean_depth,
            "tstv_ratio": run.tstv_ratio,
            "tstv_note": tstv_note,
            "tstv_transition_count": ts_count,
            "tstv_transversion_count": tv_count,
            "total_variants": len(variants),
        },

        "variants": [
            serialize_variant(v)
            for v in variants
        ],
    }



def query_variants(db, run_id: str, risk_level=None, snpeff_effect=None, min_pos=None, max_pos=None):
    """Query varian + filter + urutan default (HIGH → MODERATE → LOW → OUTSIDE_EPITOPE, lalu pos ascending)."""
    VR = models.VariantResult
    query = db.query(VR).filter(VR.run_id == run_id)

    if risk_level:
        query = query.filter(VR.risk_level == risk_level.strip().upper())
    if snpeff_effect:
        query = query.filter(VR.snpeff_effect.ilike(f"%{snpeff_effect}%"))
    if min_pos is not None:
        query = query.filter(VR.position >= min_pos)
    if max_pos is not None:
        query = query.filter(VR.position <= max_pos)

    risk_order = case(
        {"HIGH": 1, "MODERATE": 2, "LOW": 3, "OUTSIDE_EPITOPE": 4},
        value=VR.risk_level,
        else_=5,
    )
    return query.order_by(risk_order, VR.position.asc()).all()


def build_station_status(run: models.AnalysisRun, logs: List[models.PipelineLog]) -> List[dict]:
    """Status per stasiun berdasarkan log SUCCESS/ERROR yang ditulis pipeline."""
    run_status = enum_value(run.status)
    done = {log.station_number for log in logs if log.log_level == "SUCCESS"}
    error_station = next((log.station_number for log in reversed(logs) if log.log_level == "ERROR"), None)
    next_station = min((n for n, _ in STATIONS if n not in done), default=None)

    result = []
    for num, name in STATIONS:
        if run_status == "COMPLETED" or num in done:
            st = "COMPLETED"
        elif run_status == "FAILED":
            st = "FAILED" if num == (error_station or next_station) else "PENDING"
        elif run_status == "RUNNING":
            st = "RUNNING" if num == next_station else "PENDING"
        else:
            st = "PENDING"
        result.append({"station": num, "name": name, "status": st})
    return result


def serialize_logs(logs: List[models.PipelineLog]) -> List[dict]:
    return [
        {
            "station_number": log.station_number,
            "timestamp": log.created_at.strftime("%H:%M:%S") if log.created_at else "",
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "log_level": log.log_level,
            "message": log.message,
        }
        for log in logs
    ]
