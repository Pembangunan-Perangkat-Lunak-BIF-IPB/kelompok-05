import os
import uuid
import hashlib
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text

import models
from database import engine, SessionLocal

# Otomatis buat tabel di database PostgreSQL saat server dijalankan
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VarEscape API",
    description="Backend API untuk Platform Analisis Variasi Genomik SARS-CoV-2",
    version="1.0.0"
)

# Konfigurasi CORS (agar Frontend bisa terhubung)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency untuk mendapatkan koneksi database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper sederhana untuk hashing password
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ===================================================================
# PYDANTIC SCHEMAS (Format Body Request & Response)
# ===================================================================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    institution: Optional[str] = None
    phone_number: Optional[str] = None
    registration_reason: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class VisibilityUpdateRequest(BaseModel):
    visibility: str  # "PUBLIC" atau "PRIVATE"


# ===================================================================
# 1. HEALTH CHECK (`UC-03`)
# ===================================================================
@app.get("/api/v1/health", tags=["Infrastruktur"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected ({str(e)})"

    return {
        "status": "healthy",
        "database": db_status
    }


# ===================================================================
# 2. MODUL AUTENTIKASI (`UC-01`, `UC-02`)
# ===================================================================
@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED, tags=["Autentikasi"])
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    # Cek apakah email sudah terdaftar
    existing_user = db.query(models.User).filter(models.User.email == req.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar"
        )

    # Buat entitas User
    new_user = models.User(
        email=req.email,
        hashed_password=hash_password(req.password),
        role=models.UserRole.RESEARCHER,
        status_aktif=models.UserStatus.PENDING_APPROVAL
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Buat entitas UserProfile
    new_profile = models.UserProfile(
        user_id=new_user.id,
        full_name=req.full_name,
        institution=req.institution,
        phone_number=req.phone_number,
        registration_reason=req.registration_reason
    )
    db.add(new_profile)
    db.commit()

    return {
        "user_id": new_user.id,
        "email": new_user.email,
        "role": new_user.role,
        "status_aktif": new_user.status_aktif,
        "message": "Registrasi berhasil. Akun Anda menunggu persetujuan admin."
    }


@app.post("/api/v1/auth/login", tags=["Autentikasi"])
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user or user.hashed_password != hash_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah"
        )

    # Mock JWT Token sederana
    access_token = f"jwt_mock_token_user_{user.id}_{uuid.uuid4().hex[:8]}"

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "status_aktif": user.status_aktif
        }
    }


