from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.auth import UserRegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.events import publish_user_login_event, publish_user_sync_event


class AuthService:

    @staticmethod
    async def register_user(db: Session, user_in: UserRegisterRequest) -> UserResponse:
        db_user = db.query(User).filter(
            (User.username == user_in.username) | (User.email == user_in.email)
        ).first()
        
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Tài khoản hoặc Email đã tồn tại trong hệ thống."
            )
        
        new_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            role=user_in.role
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Bắn Kafka event đồng bộ user mới tạo sang Pricing Service
        await publish_user_sync_event(
            user_id=str(new_user.id),
            username=new_user.username,
            email=new_user.email
        )

        return UserResponse(
            id=str(new_user.id),
            username=new_user.username,
            email=new_user.email,
            role=new_user.role.value if hasattr(new_user.role, 'value') else str(new_user.role),
            is_active=new_user.is_active
        )

    @staticmethod
    async def authenticate_user(db: Session, login_in: LoginRequest) -> TokenResponse:
        user = db.query(User).filter(User.username == login_in.username).first()
        if not user or not verify_password(login_in.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Mật khẩu hoặc tên đăng nhập không chính xác."
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Tài khoản đã bị vô hiệu hóa."
            )

        role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)

        access_token = create_access_token(
            data={"sub": str(user.id), "role": role_value, "username": user.username}
        )

        # Đã cập nhật: Truyền đủ user_id, username và role
        await publish_user_login_event(
            user_id=str(user.id),
            username=user.username,
            role=role_value
        )

        return TokenResponse(
            access_token=access_token,
            role=role_value
        )