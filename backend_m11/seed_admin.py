"""
seed_admin.py
Helper membuat akun ADMIN berstatus ACTIVE, dan/atau mengaktifkan akun yang ada.
Jalankan dari folder backend (environment yang sama dengan uvicorn):

    python seed_admin.py --email admin@ipb.ac.id --password RahasiaKuat123 --full-name "Administrator"
    python seed_admin.py --activate peneliti@ipb.ac.id      # ubah 1 akun jadi ACTIVE
"""

import argparse

import config  # noqa: F401  (memuat .env)
import models
from database import SessionLocal, engine
from security import get_password_hash

models.Base.metadata.create_all(bind=engine)


def create_admin(email: str, password: str, full_name: str):
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if user:
            user.role = models.UserRole.ADMIN
            user.status_aktif = models.UserStatus.ACTIVE
            user.hashed_password = get_password_hash(password)
            print(f"Akun {email} diperbarui menjadi ADMIN + ACTIVE.")
        else:
            user = models.User(
                email=email,
                hashed_password=get_password_hash(password),
                role=models.UserRole.ADMIN,
                status_aktif=models.UserStatus.ACTIVE,
            )
            db.add(user)
            db.flush()
            db.add(models.UserProfile(user_id=user.id, full_name=full_name, institution="IPB University"))
            print(f"Akun ADMIN baru dibuat: {email}")
        db.commit()
    finally:
        db.close()


def activate(email: str):
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"Akun {email} tidak ditemukan.")
            return
        user.status_aktif = models.UserStatus.ACTIVE
        db.commit()
        print(f"Akun {email} kini ACTIVE.")
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Seed/aktivasi akun VarEscape")
    p.add_argument("--email")
    p.add_argument("--password")
    p.add_argument("--full-name", default="Administrator")
    p.add_argument("--activate", metavar="EMAIL", help="Aktifkan akun yang sudah ada")
    args = p.parse_args()

    if args.activate:
        activate(args.activate)
    elif args.email and args.password:
        create_admin(args.email, args.password, args.full_name)
    else:
        p.error("Beri --email dan --password untuk buat admin, atau --activate EMAIL untuk aktivasi.")
