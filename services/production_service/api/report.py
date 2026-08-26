from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import require_role
from services.report_service import ReportService

router = APIRouter()

@router.get("/export")
def export_volumes(customer_id: int = None, contract_id: int = None, period_key: str = None, db: Session = Depends(get_db), user: dict = Depends(require_role(["OPERATION_STAFF", "OPERATION_MANAGER", "DIRECTOR"]))):
    file_bytes = ReportService.export_volumes_excel(db, customer_id, contract_id, period_key)
    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=volumes_report.xlsx"}
    )
