import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import config  # noqa: F401  (memuat .env)
import models
from database import get_db

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = "dev-only-secret-key-ganti-di-env"
    print("⚠️  SECRET_KEY belum diisi di .env, memakai kunci development (jangan dipakai di production).")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_user_id(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sudah expired, silakan login ulang")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid")

    sub = payload.get("sub")
    try:
        return int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> int:
    """Mengembalikan user_id. Hanya akun berstatus ACTIVE yang boleh memakai workbench."""
    user_id = _decode_user_id(credentials.credentials)

    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Akun tidak ditemukan")

    if user.status_aktif == models.UserStatus.REJECTED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun Anda ditolak oleh admin")
    if user.status_aktif == models.UserStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun Anda dinonaktifkan oleh administrator")
    if user.status_aktif != models.UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun Anda masih menunggu persetujuan admin")

    return user.id


def require_admin(
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> models.User:
    """Otorisasi server-side untuk semua endpoint /admin/* ."""
    user = db.get(models.User, user_id)
    if user is None or user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hanya Administrator yang memiliki akses")
    return user


def require_researcher(
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> int:
    """Mencegah akun PUBLIC/ADMIN memanggil workbench lewat API langsung."""
    user = db.get(models.User, user_id)
    if user is None or user.role != models.UserRole.RESEARCHER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hanya akun Peneliti yang memiliki akses")
    return user_id
