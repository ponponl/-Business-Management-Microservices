from sqlalchemy.orm import Session
from models.operation import OperationVolume
from utils.excel import generate_excel

#EXPORT EXCEL

class ReportService:
    @staticmethod
    def export_volumes_excel(db: Session, customer_id: int = None, contract_id: int = None, period_key: str = None):
        query = db.query(OperationVolume)
        if customer_id:
            query = query.filter(OperationVolume.customer_id == customer_id)
        if contract_id:
            query = query.filter(OperationVolume.contract_id == contract_id)
        if period_key:
            query = query.filter(OperationVolume.period_key == period_key)
            
        volumes = query.all()
        data = []
        for v in volumes:
            data.append({
                "ID": v.id,
                "Customer ID": v.customer_id,
                "Contract ID": v.contract_id,
                "Service Code": v.service_code,
                "Date": v.volume_date.strftime("%Y-%m-%d") if v.volume_date else "",
                "Period": v.period_key,
                "Quantity": v.quantity,
                "Unit": v.unit,
                "Status": "LOCKED" if v.is_locked else "OPEN"
            })
            
        return generate_excel(data)
