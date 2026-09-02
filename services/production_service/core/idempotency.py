import json
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.routing import APIRoute
from core.redis import redis_client

class IdempotentRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            idempotency_key = request.headers.get("Idempotency-Key")
            
            # Nếu không có header Idempotency-Key, bỏ qua và chạy bình thường
            if not idempotency_key:
                return await original_route_handler(request)

            # Prefix để tránh trùng với các key khác trong Redis
            redis_key = f"idempotency:{idempotency_key}"

            # Cố gắng lưu key với trạng thái PROCESSING. Thời gian khóa ngắn (ví dụ 10 phút).
            # nx=True: Chỉ lưu thành công nếu key chưa tồn tại.
            success = redis_client.set(redis_key, "PROCESSING", nx=True, ex=600)

            if not success:
                # Key đã tồn tại, kiểm tra trạng thái
                val = redis_client.get(redis_key)
                if val:
                    val_str = val.decode() if isinstance(val, bytes) else val
                    if val_str == "PROCESSING":
                        raise HTTPException(
                            status_code=409, 
                            detail="Duplicate request detected. Please wait."
                        )
                    else:
                        # Trạng thái COMPLETED, trả về kết quả cũ
                        try:
                            data = json.loads(val_str)
                            return Response(
                                content=data["body"],
                                status_code=data["status_code"],
                                media_type=data["media_type"]
                            )
                        except json.JSONDecodeError:
                            # Trạng thái không hợp lệ, fallback
                            raise HTTPException(
                                status_code=409,
                                detail="Duplicate request detected. Please wait."
                            )

            try:
                # Gọi hàm gốc để thực thi business logic
                response: Response = await original_route_handler(request)
                
                # Nếu thành công (2xx), lưu lại kết quả vào Redis
                if 200 <= response.status_code < 300:
                    completed_data = {
                        "status_code": response.status_code,
                        "body": response.body.decode() if isinstance(response.body, bytes) else response.body,
                        "media_type": response.media_type
                    }
                    # Lưu lại kết quả với thời gian dài hơn (24 giờ)
                    redis_client.set(redis_key, json.dumps(completed_data), ex=86400)
                else:
                    # Nếu lỗi nghiệp vụ hoặc 4xx/5xx, xóa key để user có thể Retry
                    redis_client.delete(redis_key)
                    
                return response
            except Exception as e:
                # Nếu có Exception (chưa kịp bắt lỗi), cũng xóa key để user Retry
                redis_client.delete(redis_key)
                raise e

        return custom_route_handler
