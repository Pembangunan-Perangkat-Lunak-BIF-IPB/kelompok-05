import gzip
import re
from itertools import zip_longest

from fastapi import HTTPException, status

from utils.iedb import IEDBFormatError, read_iedb_rows


def _err(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _extract_fastq_read_id(header_line: str) -> str:
    """Ekstraksi Base Read ID secara fleksibel dari header FASTQ.

    Mendukung format Casava lama (/1, /2), SRA (.1, .2), Casava 1.8+ (dipisahkan spasi),
    serta konvensi penamaan _1/_2.
    """
    if not header_line:
        return ""
    clean_line = header_line.strip().lstrip('@')
    if not clean_line:
        return ""
    base_id = clean_line.split()[0]
    base_id = re.sub(r'[/._][12]$', '', base_id)
    return base_id


def validate_fasta_single_contig(fasta_path: str, allow_multi_contig: bool = False) -> int:
    """Validasi Lapis 2: Memastikan berkas FASTA valid dan menghitung total panjang sekuens genom."""
    contig_count = 0
    sequence_length = 0

    with open(fasta_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                contig_count += 1
            else:
                sequence_length += len(line)

    if contig_count == 0:
        raise _err("Validasi Lapis 2 Gagal: Berkas FASTA tidak memiliki header contig (memulai dengan '>').")

    if not allow_multi_contig and contig_count > 1:
        raise _err(f"Validasi Lapis 2 Gagal: Berkas FASTA memiliki {contig_count} contig. Diperlukan tepat 1 contig genom acuan.")

    if sequence_length == 0:
        raise _err("Validasi Lapis 2 Gagal: Berkas FASTA tidak berisi sekuens.")

    return sequence_length


def validate_fastq_pairs(r1_path: str, r2_path: str):
    """Validasi Lapis 2: Memastikan header FASTQ R1 dan R2 cocok dan jumlah read sama."""
    def open_file(path):
        if path.endswith(".gz"):
            return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
        return open(path, "r", encoding="utf-8", errors="ignore")

    line_count = 0
    with open_file(r1_path) as f1, open_file(r2_path) as f2:
        for line_num, (l1, l2) in enumerate(zip_longest(f1, f2)):
            # Salah satu berkas habis lebih dulu -> jumlah read tidak sama
            if l1 is None or l2 is None:
                remaining = l2 if l1 is None else l1
                if remaining.strip():
                    raise _err("Validasi Lapis 2 Gagal: Jumlah baris FASTQ R1 dan R2 berbeda (read tidak berpasangan).")
                continue

            line_count += 1
            if line_num % 4 == 0:  # Baris header FASTQ
                if not l1.strip() and not l2.strip():
                    continue
                if not l1.startswith("@") or not l2.startswith("@"):
                    raise _err(f"Validasi Lapis 2 Gagal: Baris {line_num + 1} bukan header FASTQ (harus diawali '@').")

                id1 = _extract_fastq_read_id(l1)
                id2 = _extract_fastq_read_id(l2)
                if id1 != id2:
                    raise _err(
                        f"Validasi Lapis 2 Gagal: Header FASTQ R1 ('{id1}') dan R2 ('{id2}') "
                        f"tidak cocok pada baris {line_num + 1}."
                    )

    if line_count == 0:
        raise _err("Validasi Lapis 2 Gagal: Berkas FASTQ kosong.")


def validate_iedb_coordinates(iedb_path: str, max_genome_len: int):
    """Validasi Lapis 3: Memastikan koordinat epitope IEDB berada dalam rentang genom FASTA."""
    try:
        rows = read_iedb_rows(iedb_path)
    except IEDBFormatError as e:
        raise _err(f"Validasi Lapis 3 Gagal: {e}")

    if not rows:
        raise _err("Validasi Lapis 3 Gagal: Berkas IEDB tidak berisi data epitope.")

    for row_num, start, end in rows:
        if start < 1 or end > max_genome_len or start > end:
            raise _err(
                f"Validasi Lapis 3 Gagal: Baris {row_num} koordinat epitope [{start}-{end}] "
                f"di luar rentang genom (1-{max_genome_len} bp)."
            )
