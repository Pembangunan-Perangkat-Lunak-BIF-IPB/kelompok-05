"""
utils/genomics.py
Modul untuk Quality Filtering, kalkulasi Ts/Tv ratio, dan pengolahan varian VCF.
"""

from typing import List, Dict, Any, Tuple

def check_variant_pass(dp: float, mq: float, qual: float, af: float) -> bool:
    """
    Memeriksa apakah varian memenuhi ambang batas Quality Filtering SKPL:
    - DP >= 10 (Read Depth)
    - MQ >= 30 (Mapping Quality)
    - QUAL >= 30 (Variant Call Quality)
    - AF >= 0.20 (Allele Frequency)
    """
    return (dp >= 10.0) and (mq >= 30.0) and (qual >= 30.0) and (af >= 0.20)


def calculate_tstv_ratio(snp_variants: List[Dict[str, str]]) -> Tuple[int, int, float]:
    """
    Menghitung rasio Transition/Transversion (Ts/Tv) dari daftar varian SNP yang PASS.
    - Ts (Transisi): Purin <-> Purin (A <-> G) atau Pirimidin <-> Pirimidin (C <-> T)
    - Tv (Transversi): Purin <-> Pirimidin (A <-> C, A <-> T, G <-> C, G <-> T)
    """
    transitions = 0
    transversions = 0

    # Pasangan basa Transisi (A<->G, C<->T)
    ts_pairs = {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}

    for var in snp_variants:
        ref = var.get("ref", "").upper()
        alt = var.get("alt", "").upper()

        # Hanya proses jika berupa single-nucleotide substitution (SNP)
        if len(ref) == 1 and len(alt) == 1 and ref != alt:
            if (ref, alt) in ts_pairs:
                transitions += 1
            else:
                transversions += 1

    # Hitung rasio (hindari DivisionByZero Error)
    if transversions == 0:
        ratio = float(transitions)  # Jika Tv = 0, rasio diset ke total Ts
    else:
        ratio = round(transitions / transversions, 2)

    return transitions, transversions, ratio

#if __name__ == "__main__":
    # 1. Uji Quality Filtering
    print("--- Tes Quality Filtering ---")
    v1_pass = check_variant_pass(dp=15, mq=35, qual=40, af=0.25)
    v2_fail = check_variant_pass(dp=5, mq=35, qual=40, af=0.25) # DP di bawah 10
    print("Varian Valid (Harus True):", v1_pass)
    print("Varian Low DP (Harus False):", v2_fail)

    # 2. Uji Kalkulasi Ts/Tv Ratio
    print("\n--- Tes Ts/Tv Ratio ---")
    sample_snps = [
        {"ref": "A", "alt": "G"},  # Transition (Ts)
        {"ref": "C", "alt": "T"},  # Transition (Ts)
        {"ref": "A", "alt": "C"},  # Transversion (Tv)
        {"ref": "G", "alt": "T"},  # Transversion (Tv)
    ]
    ts, tv, ratio = calculate_tstv_ratio(sample_snps)
    print(f"Transitions (Ts): {ts}")
    print(f"Transversions (Tv): {tv}")
    print(f"Rasio Ts/Tv: {ratio}")