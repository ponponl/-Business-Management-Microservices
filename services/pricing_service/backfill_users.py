import httpx
from app.db.session import SessionLocal
from app.models.pricing import UserCache

AUTH_SERVICE_USERS_API = "http://localhost:8000/api/v1/users"


def sync_existing_users():
    """Đồng bộ danh sách User hiện có từ Auth Service sang bảng UserCache của Pricing Service"""
    print("Bắt đầu lấy dữ liệu từ Auth Service...")
    try:
        response = httpx.get(AUTH_SERVICE_USERS_API, timeout=5.0)
        if response.status_code != 200:
            print(f"Lỗi: Auth Service trả về Status Code {response.status_code}")
            return

        users_data = response.json()
        db = SessionLocal()
        count = 0

        try:
            for user in users_data:
                u_id = str(user.get("id", "")).strip().lower()
                u_name = str(user.get("username", "")).strip()

                if u_id and u_name:
                    cache = (
                        db.query(UserCache)
                        .filter(UserCache.user_id == u_id)
                        .first()
                    )
                    if not cache:
                        cache = UserCache(
                            user_id=u_id, username=u_name, full_name=u_name
                        )
                        db.add(cache)
                    else:
                        cache.username = u_name
                        cache.full_name = u_name
                    count += 1

            db.commit()
            print(f"-> Đã đồng bộ thành công {count} tài khoản vào UserCache!")

        except Exception as e:
            db.rollback()
            print(f"Lỗi lưu vào DB: {e}")
        finally:
            db.close()

    except Exception as e:
        print(f"Không thể kết nối tới Auth Service: {e}")


if __name__ == "__main__":
    sync_existing_users()