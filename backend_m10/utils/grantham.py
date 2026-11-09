"""
utils/grantham.py
Modul untuk kalkulasi Grantham Distance, pemetaan Epitope IEDB, 
dan klasifikasi Immune Escape Risk Score sesuai spesifikasi SKPL.
"""

import re
from typing import List, Tuple, Optional, Dict

# Matriks Grantham Distance (1974) untuk 20 Asam Amino Standar
# Nilai 0 s.d. 215 mengukur disparitas komposisi, kepolaran, dan volume molekul.
GRANTHAM_MATRIX: Dict[Tuple[str, str], int] = {
    ('A', 'A'): 0,   ('A', 'R'): 112, ('A', 'N'): 111, ('A', 'D'): 126, ('A', 'C'): 195,
    ('A', 'E'): 107, ('A', 'Q'): 91,  ('A', 'G'): 60,  ('A', 'H'): 86,  ('A', 'I'): 94,
    ('A', 'L'): 96,  ('A', 'K'): 106, ('A', 'M'): 84,  ('A', 'F'): 113, ('A', 'P'): 27,
    ('A', 'S'): 99,  ('A', 'T'): 58,  ('A', 'W'): 148, ('A', 'Y'): 112, ('A', 'V'): 64,

    ('R', 'R'): 0,   ('R', 'N'): 86,  ('R', 'D'): 96,  ('R', 'C'): 180, ('R', 'E'): 54,
    ('R', 'Q'): 43,  ('R', 'G'): 125, ('R', 'H'): 29,  ('R', 'I'): 97,  ('R', 'L'): 102,
    ('R', 'K'): 26,  ('R', 'M'): 91,  ('R', 'F'): 97,  ('R', 'P'): 103, ('R', 'S'): 110,
    ('R', 'T'): 71,  ('R', 'W'): 101, ('R', 'Y'): 77,  ('R', 'V'): 96,

    ('N', 'N'): 0,   ('N', 'D'): 23,  ('N', 'C'): 139, ('N', 'E'): 42,  ('N', 'Q'): 46,
    ('N', 'G'): 80,  ('N', 'H'): 68,  ('N', 'I'): 149, ('N', 'L'): 153, ('N', 'K'): 94,
    ('N', 'M'): 142, ('N', 'F'): 158, ('N', 'P'): 91,  ('N', 'S'): 46,  ('N', 'T'): 65,
    ('N', 'W'): 174, ('N', 'Y'): 143, ('N', 'V'): 133,

    ('D', 'D'): 0,   ('D', 'C'): 154, ('D', 'E'): 45,  ('D', 'Q'): 61,  ('D', 'G'): 94,
    ('D', 'H'): 81,  ('D', 'I'): 168, ('D', 'L'): 172, ('D', 'K'): 101, ('D', 'M'): 160,
    ('D', 'F'): 177, ('D', 'P'): 108, ('D', 'S'): 65,  ('D', 'T'): 85,  ('D', 'W'): 191,
    ('D', 'Y'): 160, ('D', 'V'): 152,

    ('C', 'C'): 0,   ('C', 'E'): 170, ('C', 'Q'): 154, ('C', 'G'): 159, ('C', 'H'): 174,
    ('C', 'I'): 198, ('C', 'L'): 198, ('C', 'K'): 202, ('C', 'M'): 196, ('C', 'F'): 205,
    ('C', 'P'): 169, ('C', 'S'): 112, ('C', 'T'): 149, ('C', 'W'): 215, ('C', 'Y'): 194,
    ('C', 'V'): 192,

    ('E', 'E'): 0,   ('E', 'Q'): 29,  ('E', 'G'): 98, ('E', 'H'): 40,  ('E', 'I'): 134,
    ('E', 'L'): 138, ('E', 'K'): 56,  ('E', 'M'): 126, ('E', 'F'): 140, ('E', 'P'): 93,
    ('E', 'S'): 80,  ('E', 'T'): 65,  ('E', 'W'): 152, ('E', 'Y'): 122, ('E', 'V'): 121,

    ('Q', 'Q'): 0,   ('Q', 'G'): 87,  ('Q', 'H'): 24,  ('Q', 'I'): 109, ('Q', 'L'): 113,
    ('Q', 'K'): 53,  ('Q', 'M'): 101, ('Q', 'F'): 116, ('Q', 'P'): 76,  ('Q', 'S'): 68,
    ('Q', 'T'): 42,  ('Q', 'W'): 130, ('Q', 'Y'): 99,  ('Q', 'V'): 96,

    ('G', 'G'): 0,   ('G', 'H'): 98,  ('G', 'I'): 135, ('G', 'L'): 138, ('G', 'K'): 127,
    ('G', 'M'): 127, ('G', 'F'): 153, ('G', 'P'): 42,  ('G', 'S'): 56,  ('G', 'T'): 59,
    ('G', 'W'): 184, ('G', 'Y'): 147, ('G', 'V'): 109,

    ('H', 'H'): 0,   ('H', 'I'): 94,  ('H', 'L'): 99,  ('H', 'K'): 32,  ('H', 'M'): 87,
    ('H', 'F'): 100, ('H', 'P'): 77,  ('H', 'S'): 89,  ('H', 'T'): 47,  ('H', 'W'): 115,
    ('H', 'Y'): 83,  ('H', 'V'): 84,

    ('I', 'I'): 0,   ('I', 'L'): 5,   ('I', 'K'): 102, ('I', 'M'): 10,  ('I', 'F'): 21,
    ('I', 'P'): 95,  ('I', 'S'): 142, ('I', 'T'): 89,  ('I', 'W'): 61,  ('I', 'Y'): 33,
    ('I', 'V'): 29,

    ('L', 'L'): 0,   ('L', 'K'): 107, ('L', 'M'): 15,  ('L', 'F'): 22,  ('L', 'P'): 98,
    ('L', 'S'): 145, ('L', 'T'): 92,  ('L', 'W'): 61,  ('L', 'Y'): 36,  ('L', 'V'): 32,

    ('K', 'K'): 0,   ('K', 'M'): 95,  ('K', 'F'): 102, ('K', 'P'): 103, ('K', 'S'): 121,
    ('K', 'T'): 78,  ('K', 'W'): 110, ('K', 'Y'): 85,  ('K', 'V'): 97,

    ('M', 'M'): 0,   ('M', 'F'): 28,  ('M', 'P'): 87,  ('M', 'S'): 135, ('M', 'T'): 81,
    ('M', 'W'): 67,  ('M', 'Y'): 36,  ('M', 'V'): 21,

    ('F', 'F'): 0,   ('F', 'P'): 114, ('F', 'S'): 155, ('F', 'T'): 103, ('F', 'W'): 40,
    ('F', 'Y'): 22,  ('F', 'V'): 50,

    ('P', 'P'): 0,   ('P', 'S'): 74,  ('P', 'T'): 38,  ('P', 'W'): 147, ('P', 'Y'): 110,
    ('P', 'V'): 68,

    ('S', 'S'): 0,   ('S', 'T'): 58,  ('S', 'W'): 177, ('S', 'Y'): 144, ('S', 'V'): 124,

    ('T', 'T'): 0,   ('T', 'W'): 128, ('T', 'Y'): 92,  ('T', 'V'): 69,

    ('W', 'W'): 0,   ('W', 'Y'): 37,  ('W', 'V'): 88,

    ('Y', 'Y'): 0,   ('Y', 'V'): 55,

    ('V', 'V'): 0
}

