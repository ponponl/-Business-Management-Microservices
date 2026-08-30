import os
import uuid
from typing import List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

# Sử dụng HTTPBearer thay cho OAuth2PasswordBearer để dán trực tiếp JWT Token trên Swagger
security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_jwt_key")
ALGORITHM = "HS256"


class CurrentUser:
    """Class đại diện cho thông tin User đăng nhập trong hệ thống"""
    def __init__(self, user_id: uuid.UUID, full_name: str, email: str = None, roles: List[str] = None):
        self.id = user_id
        self.user_id = user_id
        self.full_name = full_name
        self.email = email
        self.roles = roles or []


def get_current_user(auth: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """
    Dependency lấy Token trực tiếp từ HTTPBearer Header và giải mã.
    """
    token = auth.credentials  # Lấy chuỗi Bearer Token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        raw_user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
        
        if not raw_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ: Không tìm thấy ID người dùng."
            )

        user_uuid = uuid.UUID(str(raw_user_id))
        full_name: str = payload.get("full_name") or payload.get("name") or payload.get("username") or "Hệ thống"
        email: str = payload.get("email")
        
        raw_roles = payload.get("role") or payload.get("roles") or payload.get("authorities") or []

        if isinstance(raw_roles, str):
            roles = [raw_roles]
        elif isinstance(raw_roles, list):
            roles = [str(r) for r in raw_roles]
        else:
            roles = []

        return CurrentUser(
            user_id=user_uuid,
            full_name=str(full_name),
            email=email,
            roles=roles
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không thể xác thực thông tin Token hoặc Token đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng User ID trong Token không đúng chuẩn UUID."
        )


def require_roles(allowed_roles: List[str]) -> Callable:
    """Dependency phân quyền RBAC"""
    def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        user_roles = [
            str(r).upper().replace("ROLE_", "").strip() 
            for r in current_user.roles
        ]
        
        required_roles = [
            str(r).upper().replace("ROLE_", "").strip() 
            for r in allowed_roles
        ]

        has_permission = any(role in user_roles for role in required_roles)
        is_director = "DIRECTOR" in user_roles
        
        if not has_permission and not is_director:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản không đủ quyền thực hiện thao tác. Quyền hiện tại: {user_roles}. Bắt buộc: {allowed_roles}"
            )
        return current_user

    return role_checker