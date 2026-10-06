import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database import Base


# -------------------------------------------------------------------
# ENUM DEFINITIONS (Status & Role)
# -------------------------------------------------------------------
class UserRole(str, enum.Enum):
    RESEARCHER = "RESEARCHER"
    PUBLIC = "PUBLIC"
    ADMIN = "ADMIN"

class UserStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"

class RunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class VisibilityType(str, enum.Enum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"

class FileType(str, enum.Enum):
    FASTQ_R1 = "FASTQ_R1"
    FASTQ_R2 = "FASTQ_R2"
    FASTA = "FASTA"
    IEDB = "IEDB"


# -------------------------------------------------------------------
# 1. TABEL USERS & USER_PROFILES (Autentikasi & Akun)
# -------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.RESEARCHER, nullable=False)
    status_aktif = Column(SQLEnum(UserStatus), default=UserStatus.PENDING_APPROVAL, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relasi 1:1 ke UserProfile
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    # Relasi 1:N ke AnalysisRun
    analysis_runs = relationship("AnalysisRun", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    institution = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    registration_reason = Column(Text, nullable=True)

    # Relasi balik ke User
    user = relationship("User", back_populates="profile")


# -------------------------------------------------------------------
# 2. TABEL ANALYSIS_RUNS & UPLOADED_FILES (Workbench & Upload)
# -------------------------------------------------------------------
class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    run_id = Column(String(50), primary_key=True, index=True)  # Format: VE-0001
    sample_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(RunStatus), default=RunStatus.PENDING, nullable=False)
    visibility = Column(SQLEnum(VisibilityType), default=VisibilityType.PRIVATE, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relasi balik ke User
    user = relationship("User", back_populates="analysis_runs")
    # Relasi 1:N ke UploadedFile
    uploaded_files = relationship("UploadedFile", back_populates="analysis_run")
    # Relasi 1:N ke VariantResult
    variant_results = relationship("VariantResult", back_populates="analysis_run")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), ForeignKey("analysis_runs.run_id"), nullable=False)
    file_type = Column(SQLEnum(FileType), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    validation_status = Column(String(50), default="PASS", nullable=False)  # PASS / FAIL
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relasi balik ke AnalysisRun
    analysis_run = relationship("AnalysisRun", back_populates="uploaded_files")


# -------------------------------------------------------------------
# 3. TABEL VARIANT_RESULTS (Hasil Analisis Varian)
# -------------------------------------------------------------------
class VariantResult(Base):
    __tablename__ = "variant_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), ForeignKey("analysis_runs.run_id"), nullable=False)
    position = Column(Integer, nullable=False)
    ref_allele = Column(String(50), nullable=False)
    alt_allele = Column(String(50), nullable=False)
    qual = Column(String(50), nullable=True)
    dp = Column(Integer, nullable=True)
    snpeff_effect = Column(String(255), nullable=True)
    grantham_score = Column(Integer, nullable=True)
    risk_level = Column(String(50), nullable=True)

    # Relasi balik ke AnalysisRun
    analysis_run = relationship("AnalysisRun", back_populates="variant_results")