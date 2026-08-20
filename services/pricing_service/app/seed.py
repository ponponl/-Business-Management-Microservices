import uuid
from datetime import date, datetime

from app.db.session import SessionLocal, engine, Base

import app.models.pricing 
from app.models.pricing import (
    ServiceItem,
    PriceList,
    PriceListVersion,
    PriceListDetail,
    PriceChangeHistory,
    PriceListUsageLog,
)


def seed_rich_data():
    print("1. Đang Drop và Re-create lại toàn bộ Bảng trong Database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("2. Đang khởi tạo danh mục Dịch vụ (SERVICE_ITEM)...")
        services_data = [
            ("SRV-20ft-IN", "Bốc xếp container 20ft (Hàng nhập)", "Container"),
            ("SRV-WH-GEN", "Lưu kho bãi tổng hợp", "Ngày/Tấn"),
            ("SRV-PORT-OP", "Khai thác bến bãi hạ tải", "Lượt xe"),
            ("SRV-40ft-OUT", "Bốc xếp container 40ft (Hàng xuất)", "Container"),
            ("SRV-CUST-CLR", "Khai báo hải quan trọn gói", "Tờ khai"),
        ]

        service_objects = {}
        for code, name, unit in services_data:
            item = ServiceItem(
                id=uuid.uuid4(),
                service_code=code,
                service_name=name,
                unit=unit,
                status="ACTIVE"
            )
            db.add(item)
            service_objects[code] = item
        db.flush()

        print("3. Đang khởi tạo Bảng giá và các Phiên bản...")
        dummy_user_id = uuid.uuid4()

        price_lists_raw = [
            ("PL-2026-001", "Cảng Cát Lái", "CUSTOMER", "v3.0", "SUBMITTED", date(2026, 1, 1), date(2026, 12, 31)),
            ("PL-2026-002", "Công ty CP XNK Đại Dương", "CONTRACT", "v1.0", "DRAFT", date(2026, 6, 1), date(2027, 6, 30)),
            ("PL-2026-003", "Cảng Cái Mép Thượng", "GENERAL", "v2.1", "EFFECTIVE", date(2026, 6, 1), date(2026, 12, 31)),
            ("PL-2026-004", "Cty TNHH Vận tải Phương Nam", "CUSTOMER", "v1.2", "REJECTED", date(2026, 6, 1), date(2026, 12, 31)),
            ("PL-2026-005", "Cảng Cát Lái", "CUSTOMER", "v2.0", "EFFECTIVE", date(2026, 5, 1), date(2026, 11, 30)),
            ("PL-2026-006", "Tập đoàn Hòa Phát", "SERVICE_GROUP", "v1.0", "SUBMITTED", date(2026, 6, 15), date(2027, 6, 15)),
            ("PL-2026-007", "Kho vận Gemadept", "SERVICE_TYPE", "v4.2", "EFFECTIVE", date(2026, 1, 1), date(2026, 12, 31)),
            ("PL-2026-008", "Logistics TTC", "CUSTOMER", "v1.1", "DRAFT", date(2026, 7, 1), date(2026, 12, 31)),
            ("PL-2026-009", "Cảng Quốc Tế Tân Cảng", "CONTRACT", "v2.0", "SUBMITTED", date(2026, 6, 20), date(2027, 6, 20)),
            ("PL-2026-010", "Tổng kho Vĩnh Long", "GENERAL", "v1.0", "EFFECTIVE", date(2026, 1, 1), date(2026, 12, 31)),
            ("PL-2026-011", "Vận Tải Phương Hoàng", "CUSTOMER", "v1.3", "REJECTED", date(2026, 3, 1), date(2026, 12, 31)),
            ("PL-2026-012", "Bảng giá bốc xếp hạ tải nội địa 2026", "CUSTOMER", "v1.0", "DRAFT", date(2026, 7, 20), date(2027, 7, 20)),
            ("PL-2026-013", "Kho lạnh Tân Tạo - Khách mới", "CUSTOMER", "v1.0", "DRAFT", date(2026, 8, 1), date(2026, 12, 31)),
            ("PL-2026-014", "Dịch vụ Hải quan Tân Cảng Quý 3", "SERVICE_TYPE", "v1.0", "DRAFT", date(2026, 9, 1), date(2026, 12, 31)),
            ("PL-2026-015", "Hợp đồng nguyên tắc Vinalines", "CONTRACT", "v0.1", "DRAFT", date(2026, 8, 15), date(2027, 8, 15)),
        ]

        for code, name, scope_type, ver_str, status, valid_from, valid_to in price_lists_raw:
            pl = PriceList(
                id=uuid.uuid4(),
                price_list_code=code,
                price_list_name=name,
                customer_id=uuid.uuid4(),
                contract_id=uuid.uuid4(),
                scope_type=scope_type,
                scope_id="SCOPE-" + code,
                description=f"Cấu hình bảng giá cho {name}",
                created_by=dummy_user_id,
                is_deleted=False
            )
            db.add(pl)
            db.flush()

            try:
                ver_num = int(ver_str.replace("v", "").split(".")[0])
            except Exception:
                ver_num = 1

            ver = PriceListVersion(
                id=uuid.uuid4(),
                price_list_id=pl.id,
                version_number=ver_num,
                valid_from=valid_from,
                valid_to=valid_to,
                status=status,
                created_by=dummy_user_id,
                approval_stage="COMPLETED" if status == "EFFECTIVE" else "MANAGER_PENDING"
            )
            db.add(ver)
            db.flush()

            prices = {
                "SRV-20ft-IN": 350000.00,
                "SRV-WH-GEN": 42000.00 if ver_str == "v3.0" else 45000.00,
                "SRV-PORT-OP": 125000.00 if ver_str == "v3.0" else 120000.00,
                "SRV-40ft-OUT": 550000.00,
                "SRV-CUST-CLR": 800000.00
            }

            for srv_code, price_val in prices.items():
                detail = PriceListDetail(
                    id=uuid.uuid4(),
                    price_list_id=pl.id,
                    price_list_version_id=ver.id,
                    service_item_id=service_objects[srv_code].id,
                    unit_price=price_val
                )
                db.add(detail)

            if code == "PL-2026-001":
                history_1 = PriceChangeHistory(
                    id=uuid.uuid4(),
                    price_list_version_id=ver.id,
                    field_name="price_list_name",
                    old_value="Bảng giá bốc xếp 2026",
                    new_value="Bảng giá bốc hạ tải nội địa 2027",
                    change_reason="Cập nhật tên gọi chuẩn danh mục năm mới",
                    changed_by=dummy_user_id,
                    changed_at=datetime(2026, 7, 20, 9, 12)
                )
                history_2 = PriceChangeHistory(
                    id=uuid.uuid4(),
                    price_list_version_id=ver.id,
                    field_name="SRV-20ft-IN",
                    old_value="350.000 VND",
                    new_value="360.000 VND",
                    change_reason="Trượt giá nhiên liệu nâng hạ bến cảng",
                    changed_by=dummy_user_id,
                    changed_at=datetime(2026, 7, 20, 9, 15)
                )
                db.add_all([history_1, history_2])

                for _ in range(4):
                    log = PriceListUsageLog(
                        id=uuid.uuid4(),
                        price_list_version_id=ver.id,
                        billing_statement_id=uuid.uuid4(),
                        service_item_id=service_objects["SRV-20ft-IN"].id,
                        applied_at=datetime.utcnow()
                    )
                    db.add(log)

        db.commit()
        print("Tạo thành công dữ liệu mẫu cực kỳ phong phú bao gồm các bản ghi DRAFT!")

    except Exception as e:
        db.rollback()
        print(f"Lỗi khi seed dữ liệu: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_rich_data()