# ===================================================================
# 3. MODUL WORKBENCH & UPLOAD BERKAS ANALISIS (`UC-05` / `FR-01`)
# ===================================================================
@app.post("/api/v1/analysis/upload", status_code=status.HTTP_201_CREATED, tags=["Workbench Analysis"])
async def upload_analysis_files(
    sample_name: str = Form(...),
    file_fastq_r1: UploadFile = File(...),
    file_fastq_r2: UploadFile = File(...),
    file_fasta: UploadFile = File(...),
    file_iedb: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Validasi Lapis 1: Ekstensi Berkas
    validations = [
        (file_fastq_r1.filename, ('.fastq', '.fq', '.fastq.gz', '.fq.gz'), "FASTQ R1"),
        (file_fastq_r2.filename, ('.fastq', '.fq', '.fastq.gz', '.fq.gz'), "FASTQ R2"),
        (file_fasta.filename, ('.fasta', '.fa', '.fna'), "FASTA Genom Acuan"),
        (file_iedb.filename, ('.csv', '.tsv', '.gff'), "Tabel Epitope IEDB")
    ]

    for fname, allowed_exts, label in validations:
        if not fname.lower().endswith(allowed_exts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format berkas {label} tidak valid ({fname}). Ekstensi yang diizinkan: {allowed_exts}"
            )

    # Generate Run ID (format: VE-XXXX)
    short_code = uuid.uuid4().hex[:4].upper()
    run_id = f"VE-{short_code}"

    # Buat direktori penyimpanan fisik di backend/uploads/{run_id}
    upload_dir = os.path.join("uploads", run_id)
    os.makedirs(upload_dir, exist_ok=True)

    # Buat record AnalysisRun di database
    analysis_run = models.AnalysisRun(
        run_id=run_id,
        sample_name=sample_name,
        status=models.RunStatus.PENDING,
        visibility=models.VisibilityType.PRIVATE
    )
    db.add(analysis_run)

    files_info = [
        (file_fastq_r1, models.FileType.FASTQ_R1),
        (file_fastq_r2, models.FileType.FASTQ_R2),
        (file_fasta, models.FileType.FASTA),
        (file_iedb, models.FileType.IEDB),
    ]

    saved_files_summary = []

    for upload_file, file_type in files_info:
        file_path = os.path.join(upload_dir, upload_file.filename)
        
        # Simpan file fisik ke storage lokal
        content = await upload_file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Simpan metadata ke tabel uploaded_files
        db_file = models.UploadedFile(
            run_id=run_id,
            file_type=file_type,
            file_name=upload_file.filename,
            file_path=file_path,
            validation_status="PASS"
        )
        db.add(db_file)
        saved_files_summary.append({
            "file_type": file_type,
            "file_name": upload_file.filename,
            "validation_status": "PASS"
        })

    db.commit()

    return {
        "run_id": run_id,
        "sample_name": sample_name,
        "status": models.RunStatus.PENDING,
        "uploaded_files_summary": saved_files_summary
    }


# ===================================================================
# 4. MODUL RETRIEVAL DATA & VISIBILITAS (`UC-07`, `UC-08`, `UC-09`)
# ===================================================================
@app.get("/api/v1/analysis/{run_id}/status", tags=["Workbench Analysis"])
def get_analysis_status(run_id: str, db: Session = Depends(get_db)):
    run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesi analisis dengan run_id '{run_id}' tidak ditemukan"
        )

    # Dummy progress stasiun pipeline
    return {
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "status": run.status,
        "current_station": 1,
        "stations_status_list": [
            {"station": 1, "name": "Quality Control (fastp)", "status": "COMPLETED"},
            {"station": 2, "name": "Read Mapping (BWA-MEM2)", "status": "PENDING"},
            {"station": 3, "name": "Variant Calling (BCFtools)", "status": "PENDING"},
            {"station": 4, "name": "Functional Annotation (SnpEff)", "status": "PENDING"},
            {"station": 5, "name": "Epitope Mapping & Grantham", "status": "PENDING"}
        ]
    }


@app.get("/api/v1/analysis/{run_id}/results", tags=["Workbench Analysis"])
def get_analysis_results(run_id: str, db: Session = Depends(get_db)):
    run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesi analisis dengan run_id '{run_id}' tidak ditemukan"
        )

    results = db.query(models.VariantResult).filter(models.VariantResult.run_id == run_id).all()

    return {
        "run_id": run.run_id,
        "sample_name": run.sample_name,
        "visibility": run.visibility,
        "total_variants": len(results),
        "variant_results": results
    }


@app.patch("/api/v1/analysis/{run_id}/visibility", tags=["Workbench Analysis"])
def update_analysis_visibility(run_id: str, req: VisibilityUpdateRequest, db: Session = Depends(get_db)):
    run = db.query(models.AnalysisRun).filter(models.AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sesi analisis dengan run_id '{run_id}' tidak ditemukan"
        )

    if req.visibility not in ["PUBLIC", "PRIVATE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nilai visibility harus 'PUBLIC' atau 'PRIVATE'"
        )

    run.visibility = req.visibility
    db.commit()

    return {
        "run_id": run.run_id,
        "visibility": run.visibility,
        "message": f"Visibilitas analisis berhasil diubah menjadi {run.visibility}"
    }