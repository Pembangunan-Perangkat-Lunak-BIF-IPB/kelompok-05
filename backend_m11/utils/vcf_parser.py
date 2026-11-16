"""
utils/vcf_parser.py
Quality filtering VCF dan penyimpanan anotasi (Stasiun 4).
"""

import os
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

import models
from utils.genomics import evaluate_variant

# Kolom ANN SnpEff (spesifikasi VCF ANN 1.0)
ANN_ALLELE, ANN_EFFECT, ANN_IMPACT, ANN_GENE = 0, 1, 2, 3
ANN_HGVS_P, ANN_AA_POS, ANN_ERRORS = 10, 13, 15


def parse_info(info: str) -> Dict[str, str]:
    """Mengubah kolom INFO VCF ('DP=10;MQ=60;INDEL') menjadi dict."""
    out: Dict[str, str] = {}
    for item in info.split(";"):
        if not item:
            continue
        if "=" in item:
            key, val = item.split("=", 1)
            out[key] = val
        else:
            out[item] = "true"
    return out


def _to_float(value) -> Optional[float]:
    if value in (None, "", "."):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _format_dp(parts: List[str]) -> Optional[int]:
    """Membaca FORMAT/DP dari sampel pertama pada VCF."""
    if len(parts) < 10:
        return None

    keys = parts[8].split(":")
    values = parts[9].split(":")

    if "DP" not in keys:
        return None

    idx = keys.index("DP")
    if idx >= len(values):
        return None

    value = values[idx]

    if not value.isdigit():
        return None

    return int(value)

def _format_af(parts: List[str]) -> Optional[float]:
    """Hitung AF dari FORMAT/AD untuk satu sampel, satu alel ALT."""
    if len(parts) < 10:
        return None

    # Multi-allelic membutuhkan perhitungan AF untuk setiap ALT.
    # Jangan gabungkan semua ALT menjadi satu nilai.
    if "," in parts[4]:
        return None

    keys = parts[8].split(":")
    values = parts[9].split(":")

    if "AD" not in keys:
        return None

    idx = keys.index("AD")
    if idx >= len(values):
        return None

    try:
        raw_ad = values[idx].split(",")

        # Untuk record bialelik: AD_REF, AD_ALT
        if len(raw_ad) != 2:
            return None

        ref_depth, alt_depth = map(int, raw_ad)

        if ref_depth < 0 or alt_depth < 0:
            return None

        total = ref_depth + alt_depth
        if total == 0:
            return None

        return alt_depth / total

    except (ValueError, TypeError):
        return None


def compute_allele_frequency(
    info: Dict[str, str],
    parts: Optional[List[str]] = None
) -> Optional[float]:
    """Hitung AF dengan FORMAT/AD sebagai sumber utama."""

    # Hindari perhitungan ambigu untuk multi-allelic.
    if parts and len(parts) > 4 and "," in parts[4]:
        return None

    # 1. Prioritas utama: FORMAT/AD
    if parts:
        af = _format_af(parts)
        if af is not None:
            return af

    # 2. Cadangan: INFO/DP4 untuk record bialelik
    dp4 = info.get("DP4")
    if dp4:
        try:
            counts = [int(x) for x in dp4.split(",")]
            if len(counts) == 4 and all(x >= 0 for x in counts):
                total = sum(counts)
                if total > 0:
                    return (counts[2] + counts[3]) / total
        except (TypeError, ValueError):
            pass

    # 3. Cadangan terakhir: INFO/AF jika valid
    af = _to_float(info.get("AF", "").split(",")[0])

    if af is not None and 0 <= af <= 1:
        return af

    return None



def filter_vcf(
    in_path: str,
    out_path: str,
    thresholds: Optional[dict] = None,
    audit_rows: Optional[List[dict]] = None,
) -> Tuple[int, int]:
    """Filter VCF dan kumpulkan alasan evaluasi tiap kandidat."""

    if not os.path.exists(in_path):
        raise FileNotFoundError(
            f"Berkas VCF tidak ditemukan: {in_path}"
        )

    total = 0
    passed = 0

    with open(in_path, "r", encoding="utf-8") as fin, \
         open(out_path, "w", encoding="utf-8") as fout:

        for line in fin:
            if line.startswith("#"):
                fout.write(line)
                continue

            parts = line.rstrip("\n").split("\t")

            if len(parts) < 8:
                raise ValueError(
                    "Record VCF tidak memiliki 8 kolom wajib."
                )

            total += 1

            info = parse_info(parts[7])

            dp = _format_dp(parts)
            qual = _to_float(parts[5])
            af = compute_allele_frequency(info, parts)

            ok, reasons = evaluate_variant(
                dp=dp,
                mq=None,
                qual=qual,
                af=af,
                thresholds=thresholds,
            )

            if audit_rows is not None:
                audit_rows.append({
                    "chrom": parts[0],
                    "position": int(parts[1]),
                    "ref_allele": parts[3],
                    "alt_allele": parts[4],
                    "qual": qual,
                    "dp": dp,
                    "af": af,
                    "filter_status": (
                        "PASS" if ok else "FILTERED"
                    ),
                    "filter_reason": (
                        None if ok else "; ".join(reasons)
                    ),
                })

            if ok:
                passed += 1
                fout.write(line)

    return total, passed



