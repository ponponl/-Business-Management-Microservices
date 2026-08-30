from fastapi import Header, HTTPException, Request
from core.redis import redis_client

async def check_idempotency(request: Request, x_idempotency_key: str = Header(None)):
    """
    Dependency to check for Idempotency-Key in the request header.
    If the key exists, it ensures the request is only processed once within a 10-minute window.
    """
    if not x_idempotency_key:
        # Nếu client không gửi key, có thể bỏ qua hoặc bắt buộc phải gửi.
        # Ở đây ta linh động bỏ qua nếu không gửi để tương thích ngược.
        return None

    # Prefix để tránh trùng với các key khác trong Redis
    redis_key = f"idempotency:{x_idempotency_key}"

    # Cố gắng lưu key với thời gian sống 10 phút (600 giây).
    # nx=True (Set if Not eXists): Chỉ lưu thành công nếu key chưa tồn tại.
    success = redis_client.set(redis_key, "PROCESSING", nx=True, ex=600)

    if not success:
        # Key đã tồn tại -> Double Submit
        raise HTTPException(
            status_code=409, 
            detail="Duplicate request detected. Please wait."
        )

    return x_idempotency_key
