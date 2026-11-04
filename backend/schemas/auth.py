from typing import Optional
from pydantic import BaseModel, EmailStr
import models

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    institution: Optional[str] = None
    phone_number: Optional[str] = None
    registration_reason: Optional[str] = None
    role: Optional[models.UserRole] = models.UserRole.PUBLIC

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"