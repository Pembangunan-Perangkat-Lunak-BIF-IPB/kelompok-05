import os
import re
import csv
from sqlalchemy.orm import Session
import models
from utils.grantham import parse_snpeff_amino_acid_change, get_grantham_score, is_in_iedb_epitope, calculate_risk_level

def load_iedb_regions(iedb_path: str):
    """Membaca koordinat start_pos dan end_pos dari berkas IEDB."""
    regions = []
    if not os.path.exists(iedb_path):
        return regions
    with open(iedb_path, "r", encoding="utf-8") as f:
        sample = f.read(1024)
        f.seek(0)
        delimiter = "\t" if "\t" in sample else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            try:
                start = int(row.get("start_pos", 0))
                end = int(row.get("end_pos", 0))
                regions.append((start, end))
            except ValueError:
                continue
    return regions

def parse_and_store_vcf(vcf_path: str, run_id: str, iedb_path: str, db: Session):
    """Membaca berkas VCF hasil pipeline dan menghitung Immune Escape Risk Level."""
    if not os.path.exists(vcf_path):
        return

    iedb_regions = load_iedb_regions(iedb_path)

    with open(vcf_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue

            parts = line.strip().split("\t")
            if len(parts) < 8:
                continue

            pos = int(parts[1])
            ref = parts[3]
            alt = parts[4]
            qual_str = parts[5]
            info = parts[7]

            # Ekstrak Depth (DP) dari INFO VCF
            dp_val = None
            dp_match = re.search(r"DP=(\d+)", info)
            if dp_match:
                dp_val = int(dp_match.group(1))

            # Hitung Grantham & Risk Level
            in_epitope = is_in_iedb_epitope(pos, iedb_regions)
            
            # Simulasi/Parsing SnpEff jika tersedia di INFO
            aa_ref, aa_alt = parse_snpeff_amino_acid_change(info)
            g_score = get_grantham_score(aa_ref, aa_alt) if (aa_ref and aa_alt) else 0
            risk = calculate_risk_level(in_epitope, g_score)

            variant_entry = models.VariantResult(
                run_id=run_id,
                position=pos,
                ref_allele=ref,
                alt_allele=alt,
                qual=qual_str,
                dp=dp_val,
                grantham_score=g_score,
                risk_level=risk
            )
            db.add(variant_entry)

    db.commit()