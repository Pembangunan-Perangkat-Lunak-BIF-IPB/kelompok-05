import csv
import gzip
from fastapi import HTTPException, status

def validate_fasta_single_contig(fasta_path: str) -> int:
    """Validasi Lapis 2: Memastikan FASTA hanya punya 1 contig header dan mengembalikan panjang genom."""
    contig_count = 0
    sequence_length = 0
    
    with open(fasta_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                contig_count += 1
            else:
                sequence_length += len(line)
                
    if contig_count != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validasi Lapis 2 Gagal: Berkas FASTA harus memiliki tepat 1 contig header (Ditemukan: {contig_count})."
        )
    return sequence_length

def validate_fastq_pairs(r1_path: str, r2_path: str):
    """Validasi Lapis 2: Memastikan header FASTQ R1 dan R2 cocok."""
    def open_file(path):
        return gzip.open(path, "rt", encoding="utf-8") if path.endswith(".gz") else open(path, "r", encoding="utf-8")

    with open_file(r1_path) as f1, open_file(r2_path) as f2:
        for line_num, (l1, l2) in enumerate(zip(f1, f2)):
            if line_num % 4 == 0:  # Baris header FASTQ
                id1 = l1.split()[0]
                id2 = l2.split()[0]
                if id1 != id2:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Validasi Lapis 2 Gagal: Header FASTQ R1 dan R2 tidak cocok pada baris {line_num + 1}."
                    )

def validate_iedb_coordinates(iedb_path: str, max_genome_len: int):
    """Validasi Lapis 3: Memastikan koordinat epitope IEDB berada dalam rentang genom FASTA."""
    with open(iedb_path, "r", encoding="utf-8") as f:
        sample = f.read(1024)
        f.seek(0)
        delimiter = "\t" if "\t" in sample else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        
        for row_num, row in enumerate(reader, start=2):
            start = int(row.get("start_pos", 0))
            end = int(row.get("end_pos", 0))
            
            if start < 1 or end > max_genome_len or start > end:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validasi Lapis 3 Gagal: Baris {row_num} koordinat epitope [{start}-{end}] di luar rentang genom (1-{max_genome_len} bp)."
                )