# Pemetaan Kode Asam Amino 3-Huruf ke 1-Huruf
AA_3TO1 = {
    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C',
    'GLU': 'E', 'GLN': 'Q', 'GLY': 'G', 'HIS': 'H', 'ILE': 'I',
    'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P',
    'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V'
}


def parse_snpeff_amino_acid_change(effect_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Mengekstrak asam amino asal dan mutan dari format SnpEff/HGVS p.
    Contoh: 'p.Asn501Tyr' -> ('N', 'Y')
    """
    if not effect_str:
        return None, None
        
    match = re.search(r'p\.([A-Z][a-z]{2})\d+([A-Z][a-z]{2})', effect_str)
    if match:
        aa1_3, aa2_3 = match.group(1).upper(), match.group(2).upper()
        aa1 = AA_3TO1.get(aa1_3)
        aa2 = AA_3TO1.get(aa2_3)
        return aa1, aa2
    return None, None



def get_grantham_score(
    aa1: Optional[str],
    aa2: Optional[str]
) -> Optional[int]:
    """
    Mengembalikan skor jika pasangan input tersedia dalam matriks.

    None berarti informasi tidak tersedia atau tidak dikenali.
    Angka 0 hanya digunakan jika memang tercatat dalam matriks.
    """
    if not aa1 or not aa2:
        return None

    aa1 = aa1.upper()
    aa2 = aa2.upper()

    return GRANTHAM_MATRIX.get(
        (aa1, aa2),
        GRANTHAM_MATRIX.get((aa2, aa1))
    )


def is_in_iedb_epitope(pos: int, epitope_ranges: List[Tuple[int, int]]) -> bool:
    """
    Memeriksa apakah koordinat mutasi (POS) berada di dalam salah satu
    rentang wilayah epitope IEDB yang dipetakan.
    """
    for start, end in epitope_ranges:
        if start <= pos <= end:
            return True
    return False


def calculate_risk_level(is_in_epitope: bool, grantham_score: int) -> str:
    """
    Menentukan batas tingkat risiko (risk_level) sesuai aturan SKPL:
    - OUTSIDE_EPITOPE: Di luar rentang koordinat epitope IEDB.
    - HIGH: Di dalam epitope DAN Grantham > 100.
    - MODERATE: Di dalam epitope DAN 51 <= Grantham <= 100.
    - LOW: Di dalam epitope DAN (1 <= Grantham <= 50 atau mutasi sinonim/G=0).
    """
    if not is_in_epitope:
        return "OUTSIDE_EPITOPE"
    
    if grantham_score > 100:
        return "HIGH"
    elif 51 <= grantham_score <= 100:
        return "MODERATE"
    else:
        return "LOW"



if __name__ == "__main__":
    # Uji cepat: python -m utils.grantham
    regions = [(22500, 23500)]
    aa_ref, aa_alt = parse_snpeff_amino_acid_change("S: p.Asn501Tyr (missense)")
    score = get_grantham_score(aa_ref, aa_alt)
    print(f"Asn501Tyr: Grantham={score} (harus 143), Risk={calculate_risk_level(is_in_iedb_epitope(23063, regions), score)} (harus HIGH)")
