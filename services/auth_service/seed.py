import sys
import os

# Thêm thư mục hiện tại vào python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal, engine
from app.models.user import Base, User, UserRole
from app.core.security import get_password_hash

def seed_data():
    # Tự động tạo bảng nếu chưa có
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Danh sách người dùng mẫu (mật khẩu chung: Password@123)
        sample_users = [
            {
                "username": "staff01",
                "email": "staff01@company.com",
                "password": "Password@123",
                "role": UserRole.STAFF
            },
            {
                "username": "manager01",
                "email": "manager01@company.com",
                "password": "Password@123",
                "role": UserRole.MANAGER
            },
            {
                "username": "director01",
                "email": "director01@company.com",
                "password": "Password@123",
                "role": UserRole.DIRECTOR
            }
        ]

        print("🌱 Đang tiến hành seed data người dùng...")

        created_count = 0
        for user_data in sample_users:
            # Kiểm tra xem user đã tồn tại chưa
            existing_user = db.query(User).filter(
                (User.username == user_data["username"]) | (User.email == user_data["email"])
            ).first()

            if not existing_user:
                new_user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    hashed_password=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    is_active=True
                )
                db.add(new_user)
                created_count += 1
                print(f"  + Tạo thành công user: {user_data['username']} [{user_data['role'].value}]")
            else:
                print(f"  - User {user_data['username']} đã tồn tại. Bỏ qua.")

        db.commit()
        print(f"✅ Hoàn thành Seed Data! Đã thêm mới {created_count} tài khoản.")

    except Exception as e:
        print(f"❌ Lỗi trong quá trình Seed Data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()