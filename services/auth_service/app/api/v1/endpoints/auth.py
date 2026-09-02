from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import UserRole
from app.schemas.auth import (
    LoginRequest, 
    TokenResponse, 
    UserRegisterRequest, 
    UserResponse
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegisterRequest, db: Session = Depends(get_db)):
    """API Đăng ký tài khoản (Đã thêm async/await để bắn Kafka sync dữ liệu)"""
    return await AuthService.register_user(db=db, user_in=user_in)


@router.post("/login", response_model=TokenResponse)
async def login(login_in: LoginRequest, db: Session = Depends(get_db)):
    """API Đăng nhập (Bắn Kafka event kèm thông tin username)"""
    return await AuthService.authenticate_user(db=db, login_in=login_in)


@router.get("/users", response_model=List[UserResponse], summary="Lấy danh sách tất cả Users")
def get_users(
    role: Optional[UserRole] = Query(None, description="Lọc danh sách theo vai trò (STAFF, MANAGER, DIRECTOR)"),
    db: Session = Depends(get_db)
):
    """
    API trả về danh sách người dùng trong hệ thống (Staff, Manager, Director...).
    """
    return AuthService.get_all_users(db=db, role=role)