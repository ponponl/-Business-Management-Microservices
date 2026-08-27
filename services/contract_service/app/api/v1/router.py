from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import CurrentUser, get_current_user
from app.db.session import get_db


api_router = APIRouter()


@api_router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "contract-service",
    }
    
@api_router.get("/contracts/health")
def contract_health():
    return {
        "status": "ok",
        "service": "contract-service",
    }


@api_router.get("/health/db")
def database_health_check(
    db: Session = Depends(get_db),
):
    db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }


@api_router.get("/me")
def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user),
):
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role,
    }