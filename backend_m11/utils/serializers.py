"""
utils/serializers.py
Bentuk respons JSON yang dipakai bersama router analysis & public, mengikuti kontrak api.md
(pos/ref/alt, bukan nama kolom database position/ref_allele/alt_allele).
"""

from typing import List, Optional


import models
from utils.genomics import calculate_tstv_ratio



STATIONS = [
    (1, "Quality Control (fastp)"),
    (2, "Read Mapping (BWA-MEM2)"),
    (3, "Variant Calling (BCFtools)"),
    (4, "Quality Filtering & SnpEff Annotation"),
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
        "execution_mode": enum_value(run.execution_mode),
        "parameters": {"min_dp":run.min_dp,"min_mq":run.min_mq, "min_base_quality": run.min_base_quality,
            "max_depth": run.max_depth,"min_qual":run.min_qual,"min_af":run.min_af},
        "total_variants": run.passed_variant_count,
        "raw_variant_count": run.raw_variant_count,
        "passed_variant_count": run.passed_variant_count,
        "filtered_variant_count": run.filtered_variant_count,
        "annotation_status": enum_value(run.annotation_status),
    }


def safe_assessment_values(v: models.VariantResult) -> dict:
    """Status anotasi untuk kompatibilitas dengan ekspor lama."""
    annotated = bool(v.snpeff_effect and str(v.snpeff_effect).strip())
    return {"annotation_status": "PRESENT" if annotated else "UNAVAILABLE"}


def serialize_variant(v: models.VariantResult) -> dict:
    return {
        "id": v.id,
        "run_id": v.run_id,
        "pos": v.position,
        "ref": v.ref_allele,
        "alt": v.alt_allele,
        "qual": to_float(v.qual),
        "dp": v.dp,
        "mq": getattr(v, "mq", None),
        "af": getattr(v, "af", None),
        "chrom": getattr(v, "chrom", None),
        "snpeff_effect": v.snpeff_effect,
        "gene_name": getattr(v, "gene_name", None),
        "impact": getattr(v, "impact", None),
        "hgvs_c": getattr(v, "hgvs_c", None),
        "hgvs_p": getattr(v, "hgvs_p", None),
        "flank_left": getattr(v, "flank_left", None),
        "flank_right": getattr(v, "flank_right", None),
        **safe_assessment_values(v),
    }


def build_results_response(
    run: models.AnalysisRun,
    variants: List[models.VariantResult],
    *,
    tstv_variants=None
) -> dict:

    source_variants = (
        tstv_variants
        if tstv_variants is not None
        else variants
    )

    ts_count = None
    tv_count = None
    calculated_ratio = None
    tstv_note = None

    if enum_value(run.status) == "COMPLETED":
        ts_count, tv_count, calculated_ratio = calculate_tstv_ratio([
            {
                "ref": v.ref_allele,
                "alt": v.alt_allele
            }
            for v in source_variants
        ])

        if tv_count == 0:
            if ts_count == 0:
                tstv_note = "Tidak ada SNP yang dapat dihitung."
            else:
                tstv_note = (
                    "Ts/Tv tidak terdefinisi karena "
                    "jumlah transversion adalah 0."
                )
    else:
        tstv_note = "Ts/Tv belum tersedia karena analisis belum selesai."
        # Menghitung distribusi efek anotasi SnpEff
    effects = [
        str(v.snpeff_effect or "").lower()
        for v in variants
    ]

    missense_count = sum(
        "missense" in effect
        for effect in effects
    )

    synonymous_count = sum(
        "synonymous" in effect
        for effect in effects
    )

    frameshift_count = sum(
        "frameshift" in effect
        for effect in effects
    )

    stop_gained_count = sum(
        "stop_gained" in effect or "stop gained" in effect
        for effect in effects
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
            "tstv_ratio": calculated_ratio,
            "tstv_note": tstv_note,
            "tstv_transition_count": ts_count,
            "tstv_transversion_count": tv_count,
            "total_variants": len(variants),
            "raw_variant_count": run.raw_variant_count,
            "raw_snp_count": run.raw_snp_count,
            "raw_indel_count": run.raw_indel_count,
            "passed_variant_count": run.passed_variant_count,
            "filtered_variant_count": run.filtered_variant_count,
            "annotation_status": enum_value(run.annotation_status),
            "annotated_variant_count": run.annotated_variant_count,
            "q20_before": run.q20_before,
            "q30_before": run.q30_before,
            "reads_before": run.reads_before,
            "reads_after": run.reads_after,
            "passed_reads_pct": run.passed_reads_pct,
            
            "adapter_trimmed_pct": run.adapter_trimmed_pct,
            "unmapped_reads": run.unmapped_reads,
            "missense_count": missense_count,
            "synonymous_count": synonymous_count,
            "frameshift_count": frameshift_count,
            "stop_gained_count": stop_gained_count,

        },

        "variants": [serialize_variant(v) for v in variants],
    }


def query_variants(db, run_id: str, risk_level=None, snpeff_effect=None, min_pos=None, max_pos=None):
    """Query varian berdasarkan posisi dan anotasi; risk_level lama diabaikan."""
    VR = models.VariantResult
    query = db.query(VR).filter(VR.run_id == run_id)
    if snpeff_effect:
        query = query.filter(VR.snpeff_effect.ilike(f"%{snpeff_effect}%"))
    if min_pos is not None:
        query = query.filter(VR.position >= min_pos)
    if max_pos is not None:
        query = query.filter(VR.position <= max_pos)
    return query.order_by(VR.position.asc()).all()


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
