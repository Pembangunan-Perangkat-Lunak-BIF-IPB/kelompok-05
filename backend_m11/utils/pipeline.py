"""
utils/pipeline.py
Eksekusi pipeline 4 stasiun di latar belakang.

Stasiun 1  QC (fastp)
Stasiun 2  Read mapping (bwa-mem2 + samtools)
Stasiun 3  Variant calling (bcftools, ploidy 1 untuk virus)
Stasiun 4  Quality filtering dan anotasi SnpEff
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import signal
import time
from contextvars import ContextVar
import traceback
from datetime import datetime, timezone
import hashlib
from sqlalchemy.orm import Session

import models
from config import UPLOAD_DIR, PIPELINE_THREADS
from database import SessionLocal
from utils.genomics import calculate_tstv_ratio
from utils.snpeff import anotasi as anotasi_snpeff
from utils.vcf_parser import filter_vcf, parse_and_store_vcf

REQUIRED_TOOLS = ["fastp", "bwa-mem2", "samtools", "bcftools"]


class PipelineError(Exception):
    pass


class PipelineCancelled(PipelineError):
    pass


_ACTIVE_RUN_ID = ContextVar("varescape_active_run_id", default=None)


def cancellation_path(run_id):
    # run_id berasal dari DB; endpoint pembatalan memeriksa kepemilikan.
    return UPLOAD_DIR / run_id / ".cancel_requested"


def check_cancelled(run_id=None):
    current = run_id or _ACTIVE_RUN_ID.get()
    if current and cancellation_path(current).is_file():
        raise PipelineCancelled("Pembatalan diminta oleh pengguna.")


def _stop_group(proc):
    """Hentikan bash beserta pipeline anaknya, bukan hanya shell induknya."""
    if proc.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    else:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _now():
    return datetime.now(timezone.utc)


def _q(path) -> str:
    """Quote path agar aman untuk shell (spasi, karakter khusus)."""
    return shlex.quote(str(path))


def log_pipeline(db: Session, run_id: str, station_number: int, log_level: str, message: str):
    """Menyimpan log ke tabel pipeline_logs (dibaca FE lewat endpoint status) dan mencetak ke terminal."""
    print(f"[{run_id}][Stasiun {station_number}][{log_level}] {message}")
    try:
        db.add(models.PipelineLog(
            run_id=run_id,
            station_number=station_number,
            log_level=log_level,
            message=message,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Gagal menyimpan log pipeline: {e}")


def execute_cmd(command: str) -> str:
    """Jalankan perintah dan polling pembatalan tiap 0,5 detik.

    Proses bash berjalan dalam process group sendiri (WSL/POSIX), sehingga
    membatalkan BWA/SAMtools/BCFtools dalam pipeline shell sekaligus.
    """
    check_cancelled()
    proc = subprocess.Popen(
        ["bash", "-c", f"set -o pipefail; {command}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=(os.name == "posix"),
    )
    try:
        while True:
            try:
                stdout, stderr = proc.communicate(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                check_cancelled()
        check_cancelled()
        if proc.returncode != 0:
            err = (stderr or stdout or "").strip()
            raise PipelineError(f"Perintah gagal: {command}\\n{err[-1500:]}")
        return stdout or stderr
    except BaseException:
        _stop_group(proc)
        proc.communicate()
        raise


def check_tools():
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing:
        raise PipelineError(
            f"Tool tidak ditemukan di PATH: {', '.join(missing)}. "
            "Pastikan uvicorn dijalankan dari WSL di environment (conda) yang berisi tool tersebut."
        )


def _get_file(db: Session, run_id: str, file_type: models.FileType):
    return db.query(models.UploadedFile).filter(
        models.UploadedFile.run_id == run_id,
        models.UploadedFile.file_type == file_type,
    ).first()


def _fasta_length(path: str) -> int:
    total = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.startswith(">"):
                total += len(line.strip())
    return total


def record_run_metadata(run, fasta_path):
    """Catat identitas referensi dan versi tool untuk reproducibility."""

    run.reference_accession = "NC_045512.2"

    sha256 = hashlib.sha256()

    with open(fasta_path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha256.update(chunk)

    run.reference_sha256 = sha256.hexdigest()

    commands = {
        "fastp": ["fastp", "--version"],
        "bwa-mem2": ["bwa-mem2", "version"],
        "samtools": ["samtools", "--version"],
        "bcftools": ["bcftools", "--version"],
        "snpeff": ["snpEff", "-version"],
    }

    versions = {}

    for tool, command in commands.items():
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            output = (
                (proc.stdout or "") + "\n" + (proc.stderr or "")
            ).strip()

            versions[tool] = (
                output.splitlines()[0][:300]
                if output and proc.returncode == 0
                else None
            )

        except (OSError, subprocess.TimeoutExpired):
            versions[tool] = None

    run.tool_versions_json = json.dumps(
        versions,
        ensure_ascii=False,
    )

def run_analysis_pipeline(run_id: str):
    db: Session = SessionLocal()
    station = 0
    context_token = _ACTIVE_RUN_ID.set(run_id)
    try:
        run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
        if not run:
            print(f"Run ID {run_id} tidak ditemukan.")
            return

        check_cancelled(run_id)
        run.status = models.RunStatus.RUNNING
        if run.started_at is None:
            run.started_at = _now()
        db.commit()

        run_folder = UPLOAD_DIR / run_id
        run_folder.mkdir(parents=True, exist_ok=True)

        f_r1 = _get_file(db, run_id, models.FileType.FASTQ_R1)
        f_r2 = _get_file(db, run_id, models.FileType.FASTQ_R2)
        f_fa = _get_file(db, run_id, models.FileType.FASTA)

        if not f_r1:
            raise PipelineError("Berkas FASTQ R1 tidak ditemukan di database.")

        if not f_fa:
            raise PipelineError("Referensi sistem NC_045512.2 tidak tercatat pada analisis.")

        r1_path = f_r1.file_path
        r2_path = f_r2.file_path if f_r2 else None
        fasta_path = f_fa.file_path

        # Validasi keberadaan file wajib
        for p in [r1_path, fasta_path]:
            if not os.path.isfile(p):
                raise PipelineError(f"Berkas tidak ditemukan di disk: {p}")

        # Validasi R2 hanya jika digunakan
        if r2_path is not None and not os.path.isfile(r2_path):
            raise PipelineError(f"Berkas FASTQ R2 tidak ditemukan: {r2_path}")
        check_tools()
        record_run_metadata(run, fasta_path)
        db.commit()

        clean_r1 = run_folder / "clean_R1.fq"
        clean_r2 = run_folder / "clean_R2.fq"
        aligned_bam = run_folder / "aligned.bam"
        raw_vcf = run_folder / "variants.vcf"
        filtered_vcf = run_folder / "variants.filtered.vcf"
        annotated_vcf = run_folder / "variants.ann.vcf"
        if annotated_vcf.exists():
            annotated_vcf.unlink()  # jangan pakai sisa anotasi dari percobaan sebelumnya

        # --- STASIUN 1: Quality Control (fastp) ---
        station = 1
        log_pipeline(db, run_id, 1, "INFO", "Memulai Stasiun 1: Quality Control dengan fastp...")
        fastp_json = run_folder / "fastp.json"
        report = f"-h {_q(run_folder / 'fastp.html')} -j {_q(fastp_json)} -w {PIPELINE_THREADS}"
        if r2_path:
            execute_cmd(f"fastp -i {_q(r1_path)} -I {_q(r2_path)} -o {_q(clean_r1)} -O {_q(clean_r2)} {report}")
        else:
            execute_cmd(f"fastp -i {_q(r1_path)} -o {_q(clean_r1)} {report}")

        try:
            with open(fastp_json, "r") as f:
                report_data = json.load(f)
                summary = report_data.get("summary", {})
                before = summary.get("before_filtering", {})
                after = summary.get("after_filtering", {})
                run.q20_before = round(before["q20_rate"] * 100, 2) if before.get("q20_rate") is not None else None
                run.q30_before = round(before["q30_rate"] * 100, 2) if before.get("q30_rate") is not None else None
                run.reads_before = before.get("total_reads")
                run.reads_after = after.get("total_reads")
                adapter = report_data.get("adapter_cutting", {})
                trimmed = adapter.get("adapter_trimmed_reads")

                if trimmed is not None and run.reads_before:
                    run.adapter_trimmed_pct = round(
                        100 * trimmed / run.reads_before, 2
                    )
                else:
                    run.adapter_trimmed_pct = None
                if run.reads_before:
                    run.passed_reads_pct = round(100 * run.reads_after / run.reads_before, 2) if run.reads_after is not None else None
            run.q20_rate = round(after.get("q20_rate", 0.0) * 100, 2)
            run.q30_rate = round(after.get("q30_rate", 0.0) * 100, 2)
            db.commit()
        except Exception as e:
            db.rollback()
            log_pipeline(db, run_id, 1, "WARNING", f"Gagal membaca fastp.json: {e}")
        log_pipeline(db, run_id, 1, "SUCCESS", "Stasiun 1 selesai: pembersihan read FASTQ berhasil.")

        # --- STASIUN 2: Read Mapping (bwa-mem2 & samtools) ---
        station = 2
        log_pipeline(db, run_id, 2, "INFO", "Memulai Stasiun 2: pemetaan read dengan bwa-mem2...")
        if not os.path.exists(f"{fasta_path}.bwt.2bit.64"):
            execute_cmd(f"bwa-mem2 index {_q(fasta_path)}")
        if not os.path.exists(f"{fasta_path}.fai"):
            execute_cmd(f"samtools faidx {_q(fasta_path)}")

        reads = f"{_q(clean_r1)} {_q(clean_r2)}" if r2_path else _q(clean_r1)
        execute_cmd(
            f"bwa-mem2 mem -t {PIPELINE_THREADS} {_q(fasta_path)} {reads} "
            f"| samtools sort -@ 2 -o {_q(aligned_bam)} -"
        )
        execute_cmd(f"samtools index {_q(aligned_bam)}")

        # Statistik coverage genom SARS-CoV-2
        # Dihitung setelah BAM berhasil dibuat dan diindeks.
        try:
            depth_output = execute_cmd(
                f"samtools depth -aa "
                f"-q {int(run.min_base_quality)} "
                f"-Q {int(run.min_mq)} "
                f"{_q(aligned_bam)}"
            )

            total_positions = 0
            covered_1x = 0
            covered_30x = 0

            for line in depth_output.splitlines():
                cols = line.split("\t")
                if len(cols) < 3:
                    continue

                depth = int(cols[2])
                total_positions += 1

                if depth >= 1:
                    covered_1x += 1

                if depth >= 30:
                    covered_30x += 1

            reference_length = _fasta_length(fasta_path)

            if total_positions != reference_length:
                raise ValueError(
                    "Jumlah posisi depth tidak sesuai "
                    "dengan panjang genom referensi."
                )

            genome_coverage_pct = round(
                100 * covered_1x / reference_length, 2
            )

            genome_coverage_30x_pct = round(
                100 * covered_30x / reference_length, 2
            )

            coverage_metrics = {
                "reference_length": reference_length,
                "covered_positions_1x": covered_1x,
                "covered_positions_30x": covered_30x,
                "genome_coverage_pct": genome_coverage_pct,
                "genome_coverage_30x_pct": genome_coverage_30x_pct,
                "min_base_quality": int(run.min_base_quality),
                "min_mapping_quality": int(run.min_mq),
            }

            coverage_path = run_folder / "coverage_metrics.json"

            with open(coverage_path, "w", encoding="utf-8") as f:
                json.dump(coverage_metrics, f, indent=2)

            log_pipeline(
                db, run_id, 2, "INFO",
                f"Genome coverage >=1x: {genome_coverage_pct}%; "
                f"coverage >=30x: {genome_coverage_30x_pct}%."
            )

        except Exception as exc:
            log_pipeline(
                db, run_id, 2, "WARNING",
                f"Statistik genome coverage tidak tersedia: {exc}"
            )

        try:
            flagstat = execute_cmd(
                f"samtools flagstat {_q(aligned_bam)}"
            )
            

            # Simpan output asli SAMtools flagstat
            (run_folder / "alignment.flagstat.txt").write_text(
                flagstat,
                encoding="utf-8"
            )

            # Hitung jumlah primary reads yang tidak terpetakan
            primary_match = re.search(
                r"(?m)^\s*(\d+)\s*\+\s*(\d+)\s+primary\s*$",
                flagstat
            )

            primary_mapped_match = re.search(
                r"(?m)^\s*(\d+)\s*\+\s*(\d+)\s+primary mapped\b",
                flagstat
            )

            if primary_match and primary_mapped_match:
                total_primary = (
                    int(primary_match.group(1))
                    + int(primary_match.group(2))
                )

                mapped_primary = (
                    int(primary_mapped_match.group(1))
                    + int(primary_mapped_match.group(2))
                )

                run.unmapped_reads = total_primary - mapped_primary

                if run.unmapped_reads < 0:
                    raise ValueError(
                        "Statistik SAMtools tidak konsisten: "
                        "primary mapped melebihi total primary."
                    )
            else:
                run.unmapped_reads = None
                log_pipeline(
                    db, run_id, 2, "WARNING",
                    "Tidak dapat membaca primary reads "
                    "dan primary mapped dari SAMtools flagstat."
                )


            # Persentase alignment records yang terpetakan
            mapped_match = re.search(
                r"(?m)^\s*\d+\s+\+\s+\d+\s+mapped\s+\((\d+(?:\.\d+)?)%",
                flagstat
            )

            run.mapping_rate = (
                float(mapped_match.group(1))
                if mapped_match
                else None
            )
            coverage_text = execute_cmd(
                f"samtools coverage {_q(aligned_bam)}"
            )

            (run_folder / "alignment.coverage.tsv").write_text(
                coverage_text,
                encoding="utf-8"
            )

            cov_lines = [
                line
                for line in coverage_text.strip().splitlines()
                if line
            ]
            if len(cov_lines) >= 2:
                header = cov_lines[0].lstrip("#").split("\t")
                idx = header.index("meandepth") if "meandepth" in header else 6
                depths = [float(l.split("\t")[idx]) for l in cov_lines[1:]]
                run.mean_depth = round(sum(depths) / len(depths), 2)
            db.commit()
        except Exception as e:
            db.rollback()
            log_pipeline(db, run_id, 2, "WARNING", f"Gagal menghitung statistik BAM: {e}")
        log_pipeline(db, run_id, 2, "SUCCESS", "Stasiun 2 selesai: alignment dan indexing BAM berhasil.")

        # --- STASIUN 3: Variant Calling (bcftools) ---
        station = 3
        log_pipeline(db, run_id, 3, "INFO", "Memulai Stasiun 3: variant calling dengan bcftools...")
        execute_cmd(
            f"bcftools mpileup -f {_q(fasta_path)} "
            f"-q {int(run.min_mq)} "
            f"-Q {int(run.min_base_quality)} "
            f"-d {int(run.max_depth)} "
            f"-a FORMAT/AD,FORMAT/DP "
            f"-Ou {_q(aligned_bam)} "
            f"| bcftools call --ploidy 1 -mv -Ov -o {_q(raw_vcf)}"
        )
        try:
            stats_text = execute_cmd(
                f"bcftools stats {_q(raw_vcf)}"
            )

            (run_folder / "variants.stats.txt").write_text(
                stats_text,
                encoding="utf-8"
            )

        except Exception as exc:
            log_pipeline(
                db,
                run_id,
                3,
                "WARNING",
                f"Statistik tambahan BCFtools tidak tersedia: {exc}"
            )
        from utils.genomics import calculate_tstv_ratio
        raw_variants = []
        with open(raw_vcf, encoding="utf-8") as rf:
            for raw_line in rf:
                if raw_line.startswith("#"):
                    continue
                cols = raw_line.rstrip("\n").split("\t")
                if len(cols) >= 5:
                    raw_variants.append({"ref":cols[3],"alt":cols[4]})
        run.raw_variant_count = len(raw_variants)

        run.raw_snp_count = sum(
            len(v["ref"]) == 1 and len(v["alt"]) == 1
            for v in raw_variants
        )

        run.raw_indel_count = sum(
            len(v["ref"]) != len(v["alt"])
            for v in raw_variants
        )

                # Ts/Tv dihitung dari kandidat pada raw VCF,
        # konsisten dengan statistik Stasiun 3.
        ts_count, tv_count, raw_tstv = calculate_tstv_ratio(
            raw_variants
        )

        run.tstv_ratio = raw_tstv
        db.commit()
        log_pipeline(db, run_id, 3, "SUCCESS", "Stasiun 3 selesai: berkas VCF varian berhasil dibuat.")

        # --- STASIUN 4: Quality Filtering dan Anotasi SnpEff ---
        station = 4
        log_pipeline(db, run_id, 4, "INFO", "Memulai Stasiun 4: filtering dan anotasi...")
        
        thresholds = {
            "dp": run.min_dp,
            "qual": run.min_qual,
            "af": run.min_af,
        }

        audit_rows = []

        total, passed = filter_vcf(
            str(raw_vcf),
            str(filtered_vcf),
            thresholds=thresholds,
            audit_rows=audit_rows,
        )

        # Hapus audit lama hanya untuk run ini
        db.query(models.VariantFilterResult).filter(
            models.VariantFilterResult.run_id == run_id
        ).delete(synchronize_session=False)

        # Simpan semua kandidat, termasuk yang gagal filter
        for item in audit_rows:
            db.add(
                models.VariantFilterResult(
                    run_id=run_id,
                    **item,
                )
            )

        run.passed_variant_count = passed
        run.filtered_variant_count = total - passed

        db.commit()

        run.passed_variant_count = passed
        run.filtered_variant_count = total-passed
        db.commit()
        log_pipeline(db, run_id, 4, "INFO",
                     f"Filtering: {passed} dari {total} varian dipertahankan.")

        if passed == 0:
            # Nol PASS adalah hasil filtering yang valid, bukan kegagalan SnpEff.
            # Jangan mengklaim annotated COMPLETED apabila tidak ada record.
            run.annotated_variant_count = 0
            run.annotation_status = models.AnnotationStatus.SKIPPED
            db.commit()
            log_pipeline(
                db, run_id, 4, "WARNING",
                "Tidak ada varian PASS; anotasi SnpEff dilewati (SKIPPED). "
                "Hasil 0 PASS tetap sah dan file dari stasiun sebelumnya tersedia."
            )
            stored = annotated = 0
        else:
            check_cancelled(run_id)
            ok_ann, vcf_to_store, ringkas = anotasi_snpeff(
                str(filtered_vcf), str(annotated_vcf),
                catat=lambda level, pesan: log_pipeline(db, run_id, 4, level, pesan),
                panjang_referensi=_fasta_length(fasta_path),
            )
            check_cancelled(run_id)
            if not ok_ann:
                run.annotation_status = models.AnnotationStatus.FAILED
                db.commit()
                raise PipelineError(f"Anotasi belum berhasil: {ringkas}")

            stored, annotated, _ = parse_and_store_vcf(
                str(vcf_to_store), run_id, db, reference_path=fasta_path
            )
            # Anotasi sukses hanya untuk berkas/record yang benar-benar teranotasi.
            run.annotated_variant_count = annotated
            if annotated > 0:
                run.annotation_status = models.AnnotationStatus.COMPLETED
            else:
                run.annotation_status = models.AnnotationStatus.FAILED
            db.commit()
            if annotated == 0:
                raise PipelineError("SnpEff tidak menghasilkan anotasi pada varian PASS.")

        run = db.query(models.AnalysisRun).filter(
            models.AnalysisRun.run_id == run_id
        ).first()

        check_cancelled(run_id)
        run.status = models.RunStatus.COMPLETED
        run.completed_at = _now()
        db.commit()
        log_pipeline(db, run_id, 4, "SUCCESS",
                     f"Pipeline selesai: {stored} varian disimpan, {annotated} teranotasi SnpEff.")

    except PipelineCancelled as exc:
        db.rollback()
        try:
            run = db.query(models.AnalysisRun).filter(
                models.AnalysisRun.run_id == run_id
            ).first()
            if run and run.status not in (
                models.RunStatus.COMPLETED, models.RunStatus.FAILED
            ):
                run.status = models.RunStatus.CANCELLED
                run.completed_at = _now()
                db.commit()
        except Exception:
            db.rollback()
            traceback.print_exc()
        log_pipeline(db, run_id, station or 1, "WARNING",
                     f"Pipeline dibatalkan: {exc}")
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        try:
            run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
            if run:
                run.status = models.RunStatus.FAILED
                run.completed_at = _now()
                db.commit()
        except Exception:
            db.rollback()
        log_pipeline(db, run_id, station or 1, "ERROR", f"Pipeline terhenti: {e}"[:4000])
    finally:
        _ACTIVE_RUN_ID.reset(context_token)
        db.close()
