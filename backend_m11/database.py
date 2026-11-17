import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

import config  # noqa: F401  (memuat .env)

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "varescape_db")

if not DB_PASSWORD:
    print("⚠️  DB_PASSWORD belum diisi di .env, koneksi database kemungkinan gagal.")

# URL.create meng-escape karakter khusus pada password (@, :, / dll.)
_db_url = URL.create(
    "postgresql",
    username=DB_USER,
    password=DB_PASSWORD or None,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)
DATABASE_URL = _db_url.render_as_string(hide_password=False)

# Password disembunyikan saat dicetak ke terminal
print(f"\n🚀 Uvicorn terhubung ke database: {_db_url.render_as_string(hide_password=True)}\n")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
