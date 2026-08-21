from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserRegisterRequest, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegisterRequest, db: Session = Depends(get_db)):
    return AuthService.register_user(db=db, user_in=user_in)

@router.post("/login", response_model=TokenResponse)
async def login(login_in: LoginRequest, db: Session = Depends(get_db)):
    return await AuthService.authenticate_user(db=db, login_in=login_in)