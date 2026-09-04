import os
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_jwt_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    role: str
    username: str


def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "role", "exp"]},
        )
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user = AuthenticatedUser(
        user_id=str(claims["sub"]),
        role=str(claims["role"]).upper(),
        username=str(claims.get("username", "")),
    )
    request.state.user = user
    return user


def authenticated_user(request: Request) -> AuthenticatedUser:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa xác thực người dùng")
    return user


def require_roles(request: Request, *roles: str) -> AuthenticatedUser:
    user = authenticated_user(request)
    if user.role not in {role.upper() for role in roles}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền thực hiện thao tác này")
    return user