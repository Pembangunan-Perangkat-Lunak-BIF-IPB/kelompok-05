from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
from database import get_db
from security import get_password_hash, verify_password, create_access_token
from schemas.auth import UserRegister, UserLogin, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# Role yang boleh dipilih sendiri saat registrasi. ADMIN hanya dibuat lewat database (seed).
SELF_REGISTER_ROLES = {models.UserRole.RESEARCHER.value, models.UserRole.PUBLIC.value}


def _enum_value(value):
    return getattr(value, "value", value)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email sudah terdaftar")

    role_val = str(_enum_value(getattr(user_data, "role", None)) or models.UserRole.RESEARCHER.value).upper()
    if role_val == models.UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun ADMIN tidak dapat dibuat melalui registrasi")
    if role_val not in SELF_REGISTER_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role harus 'RESEARCHER' atau 'PUBLIC'")

    new_user = models.User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=models.UserRole(role_val),
        status_aktif=models.UserStatus.PENDING_APPROVAL,
    )
    try:
        db.add(new_user)
        db.flush()
        db.add(models.UserProfile(
            user_id=new_user.id,
            full_name=user_data.full_name,
            institution=user_data.institution,
            phone_number=user_data.phone_number,
            registration_reason=user_data.registration_reason,
        ))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Data akun sudah terdaftar atau melanggar aturan database")
    except Exception:
        db.rollback()
        raise
    db.refresh(new_user)

    return {
        "user_id": new_user.id,
        "email": new_user.email,
        "role": _enum_value(new_user.role),
        "status_aktif": _enum_value(new_user.status_aktif),
        "message": "Registrasi berhasil. Akun Anda menunggu persetujuan admin.",
    }


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email atau password salah")

    if user.status_aktif == models.UserStatus.REJECTED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun Anda ditolak oleh admin")
    if user.status_aktif == models.UserStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun Anda dinonaktifkan oleh administrator")

    # Akun PENDING_APPROVAL tetap boleh login (FE bisa menampilkan status),
    # namun endpoint workbench akan menolak dengan 403 sampai disetujui admin.
    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": _enum_value(user.role),
            "status_aktif": _enum_value(user.status_aktif),
        },
    }
