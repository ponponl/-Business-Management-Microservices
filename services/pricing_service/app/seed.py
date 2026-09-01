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


def seed_rich_data():
    print("1. Đang Drop và Re-create lại toàn bộ Bảng trong Database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("2. Đang khởi tạo danh mục Dịch vụ (SERVICE_ITEM)...")
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

        print("3. Đang khởi tạo Bảng giá gắn với Mã Khách hàng (CUS-xxx) & Mã Hợp đồng (HD-xxx)...")

        staff_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        manager_user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        director_user_id = uuid.UUID("030b4950-4ccf-4437-bf14-5c8debfa3e8d")

        detailed_rejection_reasons = [
            "Đơn giá dịch vụ lưu kho bãi vượt quá định mức chiết khấu cho phép 15% so với chính sách chung.",
            "Thiếu phụ lục hợp đồng cam kết sản lượng tối thiểu đi kèm đối với khách hàng VIP.",
            "Thời gian hiệu lực bảng giá trùng lặp với Bảng giá ưu đãi Q1/2026 đang áp dụng.",
            "Cơ cấu đơn giá bốc xếp container 40ft chưa cập nhật chi phí phụ trội nhiên liệu theo quy định mới.",
        ]

        # Khởi tạo chuẩn xác theo Mã Khách hàng (CUS-xxx) và Mã Hợp đồng (HD-2026-xxx)
        price_lists_raw = [
            ("PL-2026-001", "Bảng giá Áp dụng KH ABC Logistics", "CUSTOMER", "CUS-001", "v3.0", "EFFECTIVE", date(2026, 1, 1), date(2026, 12, 31)),
            ("PL-2026-002", "Bảng giá Hợp đồng HD-2026-001", "CONTRACT", "HD-2026-001", "v1.0", "DRAFT", date(2026, 6, 1), date(2027, 6, 30)),
            ("PL-2026-003", "Bảng giá Khách hàng XYZ Shipping", "CUSTOMER", "CUS-002", "v2.0", "EFFECTIVE", date(2026, 1, 1), date(2026, 12, 31)),
            ("PL-2026-004", "Bảng giá Hợp đồng HD-2026-002 (Điều chỉnh)", "CONTRACT", "HD-2026-002", "v1.0", "REJECTED", date(2026, 6, 1), date(2026, 12, 31)),
            ("PL-2026-005", "Bảng giá Chung - Toàn Cảng Q3", "GENERAL", "GENERAL_ALL", "v2.0", "EFFECTIVE", date(2026, 5, 1), date(2026, 11, 30)),
            ("PL-2026-006", "Bảng giá Khách hàng Tân Cảng Freight", "CUSTOMER", "CUS-003", "v1.0", "SUBMITTED", date(2026, 6, 15), date(2027, 6, 15)),
            ("PL-2026-007", "Bảng giá Hợp đồng HD-2026-003", "CONTRACT", "HD-2026-003", "v4.0", "EFFECTIVE", date(2026, 1, 1), date(2026, 12, 31)),
            ("PL-2026-008", "Bảng giá Ưu đãi KH ABC Logistics Q3", "CUSTOMER", "CUS-001", "v1.0", "DRAFT", date(2026, 7, 1), date(2026, 12, 31)),
            ("PL-2026-009", "Bảng giá Hợp đồng HD-2026-004", "CONTRACT", "HD-2026-004", "v2.0", "SUBMITTED", date(2026, 6, 20), date(2027, 6, 20)),
            ("PL-2026-010", "Bảng giá Niêm yết Kho bãi 2026", "GENERAL", "GENERAL_ALL", "v1.0", "EFFECTIVE", date(2026, 1, 1), date(2026, 12, 31)),
            ("PL-2026-011", "Bảng giá Hợp đồng HD-2026-005", "CONTRACT", "HD-2026-005", "v1.0", "APPROVED", date(2026, 3, 1), date(2026, 12, 31)),
            ("PL-2026-012", "Bảng giá Phụ phí Hạ tải Khách hàng CUS-004", "CUSTOMER", "CUS-004", "v1.0", "DRAFT", date(2026, 7, 20), date(2027, 7, 20)),
        ]

        created_versions = []

        for idx, (code, name, scope_type, scope_id, ver_num, status, valid_from, valid_to) in enumerate(price_lists_raw):
            pl = PriceList(
                id=uuid.uuid4(),
                price_list_code=code,
                price_list_name=name,
                scope_type=scope_type,
                scope_id=scope_id,  # Lưu trực tiếp CUS-xxx hoặc HD-2026-xxx
                description=f"Cấu hình bảng giá {name} cho mã quy định {scope_id}",
                created_by=staff_user_id,
                is_deleted=False,
            )
            db.add(pl)
            db.flush()

            rejection_note = None
            approver_id = None

            if status in ["EFFECTIVE", "SUPERSEDED", "EXPIRED"]:
                stage = "COMPLETED"
                approver_id = director_user_id
            elif status == "APPROVED":
                stage = "APPROVED"
                approver_id = director_user_id
            elif status == "REJECTED":
                stage = "REJECTED"
                approver_id = manager_user_id
                rejection_note = detailed_rejection_reasons[idx % len(detailed_rejection_reasons)]
            elif status == "SUBMITTED":
                stage = "MANAGER_PENDING"
            else:
                stage = "DRAFT"

            ver = PriceListVersion(
                id=uuid.uuid4(),
                price_list_id=pl.id,
                price_list_name=name,
                version_number=ver_num,
                valid_from=valid_from,
                valid_to=valid_to,
                status=status,
                created_by=staff_user_id,
                approved_by=approver_id,
                rejected_reason=rejection_note,
                approval_stage=stage,
            )
            db.add(ver)
            db.flush()
            created_versions.append((pl, ver))

            prices = {
                "SRV-20ft-IN": 350000.00 + (idx * 5000),
                "SRV-WH-GEN": 42000.00 if ver_num == "v3.0" else 45000.00,
                "SRV-PORT-OP": 125000.00,
                "SRV-40ft-OUT": 550000.00 + (idx * 10000),
                "SRV-CUST-CLR": 800000.00,
                "SRV-REEFER-PLUG": 65000.00,
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

        print("4. Đang tạo dữ liệu Lịch sử thay đổi (PriceChangeHistory) cực kỳ phong phú...")
        total_history_count = 0

        field_change_pool = [
            ("price_list_name", "Bảng giá Nháp 2026", "Bảng giá Áp dụng Khách hàng CUS-001", "Cập nhật lại tên gọi chuẩn theo phòng Kinh doanh"),
            ("valid_to", "2026-06-30", "2026-12-31", "Gia hạn thời hạn áp dụng bảng giá theo Hợp đồng bổ sung"),
            ("valid_from", "2026-02-01", "2026-01-01", "Điều chỉnh ngày hiệu lực áp dụng sớm hơn cho Khách hàng"),
            ("unit_price (SRV-20ft-IN)", "300,000 VND", "350,000 VND", "Tăng giá bốc xếp do chi phí nhiên liệu tăng"),
            ("unit_price (SRV-WH-GEN)", "40,000 VND", "42,000 VND", "Điều chỉnh đơn giá lưu kho bãi theo khung giá niêm yết mới"),
            ("unit_price (SRV-40ft-OUT)", "500,000 VND", "550,000 VND", "Tăng giá nâng hạ container 40ft"),
            ("unit_price (SRV-REEFER-PLUG)", "55,000 VND", "65,000 VND", "Tăng đơn giá cắm điện container lạnh"),
            ("status", "DRAFT", "SUBMITTED", "Trình duyệt bảng giá cho Trưởng phòng Kinh doanh"),
            ("status", "SUBMITTED", "APPROVED", "Trưởng phòng Kinh doanh chấp thuận phê duyệt"),
            ("status", "APPROVED", "EFFECTIVE", "Kích hoạt hiệu lực bảng giá trên hệ thống"),
            ("status", "SUBMITTED", "REJECTED", "Từ chối do đơn giá chiết khấu chưa phù hợp"),
            ("status", "REJECTED", "DRAFT", "Trả về trạng thái Nháp để chuyên viên điều chỉnh lại đơn giá"),
        ]

        actors = [staff_user_id, manager_user_id, director_user_id]

        for pl, ver in created_versions:
            # Tạo ngẫu nhiên từ 8 đến 15 bản ghi Lịch sử cho MỖI Bảng giá
            history_entries_count = random.randint(8, 15)
            base_time = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)

            for i in range(history_entries_count):
                field_name, old_val, new_val, reason = field_change_pool[i % len(field_change_pool)]
                actor = actors[i % len(actors)]
                
                history_item = PriceChangeHistory(
                    id=uuid.uuid4(),
                    price_list_version_id=ver.id,
                    entity_type="PRICE_LIST_VERSION" if "unit_price" not in field_name else "PRICE_LIST_DETAIL",
                    entity_name=ver.price_list_name,
                    field_name=field_name,
                    old_value=old_val,
                    new_value=new_val,
                    change_reason=f"{reason} (Mã đối tượng: {pl.scope_id})",
                    changed_by=actor,
                    changed_at=base_time + timedelta(days=i * 2, hours=random.randint(1, 10), minutes=random.randint(0, 59)),
                )
                db.add(history_item)
                total_history_count += 1

        print("5. Đang sinh dữ liệu Nhật ký sử dụng (PriceListUsageLog) siêu nhiều phục vụ UI/UX Audit Log...")
        total_log_count = 0
        effective_versions = [ver for pl, ver in created_versions if ver.status in ["EFFECTIVE", "APPROVED"]]

        start_log_date = datetime(2026, 4, 1, 7, 0, 0)
        srv_list = list(service_objects.values())

        for ver in effective_versions:
            # Sinh 40 - 60 lượt áp dụng bảng giá cho mỗi bảng giá EFFECTIVE/APPROVED
            logs_to_generate = random.randint(40, 60)
            
            for i in range(logs_to_generate):
                selected_srv = srv_list[i % len(srv_list)]
                applied_time = start_log_date + timedelta(
                    days=random.randint(0, 120),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
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
        print(f"✅ Hoàn tất Seed dữ liệu thành công!")
        print(f"   👉 Mã Khách hàng: CUS-001, CUS-002, CUS-003, CUS-004")
        print(f"   👉 Mã Hợp đồng: HD-2026-001 đến HD-2026-005")
        print(f"   👉 Lịch sử thay đổi (PriceChangeHistory): {total_history_count} bản ghi")
        print(f"   👉 Nhật ký sử dụng (PriceListUsageLog): {total_log_count} bản ghi")

    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi seed dữ liệu: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_rich_data()