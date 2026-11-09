"""
utils/iedb.py
Pembaca berkas epitope IEDB yang dipakai bersama oleh validator (Lapis 3) dan parser VCF,
supaya aturan nama kolom & delimiter tidak beda lagi di dua tempat.

Format yang didukung:
- CSV / TSV / titik koma, dengan kolom start & end (nama kolom fleksibel)
- GFF/GFF3 (start di kolom ke-4, end di kolom ke-5)
Koordinat diasumsikan koordinat GENOM (nukleotida), sama dengan POS di VCF.
"""

import csv
from typing import List, Optional, Tuple

START_CANDIDATES = ["start_pos", "start", "start_position", "seq_start", "epitope_start", "pos_start"]
END_CANDIDATES = ["end_pos", "end", "end_position", "seq_end", "epitope_end", "pos_end"]


class IEDBFormatError(ValueError):
    """Dilempar jika isi berkas IEDB tidak bisa dibaca."""


def _get_field_val(row: dict, candidates: List[str]) -> Optional[str]:
    """Mencari nilai kolom dari beberapa variasi nama header (case-insensitive). String kosong dianggap tidak ada."""
    norm = {}
    for k, v in row.items():
        if k is None:
            continue
        norm[str(k).strip().lower()] = "" if v is None else str(v).strip()
    for cand in candidates:
        val = norm.get(cand.lower())
        if val:
            return val
    return None


def _is_gff(path: str) -> bool:
    return path.lower().endswith((".gff", ".gff3"))


def read_iedb_rows(path: str) -> List[Tuple[int, int, int]]:
    """Mengembalikan list (nomor_baris, start, end). Melempar IEDBFormatError jika format salah."""
    rows: List[Tuple[int, int, int]] = []

    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        if _is_gff(path):
            for n, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                cols = line.split("\t")
                if len(cols) < 5:
                    raise IEDBFormatError(f"Baris {n}: format GFF harus memiliki minimal 5 kolom (start di kolom 4, end di kolom 5).")
                try:
                    rows.append((n, int(cols[3]), int(cols[4])))
                except ValueError:
                    raise IEDBFormatError(f"Baris {n}: nilai koordinat [{cols[3]}-{cols[4]}] bukan integer yang valid.")
            return rows

        sample = f.read(2048)
        f.seek(0)
        delimiter = "\t" if "\t" in sample else (";" if ";" in sample else ",")
        reader = csv.DictReader(f, delimiter=delimiter)

        for n, row in enumerate(reader, start=2):
            if not any(isinstance(v, str) and v.strip() for v in row.values()):
                continue

            raw_start = _get_field_val(row, START_CANDIDATES)
            raw_end = _get_field_val(row, END_CANDIDATES)
            if raw_start is None or raw_end is None:
                raise IEDBFormatError(f"Baris {n} tidak memiliki kolom koordinat 'start' atau 'end' yang dikenal.")

            try:
                rows.append((n, int(raw_start), int(raw_end)))
            except ValueError:
                raise IEDBFormatError(f"Baris {n}: nilai koordinat [{raw_start}-{raw_end}] bukan integer yang valid.")

    return rows


def load_iedb_regions(path: str) -> List[Tuple[int, int]]:
    """Mengembalikan list (start, end) untuk pemetaan epitope."""
    return [(start, end) for _, start, end in read_iedb_rows(path)]
