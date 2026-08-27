from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import bearer_scheme, verify_access_token


@dataclass
class CurrentUser:
    user_id: str
    username: str
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:

    payload = verify_access_token(credentials.credentials)

    user_id = payload.get("sub")
    username = payload.get("username")
    role = payload.get("role")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identity",
        )

    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing role",
        )

    return CurrentUser(
        user_id=user_id,
        username=username or "",
        role=role,
    )