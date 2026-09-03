import random
import uuid
from datetime import date

from app.db.session import Base, SessionLocal, engine
import app.models.pricing 
from app.models.pricing import (
    PriceList,
    PriceListDetail,
    PriceListVersion,
    ServiceItem,
    UserCache,
)


def seed_rich_data():
    print("1. Đang Drop và Re-create lại toàn bộ Bảng trong Database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("2. Đang seed dữ liệu User Cache / Người dùng...")
        staff_user_id = uuid.UUID("55399947-e92e-4afb-a8af-572b84050f4b")
        manager_user_id = uuid.UUID("31ef2ba5-15d4-4411-afa1-d1661dd6719f")
        director_user_id = uuid.UUID("030b4950-4ccf-4437-bf14-5c8debfa3e8d")

        users_data = [
            (staff_user_id, "staff01", "Nhan Vien"),
            (manager_user_id, "manager01", "Truong Phong"),
            (director_user_id, "director01", "Giam Doc"),
        ]

        for u_id, u_name, full_name in users_data:
            user_obj = UserCache(
                user_id=str(u_id),
                username=u_name,
                full_name=full_name,
            )
            db.add(user_obj)
        db.flush()

        print("3. Đang khởi tạo danh mục Dịch vụ (SERVICE_ITEM)...")
        services_data = [
            ("SRV-20ft-IN", "Bốc xếp container 20ft (Hàng nhập)", "Bốc xếp & Nâng hạ", "Container"),
            ("SRV-WH-GEN", "Lưu kho bãi tổng hợp", "Lưu kho & Bãi container", "Ngày/Tấn"),
            ("SRV-PORT-OP", "Khai thác bến bãi hạ tải", "Dịch vụ Cảng & Bến bãi", "Lượt xe"),
            ("SRV-40ft-OUT", "Bốc xếp container 40ft (Hàng xuất)", "Bốc xếp & Nâng hạ", "Container"),
            ("SRV-CUST-CLR", "Khai báo hải quan trọn gói", "Thủ tục Hải quan", "Tờ khai"),
            ("SRV-REEFER-PLUG", "Cắm điện container lạnh 24/7", "Dịch vụ Container lạnh", "Giờ"),
            ("SRV-CLEAN-CONT", "Vệ sinh container tiêu chuẩn", "Dịch vụ Bổ trợ", "Container"),
        ]

        service_objects = {}
        for code, name, s_group, unit in services_data:
            item = ServiceItem(
                id=uuid.uuid4(),
                service_code=code,
                service_name=name,
                service_group=s_group,
                unit=unit,
                status="ACTIVE",
            )
            db.add(item)
            service_objects[code] = item
        db.flush()

        print("4. Khởi tạo Bảng giá với scope_id là Mã Khách hàng/Hợp đồng chuẩn...")

        price_lists_config = [
            {
                "code": "PL-2026-001",
                "name": "Bảng giá Dịch vụ Hợp đồng CTR-SEED-001",
                "scope_type": "CONTRACT",
                "scope_id": "CTR-SEED-001",
                "versions": [
                    {"ver": "v1.0", "status": "SUPERSEDED", "from": date(2026, 1, 1), "to": date(2026, 3, 31), "stage": "COMPLETED", "approver": director_user_id},
                    {"ver": "v1.1", "status": "SUPERSEDED", "from": date(2026, 4, 1), "to": date(2026, 6, 30), "stage": "COMPLETED", "approver": director_user_id},
                    {"ver": "v2.0", "status": "EFFECTIVE", "from": date(2026, 7, 1), "to": date(2026, 12, 31), "stage": "COMPLETED", "approver": director_user_id},
                ]
            },
            {
                "code": "PL-2026-002",
                "name": "Bảng giá Áp dụng Khách hàng CUS001",
                "scope_type": "CUSTOMER",
                "scope_id": "CUS001",
                "versions": [
                    {"ver": "v1.0", "status": "REJECTED", "from": date(2026, 1, 1), "to": date(2026, 6, 30), "stage": "REJECTED", "approver": manager_user_id, "reason": "Đơn giá chiết khấu kho bãi vượt quá quy định 15%."},
                    {"ver": "v1.1", "status": "SUBMITTED", "from": date(2026, 1, 1), "to": date(2026, 12, 31), "stage": "MANAGER_PENDING", "approver": None},
                ]
            },
            {
                "code": "PL-2026-003",
                "name": "Bảng giá Khai thác Niêm yết Chung 2026",
                "scope_type": "GENERAL",
                "scope_id": "GENERAL_ALL",
                "versions": [
                    {"ver": "v1.0", "status": "SUPERSEDED", "from": date(2025, 1, 1), "to": date(2025, 12, 31), "stage": "COMPLETED", "approver": director_user_id},
                    {"ver": "v2.0", "status": "EFFECTIVE", "from": date(2026, 1, 1), "to": date(2026, 12, 31), "stage": "COMPLETED", "approver": director_user_id},
                    {"ver": "v2.1", "status": "DRAFT", "from": date(2027, 1, 1), "to": date(2027, 12, 31), "stage": "DRAFT", "approver": None},
                ]
            },
            {
                "code": "PL-2026-004",
                "name": "Bảng giá Hợp đồng Khai thác Cảng CTR-SEED-002",
                "scope_type": "CONTRACT",
                "scope_id": "CTR-SEED-002",
                "versions": [
                    {"ver": "v1.0", "status": "APPROVED", "from": date(2026, 6, 1), "to": date(2027, 5, 31), "stage": "APPROVED", "approver": director_user_id},
                ]
            },
            {
                "code": "PL-2026-005",
                "name": "Bảng giá Ưu đãi Dịch vụ Khách hàng CUS002",
                "scope_type": "CUSTOMER",
                "scope_id": "CUS002",
                "versions": [
                    {"ver": "v1.0", "status": "DRAFT", "from": date(2026, 9, 1), "to": date(2027, 8, 31), "stage": "DRAFT", "approver": None},
                ]
            }
        ]

        for pl_cfg in price_lists_config:
            pl = PriceList(
                id=uuid.uuid4(),
                price_list_code=pl_cfg["code"],
                price_list_name=pl_cfg["name"],
                scope_type=pl_cfg["scope_type"],
                scope_id=pl_cfg["scope_id"],
                description=f"Cấu hình bảng giá {pl_cfg['name']} cho phạm vi {pl_cfg['scope_type']} ({pl_cfg['scope_id']})",
                created_by=staff_user_id,
                is_deleted=False,
            )
            db.add(pl)
            db.flush()

            for v_idx, v_cfg in enumerate(pl_cfg["versions"]):
                ver = PriceListVersion(
                    id=uuid.uuid4(),
                    price_list_id=pl.id,
                    price_list_name=pl_cfg["name"],
                    version_number=v_cfg["ver"],
                    valid_from=v_cfg["from"],
                    valid_to=v_cfg["to"],
                    status=v_cfg["status"],
                    created_by=staff_user_id,
                    approved_by=v_cfg.get("approver"),
                    rejected_reason=v_cfg.get("reason"),
                    approval_stage=v_cfg["stage"],
                )
                db.add(ver)
                db.flush()

                base_multiplier = 1.0 + (v_idx * 0.08)
                prices = {
                    "SRV-20ft-IN": round(350000.00 * base_multiplier, -3),
                    "SRV-WH-GEN": round(45000.00 * base_multiplier, -2),
                    "SRV-PORT-OP": 125000.00,
                    "SRV-40ft-OUT": round(550000.00 * base_multiplier, -3),
                    "SRV-CUST-CLR": 800000.00,
                    "SRV-REEFER-PLUG": round(65000.00 * base_multiplier, -2),
                    "SRV-CLEAN-CONT": 180000.00,
                }

                for srv_code, price_val in prices.items():
                    detail = PriceListDetail(
                        id=uuid.uuid4(),
                        price_list_id=pl.id,
                        price_list_version_id=ver.id,
                        service_item_id=service_objects[srv_code].id,
                        unit_price=price_val,
                    )
                    db.add(detail)

        db.commit()
        print("✅ Hoàn tất Seed dữ liệu cơ bản thành công!")
        print(f"   👉 Seed thành công 3 User Cache với đúng UUID cung cấp:")
        print(f"      - staff01    ({staff_user_id})")
        print(f"      - manager01  ({manager_user_id})")
        print(f"      - director01 ({director_user_id})")

    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi seed dữ liệu: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_rich_data()