from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.sql import text
from database import engine, Base, SessionLocal
import models

# Otomatis membuat tabel di PostgreSQL saat server pertama kali menyala
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Catatan: Koneksi basis data belum siap -> {e}")

app = FastAPI(title="VarEscape Backend Engine")

# Mengizinkan akses lintas domain (CORS) untuk Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
def health_check():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "message": "Server backend dan PostgreSQL VarEscape siap digunakan!"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Koneksi database gagal: {str(e)}"
        )
    finally:
        db.close()