import random
import uuid
from datetime import date, datetime, timedelta, timezone

from app.db.session import Base, SessionLocal, engine
import app.models.pricing 
from app.models.pricing import (
    PriceChangeHistory,
    PriceList,
    PriceListDetail,
    PriceListUsageLog,
    PriceListVersion,
    ServiceItem,
)
# Nhập Model User / UserCache của ứng dụng
try:
    from app.models.user import User  # Hoặc UserCache
except ImportError:
    from app.models.pricing import User  # Thay thế bằng import đúng với cấu trúc dự án của bạn


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
            (staff_user_id, "staff01", "staff01@company.com", "Nhan Vien"),
            (manager_user_id, "manager01", "manager01@company.com", "Truong Phong"),
            (director_user_id, "director01", "director01@company.com", "Giam Doc"),
        ]

        for u_id, u_name, u_email, full_name in users_data:
            # Tạo instance tương ứng với model User/UserCache của dự án
            user_obj = User(
                id=u_id,
                username=u_name,
                email=u_email,
                full_name=full_name,
                is_active=True
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

        created_versions_detail = []

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

                created_versions_detail.append((pl, ver))

        print("5. Đang sinh Lịch sử thay đổi (PriceChangeHistory) phong phú...")

        history_templates = [
            ("price_list_name", "Bảng giá Nháp 2026", "Bảng giá Dịch vụ Hợp đồng CTR-SEED-001", "Chuẩn hóa tên gọi bảng giá theo hợp đồng ký kết", "PRICE_LIST_VERSION"),
            ("valid_from", "2026-01-01", "2026-02-01", "Điều chỉnh thời gian áp dụng lùi lại 1 tháng theo yêu cầu đối tác", "PRICE_LIST_VERSION"),
            ("valid_to", "2026-06-30", "2026-12-31", "Gia hạn thời hạn bảng giá theo phụ lục hợp đồng mới", "PRICE_LIST_VERSION"),
            ("unit_price (SRV-20ft-IN)", "320,000 VND", "350,000 VND", "Tăng giá bốc xếp 20ft do biến động chi phí nhiên liệu", "PRICE_LIST_DETAIL"),
            ("unit_price (SRV-WH-GEN)", "40,000 VND", "45,000 VND", "Điều chỉnh đơn giá lưu kho bãi theo khung niêm yết năm 2026", "PRICE_LIST_DETAIL"),
            ("unit_price (SRV-40ft-OUT)", "500,000 VND", "550,000 VND", "Cập nhật đơn giá bốc xếp container 40ft xuất khẩu", "PRICE_LIST_DETAIL"),
            ("unit_price (SRV-REEFER-PLUG)", "60,000 VND", "65,000 VND", "Tăng giá dịch vụ cắm điện container lạnh 24/7", "PRICE_LIST_DETAIL"),
            ("status", "DRAFT", "SUBMITTED", "Chuyên viên gửi yêu cầu phê duyệt bảng giá lên Trưởng phòng", "PRICE_LIST_VERSION"),
            ("status", "SUBMITTED", "APPROVED", "Trưởng phòng Kinh doanh đã thẩm định và phê duyệt nội dung", "PRICE_LIST_VERSION"),
            ("status", "APPROVED", "EFFECTIVE", "Kích hoạt bảng giá chính thức có hiệu lực trên hệ thống", "PRICE_LIST_VERSION"),
            ("status", "EFFECTIVE", "SUPERSEDED", "Chuyển sang trạng thái hết hiệu lực do đã phát hành phiên bản v2.0", "PRICE_LIST_VERSION"),
            ("status", "SUBMITTED", "REJECTED", "Ban quản lý từ chối phê duyệt do mức chiết khấu chưa hợp lý", "PRICE_LIST_VERSION"),
            ("status", "REJECTED", "DRAFT", "Chuyển về trạng thái Nháp để cập nhật lại cấu hình đơn giá", "PRICE_LIST_VERSION"),
        ]

        actors = [staff_user_id, manager_user_id, director_user_id]
        total_history_count = 0

        for pl, ver in created_versions_detail:
            num_logs = random.randint(6, 12)
            base_time = datetime(2026, 1, 10, 8, 30, tzinfo=timezone.utc)

            for i in range(num_logs):
                field_name, old_val, new_val, reason, entity_type = history_templates[i % len(history_templates)]
                actor = actors[i % len(actors)]

                history_item = PriceChangeHistory(
                    id=uuid.uuid4(),
                    price_list_version_id=ver.id,
                    entity_type=entity_type,
                    entity_name=f"{ver.price_list_name} ({ver.version_number})",
                    field_name=field_name,
                    old_value=old_val,
                    new_value=new_val,
                    change_reason=f"{reason} (Mã đối tượng: {pl.scope_id})",
                    changed_by=actor,
                    changed_at=base_time + timedelta(days=i * 2, hours=random.randint(1, 8), minutes=random.randint(10, 50)),
                )
                db.add(history_item)
                total_history_count += 1

        print("6. Đang sinh Nhật ký sử dụng (PriceListUsageLog)...")
        total_log_count = 0
        effective_versions = [ver for pl, ver in created_versions_detail if ver.status in ["EFFECTIVE", "APPROVED", "SUPERSEDED"]]

        start_log_date = datetime(2026, 2, 1, 8, 0, 0)
        srv_list = list(service_objects.values())

        for ver in effective_versions:
            logs_to_generate = random.randint(20, 40)
            for i in range(logs_to_generate):
                selected_srv = srv_list[i % len(srv_list)]
                applied_time = start_log_date + timedelta(
                    days=random.randint(0, 150),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )

                log = PriceListUsageLog(
                    id=uuid.uuid4(),
                    price_list_version_id=ver.id,
                    payment_board_id=uuid.uuid4(),
                    service_item_id=selected_srv.id,
                    applied_at=applied_time,
                )
                db.add(log)
                total_log_count += 1

        db.commit()
        print("✅ Hoàn tất Seed dữ liệu thành công!")
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