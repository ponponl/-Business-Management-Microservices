import os
import uuid
from typing import List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt

# OAuth2 Scheme lấy Token từ Header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Lấy JWT_SECRET từ Docker environment (Fallback: super_secret_jwt_key)
SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_jwt_key")
ALGORITHM = "HS256"


class CurrentUser:
    """Class đại diện cho thông tin User đăng nhập trong hệ thống"""
    def __init__(self, user_id: uuid.UUID, full_name: str, email: str = None, roles: List[str] = None):
        self.id = user_id
        self.user_id = user_id  # Đồng bộ để sử dụng linh hoạt .id hoặc .user_id
        self.full_name = full_name
        self.email = email
        self.roles = roles or []


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    """
    Dependency giải mã JWT Token và chuyển đổi thông tin thành đối tượng CurrentUser.
    Đã hỗ trợ đọc cả 'role' (số ít) lẫn 'roles' (mảng) từ Payload của Token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Bốc UUID người dùng từ payload Token
        raw_user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
        
        if not raw_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ: Không tìm thấy ID người dùng."
            )

        # Chuyển string ID sang kiểu uuid.UUID chuẩn
        user_uuid = uuid.UUID(str(raw_user_id))
        
        full_name: str = payload.get("full_name") or payload.get("name") or payload.get("username") or "Hệ thống"
        email: str = payload.get("email")
        
        # Lấy role từ payload (kiểm tra cả 'role', 'roles', 'authorities')
        raw_roles = payload.get("role") or payload.get("roles") or payload.get("authorities") or []

        # Chuẩn hóa về dạng List[str]
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
    """
    Dependency dùng cho phân quyền Role-based Access Control (RBAC).
    Hỗ trợ hệ thống có các Role: STAFF, MANAGER, DIRECTOR.
    Cho phép truy cập nếu User sở hữu Role trong danh sách yêu cầu hoặc là DIRECTOR.
    """
    def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        # Chuẩn hóa danh sách Role của User (Viết hoa, loại bỏ tiền tố ROLE_ nếu có)
        user_roles = [
            str(r).upper().replace("ROLE_", "").strip() 
            for r in current_user.roles
        ]
        
        # Chuẩn hóa danh sách Role yêu cầu
        required_roles = [
            str(r).upper().replace("ROLE_", "").strip() 
            for r in allowed_roles
        ]

        # Kiểm tra người dùng có Role phù hợp hoặc cấp cao DIRECTOR hay không
        has_permission = any(role in user_roles for role in required_roles)
        is_director = "DIRECTOR" in user_roles
        
        if not has_permission and not is_director:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản không đủ quyền thực hiện thao tác. Quyền hiện tại: {user_roles}. Bắt buộc: {allowed_roles}"
            )
        return current_user

    return role_checker