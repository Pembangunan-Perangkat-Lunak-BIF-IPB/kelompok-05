import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

import models
from database import engine, get_db
from routers import auth, analysis, public, admin

load_dotenv()

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VarEscape API Workbench",
    description="Backend API untuk Platform Analisis Variasi Genomik SARS-CoV-2",
    version="1.0.0"
)

raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173")
origins = [origin.strip() for origin in raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(public.router)
app.include_router(admin.router)

@app.get("/", tags=["Infrastruktur"])
def root():
    return {"message": "VarEscape API Workbench is running"}

@app.get("/api/v1/health", tags=["Infrastruktur"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        # Jangan mengembalikan detail error koneksi/kredensial ke pengunjung API.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Koneksi database sedang tidak tersedia",
        )

    return {
        "status": "healthy",
        "database": db_status
    }