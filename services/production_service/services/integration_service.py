import httpx
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# URL cố định theo docker-compose DNS internal
PRICING_SERVICE_URL = "http://pricing-service:8000/api/v1/price-lists/services"

class IntegrationService:
    @staticmethod
    async def get_pricing_services(auth_header: str = None):
        """Gọi sang Pricing Service để lấy danh sách dịch vụ"""
        headers = {}
        if auth_header:
            headers["Authorization"] = auth_header
            
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(PRICING_SERVICE_URL, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Lỗi khi kết nối đến Pricing Service: {e}")
            raise HTTPException(status_code=502, detail="Không thể kết nối đến Pricing Service")
        except httpx.HTTPStatusError as e:
            logger.error(f"Lỗi trả về từ Pricing Service: {e.response.status_code}")
            raise HTTPException(status_code=502, detail="Lỗi từ Pricing Service")
