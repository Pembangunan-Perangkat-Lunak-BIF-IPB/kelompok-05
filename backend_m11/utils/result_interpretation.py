
"""
Interpretasi deskriptif hasil analisis VarEscape.

Modul ini tidak menentukan status keberhasilan pipeline
dan tidak melakukan klasifikasi kualitas GOOD/WARNING/POOR.
"""

import json
import re
from pathlib import Path

from config import UPLOAD_DIR


def _value(run, field):
    return getattr(run, field, None)


def _status(value):
    return str(getattr(value, "value", value)).upper()


def _coverage(run_id):
    """Membaca statistik coverage jika tersedia."""
    if not re.fullmatch(r"VE-[A-Za-z0-9-]+", str(run_id)):
        return {}

    root = Path(UPLOAD_DIR).resolve()
    run_dir = root / run_id

    if run_dir.is_symlink():
        return {}

    path = run_dir / "coverage_metrics.json"

    if path.is_symlink() or not path.is_file():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def interpret_station(run, station, execution_status):
    """
    Menghasilkan interpretasi berdasarkan metrik tersimpan.
    Tidak mengubah status analisis.
    """

    status = _status(execution_status)

    result = {
        "station": station,
        "execution_status": status,
        "interpretation": "",
        "notes": [],
        "recommendations": [],
    }

    if status == "FAILED":
        result["interpretation"] = (
            "Proses stasiun mengalami kegagalan teknis. "
            "Periksa pipeline log untuk mengetahui penyebabnya."
        )
        return result

    if status == "PENDING":
        result["interpretation"] = (
            "Stasiun belum dijalankan."
        )
        return result

    if status == "RUNNING":
        result["interpretation"] = (
            "Stasiun sedang memproses data. "
            "Interpretasi tersedia setelah proses selesai."
        )
        return result

    if status != "COMPLETED":
        return result

    # STASIUN 1 — QUALITY CONTROL
    if station == 1:
        q20_before = _value(run, "q20_before")
        q30_before = _value(run, "q30_before")
        q20_after = _value(run, "q20_rate")
        q30_after = _value(run, "q30_rate")
        reads_before = _value(run, "reads_before")
        reads_after = _value(run, "reads_after")

        parts = ["Quality control dan preprocessing selesai."]

        if q20_before is not None and q20_after is not None:
            parts.append(
                f"Proporsi basa Q20 berubah dari "
                f"{q20_before:.2f}% menjadi {q20_after:.2f}%."
            )

        if q30_before is not None and q30_after is not None:
            parts.append(
                f"Proporsi basa Q30 berubah dari "
                f"{q30_before:.2f}% menjadi {q30_after:.2f}%."
            )

        if reads_before is not None and reads_after is not None:
            parts.append(
                f"Jumlah reads berubah dari "
                f"{reads_before:,} menjadi {reads_after:,} "
                "setelah preprocessing."
            )

        result["interpretation"] = " ".join(parts)

        result["notes"].append(
            "Q20 dan Q30 menggambarkan proporsi basa "
            "yang mencapai skor kualitas Phred tertentu. "
            "Nilainya tidak digunakan sendiri untuk "
            "menentukan kelayakan keseluruhan sampel."
        )

        result["recommendations"].append(
            "Periksa laporan fastp untuk melihat distribusi "
            "kualitas basa dan hasil trimming."
        )

    # STASIUN 2 — READ ALIGNMENT
    elif station == 2:
        mapping = _value(run, "mapping_rate")
        depth = _value(run, "mean_depth")
        coverage = _coverage(run.run_id)

        parts = ["Read alignment selesai."]

        if mapping is not None:
            parts.append(
                f"Mapping rate tercatat sebesar {mapping:.2f}%."
            )

        if depth is not None:
            parts.append(
                f"Rata-rata kedalaman pembacaan "
                f"sebesar {depth:.2f}x."
            )

        cov1 = coverage.get("genome_coverage_pct")
        cov30 = coverage.get("genome_coverage_30x_pct")

        if isinstance(cov1, (int, float)):
            parts.append(
                f"Sebanyak {cov1:.2f}% posisi genom "
                "memiliki coverage minimal 1x."
            )

        if isinstance(cov30, (int, float)):
            parts.append(
                f"Sebanyak {cov30:.2f}% posisi genom "
                "memiliki coverage minimal 30x."
            )

        result["interpretation"] = " ".join(parts)

        result["notes"].append(
            "Mapping rate menunjukkan proporsi reads "
            "yang terpetakan ke referensi. Mean depth "
            "merupakan nilai rata-rata dan tidak "
            "menjamin seluruh posisi genom tercakup."
        )

        if not coverage:
            result["notes"].append(
                "Statistik distribusi coverage belum tersedia."
            )

        result["recommendations"].append(
            "Periksa laporan coverage untuk mengetahui "
            "wilayah genom dengan kedalaman rendah."
        )

    # STASIUN 3 — VARIANT CALLING
    elif station == 3:
        raw = _value(run, "raw_variant_count")
        snp = _value(run, "raw_snp_count")
        indel = _value(run, "raw_indel_count")
        tstv = _value(run, "tstv_ratio")

        if raw is None:
            result["interpretation"] = (
                "Variant calling selesai, tetapi statistik "
                "jumlah kandidat varian belum tersedia."
            )
        elif raw == 0:
            result["interpretation"] = (
                "Variant calling selesai dan tidak ada "
                "kandidat varian yang terdeteksi."
            )
        else:
            parts = [
                f"Variant calling menghasilkan "
                f"{raw} kandidat varian mentah."
            ]

            if snp is not None:
                parts.append(f"Jumlah SNP tercatat {snp}.")

            if indel is not None:
                parts.append(f"Jumlah INDEL tercatat {indel}.")

            if tstv is not None:
                parts.append(
                    f"Rasio Ts/Tv tercatat {tstv:.2f}."
                )

            result["interpretation"] = " ".join(parts)

        result["notes"].append(
            "Jumlah kandidat varian dan rasio Ts/Tv "
            "merupakan statistik deskriptif, bukan "
            "penentu tunggal validitas varian."
        )

        result["recommendations"].append(
            "Periksa raw VCF, kedalaman posisi varian, "
            "serta hasil filtering pada stasiun berikutnya."
        )

    
    # STASIUN 4 — FILTERING & ANNOTATION
    elif station == 4:
        passed = _value(run, "passed_variant_count")
        filtered = _value(run, "filtered_variant_count")
        annotated = _value(run, "annotated_variant_count")
        annotation_status = _status(
            _value(run, "annotation_status")
        )

        if annotation_status == "SKIPPED":
            parts = ["Quality filtering selesai."]

            if passed is not None:
                parts.append(
                    f"Sebanyak {passed} varian memenuhi "
                    "parameter filtering."
                )

            if filtered is not None:
                parts.append(
                    f"Sebanyak {filtered} kandidat varian "
                    "tidak memenuhi parameter filtering."
                )

            parts.append(
                "Karena tidak terdapat varian PASS, "
                "anotasi SnpEff tidak dijalankan (SKIPPED). "
                "Hasil analisis tetap tersedia untuk diperiksa."
            )

            result["interpretation"] = " ".join(parts)

            result["notes"].append(
                "SKIPPED bukan kegagalan teknis. "
                "Anotasi dilewati karena tidak ada varian "
                "yang memenuhi parameter filtering."
            )

            result["recommendations"].append(
                "Periksa raw VCF, coverage genom, serta "
                "Audit Quality Filtering untuk mengetahui "
                "alasan penolakan kandidat varian."
            )

        elif annotation_status == "COMPLETED":
            parts = ["Quality filtering dan anotasi SnpEff selesai."]

            if passed is not None:
                parts.append(
                    f"Sebanyak {passed} varian memenuhi "
                    "parameter filtering."
                )

            if filtered is not None:
                parts.append(
                    f"Sebanyak {filtered} kandidat varian "
                    "tidak memenuhi parameter filtering."
                )

            if annotated is not None:
                parts.append(
                    f"Sebanyak {annotated} varian "
                    "berhasil dianotasi SnpEff."
                )

            result["interpretation"] = " ".join(parts)

            result["notes"].append(
                "Status PASS menunjukkan varian memenuhi "
                "parameter filtering pada run ini, bukan "
                "jaminan validitas biologis atau klinis."
            )

            result["recommendations"].append(
                "Periksa hasil anotasi SnpEff, parameter "
                "DP, QUAL, AF, serta filtered VCF."
            )

        elif annotation_status == "FAILED":
            result["interpretation"] = (
                "Quality filtering telah dijalankan, "
                "tetapi anotasi SnpEff mengalami "
                "kegagalan teknis."
            )

            result["recommendations"].append(
                "Periksa pipeline log dan artefak "
                "Stasiun 4 untuk mengetahui penyebabnya."
            )

        else:
            result["interpretation"] = (
                "Status anotasi SnpEff belum dapat "
                "dikonfirmasi dari data yang tersedia."
            )
    return result


def build_station_interpretations(run, stations):
    """Menghasilkan interpretasi untuk seluruh stasiun."""

    status_map = {
        int(item["station"]): item["status"]
        for item in stations
    }

    return {
        f"station_{n}": interpret_station(
            run,
            n,
            status_map.get(n, "PENDING")
        )
        for n in range(1, 5)
    }
