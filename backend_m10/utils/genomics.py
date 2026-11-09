"""
utils/genomics.py
Modul untuk Quality Filtering, kalkulasi Ts/Tv ratio, dan pengolahan varian VCF.
"""

from typing import List, Dict, Optional, Tuple

# Ambang batas Quality Filtering sesuai SKPL
QC_THRESHOLDS = {"dp": 10.0, "mq": 30.0, "qual": 30.0, "af": 0.20}


def check_variant_pass(dp: float, mq: float, qual: float, af: float) -> bool:
    """
    Memeriksa apakah varian memenuhi ambang batas Quality Filtering SKPL:
    - DP >= 10 (Read Depth)
    - MQ >= 30 (Mapping Quality)
    - QUAL >= 30 (Variant Call Quality)
    - AF >= 0.20 (Allele Frequency)
    """
    return (dp >= 10.0) and (mq >= 30.0) and (qual >= 30.0) and (af >= 0.20)


def evaluate_variant(
    dp: Optional[float] = None,
    mq: Optional[float] = None,
    qual: Optional[float] = None,
    af: Optional[float] = None,
) -> Tuple[bool, List[str]]:
    """
    Versi toleran dari check_variant_pass untuk data VCF nyata.
    Metrik yang tidak tersedia (None) dilewati agar varian tidak terbuang hanya karena
    tag INFO-nya tidak ada. Mengembalikan (lolos, daftar_alasan_gagal).
    """
    values = {"dp": dp, "mq": mq, "qual": qual, "af": af}
    reasons = []
    for name, threshold in QC_THRESHOLDS.items():
        val = values[name]
        if val is not None and val < threshold:
            reasons.append(f"{name.upper()}<{threshold}")
    return (len(reasons) == 0, reasons)


def calculate_tstv_ratio(snp_variants: List[Dict[str, str]]) -> Tuple[int, int, Optional[float]]:
    """
    Menghitung rasio Transition/Transversion (Ts/Tv) dari daftar varian SNP yang PASS.
    - Ts (Transisi): Purin <-> Purin (A <-> G) atau Pirimidin <-> Pirimidin (C <-> T)
    - Tv (Transversi): Purin <-> Pirimidin (A <-> C, A <-> T, G <-> C, G <-> T)
    """
    transitions = 0
    transversions = 0
    ts_pairs = {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}

    for var in snp_variants:
        ref = (var.get("ref") or "").upper()
        alt = (var.get("alt") or "").upper()

        # Hanya proses jika berupa single-nucleotide substitution (SNP)
        if len(ref) == 1 and len(alt) == 1 and ref != alt:
            if (ref, alt) in ts_pairs:
                transitions += 1
            else:
                transversions += 1

    if transversions == 0:
        # Rasio tidak terdefinisi (pembagian nol). Jangan kembalikan jumlah Ts sebagai
        # rasio, karena itu angka yang berbeda artinya dan menyesatkan di laporan.
        ratio = None
    else:
        ratio = round(transitions / transversions, 2)

    return transitions, transversions, ratio


if __name__ == "__main__":
    # Uji cepat: python -m utils.genomics
    print("Varian valid (harus True):", check_variant_pass(dp=15, mq=35, qual=40, af=0.25))
    print("Varian low DP (harus False):", check_variant_pass(dp=5, mq=35, qual=40, af=0.25))
    print("Ts/Tv (harus 2, 2, 1.0):", calculate_tstv_ratio([
        {"ref": "A", "alt": "G"}, {"ref": "C", "alt": "T"},
        {"ref": "A", "alt": "C"}, {"ref": "G", "alt": "T"},
    ]))
