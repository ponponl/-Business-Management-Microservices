import httpx
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)



class IntegrationService:


    @staticmethod
    async def get_pricing_services_by_contract(contract_id: str, auth_header: str = None):
        """Gọi sang Pricing Service để lấy danh sách dịch vụ theo hợp đồng"""
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
            
        url = f"http://pricing-service:8000/api/v1/contracts/{contract_id}/services"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 404:
                    return []
                response.raise_for_status()
                data = response.json()
                return data.get("services", [])
        except httpx.RequestError as e:
            logger.error(f"Lỗi khi kết nối đến Pricing Service: {e}")
            raise HTTPException(status_code=502, detail="Không thể kết nối đến Pricing Service")
        except httpx.HTTPStatusError as e:
            logger.error(f"Lỗi trả về từ Pricing Service: {e.response.status_code}")
            raise HTTPException(status_code=502, detail="Lỗi từ Pricing Service")