def _choose_ann_entry(ann: str, alt: str) -> Optional[List[str]]:
    """Memilih entri ANN yang valid untuk alel ALT pertama.
    SnpEff mengurutkan entri dari dampak tertinggi; entri dengan HGVS.p (perubahan protein)
    diutamakan bila perubahan protein tersedia."""
    first_alt = alt.split(",")[0]
    entries = []
    for raw in ann.split(","):
        f = raw.split("|")
        if len(f) < 11 or not f[ANN_EFFECT].strip():
            continue
        if len(f) > ANN_ERRORS and "ERROR_CHROMOSOME_NOT_FOUND" in f[ANN_ERRORS]:
            continue
        entries.append(f)
    if not entries:
        return None
    same_allele = [f for f in entries if f[ANN_ALLELE] == first_alt] or entries
    with_protein = [f for f in same_allele if f[ANN_HGVS_P].strip()]
    return (with_protein or same_allele)[0]


def parse_snpeff_ann(info: Dict[str, str], alt: str = "") -> Dict[str, Optional[object]]:
    """
    Membaca anotasi SnpEff (tag ANN). Format: ALT|Effect|Impact|Gene|...|HGVS.c|HGVS.p|cDNA|CDS|AA.pos/len|...
    Mengembalikan dict: label, hgvs_p, gene, aa_pos. label None jika tidak ada anotasi valid.
    """
    out = {"label": None, "hgvs_p": None, "gene": None, "aa_pos": None, "effect": None, "impact": None, "transcript_id": None, "hgvs_c": None, "annotation_raw": None}
    ann = info.get("ANN")
    if not ann:
        return out
    f = _choose_ann_entry(ann, alt)
    if f is None:
        return out

    effect = f[ANN_EFFECT].replace("_variant", "").replace("&", ", ")
    gene = f[ANN_GENE] or None
    hgvs_p = f[ANN_HGVS_P] or None
    aa_pos = None
    if len(f) > ANN_AA_POS and f[ANN_AA_POS]:
        try:
            aa_pos = int(f[ANN_AA_POS].split("/")[0])
        except ValueError:
            aa_pos = None

    if hgvs_p:
        label = f"{gene}: {hgvs_p} ({effect})" if gene else f"{hgvs_p} ({effect})"
    else:
        label = f"{gene}: {effect}" if gene else effect
    out.update(label=label[:255], hgvs_p=hgvs_p, gene=gene, aa_pos=aa_pos, effect=f[ANN_EFFECT], impact=f[ANN_IMPACT], transcript_id=f[6] if len(f)>6 else None, hgvs_c=f[9] if len(f)>9 else None, annotation_raw=ann)
    return out


def parse_and_store_vcf(vcf_path: str, run_id: str, db: Session, reference_path: Optional[str] = None) -> Tuple[int, int, dict]:
    """Simpan varian dan ringkasan anotasi SnpEff tanpa pemetaan epitope.

    Mengembalikan (jumlah_varian, jumlah_teranotasi, statistik).
    """
    if not os.path.exists(vcf_path):
        raise FileNotFoundError(f"Berkas VCF tidak ditemukan: {vcf_path}")

    db.query(models.VariantResult).filter(
        models.VariantResult.run_id == run_id
    ).delete(synchronize_session=False)

    stored = annotated = 0
    reference = ""
    if reference_path:
        with open(reference_path, encoding="utf-8") as fasta:
            reference = "".join(line.strip().upper() for line in fasta if not line.startswith(">"))
    with open(vcf_path, "r", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 8:
                continue
            try:
                pos = int(parts[1])
            except ValueError:
                continue
            info = parse_info(parts[7])
            ann = parse_snpeff_ann(info, parts[4])
            if ann["label"] is not None:
                annotated += 1
            dp_raw = _format_dp(parts)
            db.add(models.VariantResult(
                run_id=run_id,
                chrom=parts[0][:100],
                position=pos,
                ref_allele=parts[3][:50],
                alt_allele=parts[4][:50],
                qual=_to_float(parts[5]),
                dp=dp_raw,
                snpeff_effect=ann["label"],
                gene_name=ann["gene"],
                impact=ann["impact"],
                transcript_id=ann["transcript_id"],
                hgvs_c=ann["hgvs_c"],
                hgvs_p=ann["hgvs_p"],
                annotation_raw=ann["annotation_raw"],
                amino_acid_change=ann["hgvs_p"],
                mq=_to_float(info.get("MQ")),
                af=compute_allele_frequency(info, parts),
                filter_status="PASS",
                flank_left=reference[max(0,pos-1-50):pos-1] if reference else None,
                flank_right=reference[pos-1+len(parts[3]):pos-1+len(parts[3])+50] if reference else None,
            ))
            stored += 1
    db.commit()
    return stored, annotated, {"annotation_available": annotated, "total": stored}
