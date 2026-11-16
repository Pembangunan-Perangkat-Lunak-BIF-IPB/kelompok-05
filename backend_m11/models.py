"""SQLAlchemy models for VarEscape's four-station variant-calling MVP.

Station 1: fastp
Station 2: BWA-MEM2 / SAMtools
Station 3: BCFtools variant calling
Station 4: quality filtering / SnpEff annotation

Schema declarations only. Pipeline, API serializers, and migrations are separate steps.
"""

import enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class UserRole(str, enum.Enum):
    RESEARCHER = "RESEARCHER"
    PUBLIC = "PUBLIC"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class RunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class VisibilityType(str, enum.Enum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"


class FileType(str, enum.Enum):
    FASTQ_R1 = "FASTQ_R1"
    FASTQ_R2 = "FASTQ_R2"
    FASTA = "FASTA"


class ExecutionMode(str, enum.Enum):
    DEFAULT = "default"
    CUSTOM = "custom"


class AnnotationStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole, name="userrole"), nullable=False, default=UserRole.RESEARCHER)
    status_aktif = Column(SQLEnum(UserStatus, name="userstatus"), nullable=False, default=UserStatus.PENDING_APPROVAL)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRun", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    institution = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    registration_reason = Column(Text, nullable=True)

    user = relationship("User", back_populates="profile")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        CheckConstraint("min_dp >= 1", name="ck_run_min_dp"),
        CheckConstraint("min_mq >= 0 AND min_mq <= 60", name="ck_run_min_mq"),
        CheckConstraint("min_base_quality >= 0 AND min_base_quality <= 60",name="ck_run_min_bq"),
        CheckConstraint("max_depth >= 100 AND max_depth <= 100000",name="ck_run_max_depth"),
        CheckConstraint("min_qual >= 0", name="ck_run_min_qual"),
        CheckConstraint("min_af >= 0.01 AND min_af <= 1.0", name="ck_run_min_af"),
    )

    run_id = Column(String(50), primary_key=True, index=True)
    sample_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(RunStatus, name="runstatus"), nullable=False, default=RunStatus.PENDING)
    visibility = Column(SQLEnum(VisibilityType, name="visibilitytype"), nullable=False, default=VisibilityType.PRIVATE)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Parameter efektif per run (default maupun custom).
    # Default SQLAlchemy berlaku saat objek dibuat lewat ORM; API harus memvalidasi payload.
    execution_mode = Column(SQLEnum(ExecutionMode, name="executionmode", values_callable=lambda e: [m.value for m in e]), nullable=False, default=ExecutionMode.DEFAULT)
    min_dp = Column(Integer, nullable=False, default=10)
    min_mq = Column(Integer, nullable=False, default=30)
    min_base_quality = Column(Integer, nullable=False, default=20)
    max_depth = Column(Integer, nullable=False, default=10000)
    min_qual = Column(Float, nullable=False, default=30.0)
    min_af = Column(Float, nullable=False, default=0.20)

    # Identitas input/alat untuk pencatatan reproducibility.
    reference_accession = Column(String(100), nullable=True)
    reference_sha256 = Column(String(64), nullable=True)
    tool_versions_json = Column(Text, nullable=True)

    # Stasiun 1: QC. Nilai persentase 0..100.
    q20_rate = Column(Float, nullable=True)  # pasca-fastp, tetap dipakai oleh kode lama
    q30_rate = Column(Float, nullable=True)  # pasca-fastp, tetap dipakai oleh kode lama
    q20_before = Column(Float, nullable=True)
    q30_before = Column(Float, nullable=True)
    reads_before = Column(Integer, nullable=True)
    reads_after = Column(Integer, nullable=True)
    passed_reads_pct = Column(Float, nullable=True)
    adapter_trimmed_pct = Column(Float, nullable=True)

    # Stasiun 2: alignment.
    mapping_rate = Column(Float, nullable=True)
    mean_depth = Column(Float, nullable=True)
    unmapped_reads = Column(Integer, nullable=True)

    # Stasiun 3: calling dan statistik raw VCF.
    raw_variant_count = Column(Integer, nullable=True)
    raw_snp_count = Column(Integer, nullable=True)
    raw_indel_count = Column(Integer, nullable=True)
    tstv_ratio = Column(Float, nullable=True)  # nama lama dipertahankan

    # Stasiun 4: filtering dan anotasi.
    passed_variant_count = Column(Integer, nullable=True)
    filtered_variant_count = Column(Integer, nullable=True)
    annotation_status = Column(SQLEnum(AnnotationStatus, name="annotationstatus"), nullable=False, default=AnnotationStatus.PENDING)
    annotated_variant_count = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="analysis_runs")
    uploaded_files = relationship("UploadedFile", back_populates="analysis_run", cascade="all, delete-orphan")
    variant_results = relationship("VariantResult", back_populates="analysis_run", cascade="all, delete-orphan")
    pipeline_logs = relationship("PipelineLog", back_populates="analysis_run", cascade="all, delete-orphan")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    __table_args__ = (UniqueConstraint("run_id", "file_type", name="uq_uploaded_file_run_type"),)

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), ForeignKey("analysis_runs.run_id"), nullable=False, index=True)
    file_type = Column(SQLEnum(FileType, name="filetype"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    validation_status = Column(String(50), default="PASS", nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis_run = relationship("AnalysisRun", back_populates="uploaded_files")


class VariantResult(Base):
    __tablename__ = "variant_results"
    __table_args__ = (Index("ix_variant_run_position", "run_id", "position"),)

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), ForeignKey("analysis_runs.run_id"), nullable=False)
    chrom = Column(String(100), nullable=True)
    position = Column(Integer, nullable=False)
    ref_allele = Column(String(500), nullable=False)
    alt_allele = Column(String(500), nullable=False)
    qual = Column(Float, nullable=True)
    dp = Column(Integer, nullable=True)
    mq = Column(Float, nullable=True)
    af = Column(Float, nullable=True)
    filter_status = Column(String(50), nullable=True)

    # Anotasi dari SnpEff. Nilai terisi ketika parser pipeline telah diubah.
    snpeff_effect = Column(String(255), nullable=True)  # kompatibilitas API existing
    gene_name = Column(String(255), nullable=True)
    impact = Column(String(50), nullable=True)
    transcript_id = Column(String(255), nullable=True)
    hgvs_c = Column(String(255), nullable=True)
    hgvs_p = Column(String(255), nullable=True)
    amino_acid_change = Column(String(255), nullable=True)
    annotation_raw = Column(Text, nullable=True)

    # Konteks sekuens dari FASTA referensi, bukan bagian penilaian epitope.
    flank_left = Column(Text, nullable=True)
    flank_right = Column(Text, nullable=True)

    analysis_run = relationship("AnalysisRun", back_populates="variant_results")


class VariantFilterResult(Base):
    __tablename__ = "variant_filter_results"

    id = Column(Integer, primary_key=True)

    run_id = Column(
        String(50),
        ForeignKey("analysis_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chrom = Column(String(100))
    position = Column(Integer, nullable=False)
    ref_allele = Column(String(500), nullable=False)
    alt_allele = Column(String(500), nullable=False)

    qual = Column(Float)
    dp = Column(Integer)
    af = Column(Float)

    filter_status = Column(String(20), nullable=False)
    filter_reason = Column(Text)

class PipelineLog(Base):
    __tablename__ = "pipeline_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), ForeignKey("analysis_runs.run_id"), nullable=False, index=True)
    station_number = Column(Integer, nullable=False)
    log_level = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis_run = relationship("AnalysisRun", back_populates="pipeline_logs")
