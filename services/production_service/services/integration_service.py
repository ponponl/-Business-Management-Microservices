import httpx
from fastapi import HTTPException
import logging
from sqlalchemy.orm import Session
from models.cache import ContractCache

logger = logging.getLogger(__name__)



class IntegrationService:


    @staticmethod
    async def get_pricing_services_by_contract(db: Session, contract_id: str, auth_header: str = None):
        """Gọi sang Pricing Service để lấy danh sách dịch vụ theo hợp đồng"""
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
            
        contract = db.query(ContractCache).filter(
            (ContractCache.contract_id == contract_id)
            | (ContractCache.contract_number == contract_id)
        ).first()
        contract_ids = [contract_id]
        if contract:
            for candidate in (contract.contract_id, contract.contract_number):
                if candidate and candidate not in contract_ids:
                    contract_ids.append(candidate)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                for pricing_contract_id in contract_ids:
                    url = f"http://pricing-service:8006/api/v1/contracts/{pricing_contract_id}/services"
                    response = await client.get(url, headers=headers)
                    if response.status_code == 404:
                        continue
                    response.raise_for_status()
                    data = response.json()
                    return data.get("services", [])
                return []
        except httpx.RequestError as e:
            logger.error(f"Lỗi khi kết nối đến Pricing Service: {e}")
            raise HTTPException(status_code=502, detail="Không thể kết nối đến Pricing Service")
        except httpx.HTTPStatusError as e:
            logger.error(f"Lỗi trả về từ Pricing Service: {e.response.status_code}")
            raise HTTPException(status_code=502, detail="Lỗi từ Pricing Service")
