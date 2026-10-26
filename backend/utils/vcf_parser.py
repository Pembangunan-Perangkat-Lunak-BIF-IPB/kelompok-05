import os
import re
from sqlalchemy.orm import Session
import models

def parse_and_store_vcf(vcf_path: str, run_id: str, db: Session):
    """Membaca berkas VCF hasil pipeline dan menyimpan baris varian ke tabel variant_results."""
    if not os.path.exists(vcf_path):
        return

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

            # Ekstrak Depth (DP) dari kolom INFO VCF jika tersedia
            dp_val = None
            dp_match = re.search(r"DP=(\d+)", info)
            if dp_match:
                dp_val = int(dp_match.group(1))

            # Sesuaikan persis dengan kolom pada models.VariantResult
            variant_entry = models.VariantResult(
                run_id=run_id,
                position=pos,
                ref_allele=ref,
                alt_allele=alt,
                qual=qual_str,
                dp=dp_val
            )
            db.add(variant_entry)

    db.commit()