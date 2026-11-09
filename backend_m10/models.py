import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SQLEnum, func
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

class VisibilityType(str, enum.Enum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"

class FileType(str, enum.Enum):
    FASTQ_R1 = "FASTQ_R1"
    FASTQ_R2 = "FASTQ_R2"
    FASTA = "FASTA"
    IEDB = "IEDB"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole, name="userrole"), nullable=False, default=UserRole.RESEARCHER)
    status_aktif = Column(SQLEnum(UserStatus, name="userstatus"), nullable=False, default=UserStatus.PENDING_APPROVAL)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    profile = relationship("UserProfile", back_populates="user", uselist=False)
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

    run_id = Column(String(50), primary_key=True, index=True)
    sample_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(RunStatus), default=RunStatus.PENDING, nullable=False)
    visibility = Column(SQLEnum(VisibilityType), default=VisibilityType.PRIVATE, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Kolom Metrik Sekuensing (Lengkap)
    q20_rate = Column(Float, nullable=True)
    q30_rate = Column(Float, nullable=True)
    mapping_rate = Column(Float, nullable=True)
    mean_depth = Column(Float, nullable=True)
    tstv_ratio = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="analysis_runs")
    uploaded_files = relationship("UploadedFile", back_populates="analysis_run", cascade="all, delete-orphan")
    variant_results = relationship("VariantResult", back_populates="analysis_run", cascade="all, delete-orphan")
    pipeline_logs = relationship("PipelineLog", back_populates="analysis_run", cascade="all, delete-orphan")

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), ForeignKey("analysis_runs.run_id"), nullable=False)
    file_type = Column(SQLEnum(FileType), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    validation_status = Column(String(50), default="PASS", nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis_run = relationship("AnalysisRun", back_populates="uploaded_files")

class VariantResult(Base):
    __tablename__ = "variant_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), ForeignKey("analysis_runs.run_id"), index=True, nullable=False)
    position = Column(Integer, nullable=False)
    ref_allele = Column(String(50), nullable=False)
    alt_allele = Column(String(50), nullable=False)
    qual = Column(Float, nullable=True)
    dp = Column(Integer, nullable=True)
    snpeff_effect = Column(String(255), nullable=True)
    grantham_score = Column(Integer, nullable=True)
    risk_level = Column(String(50), nullable=True)


    analysis_run = relationship("AnalysisRun", back_populates="variant_results")

class PipelineLog(Base):
    __tablename__ = "pipeline_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), ForeignKey("analysis_runs.run_id"), index=True, nullable=False)
    station_number = Column(Integer, nullable=False)
    log_level = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis_run = relationship("AnalysisRun", back_populates="pipeline_logs")