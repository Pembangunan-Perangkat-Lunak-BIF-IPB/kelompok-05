import csv
import gzip
import re
from typing import Optional
from fastapi import HTTPException, status


def _extract_fastq_read_id(header_line: str) -> str:
    """Ekstraksi Base Read ID secara fleksibel dari header FASTQ.
    
    Mendukung format Casava lama (/1, /2), SRA (.1, .2), Casava 1.8+ (dipisahkan spasi),
    serta konvensi penamaan _1/_2.
    """
    if not header_line:
        return ""
    clean_line = header_line.strip().lstrip('@')
    # Ambil elemen pertama sebelum spasi atau tab (menangani format Illumina modern)
    base_id = clean_line.split()[0]
    # Hapus penanda read pair di akhir ID jika ada (/1, /2, _1, _2, .1, .2)
    base_id = re.sub(r'[/._][12]$', '', base_id)
    return base_id


def validate_fasta_single_contig(fasta_path: str, allow_multi_contig: bool = False) -> int:
    """Validasi Lapis 2: Memastikan berkas FASTA valid dan menghitung total panjang sekuens genom.
    
    Toleran terhadap baris kosong, whitespace ekstra, dan perbedaan karakter encoding.
    """
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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Validasi Lapis 2 Gagal: Berkas FASTA tidak memiliki header contig (memulai dengan '>')."
        )
        
    if not allow_multi_contig and contig_count > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validasi Lapis 2 Gagal: Berkas FASTA memiliki {contig_count} contig. Diperlukan tepat 1 contig genom acuan."
        )
        
    return sequence_length


def validate_fastq_pairs(r1_path: str, r2_path: str):
    """Validasi Lapis 2: Memastikan header FASTQ R1 dan R2 cocok secara fleksibel."""
    def open_file(path):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore") if path.endswith(".gz") else open(path, "r", encoding="utf-8", errors="ignore")

    with open_file(r1_path) as f1, open_file(r2_path) as f2:
        for line_num, (l1, l2) in enumerate(zip(f1, f2)):
            if line_num % 4 == 0:  # Baris header FASTQ[cite: 14]
                id1 = _extract_fastq_read_id(l1)
                id2 = _extract_fastq_read_id(l2)
                
                if id1 != id2:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Validasi Lapis 2 Gagal: Header FASTQ R1 ('{id1}') dan R2 ('{id2}') "
                            f"tidak cocok pada baris {line_num + 1}."
                        )
                    )


def _get_field_val(row_dict: dict, candidate_names: list, default: Optional[str] = None) -> Optional[str]:
    """Mencari nilai kolom berdasarkan daftar variasi nama header (case-insensitive & auto-trimming)."""
    norm_dict = {str(k).strip().lower(): str(v).strip() for k, v in row_dict.items() if k is not None}
    for cand in candidate_names:
        if cand.lower() in norm_dict:
            return norm_dict[cand.lower()]
    return default


def validate_iedb_coordinates(iedb_path: str, max_genome_len: int):
    """Validasi Lapis 3: Memastikan koordinat epitope IEDB berada dalam rentang genom FASTA[cite: 14].
    
    Fleksibel terhadap variasi nama kolom (start_pos, start, seq_start) dan pemisah kolom (koma, tab, titik koma).
    """
    start_candidates = ["start_pos", "start", "start_position", "seq_start", "epitope_start", "pos_start"]
    end_candidates = ["end_pos", "end", "end_position", "seq_end", "epitope_end", "pos_end"]

    with open(iedb_path, "r", encoding="utf-8", errors="ignore") as f:
        sample = f.read(2048)
        f.seek(0)
        
        # Deteksi otomatis pemisah (delimiter) CSV/TSV/Semicolon
        delimiter = "\t" if "\t" in sample else (";" if ";" in sample else ",")
        reader = csv.DictReader(f, delimiter=delimiter)
        
        for row_num, row in enumerate(reader, start=2):
            if not any(row.values()):
                continue

            raw_start = _get_field_val(row, start_candidates)
            raw_end = _get_field_val(row, end_candidates)

            if raw_start is None or raw_end is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validasi Lapis 3 Gagal: Baris {row_num} tidak memiliki kolom koordinat 'start' atau 'end' yang dikenal."
                )

            try:
                start = int(raw_start)
                end = int(raw_end)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validasi Lapis 3 Gagal: Baris {row_num} nilai koordinat [{raw_start}-{raw_end}] bukan integer yang valid."
                )

            if start < 1 or end > max_genome_len or start > end:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validasi Lapis 3 Gagal: Baris {row_num} koordinat epitope [{start}-{end}] di luar rentang genom (1-{max_genome_len} bp)."[cite: 14]
                )