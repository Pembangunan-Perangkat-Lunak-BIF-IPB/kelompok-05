"""
utils/vcf_parser.py
Quality filtering VCF (Stasiun 4) dan penyimpanan varian + Grantham + risk level (Stasiun 5).
"""

import os
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

import models
from utils.genomics import evaluate_variant
from utils.grantham import parse_snpeff_amino_acid_change, get_grantham_score, is_in_iedb_epitope, calculate_risk_level
from utils.iedb import load_iedb_regions


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


def compute_allele_frequency(info: Dict[str, str]) -> Optional[float]:
    """AF dari DP4 bcftools: (alt_fwd + alt_rev) / total. Cadangan: tag AF di INFO."""
    dp4 = info.get("DP4")
    if dp4:
        try:
            ref_f, ref_r, alt_f, alt_r = [int(x) for x in dp4.split(",")[:4]]
            total = ref_f + ref_r + alt_f + alt_r
            if total > 0:
                return (alt_f + alt_r) / total
        except ValueError:
            pass
    if "AF" in info:
        return _to_float(info["AF"].split(",")[0])
    return None


def filter_vcf(in_path: str, out_path: str) -> Tuple[int, int]:
    """Stasiun 4: menyalin header + varian yang lolos ambang SKPL. Mengembalikan (total, lolos)."""
    if not os.path.exists(in_path):
        raise FileNotFoundError(f"Berkas VCF tidak ditemukan: {in_path}")

    total = passed = 0
    with open(in_path, "r", encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            if line.startswith("#"):
                fout.write(line)
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 8:
                continue

            total += 1
            info = parse_info(parts[7])
            ok, _ = evaluate_variant(
                dp=_to_float(info.get("DP")),
                mq=_to_float(info.get("MQ")),
                qual=_to_float(parts[5]),
                af=compute_allele_frequency(info),
            )
            if ok:
                passed += 1
                fout.write(line)

    return total, passed


def parse_snpeff_ann(info: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Membaca anotasi SnpEff (tag ANN). Format: ALT|Effect|Impact|Gene|...|HGVS.c|HGVS.p|...
    Mengembalikan (label_efek, hgvs_p), contoh ('S: p.Asn501Tyr (missense)', 'p.Asn501Tyr').
    """
    ann = info.get("ANN")
    if not ann:
        return None, None
    fields = ann.split(",")[0].split("|")
    if len(fields) < 11:
        return None, None

    effect = fields[1].replace("_variant", "").replace("&", ", ")
    gene = fields[3]
    hgvs_p = fields[10] or None

    if hgvs_p:
        label = f"{gene}: {hgvs_p} ({effect})" if gene else f"{hgvs_p} ({effect})"
    else:
        label = f"{gene}: {effect}" if gene else effect
    return label[:255], hgvs_p


def parse_and_store_vcf(vcf_path: str, run_id: str, iedb_path: str, db: Session) -> Tuple[int, int]:
    """Stasiun 5: menyimpan varian + Grantham + risk level. Mengembalikan (jumlah_varian, jumlah_teranotasi)."""
    if not os.path.exists(vcf_path):
        raise FileNotFoundError(f"Berkas VCF tidak ditemukan: {vcf_path}")

    iedb_regions = load_iedb_regions(iedb_path) if iedb_path and os.path.exists(iedb_path) else []

    # Hapus hasil lama run ini (jika pipeline pernah dijalankan ulang)
    db.query(models.VariantResult).filter(models.VariantResult.run_id == run_id).delete(synchronize_session=False)

    stored = annotated = 0
    with open(vcf_path, "r", encoding="utf-8") as f:
        for line in f:
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
            effect_label, hgvs_p = parse_snpeff_ann(info)
            if effect_label:
                annotated += 1

            aa_ref, aa_alt = parse_snpeff_amino_acid_change(hgvs_p or "")

            # Bedakan skor valid dengan informasi yang tidak tersedia
            if aa_ref is not None and aa_alt is not None:
                g_score = get_grantham_score(aa_ref, aa_alt)
            else:
                g_score = None

            # Jangan menghasilkan kategori penilaian jika skor belum tersedia
            if g_score is not None:
                risk = calculate_risk_level(
                    is_in_iedb_epitope(pos, iedb_regions),
                    g_score
                )
            else:
                risk = None

            dp_raw = info.get("DP")
            db.add(models.VariantResult(
            run_id=run_id,
            position=pos,
            ref_allele=parts[3][:50],
            alt_allele=parts[4][:50],
            qual=_to_float(parts[5]),   # '.' -> None; kolom qual bertipe Float
            dp=int(dp_raw) if dp_raw and dp_raw.isdigit() else None,
            snpeff_effect=effect_label,
            grantham_score=g_score,
            risk_level=risk,
            ))
            stored += 1

    db.commit()
    return stored, annotated
