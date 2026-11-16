import gzip
import re
from itertools import zip_longest

from fastapi import HTTPException, status
from contextlib import ExitStack


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
    invalid = set()

    with open(fasta_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                contig_count += 1
            else:
                sequence_length += len(line)
                invalid.update(set(line.upper()) - set("ACGTURYKMSWBDHVN-*"))

    if contig_count == 0:
        raise _err("Validasi Lapis 2 Gagal: Berkas FASTA tidak memiliki header contig (memulai dengan '>').")

    if not allow_multi_contig and contig_count > 1:
        raise _err(f"Validasi Lapis 2 Gagal: Berkas FASTA memiliki {contig_count} contig. Diperlukan tepat 1 contig genom acuan.")

    if sequence_length == 0:
        raise _err("Validasi Lapis 2 Gagal: Berkas FASTA tidak berisi sekuens.")

    if invalid:
        raise _err("Validasi Lapis 2 Gagal: FASTA berisi karakter non-nukleotida "
                   f"({''.join(sorted(invalid))[:20]}). Gunakan FASTA genom (nukleotida), bukan protein.")

    return sequence_length


def _open_fastq(path):
    if str(path).lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="ascii")
    return open(path, "rt", encoding="ascii")


def _read_fastq_record(stream, label):
    header = stream.readline()

    if not header:
        return None

    sequence = stream.readline()
    separator = stream.readline()
    quality = stream.readline()

    if not sequence or not separator or not quality:
        raise _err(
            f"Validasi Lapis 3 Gagal: record FASTQ {label} tidak lengkap."
        )

    header = header.rstrip("\r\n")
    sequence = sequence.rstrip("\r\n")
    separator = separator.rstrip("\r\n")
    quality = quality.rstrip("\r\n")

    if not header.startswith("@") or len(header) <= 1:
        raise _err(
            f"Validasi Lapis 2 Gagal: header FASTQ {label} tidak valid."
        )

    if not separator.startswith("+"):
        raise _err(
            f"Validasi Lapis 3 Gagal: pemisah '+' FASTQ {label} tidak valid."
        )

    if not sequence:
        raise _err(
            f"Validasi Lapis 3 Gagal: sekuens {label} kosong."
        )

    if len(sequence) != len(quality):
        raise _err(
            f"Validasi Lapis 3 Gagal: panjang sekuens dan quality "
            f"FASTQ {label} berbeda."
        )

    allowed_bases = set("ACGTNRYKMSWBDHVU")
    if not set(sequence.upper()).issubset(allowed_bases):
        raise _err(
            f"Validasi Lapis 3 Gagal: karakter sekuens {label} tidak valid."
        )

    if any(ord(char) < 33 or ord(char) > 126 for char in quality):
        raise _err(
            f"Validasi Lapis 3 Gagal: karakter kualitas {label} "
            "di luar rentang FASTQ yang diperbolehkan."
        )

    return _extract_fastq_read_id(header)


def validate_fastq_pairs(r1_path: str, r2_path=None):
    """
    Validasi penuh struktur FASTQ secara streaming.

    Lapis 2: header dan kecocokan identifier pasangan.
    Lapis 3: record lengkap, sekuens, dan quality string.

    Tidak menilai kecocokan reads dengan genom referensi.
    """
    read_count = 0

    try:
        with ExitStack() as stack:
            r1 = stack.enter_context(_open_fastq(r1_path))
            r2 = (
                stack.enter_context(_open_fastq(r2_path))
                if r2_path else None
            )

            while True:
                id1 = _read_fastq_record(r1, "R1")
                id2 = (
                    _read_fastq_record(r2, "R2")
                    if r2 is not None else None
                )

                if id1 is None:
                    if r2 is not None and id2 is not None:
                        raise _err(
                            "Validasi Lapis 2 Gagal: jumlah reads "
                            "R1 dan R2 berbeda."
                        )
                    break

                if r2 is not None:
                    if id2 is None:
                        raise _err(
                            "Validasi Lapis 2 Gagal: jumlah reads "
                            "R1 dan R2 berbeda."
                        )

                    if id1 != id2:
                        raise _err(
                            f"Validasi Lapis 2 Gagal: ID reads "
                            f"R1 ({id1}) dan R2 ({id2}) tidak cocok."
                        )

                read_count += 1

    except HTTPException:
        raise
    except (OSError, EOFError, UnicodeError, ValueError) as exc:
        raise _err(
            f"Validasi Lapis 3 Gagal: berkas FASTQ rusak "
            f"atau tidak dapat dibaca ({exc})."
        ) from exc

    if read_count == 0:
        raise _err("Validasi Lapis 3 Gagal: FASTQ tidak memiliki reads.")

    return {
        "format": "PASS",
        "header": "PASS",
        "sequence_integrity": "PASS",
        "read_count": read_count,
        "paired_end": r2_path is not None,
    }