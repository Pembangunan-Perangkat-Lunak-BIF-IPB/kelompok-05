from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models
from database import get_db
from security import get_password_hash, verify_password, create_access_token
from schemas.auth import UserRegister, UserLogin, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar"
        )
    
    hashed_pwd = get_password_hash(user_data.password)
    
    new_user = models.User(
        email=user_data.email, 
        hashed_password=hashed_pwd,
        role=user_data.role,
        status_aktif=models.UserStatus.ACTIVE
    )
    db.add(new_user)
    db.flush()

    new_profile = models.UserProfile(
        user_id=new_user.id,
        full_name=user_data.full_name,
        institution=user_data.institution,
        phone_number=user_data.phone_number,
        registration_reason=user_data.registration_reason
    )
    db.add(new_profile)
    
    db.commit()
    db.refresh(new_user)
    
    return {"message": "Registrasi berhasil", "user_id": new_user.id}


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah"
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}