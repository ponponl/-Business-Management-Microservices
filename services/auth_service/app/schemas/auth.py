from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import UserRole

class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.STAFF

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool