import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Enum, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

# ==================== 1. ENUM DEFINITIONS ====================

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    RESEARCHER = "RESEARCHER"
    GUEST = "GUEST"

class UserStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"

class RunVisibility(str, enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"

class RunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class FileType(str, enum.Enum):
    FASTQ_R1 = "FASTQ_R1"
    FASTQ_R2 = "FASTQ_R2"
    FASTA_REF = "FASTA_REF"
    IEDB_EPITOPE = "IEDB_EPITOPE"

class ValidationStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"


# ==================== 2. TABLE MODELS ====================

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.RESEARCHER)
    status_aktif = Column(Enum(UserStatus), nullable=False, default=UserStatus.PENDING_APPROVAL)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relasi 1:N ke analysis_runs
    analysis_runs = relationship("AnalysisRun", back_populates="user", cascade="all, delete-orphan")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    run_id = Column(String(50), primary_key=True)  # Contoh: 'VE-0142'
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sample_name = Column(String(255), nullable=False)
    visibility = Column(Enum(RunVisibility), nullable=False, default=RunVisibility.PRIVATE)
    status = Column(Enum(RunStatus), nullable=False, default=RunStatus.PENDING)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relasi
    user = relationship("User", back_populates="analysis_runs")
    uploaded_files = relationship("UploadedFile", back_populates="analysis_run", cascade="all, delete-orphan")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(String(50), ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    validation_status = Column(Enum(ValidationStatus), nullable=False, default=ValidationStatus.PASS)

    # Relasi
    analysis_run = relationship("AnalysisRun", back_populates="uploaded_files")